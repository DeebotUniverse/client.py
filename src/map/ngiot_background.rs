use super::ImageGenrationType;
use pyo3::prelude::*;

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
        // Phase 4A plumbing only.
        // Phase 4B will decode NGIOT mapData.data into a real raster image here.
        Ok(None)
    }
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