use super::ViewBox;
use crate::map::background_image::{MAP_IMAGE_PALETTE, MAP_IMAGE_PALETTE_TRANSPARENCY};
use base64::{Engine as _, engine::general_purpose};
use png::{BitDepth, ColorType, Compression, Encoder};
use std::error::Error;
use std::fmt;

pub const MAX_RASTER_DIMENSION: u16 = 800;
pub const MAX_RASTER_PIXELS: usize = 640_000;
/// Y1 Pro confirmed wire format: 5 cm cells. Anything else rejected.
pub const NATIVE_RESOLUTION_CM: u8 = 5;
/// Max plausible raw LZ4 input for 640000-byte output: compress_bound(640000)
/// = 640000 + 640000/255 + 16 = 642526, plus small margin.
pub const MAX_LZ4_COMPRESSED_BYTES: usize = 643_000;
/// Base64 expansion of the above: ceil(643000/3)*4 = 857336, plus margin.
pub const MAX_BASE64_LEN: usize = 860_000;

#[derive(Debug)]
pub enum NativeRasterError {
    ZeroDimension,
    DimensionOutOfBounds(u16, u16),
    PixelCountOutOfBounds(usize),
    ZeroResolution,
    UnsupportedResolution(u8),
    ExtentOverflow(String),
    Base64TooLarge(usize),
    CompressedTooLarge(usize),
    Base64(base64::DecodeError),
    Decompress(String),
    PngEncode(png::EncodingError),
}

impl fmt::Display for NativeRasterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NativeRasterError::ZeroDimension => write!(f, "Raster dimensions must be > 0"),
            NativeRasterError::DimensionOutOfBounds(w, h) => {
                write!(
                    f,
                    "Raster dimensions ({w}x{h}) exceed maximum {MAX_RASTER_DIMENSION}"
                )
            }
            NativeRasterError::PixelCountOutOfBounds(count) => {
                write!(
                    f,
                    "Raster pixel count {count} exceeds maximum {MAX_RASTER_PIXELS}"
                )
            }
            NativeRasterError::ZeroResolution => write!(f, "Resolution must be > 0"),
            NativeRasterError::UnsupportedResolution(r) => write!(
                f,
                "Unsupported resolution {r} cm: Y1 native format is {NATIVE_RESOLUTION_CM} cm"
            ),
            NativeRasterError::ExtentOverflow(detail) => {
                write!(f, "Native raster extents overflow i16 canvas: {detail}")
            }
            NativeRasterError::Base64TooLarge(len) => write!(
                f,
                "Base64 payload length {len} exceeds maximum {MAX_BASE64_LEN}"
            ),
            NativeRasterError::CompressedTooLarge(len) => write!(
                f,
                "LZ4 payload length {len} exceeds maximum {MAX_LZ4_COMPRESSED_BYTES}"
            ),
            NativeRasterError::Base64(err) => write!(f, "Base64 decode failed: {err}"),
            NativeRasterError::Decompress(err) => write!(f, "LZ4 decompression failed: {err}"),
            NativeRasterError::PngEncode(err) => write!(f, "PNG encoding failed: {err}"),
        }
    }
}

impl Error for NativeRasterError {}

pub fn decode_native_raster(
    base64_lz4: &str,
    width: u16,
    height: u16,
    resolution: u8,
) -> Result<Vec<u8>, NativeRasterError> {
    if width == 0 || height == 0 {
        return Err(NativeRasterError::ZeroDimension);
    }
    if width > MAX_RASTER_DIMENSION || height > MAX_RASTER_DIMENSION {
        return Err(NativeRasterError::DimensionOutOfBounds(width, height));
    }
    let expected_len = (width as usize) * (height as usize);
    if expected_len > MAX_RASTER_PIXELS {
        return Err(NativeRasterError::PixelCountOutOfBounds(expected_len));
    }
    if resolution == 0 {
        return Err(NativeRasterError::ZeroResolution);
    }
    if resolution != NATIVE_RESOLUTION_CM {
        return Err(NativeRasterError::UnsupportedResolution(resolution));
    }

    let trimmed = base64_lz4.trim();
    if trimmed.len() > MAX_BASE64_LEN {
        return Err(NativeRasterError::Base64TooLarge(trimmed.len()));
    }
    let compressed = general_purpose::STANDARD
        .decode(trimmed)
        .map_err(NativeRasterError::Base64)?;
    if compressed.len() > MAX_LZ4_COMPRESSED_BYTES {
        return Err(NativeRasterError::CompressedTooLarge(compressed.len()));
    }

    let pixels = crate::util::decompress_lz4_block(&compressed, expected_len)
        .map_err(|err| NativeRasterError::Decompress(err.to_string()))?;

    Ok(pixels)
}

/// Validate 800-canvas extents before any mutation. Checked i16 math only:
/// no panic, no wrap. Call before decode so extreme x_min/y_max fail fast.
pub fn validate_native_extents(
    x_min: i16,
    y_max: i16,
    width: u16,
    height: u16,
) -> Result<ViewBox, NativeRasterError> {
    if width == 0 || height == 0 {
        return Err(NativeRasterError::ZeroDimension);
    }
    if width > MAX_RASTER_DIMENSION || height > MAX_RASTER_DIMENSION {
        return Err(NativeRasterError::DimensionOutOfBounds(width, height));
    }
    let offset = super::MAP_OFFSET;
    let min_x = x_min.checked_sub(offset).ok_or_else(|| {
        NativeRasterError::ExtentOverflow(format!("x_min {x_min} minus offset {offset}"))
    })?;
    let y_min = y_max
        .checked_sub(height as i16)
        .and_then(|v| v.checked_add(1))
        .ok_or_else(|| {
            NativeRasterError::ExtentOverflow(format!("y_max {y_max} minus height {height} plus 1"))
        })?;
    let min_y = y_min.checked_sub(offset).ok_or_else(|| {
        NativeRasterError::ExtentOverflow(format!("y_min {y_min} minus offset {offset}"))
    })?;
    let max_x = min_x.checked_add(width as i16).ok_or_else(|| {
        NativeRasterError::ExtentOverflow(format!("min_x {min_x} plus width {width}"))
    })?;
    let max_y = min_y.checked_add(height as i16).ok_or_else(|| {
        NativeRasterError::ExtentOverflow(format!("min_y {min_y} plus height {height}"))
    })?;
    Ok(ViewBox {
        min_x: i32::from(min_x),
        min_y: i32::from(min_y),
        max_x: i32::from(max_x),
        max_y: i32::from(max_y),
        width,
        height,
    })
}

#[inline]
pub fn map_native_pixel_to_palette(pixel: u8) -> u8 {
    match pixel {
        0x00 => 1,
        0x7f => 0,
        0xff => 2,
        id @ 1..=0x7e => (id - 1) % 6 + 6,
        _ => 0,
    }
}

pub fn encode_native_png(
    pixels: &[u8],
    width: u16,
    height: u16,
) -> Result<String, NativeRasterError> {
    let mapped_pixels: Vec<u8> = pixels
        .iter()
        .map(|&p| map_native_pixel_to_palette(p))
        .collect();

    let mut png_data = Vec::new();
    {
        let mut encoder = Encoder::new(&mut png_data, width as u32, height as u32);
        encoder.set_compression(Compression::Balanced);
        encoder.set_color(ColorType::Indexed);
        encoder.set_depth(BitDepth::Eight);
        encoder.set_palette(MAP_IMAGE_PALETTE);
        encoder.set_trns(MAP_IMAGE_PALETTE_TRANSPARENCY.as_ref());

        let mut writer = encoder
            .write_header()
            .map_err(NativeRasterError::PngEncode)?;
        writer
            .write_image_data(&mapped_pixels)
            .map_err(NativeRasterError::PngEncode)?;
    }

    Ok(general_purpose::STANDARD.encode(&png_data))
}

#[derive(Clone, PartialEq, Debug)]
pub struct CachedNativeRaster {
    pub width: u16,
    pub height: u16,
    pub x_min: i16,
    pub y_max: i16,
    pub resolution: u8,
    pub pixels: Vec<u8>,
    pub png_base64: String,
    pub view_box: ViewBox,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn compress_raw_lz4(input: &[u8]) -> String {
        let compressed = lz4_flex::compress(input);
        general_purpose::STANDARD.encode(&compressed)
    }

    #[test]
    fn test_decode_native_raster_asymmetric() {
        // 5 columns x 3 rows = 15 pixels
        // Row 0: [Wall(0xff), Floor(0x00), Floor(0x00), Floor(0x00), Room1(0x01)]
        // Row 1: [Floor(0x00), Floor(0x00), Floor(0x00), Floor(0x00), Floor(0x00)]
        // Row 2: [Room2(0x02), Floor(0x00), Floor(0x00), Floor(0x00), Room3(0x03)]
        let raw_pixels: Vec<u8> = vec![
            0xff, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00,
            0x03,
        ];
        let b64_lz4 = compress_raw_lz4(&raw_pixels);

        let decoded = decode_native_raster(&b64_lz4, 5, 3, 5).unwrap();
        assert_eq!(decoded, raw_pixels);

        let png_b64 = encode_native_png(&decoded, 5, 3).unwrap();
        assert!(!png_b64.is_empty());

        let view_box = ViewBox::from_native_bounds(120, 230, 5, 3);
        assert_eq!(view_box.min_x, -280);
        assert_eq!(view_box.min_y, 230 - 3 + 1 - 400); // 228 - 400 = -172
        assert_eq!(view_box.width, 5);
        assert_eq!(view_box.height, 3);
    }

    #[test]
    fn test_decode_native_raster_zero_dimensions() {
        let err_w = decode_native_raster("AA==", 0, 10, 5).unwrap_err();
        assert!(matches!(err_w, NativeRasterError::ZeroDimension));

        let err_h = decode_native_raster("AA==", 10, 0, 5).unwrap_err();
        assert!(matches!(err_h, NativeRasterError::ZeroDimension));
    }

    #[test]
    fn test_decode_native_raster_dimension_out_of_bounds() {
        let err = decode_native_raster("AA==", 801, 10, 5).unwrap_err();
        assert!(matches!(
            err,
            NativeRasterError::DimensionOutOfBounds(801, 10)
        ));
    }

    #[test]
    fn test_decode_native_raster_zero_resolution() {
        let err = decode_native_raster("AA==", 10, 10, 0).unwrap_err();
        assert!(matches!(err, NativeRasterError::ZeroResolution));
    }

    #[test]
    fn test_decode_native_raster_rejects_non_5cm_resolution() {
        let raw = vec![0u8; 4];
        let b64 = compress_raw_lz4(&raw);
        let err = decode_native_raster(&b64, 2, 2, 10).unwrap_err();
        assert!(matches!(err, NativeRasterError::UnsupportedResolution(10)));
        let err = decode_native_raster(&b64, 2, 2, 1).unwrap_err();
        assert!(matches!(err, NativeRasterError::UnsupportedResolution(1)));
    }

    #[test]
    fn test_validate_extents_negative_ok() {
        let vb = validate_native_extents(-1000, 500, 5, 3).unwrap();
        assert_eq!(vb.min_x, -1400);
        assert_eq!(vb.min_y, 500 - 3 + 1 - 400);
    }

    #[test]
    fn test_validate_extents_extreme_no_panic() {
        let err = validate_native_extents(i16::MIN, 0, 800, 800).unwrap_err();
        assert!(matches!(err, NativeRasterError::ExtentOverflow(_)));
        let err = validate_native_extents(0, i16::MIN, 800, 800).unwrap_err();
        assert!(matches!(err, NativeRasterError::ExtentOverflow(_)));
    }

    #[test]
    fn test_validate_extents_outside_canvas_no_panic() {
        let err = validate_native_extents(32767, 0, 800, 800).unwrap_err();
        assert!(matches!(err, NativeRasterError::ExtentOverflow(_)));
        let err = validate_native_extents(32500, 100, 800, 800).unwrap_err();
        assert!(matches!(err, NativeRasterError::ExtentOverflow(_)));
    }

    #[test]
    fn test_decode_native_raster_base64_too_large() {
        let huge = "QUJD".repeat(MAX_BASE64_LEN + 4);
        let err = decode_native_raster(&huge, 5, 3, 5).unwrap_err();
        assert!(matches!(err, NativeRasterError::Base64TooLarge(_)));
    }

    #[test]
    fn test_decode_native_raster_compressed_too_large() {
        let raw = vec![0xabu8; MAX_LZ4_COMPRESSED_BYTES + 1000];
        let b64 = general_purpose::STANDARD.encode(&raw);
        assert!(b64.len() <= MAX_BASE64_LEN);
        let err = decode_native_raster(&b64, 800, 800, 5).unwrap_err();
        assert!(matches!(err, NativeRasterError::CompressedTooLarge(_)));
    }

    #[test]
    fn test_decode_native_raster_truncated_stream() {
        let raw_pixels = vec![0u8; 100];
        let full_compressed = compress_raw_lz4(&raw_pixels);
        let decoded_bytes = general_purpose::STANDARD.decode(&full_compressed).unwrap();
        let truncated = general_purpose::STANDARD.encode(&decoded_bytes[..decoded_bytes.len() / 2]);

        let err = decode_native_raster(&truncated, 10, 10, 5).unwrap_err();
        assert!(matches!(err, NativeRasterError::Decompress(_)));
    }

    #[test]
    fn test_decode_native_raster_size_mismatch() {
        let raw_pixels = vec![0u8; 50];
        let b64_lz4 = compress_raw_lz4(&raw_pixels);

        let err = decode_native_raster(&b64_lz4, 10, 10, 5).unwrap_err();
        assert!(matches!(err, NativeRasterError::Decompress(_)));
    }

    #[test]
    fn test_palette_mapping() {
        assert_eq!(map_native_pixel_to_palette(0x00), 1);
        assert_eq!(map_native_pixel_to_palette(0x7f), 0);
        assert_eq!(map_native_pixel_to_palette(0xff), 2);
        assert_eq!(map_native_pixel_to_palette(0x01), 6);
        assert_eq!(map_native_pixel_to_palette(0x02), 7);
        assert_eq!(map_native_pixel_to_palette(0x03), 8);
        assert_eq!(map_native_pixel_to_palette(0x04), 9);
        assert_eq!(map_native_pixel_to_palette(0x05), 10);
        assert_eq!(map_native_pixel_to_palette(0x06), 11);
        assert_eq!(map_native_pixel_to_palette(0x07), 6); // modulo 6 wrap
        assert_eq!(map_native_pixel_to_palette(0x80), 0);
    }
}
