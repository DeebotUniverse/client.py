use super::{ImageGenrationType, ViewBox};
use crate::util::decompress_base64_lz4_data;
use base64::Engine;
use base64::engine::general_purpose;
use log::debug;
use png::{BitDepth, ColorType, Compression, Encoder};
use pyo3::prelude::*;

const WORLD_PIXEL_WIDTH: f32 = 50.0;

#[derive(Debug, Clone, PartialEq, Eq)]
struct NgiotBackgroundData {
    encoded: String,
    width: u16,
    height: u16,
    total_width: u16,
    total_height: u16,
    resolution: i32,
    x_min: i32,
    y_max: i32,
}

#[pyclass]
pub(super) struct NgiotBackground {
    data: Option<NgiotBackgroundData>,
}

impl NgiotBackground {
    pub(super) fn new() -> Self {
        Self { data: None }
    }

    pub(super) fn generate(&self) -> Result<ImageGenrationType, Box<dyn std::error::Error>> {
        let Some(data) = self.data.as_ref() else {
            return Ok(None);
        };

        let expected_len = usize::from(data.width) * usize::from(data.height);
        if expected_len == 0 {
            return Ok(None);
        }

        let raster = decompress_base64_lz4_data(&data.encoded, expected_len)?;
        if raster.len() != expected_len {
            return Err(format!(
                "NGIOT raster size mismatch: expected {}, got {}",
                expected_len,
                raster.len()
            )
            .into());
        }

        let mut png_data = Vec::new();
        {
            let mut encoder = Encoder::new(&mut png_data, u32::from(data.width), u32::from(data.height));
            encoder.set_compression(Compression::Balanced);
            encoder.set_color(ColorType::Rgba);
            encoder.set_depth(BitDepth::Eight);

            let mut writer = encoder.write_header()?;
            let rgba = raster_to_rgba(&raster);
            writer.write_image_data(&rgba)?;
        }

        let left = data.x_min as f32 / WORLD_PIXEL_WIDTH;
        let top = -(data.y_max as f32) / WORLD_PIXEL_WIDTH;
        let width_svg = (f32::from(data.width) * data.resolution as f32) / WORLD_PIXEL_WIDTH;
        let height_svg = (f32::from(data.height) * data.resolution as f32) / WORLD_PIXEL_WIDTH;

        let viewbox = ViewBox::from_extents(left, top, left + width_svg, top + height_svg);

        debug!(
            "Generated NGIOT raster background: map {}x{} at world ({}, {}) size ({}, {})",
            data.width, data.height, left, top, width_svg, height_svg
        );

        Ok(Some((general_purpose::STANDARD.encode(&png_data), viewbox)))
    }
}

#[inline]
fn rgba_for_value(value: u8) -> [u8; 4] {
    match value {
        127 => [255, 255, 255, 0],     // transparent / outside map
        1 => [237, 237, 237, 255],     // light floor
        0 => [210, 210, 210, 255],     // alternate floor / unknown floor
        2 => [20, 20, 20, 255],        // dark occupied / blocked region
        3 => [83, 132, 178, 255],      // observed alternate class
        4 => [165, 92, 47, 255],       // observed alternate class
        255 => [220, 30, 30, 255],     // marker / sentinel
        _ => [255, 0, 255, 255],       // unknown class => magenta for visibility
    }
}

fn raster_to_rgba(raster: &[u8]) -> Vec<u8> {
    let mut rgba = Vec::with_capacity(raster.len() * 4);
    for &value in raster {
        rgba.extend_from_slice(&rgba_for_value(value));
    }
    rgba
}

#[pymethods]
impl NgiotBackground {
    fn set_map_data(
        &mut self,
        encoded: String,
        width: u16,
        height: u16,
        total_width: u16,
        total_height: u16,
        resolution: i32,
        x_min: i32,
        y_max: i32,
    ) -> bool {
        let new_data = NgiotBackgroundData {
            encoded,
            width,
            height,
            total_width,
            total_height,
            resolution,
            x_min,
            y_max,
        };

        if self.data.as_ref() == Some(&new_data) {
            return false;
        }

        self.data = Some(new_data);
        true
    }

    fn clear(&mut self) -> bool {
        if self.data.is_none() {
            return false;
        }
        self.data = None;
        true
    }

    fn has_data(&self) -> bool {
        self.data.is_some()
    }
}