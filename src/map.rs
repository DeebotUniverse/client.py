use std::error::Error;

use super::util::decompress_7z_base64_data;
use base64::engine::general_purpose;
use base64::Engine;
use byteorder::{LittleEndian, ReadBytesExt};
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::io::Cursor;
use svg::node::element::path::Data;
use svg::node::element::{
    Circle, Definitions, Group, Image, Path, Polygon, RadialGradient, Stop, Use,
};
use svg::Document;

const PIXEL_WIDTH: f32 = 50.0;
const ROUND_TO_DIGITS: usize = 3;

/// Trace point
#[pyclass]
#[derive(FromPyObject)]
struct TracePoint {
    #[pyo3(get)]
    x: i16,

    #[pyo3(get)]
    y: i16,

    #[pyo3(get)]
    connected: bool,
}

#[pymethods]
impl TracePoint {
    #[new]
    fn new(x: i16, y: i16, connected: bool) -> Self {
        TracePoint { x, y, connected }
    }
}

fn process_trace_points(trace_points: &[u8]) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let mut trace_values = Vec::new();
    for i in (0..trace_points.len()).step_by(5) {
        if i + 4 >= trace_points.len() {
            return Err("Invalid trace points length".into());
        }

        let mut cursor = Cursor::new(&trace_points[i..i + 4]);
        let x = cursor.read_i16::<LittleEndian>()?;
        let y = cursor.read_i16::<LittleEndian>()?;

        // Determine connection status
        let connected = (trace_points[i + 4] >> 7 & 1) == 0;

        trace_values.push(TracePoint { x, y, connected });
    }
    Ok(trace_values)
}

fn extract_trace_points(value: String) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_7z_base64_data(value)?;
    Ok(process_trace_points(&decompressed_data)?)
}

#[pyfunction(name = "extract_trace_points")]
/// Extract trace points from 7z compressed data string.
fn python_extract_trace_points(value: String) -> Result<Vec<TracePoint>, PyErr> {
    Ok(extract_trace_points(value).map_err(|err| PyValueError::new_err(err.to_string()))?)
}

fn round(value: f32, digits: usize) -> f32 {
    let factor = 10f32.powi(digits as i32);
    (value * factor).round() / factor
}

fn points_to_svg_path(points: &[Point]) -> Data {
    let mut path = Data::new();

    if let Some(first_p) = points.first() {
        path = path.move_to((first_p.x, first_p.y));
    }

    for pair in points.windows(2) {
        if let [prev_p, p] = pair {
            let x = round(p.x - prev_p.x, ROUND_TO_DIGITS);
            let y = round(p.y - prev_p.y, ROUND_TO_DIGITS);
            if x == 0.0 && y == 0.0 {
                continue;
            }

            if !p.connected {
                path = path.move_by((p.x, p.y));
            } else if x == 0.0 {
                path = path.vertical_line_by(y);
            } else if y == 0.0 {
                path = path.horizontal_line_by(x);
            } else {
                path = path.line_by((x, y));
            }
        }
    }
    path
}

fn add_trace_points(document: Document, trace_points: &[TracePoint]) -> Document {
    if trace_points.len() == 0 {
        return document;
    }

    let trace = Path::new()
        .set("fill", "none")
        .set("stroke", "#fff")
        .set("stroke-width", 1.5)
        .set("stroke-linejoin", "round")
        .set("vector-effect", "non-scaling-stroke")
        .set("transform", "scale(0.2, -0.2)")
        .set(
            "d",
            points_to_svg_path(
                &trace_points
                    .iter()
                    .map(|p| p.into())
                    .collect::<Vec<Point>>(),
            ),
        );

    document.add(trace)
}

#[derive(Debug)]
struct Point {
    x: f32,
    y: f32,
    connected: bool,
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

fn calc_point(x: f32, y: f32) -> Point {
    Point {
        x: round(x / PIXEL_WIDTH, ROUND_TO_DIGITS),
        y: round((-y) / PIXEL_WIDTH, ROUND_TO_DIGITS),
        connected: true,
    }
}

fn get_color(set_type: &str) -> &'static str {
    match set_type {
        "vw" => "#f00000",
        "mw" => "#ffa500",
        _ => "#000",
    }
}

fn add_svg_subset(document: Document, subset: &MapSubset) -> Document {
    debug!("Adding subset: {:?}", subset);
    let subset_coordinates: Vec<f32> = subset
        .coordinates
        .trim_matches(|c: char| c == '[' || c == ']' || c.is_whitespace())
        .split(',')
        .map(|s| {
            s.trim_matches(|c: char| !c.is_numeric() && c != '-')
                .parse::<f32>()
                .unwrap_or_default()
        })
        .collect();

    let points: Vec<Point> = subset_coordinates
        .chunks(2)
        .map(|chunk| calc_point(chunk[0], chunk[1]))
        .collect();

    if points.len() == 2 {
        // Only 2 points: use a Path
        return document.add(
            Path::new()
                .set("stroke", get_color(&subset.set_type))
                .set("stroke-width", 1.5)
                .set("stroke-dasharray", "4")
                .set("vector-effect", "non-scaling-stroke")
                .set("d", points_to_svg_path(&points)),
        );
    } else {
        // More than 2 points: use a Polygon
        return document.add(
            Polygon::new()
                .set("fill", format!("{}30", get_color(&subset.set_type)))
                .set("stroke", get_color(&subset.set_type))
                .set("stroke-width", 1.5)
                .set("stroke-dasharray", "4")
                .set("vector-effect", "non-scaling-stroke")
                .set(
                    "points",
                    points
                        .iter()
                        .flat_map(|p| vec![p.x, p.y])
                        .collect::<Vec<f32>>(),
                ),
        );
    }
}

/// Position type
#[derive(FromPyObject, Debug)]
struct Position {
    #[pyo3(attribute("type"))]
    position_type: String,
    x: i32,
    y: i32,
}

fn calc_point_in_viewbox(x: i32, y: i32, viewbox: (f32, f32, f32, f32)) -> Point {
    let point = calc_point(x as f32, y as f32);
    Point {
        x: point.x.max(viewbox.0).min(viewbox.0 + viewbox.2),
        y: point.y.max(viewbox.1).min(viewbox.1 + viewbox.3),
        connected: false,
    }
}

#[derive(FromPyObject, Debug)]
/// Map subset event
struct MapSubset {
    #[pyo3(attribute("type"))]
    set_type: String,
    coordinates: String,
}

#[pyclass]
struct Svg {
    viewbox: (f32, f32, f32, f32),
    image: Vec<u8>,
    trace_points: Vec<TracePoint>,
    subsets: Vec<MapSubset>,
    positions: Vec<Position>,
}

#[pymethods]
impl Svg {
    #[new]
    fn new(
        viewbox: (f32, f32, f32, f32),
        image: Vec<u8>,
        trace_points: Vec<TracePoint>,
        subsets: Vec<MapSubset>,
        positions: Vec<Position>,
    ) -> Self {
        Svg {
            viewbox,
            image,
            trace_points,
            subsets,
            positions,
        }
    }

    fn generate(&self) -> PyResult<String> {
        let defs = Definitions::new()
            .add(
                // Gradient used by Bot icon
                RadialGradient::new()
                    .set("id", "dbg")
                    .set("cx", "50%")
                    .set("cy", "50%")
                    .set("r", "50%")
                    .set("fx", "50%")
                    .set("fy", "50%")
                    .add(
                        Stop::new()
                            .set("offset", "70%")
                            .set("style", "stop-color:#00f"),
                    )
                    .add(
                        Stop::new()
                            .set("offset", "97%")
                            .set("style", "stop-color:#00f0"),
                    ),
            )
            .add(
                // Bot circular icon
                Group::new()
                    .set("id", "d")
                    .add(Circle::new().set("r", 5).set("fill", "url(#dbg)"))
                    .add(
                        Circle::new()
                            .set("r", 3.5)
                            .set("stroke", "white")
                            .set("fill", "blue")
                            .set("stroke-width", 0.5),
                    ),
            )
            .add(
                // Charger pin icon (pre-flipped vertically)
                Group::new()
                    .set("id", "c")
                    .add(
                        Path::new().set("fill", "#ffe605").set(
                            "d",
                            Data::new()
                                .move_to((4, -6.4))
                                .cubic_curve_to((4, -4.2, 0, 0, 0, 0))
                                .smooth_cubic_curve_by((-4, -4.2, -4, -6.4))
                                .smooth_cubic_curve_by((1.8, -4, 4, -4))
                                .smooth_cubic_curve_by((4, 1.8, 4, 4))
                                .close(),
                        ),
                    )
                    .add(
                        Circle::new()
                            .set("fill", "#fff")
                            .set("r", 2.8)
                            .set("cy", -6.4),
                    ),
            );

        // Add image
        let base64_image = general_purpose::STANDARD.encode(&self.image);
        let image = Image::new()
            .set("x", self.viewbox.0)
            .set("y", self.viewbox.1)
            .set("width", self.viewbox.2)
            .set("height", self.viewbox.3)
            .set("style", "image-rendering: pixelated")
            .set("href", format!("data:image/png;base64,{}", base64_image));

        let mut document = Document::new()
            .set("viewBox", self.viewbox)
            .add(defs)
            .add(image);

        for subset in self.subsets.iter() {
            document = add_svg_subset(document, subset);
        }
        document = add_trace_points(document, self.trace_points.as_slice());
        document = self.add_poistions(document);

        Ok(document.to_string().replace("\n", ""))
    }
}

impl Svg {
    fn add_poistions(&self, mut document: Document) -> Document {
        let mut positions: Vec<&Position> = self.positions.iter().to_owned().collect();
        positions.sort_by_key(|d| -> i32 {
            match d.position_type.as_str() {
                "deebotPos" => 0,
                "chargePos" => 1,
                _ => 2,
            }
        });
        debug!("Adding positions: {:?}", positions);

        for position in positions {
            let pos = calc_point_in_viewbox(position.x, position.y, self.viewbox);
            let use_id = match position.position_type.as_str() {
                "deebotPos" => "d",
                "chargePos" => "c",
                _ => "",
            };
            let svg_position = Use::new()
                .set("href", format!("#{}", use_id))
                .set("x", pos.x)
                .set("y", pos.y);
            document = document.add(svg_position);
        }
        document
    }
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_extract_trace_points, m)?)?;
    m.add_class::<TracePoint>()?;
    m.add_class::<Svg>()?;
    Ok(())
}
