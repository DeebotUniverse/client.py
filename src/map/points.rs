use std::fmt::Write as FmtWrite;

use super::{common::round, ROUND_TO_DIGITS};
use crate::util::decompress_base64_data;
use log::error;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::error::Error;
use svg::node::element::Path;

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

pub(super) fn points_to_svg_path(points: &[Point]) -> Option<String> {
    // Until https://github.com/bodoni/svg/issues/68 is not implemented
    // we need to generate the path manually to avoid the extra spaces/characters which can be omitted
    if points.len() < 2 {
        // Not enough points to generate a path
        return None;
    }
    let mut svg_path = String::with_capacity(points.len() * 7); // heuristic
    let mut last_command = SvgPathCommand::MoveTo;

    let first_p = &points[0];
    let space = if 0.0 < first_p.y { " " } else { "" };
    let _ = write!(svg_path, "M{}{}{}", first_p.x, space, first_p.y);

    for pair in points.windows(2) {
        let prev_p = &pair[0];
        let p = &pair[1];
        let x = round(p.x - prev_p.x, ROUND_TO_DIGITS);
        let y = round(p.y - prev_p.y, ROUND_TO_DIGITS);
        if x == 0.0 && y == 0.0 {
            continue;
        }

        if !p.connected {
            let space = if 0.0 < y { " " } else { "" };
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

    Some(svg_path)
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

impl From<&TracePoint> for Point {
    fn from(trace_point: &TracePoint) -> Self {
        Point {
            x: trace_point.x.into(),
            y: trace_point.y.into(),
            connected: trace_point.connected,
        }
    }
}

#[pyclass]
pub(super) struct TracePoints {
    trace_points: Vec<TracePoint>,
}

impl TracePoints {
    pub(super) fn new() -> Self {
        Self {
            trace_points: Vec::new(),
        }
    }

    pub(super) fn get_path(&self) -> Option<Path> {
        if self.trace_points.is_empty() {
            return None;
        }

        let path_data = points_to_svg_path(
            &self
                .trace_points
                .iter()
                .map(Into::into)
                .collect::<Vec<Point>>(),
        )?;

        Some(
            Path::new()
                .set("fill", "none")
                .set("stroke", "#fff")
                .set("stroke-width", 1.5)
                .set("stroke-linejoin", "round")
                .set("vector-effect", "non-scaling-stroke")
                .set("transform", "scale(0.2-0.2)")
                .set("d", path_data),
        )
    }
}

#[pymethods]
impl TracePoints {
    fn add(&mut self, value: String) -> Result<(), PyErr> {
        self.trace_points
            .extend(extract_trace_points(&value).map_err(|err| {
                error!("Failed to extract trace points: {err};value:{value}");
                PyValueError::new_err(err.to_string())
            })?);
        Ok(())
    }

    fn clear(&mut self) {
        self.trace_points.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;

    impl TracePoints {
        fn add_trace_points(&mut self, points: Vec<TracePoint>) {
            self.trace_points.extend(points);
        }
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
    ], Some("M-215-70l3-3h-1l-14 1v2m-29 1l-4-11".to_string()))]
    #[case(vec![Point{x:45.58, y:176.12, connected:true}, Point{x:18.78, y:175.94, connected:true}], Some("M45.58 176.12l-26.8-0.18".to_string()))]
    #[case(vec![], None)]
    fn test_points_to_svg_path(#[case] points: Vec<Point>, #[case] expected: Option<String>) {
        let trace = points_to_svg_path(&points);
        assert_eq!(trace, expected);
    }

    #[test]
    fn test_get_trace_points_path() {
        assert!(TracePoints::new().get_path().is_none());
    }

    #[rstest]
    #[case(vec![TracePoint{x:16, y:256, connected:true},TracePoint{x:0, y:256, connected:true}], "<path d=\"M16 256h-16\" fill=\"none\" stroke=\"#fff\" stroke-linejoin=\"round\" stroke-width=\"1.5\" transform=\"scale(0.2-0.2)\" vector-effect=\"non-scaling-stroke\"/>")]
    #[case(vec![
        TracePoint{x:-215, y:-70, connected:true},
        TracePoint{x:-215, y:-70, connected:true},
        TracePoint{x:-212, y:-73, connected:true},
        TracePoint{x:-213, y:-73, connected:true},
        TracePoint{x:-227, y:-72, connected:true},
        TracePoint{x:-227, y:-70, connected:true},
        TracePoint{x:-227, y:-70, connected:true},
        TracePoint{x:-256, y:-69, connected:false},
        TracePoint{x:-260, y:-80, connected:true},
    ], "<path d=\"M-215-70l3-3h-1l-14 1v2m-29 1l-4-11\" fill=\"none\" stroke=\"#fff\" stroke-linejoin=\"round\" stroke-width=\"1.5\" transform=\"scale(0.2-0.2)\" vector-effect=\"non-scaling-stroke\"/>")]
    fn test_get_trace_path(#[case] points: Vec<TracePoint>, #[case] expected: String) {
        let mut trace_points = TracePoints::new();
        trace_points.add_trace_points(points);
        let trace = trace_points.get_path();
        assert_eq!(trace.unwrap().to_string(), expected);
    }

    #[test]
    fn test_extract_trace_points_success() {
        let input = "XQAABACvAAAAAAAAAEINQkt4BfqEvt9Pow7YU9KWRVBcSBosIDAOtACCicHy+vmfexxcutQUhqkAPQlBawOeXo/VSrOqF7yhdJ1JPICUs3IhIebU62Qego0vdk8oObiLh3VY/PVkqQyvR4dHxUDzMhX7HAguZVn3yC17+cQ18N4kaydN3LfSUtV/zejrBM4=";
        let result = extract_trace_points(input).unwrap();
        let expected = vec![
            TracePoint {
                x: 0,
                y: 1,
                connected: false,
            },
            TracePoint {
                x: -10,
                y: 1,
                connected: true,
            },
            TracePoint {
                x: -7,
                y: -8,
                connected: true,
            },
            TracePoint {
                x: 0,
                y: -15,
                connected: true,
            },
            TracePoint {
                x: 6,
                y: -23,
                connected: true,
            },
            TracePoint {
                x: 11,
                y: -32,
                connected: true,
            },
            TracePoint {
                x: 21,
                y: -30,
                connected: true,
            },
            TracePoint {
                x: 31,
                y: -30,
                connected: true,
            },
            TracePoint {
                x: 40,
                y: -34,
                connected: true,
            },
            TracePoint {
                x: 46,
                y: -42,
                connected: true,
            },
            TracePoint {
                x: 53,
                y: -51,
                connected: true,
            },
            TracePoint {
                x: 52,
                y: -61,
                connected: true,
            },
            TracePoint {
                x: 48,
                y: -70,
                connected: true,
            },
            TracePoint {
                x: 44,
                y: -79,
                connected: true,
            },
            TracePoint {
                x: 34,
                y: -83,
                connected: true,
            },
            TracePoint {
                x: 24,
                y: -83,
                connected: true,
            },
            TracePoint {
                x: 14,
                y: -82,
                connected: true,
            },
            TracePoint {
                x: 6,
                y: -76,
                connected: true,
            },
            TracePoint {
                x: 0,
                y: -68,
                connected: true,
            },
            TracePoint {
                x: -2,
                y: -59,
                connected: true,
            },
            TracePoint {
                x: 0,
                y: -48,
                connected: true,
            },
            TracePoint {
                x: 3,
                y: -38,
                connected: true,
            },
            TracePoint {
                x: 11,
                y: -32,
                connected: true,
            },
            TracePoint {
                x: 21,
                y: -29,
                connected: true,
            },
            TracePoint {
                x: 21,
                y: -19,
                connected: true,
            },
            TracePoint {
                x: 14,
                y: -12,
                connected: true,
            },
            TracePoint {
                x: 5,
                y: -7,
                connected: true,
            },
            TracePoint {
                x: 12,
                y: -14,
                connected: true,
            },
            TracePoint {
                x: 21,
                y: -18,
                connected: true,
            },
            TracePoint {
                x: 31,
                y: -20,
                connected: true,
            },
            TracePoint {
                x: 41,
                y: -20,
                connected: true,
            },
            TracePoint {
                x: 51,
                y: -24,
                connected: true,
            },
            TracePoint {
                x: 58,
                y: -31,
                connected: true,
            },
            TracePoint {
                x: 64,
                y: -39,
                connected: true,
            },
            TracePoint {
                x: 70,
                y: -47,
                connected: true,
            },
        ];
        assert_eq!(result, expected);
    }

    #[test]
    fn test_process_trace_points_to_short() {
        let input: Vec<u8> = vec![0x0, 0x0, 0x0, 0x0];
        let result = process_trace_points(&input);
        assert!(matches!(result, Err(e) if e.to_string() == "Invalid trace points length"));
    }
}
