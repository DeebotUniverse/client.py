use super::{ImageGenrationType, ViewBox, decompress_base64_data};
use base64::Engine;
use base64::engine::general_purpose;
use crc32fast::Hasher;
use image::{GenericImageView, GrayImage, Luma};
use log::{debug, error};
use png::{BitDepth, ColorType, Compression, Encoder};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const NOT_INUSE_CRC32: u32 = 1295764014;
const MAP_TRANSPARENT_INDEX: u8 = 0;

// when updating palette, update MAP_IMAGE_PALETTE_LEN and MAP_IMAGE_PALETTE_TRANSPARENCY
const MAP_IMAGE_PALETTE: &[u8] = &[
    0x00, 0x00, 0x00, // Transparent
    0xba, 0xda, 0xff, // Floor
    0x4e, 0x96, 0xe2, // Wall
    0x1a, 0x81, 0xed, // Carpet
    0xde, 0xe9, 0xfb, // Not scanned space
    0xed, 0xf3, 0xfb, // Possible obstacle
    0xa2, 0xbc, 0xe7, // Room color 0
    0xec, 0xd0, 0x99, // Room color 1
    0x9b, 0xd4, 0xda, // Room color 2
    0xec, 0xc6, 0xc9, // Room color 3
    0xd7, 0xbc, 0xe3, // Room color 4
    0xc3, 0xe2, 0xb6, // Room color 5
];
const MAP_IMAGE_PALETTE_WITHOUT_ROOMS_LEN: u8 = 6;
const MAP_IMAGE_PALETTE_ROOMS_LEN: u8 = 6;
// 0 -> Transparent, 255 -> Fully opaque
// (first entry is transparent, rest opaque)
const MAP_IMAGE_PALETTE_TRANSPARENCY: &[u8] =
    &[0u8, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255];

const MAP_PIECE_SIZE: u16 = 100;
pub(super) const MAP_MAX_SIZE: u16 = 8 * MAP_PIECE_SIZE;

#[pyclass]
pub(super) struct BackgroundImage {
    map_pieces: [MapPiece; 64],
}

impl BackgroundImage {
    pub(super) fn new() -> Self {
        BackgroundImage {
            map_pieces: core::array::from_fn(|_| MapPiece::new()),
        }
    }

    pub(super) fn generate(&self) -> Result<ImageGenrationType, Box<dyn std::error::Error>> {
        let mut image = GrayImage::new(MAP_MAX_SIZE.into(), MAP_MAX_SIZE.into());
        let mut min_x = u16::MAX;
        let mut min_y = u16::MAX;
        let mut max_x = 0u16;
        let mut max_y = 0u16;

        for (i, piece) in self.map_pieces.iter().enumerate() {
            // Order of the pieces is from bottom-left to top-right (column by column)
            let piece_x = (i as u16 / 8) * MAP_PIECE_SIZE;
            let piece_y = MAP_MAX_SIZE - (((i as u16 % 8) + 1) * MAP_PIECE_SIZE);

            if let Some(pixels) = piece.pixels_indexed() {
                debug!("Adding piece at {i} ({piece_x}, {piece_y})");
                for (j, &pixel_idx) in pixels.iter().enumerate() {
                    // Order of the pixels is from top-left to bottom-right (row by row)

                    // Check if the pixel is not fully transparent (alpha > 0)
                    if pixel_idx != MAP_TRANSPARENT_INDEX {
                        let pixel_x = j as u16 % MAP_PIECE_SIZE;
                        let pixel_y = j as u16 / MAP_PIECE_SIZE;

                        // We need to rotate the image 90 degrees counterclockwise
                        let new_x = piece_x + pixel_y;
                        let new_y = piece_y + MAP_PIECE_SIZE - 1 - pixel_x;

                        // Newer bots will return a different pixel index per room
                        // mapping all to the floor color
                        let pixel = if pixel_idx > MAP_IMAGE_PALETTE_WITHOUT_ROOMS_LEN {
                            (pixel_idx % MAP_IMAGE_PALETTE_ROOMS_LEN)
                                + MAP_IMAGE_PALETTE_WITHOUT_ROOMS_LEN
                        } else {
                            pixel_idx
                        };

                        image.put_pixel(new_x.into(), new_y.into(), Luma([pixel]));
                        min_x = min_x.min(new_x);
                        min_y = min_y.min(new_y);
                        max_x = max_x.max(new_x);
                        max_y = max_y.max(new_y);
                    }
                }
            }
        }
        if min_x == u16::MAX || min_y == u16::MAX || max_x == 0 || max_y == 0 {
            return Ok(None);
        }

        let view_box = ViewBox::new(min_x, min_y, max_x, max_y);

        debug!("Image bounding box: {view_box:?}");

        // Crop the image to the actual size
        image = image
            .view(
                min_x.into(),
                min_y.into(),
                view_box.width.into(),
                view_box.height.into(),
            )
            .to_image();

        // Convert the image to PNG format in memory and encode it as base64
        let mut png_data = Vec::new();
        {
            let mut encoder = Encoder::new(&mut png_data, image.width(), image.height());

            encoder.set_compression(Compression::Balanced);
            encoder.set_color(ColorType::Indexed);
            encoder.set_depth(BitDepth::Eight);
            encoder.set_palette(MAP_IMAGE_PALETTE.as_ref());
            encoder.set_trns(MAP_IMAGE_PALETTE_TRANSPARENCY.as_ref());

            let mut writer = encoder.write_header().unwrap();
            writer.write_image_data(image.as_ref()).unwrap();
        }

        Ok(Some((
            general_purpose::STANDARD.encode(&png_data),
            view_box,
        )))
    }
}

#[pymethods]
impl BackgroundImage {
    fn update_map_piece(&mut self, index: usize, base64_data: String) -> Result<bool, PyErr> {
        if index >= self.map_pieces.len() {
            error!("Index out of bounds; index:{index}, base64_data:{base64_data}");
            return Err(PyValueError::new_err("Index out of bounds"));
        }
        self.map_pieces[index]
            .update_points(&base64_data)
            .map_err(|err| {
                error!(
                    "Failed to update map piece: {err}; index:{index}, base64_data:{base64_data}",
                );
                PyValueError::new_err(err.to_string())
            })
    }

    fn map_piece_crc32_indicates_update(
        &mut self,
        index: usize,
        crc32: u32,
    ) -> Result<bool, PyErr> {
        if index >= self.map_pieces.len() {
            error!("Index out of bounds; index:{index}, crc32:{crc32}");
            return Err(PyValueError::new_err("Index out of bounds"));
        }
        Ok(self.map_pieces[index].crc32_indicates_update(crc32))
    }
}

struct MapPiece {
    crc32: u32,
    pixels_indexed: Option<Vec<u8>>,
}

impl MapPiece {
    fn new() -> Self {
        MapPiece {
            crc32: NOT_INUSE_CRC32,
            pixels_indexed: None,
        }
    }

    fn crc32_indicates_update(&mut self, crc32: u32) -> bool {
        if crc32 == NOT_INUSE_CRC32 {
            self.crc32 = crc32;
            self.pixels_indexed = None;
            return false;
        }
        self.crc32 != crc32
    }

    fn in_use(&self) -> bool {
        self.crc32 != NOT_INUSE_CRC32
    }

    fn pixels_indexed(&self) -> Option<&[u8]> {
        self.pixels_indexed.as_deref()
    }

    fn update_points(&mut self, base64_data: &str) -> Result<bool, Box<dyn std::error::Error>> {
        let decoded = decompress_base64_data(base64_data)?;
        let mut hasher = Hasher::new();
        hasher.update(&decoded);
        let new_crc = hasher.finalize();

        if self.crc32 == new_crc {
            // No change in data, return false
            return Ok(false);
        }

        self.crc32 = new_crc;
        if self.in_use() {
            self.pixels_indexed = Some(decoded);
        } else {
            self.pixels_indexed = None;
        }
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_update_map_piece_of_empty_piece() {
        let data = "XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6PAFLsX7Jhrz0KgA=";
        let mut map_piece = MapPiece {
            crc32: 0,
            pixels_indexed: None,
        };
        assert!(map_piece.update_points(data).unwrap());
        assert_eq!(map_piece.crc32, NOT_INUSE_CRC32);
        assert!(map_piece.pixels_indexed.is_none());
        assert!(!map_piece.update_points(data).unwrap());
    }
}
