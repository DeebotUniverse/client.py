use std::fmt::Write as FmtWrite;

use super::{PIXEL_WIDTH, ROUND_TO_DIGITS, RotationAngle, calc_point, common::round};
use crate::util::{decompress_base64_data, decompress_base64_lz4_data};
use log::error;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::error::Error;
use svg::node::element::Path;

const LEGACY_TRACE_SCALE: f32 = 0.2;

#[derive(PartialEq)]
enum SvgPathCommand {
    // To means absolute, by means relative
    MoveTo,
    MoveBy,
    LineBy,
    HorizontalLineBy,
    VerticalLineBy,
}

#[derive(Debug, PartialEq)]
pub(super) struct Point {
    pub x: f32,
    pub y: f32,
    pub connected: bool,
}

pub(super) fn points_to_svg_path(
    points: &[Point],
    close_path: bool,
    force_connected: bool,
) -> Option<Path> {
    // Until https://github.com/bodoni/svg/issues/68 is not implemented
    // we need to generate the path manually to avoid the extra spaces/characters which can be omitted
    if points.len() < 2 {
        // Not enough points to generate a path
        return None;
    }
    let mut svg_path = String::with_capacity(points.len() * 7); // heuristic
    let mut last_command = SvgPathCommand::MoveTo;

    let first_p = &points[0];
    let space = if 0.0 <= first_p.y { " " } else { "" };
    let _ = write!(svg_path, "M{}{}{}", first_p.x, space, first_p.y);

    for pair in points.windows(2) {
        let prev_p = &pair[0];
        let p = &pair[1];
        let x = round(p.x - prev_p.x, ROUND_TO_DIGITS);
        let y = round(p.y - prev_p.y, ROUND_TO_DIGITS);
        if x == 0.0 && y == 0.0 {
            continue;
        }

        if !p.connected && !force_connected {
            let space = if 0.0 <= y { " " } else { "" };
            let _ = write!(svg_path, "m{x}{space}{y}");
            last_command = SvgPathCommand::MoveBy;
        } else if x == 0.0 {
            if last_command != SvgPathCommand::VerticalLineBy {
                svg_path.push('v');
                last_command = SvgPathCommand::VerticalLineBy;
            } else if y >= 0.0 {
                svg_path.push(' ');
            }
            let _ = write!(svg_path, "{y}");
        } else if y == 0.0 {
            if last_command != SvgPathCommand::HorizontalLineBy {
                svg_path.push('h');
                last_command = SvgPathCommand::HorizontalLineBy;
            } else if x >= 0.0 {
                svg_path.push(' ');
            }
            let _ = write!(svg_path, "{x}");
        } else {
            if last_command != SvgPathCommand::LineBy {
                svg_path.push('l');
                last_command = SvgPathCommand::LineBy;
            } else if x >= 0.0 {
                svg_path.push(' ');
            }
            let space = if 0.0 < y { " " } else { "" };
            let _ = write!(svg_path, "{x}{space}{y}");
        }
    }
    if close_path {
        svg_path.push('z');
    }

    Some(Path::new().set("d", svg_path))
}

/// Trace point
#[derive(Debug, PartialEq)]
struct TracePoint {
    x: i16,
    y: i16,
    connected: bool,
}

fn process_trace_points(trace_points: &[u8]) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    trace_points
        .chunks(5)
        .map(|chunk| {
            if chunk.len() < 5 {
                return Err("Invalid trace points length".into());
            }
            let x = i16::from_le_bytes([chunk[0], chunk[1]]);
            let y = i16::from_le_bytes([chunk[2], chunk[3]]);
            let connected = ((chunk[4] >> 7) & 1) == 0;
            Ok(TracePoint { x, y, connected })
        })
        .collect()
}

fn extract_trace_points(value: &str) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_base64_data(value)?;
    process_trace_points(&decompressed_data)
}

fn extract_trace_points_lz4(
    value: &str,
    expected_len: usize,
) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_base64_lz4_data(value, expected_len)?;
    process_trace_points(&decompressed_data)
}

fn trace_point_to_point(
    trace_point: &TracePoint,
    rotation: RotationAngle,
    ngiot_origin: Option<(i32, i32)>,
    overlay_svg_offset: Option<(f32, f32)>,
) -> Point {
    if let Some((x_min, y_max)) = ngiot_origin {
        let world_x = x_min as f32 + trace_point.x as f32;
        let world_y = y_max as f32 - trace_point.y as f32;
        let mut point = calc_point(world_x, world_y, rotation);
        if let Some((dx, dy)) = overlay_svg_offset {
            point.x += dx;
            point.y += dy;
        }
        point.connected = trace_point.connected;
        return point;
    }

    let (x, y) = match rotation {
        RotationAngle::Deg0 => (trace_point.x.into(), trace_point.y.into()),
        RotationAngle::Deg90 => (trace_point.y.into(), -(trace_point.x as f32)),
        RotationAngle::Deg180 => (-(trace_point.x as f32), -(trace_point.y as f32)),
        RotationAngle::Deg270 => (-(trace_point.y as f32), trace_point.x.into()),
    };
    let mut point = Point {
        x,
        y,
        connected: trace_point.connected,
    };
    if let Some((dx, dy)) = overlay_svg_offset {
        point.x += dx;
        point.y += dy;
    }
    point
}

#[pyclass]
pub(super) struct TracePoints {
    trace_points: Vec<TracePoint>,
    svg_scale: f32,
}

impl TracePoints {
    pub(super) fn new() -> Self {
        Self {
            trace_points: Vec::new(),
            svg_scale: LEGACY_TRACE_SCALE,
        }
    }

    pub(super) fn add_points(
        &mut self,
        value: String,
        lz4_len: Option<usize>,
    ) -> Result<(), PyErr> {
        let parsed = match lz4_len {
            Some(expected_len) => extract_trace_points_lz4(&value, expected_len),
            None => extract_trace_points(&value),
        }
        .map_err(|err| {
            error!(
                "Failed to extract trace points: {err};value:{value};lz4_len:{:?}",
                lz4_len
            );
            PyValueError::new_err(err.to_string())
        })?;

        self.trace_points.extend(parsed);
        Ok(())
    }

    pub(super) fn clear_points(&mut self) {
        self.trace_points.clear();
    }

    pub(super) fn use_legacy_trace_scale(&mut self) {
        self.svg_scale = LEGACY_TRACE_SCALE;
    }

    pub(super) fn use_world_trace_scale(&mut self) {
        self.svg_scale = 1.0 / PIXEL_WIDTH;
    }

    pub(super) fn get_path(
        &self,
        rotation: RotationAngle,
        ngiot_origin: Option<(i32, i32)>,
        overlay_svg_offset: Option<(f32, f32)>,
    ) -> Option<Path> {
        if self.trace_points.is_empty() {
            return None;
        }

        let path = points_to_svg_path(
            &self
                .trace_points
                .iter()
                .map(|tp| trace_point_to_point(tp, rotation, ngiot_origin, overlay_svg_offset))
                .collect::<Vec<Point>>(),
            false,
            false,
        )?;

        let path = path
            .set("fill", "none")
            .set("stroke", "#fff")
            .set("stroke-linejoin", "round");

        Some(if ngiot_origin.is_some() {
            path
        } else {
            path.set(
                "transform",
                format!("scale({} {})", self.svg_scale, -self.svg_scale),
            )
        })
    }
}

#[pymethods]
impl TracePoints {
    #[pyo3(signature = (value, lz4_len=None))]
    fn add(&mut self, value: String, lz4_len: Option<usize>) -> Result<(), PyErr> {
        self.add_points(value, lz4_len)
    }

    fn clear(&mut self) {
        self.clear_points();
    }

    fn use_legacy_scale(&mut self) {
        self.use_legacy_trace_scale();
    }

    fn use_world_scale(&mut self) {
        self.use_world_trace_scale();
    }

    fn set_scale(&mut self, scale: f32) -> Result<(), PyErr> {
        if !scale.is_finite() || scale <= 0.0 {
            return Err(PyValueError::new_err("scale must be a finite value > 0"));
        }
        self.svg_scale = scale;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;
    use svg::node::Value;

    impl TracePoints {
        fn add_trace_points(&mut self, points: Vec<TracePoint>) {
            self.trace_points.extend(points);
        }
    }

    fn get_path_d_attribute(path: Option<Path>) -> Option<Value> {
        path?.get_attributes().get("d").cloned()
    }

    #[rstest]
    #[case(vec![Point{x:16.0, y:256.0, connected:true}], None)]
    #[case(vec![
        Point{x:-215.0, y:-70.0, connected:false},
        Point{x:-215.0, y:-70.0, connected:true},
        Point{x:-212.0, y:-73.0, connected:true},
        Point{x:-213.0, y:-73.0, connected:true},
        Point{x:-227.0, y:-72.0, connected:true},
        Point{x:-227.0, y:-70.0, connected:true},
        Point{x:-227.0, y:-70.0, connected:true},
        Point{x:-256.0, y:-69.0, connected:false},
        Point{x:-260.0, y:-80.0, connected:true},
    ], Some(Path::new().set("d", "M-215-70l3-3h-1l-14 1v2m-29 1l-4-11")))]
    #[case(vec![Point{x:45.58, y:176.12, connected:true}, Point{x:18.78, y:175.94, connected:true}], Some(Path::new().set("d", "M45.58 176.12l-26.8-0.18")))]
    #[case(vec![], None)]
    fn test_points_to_svg_path(#[case] points: Vec<Point>, #[case] expected: Option<Path>) {
        let trace = points_to_svg_path(&points, false, false);
        assert_eq!(get_path_d_attribute(trace), get_path_d_attribute(expected));
    }

    #[rstest]
    #[case(RotationAngle::Deg0, "M100 200l50 100")]
    #[case(RotationAngle::Deg90, "M200-100l100-50")]
    #[case(RotationAngle::Deg180, "M-100-200l-50-100")]
    #[case(RotationAngle::Deg270, "M-200 100l-100 50")]
    fn test_trace_points_rotation(#[case] rotation: RotationAngle, #[case] expected: &str) {
        let mut trace_points = TracePoints::new();
        trace_points.add_trace_points(vec![
            TracePoint {
                x: 100,
                y: 200,
                connected: true,
            },
            TracePoint {
                x: 150,
                y: 300,
                connected: true,
            },
        ]);

        let path = trace_points.get_path(rotation, None, None).unwrap();
        assert_eq!(path.get_attributes().get("d").unwrap(), expected);
    }

    #[test]
    fn test_trace_points_ngiot_origin_transform() {
        let mut trace_points = TracePoints::new();
        trace_points.add_trace_points(vec![
            TracePoint {
                x: 100,
                y: 200,
                connected: true,
            },
            TracePoint {
                x: 150,
                y: 300,
                connected: true,
            },
        ]);

        let path = trace_points
            .get_path(RotationAngle::Deg0, Some((1000, 2000)), None)
            .unwrap();

        assert_eq!(path.get_attributes().get("d").unwrap(), "M22-36l1-2");
        assert!(path.get_attributes().get("transform").is_none());
    }

    #[test]
    fn test_trace_points_legacy_scale_transform_present_without_ngiot_origin() {
        let mut trace_points = TracePoints::new();
        trace_points.add_trace_points(vec![
            TracePoint {
                x: 100,
                y: 200,
                connected: true,
            },
            TracePoint {
                x: 150,
                y: 300,
                connected: true,
            },
        ]);

        let path = trace_points.get_path(RotationAngle::Deg0, None, None).unwrap();
        assert_eq!(
            path.get_attributes().get("transform").unwrap(),
            "scale(0.2 -0.2)"
        );
    }
}