use std::error::Error;
use std::io::Cursor;

use super::util::decompress_7z_base64_data;
use base64::engine::general_purpose;
use base64::Engine;
use byteorder::{LittleEndian, ReadBytesExt};
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::{
    Circle, Definitions, Group, Image, Path, Polygon, RadialGradient, Stop, Use,
};
use svg::{Document, Node};

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
    trace_points
        .chunks(5)
        .map(|chunk| {
            if chunk.len() < 5 {
                return Err("Invalid trace points length".into());
            }
            let mut cursor = Cursor::new(&chunk[0..4]);
            let x = cursor.read_i16::<LittleEndian>()?;
            let y = cursor.read_i16::<LittleEndian>()?;
            let connected = (chunk[4] >> 7 & 1) == 0;
            Ok(TracePoint { x, y, connected })
        })
        .collect()
}

fn extract_trace_points(value: String) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_7z_base64_data(value)?;
    process_trace_points(&decompressed_data)
}

#[pyfunction(name = "extract_trace_points")]
fn python_extract_trace_points(value: String) -> PyResult<Vec<TracePoint>> {
    extract_trace_points(value).map_err(|err| PyValueError::new_err(err.to_string()))
}

fn round(value: f32, digits: usize) -> f32 {
    let factor = 10f32.powi(digits as i32);
    (value * factor).round() / factor
}

#[derive(PartialEq)]
enum SvgPathCommand {
    // To means absolute, by means relative
    MoveTo,
    MoveBy,
    LineBy,
    HorizontalLineBy,
    VerticalLineBy,
}

fn points_to_svg_path(points: &[Point]) -> String {
    // Until https://github.com/bodoni/svg/issues/68 is not implemented
    // we need to generate the path manually to avoid the extra spaces/characters which can be omitted
    let mut svg_path = String::new();
    let mut last_command = SvgPathCommand::MoveTo;

    if let Some(first_p) = points.first() {
        let space = if 0.0 < first_p.y { " " } else { "" };
        svg_path.push_str(&format!("M{}{}{}", first_p.x, space, first_p.y));
    }

    for pair in points.windows(2) {
        if let [prev_p, p] = pair {
            let x = round(p.x - prev_p.x, ROUND_TO_DIGITS);
            let y = round(p.y - prev_p.y, ROUND_TO_DIGITS);
            if x == 0.0 && y == 0.0 {
                continue;
            }

            if !p.connected {
                let space = if 0.0 < y { " " } else { "" };
                svg_path.push_str(&format!("m{}{}{}", x, space, y));
                last_command = SvgPathCommand::MoveBy;
            } else if x == 0.0 {
                if last_command != SvgPathCommand::VerticalLineBy {
                    svg_path.push('v');
                    last_command = SvgPathCommand::VerticalLineBy;
                } else if y >= 0.0 {
                    svg_path.push(' ');
                }
                svg_path.push_str(&format!("{}", y));
            } else if y == 0.0 {
                if last_command != SvgPathCommand::HorizontalLineBy {
                    svg_path.push('h');
                    last_command = SvgPathCommand::HorizontalLineBy;
                } else if x >= 0.0 {
                    svg_path.push(' ');
                }
                svg_path.push_str(&format!("{}", x));
            } else {
                if last_command != SvgPathCommand::LineBy {
                    svg_path.push('l');
                    last_command = SvgPathCommand::LineBy;
                } else if x >= 0.0 {
                    svg_path.push(' ');
                }
                let space = if 0.0 < y { " " } else { "" };
                svg_path.push_str(&format!("{}{}{}", x, space, y));
            }
        }
    }

    svg_path
}

fn add_trace_points(trace_points: &[TracePoint]) -> Option<Path> {
    if trace_points.is_empty() {
        return None;
    }

    let path_data =
        points_to_svg_path(&trace_points.iter().map(Into::into).collect::<Vec<Point>>());
    let trace = Path::new()
        .set("fill", "none")
        .set("stroke", "#fff")
        .set("stroke-width", 1.5)
        .set("stroke-linejoin", "round")
        .set("vector-effect", "non-scaling-stroke")
        .set("transform", "scale(0.2-0.2)")
        .set("d", path_data);

    Some(trace)
}

#[derive(Debug, PartialEq)]
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

fn add_svg_subset(document: &mut Document, subset: &MapSubset) {
    debug!("Adding subset: {:?}", subset);
    let points: Vec<Point> = subset
        .coordinates
        .split(',')
        .map(|s| {
            s.trim_matches(|c: char| !c.is_numeric() && c != '-')
                .parse::<f32>()
                .unwrap_or_default()
        })
        .collect::<Vec<f32>>()
        .chunks(2)
        .map(|chunk| calc_point(chunk[0], chunk[1]))
        .collect();

    if points.len() == 2 {
        // Only 2 points: use a Path
        document.append(
            Path::new()
                .set("stroke", get_color(&subset.set_type))
                .set("stroke-width", 1.5)
                .set("stroke-dasharray", "4")
                .set("vector-effect", "non-scaling-stroke")
                .set("d", points_to_svg_path(&points)),
        )
    } else {
        // More than 2 points: use a Polygon
        document.append(
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
        )
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
                    .add(Path::new().set("fill", "#ffe605").set(
                        "d",
                        // Path data cannot be used as it's adds a , after each parameter
                        // and repeats the command when used sequentially
                        "M4-6.4C4-4.2 0 0 0 0s-4-4.2-4-6.4 1.8-4 4-4 4 1.8 4 4z",
                    ))
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
            add_svg_subset(&mut document, subset);
        }
        if let Some(trace) = add_trace_points(self.trace_points.as_slice()) {
            document.append(trace);
        }
        self.add_poistions(&mut document);

        Ok(document.to_string().replace("\n", ""))
    }
}

impl Svg {
    fn add_poistions(&self, document: &mut Document) {
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
            if !use_id.is_empty() {
                document.append(
                    Use::new()
                        .set("href", format!("#{}", use_id))
                        .set("x", pos.x)
                        .set("y", pos.y),
                );
            }
        }
    }
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_extract_trace_points, m)?)?;
    m.add_class::<TracePoint>()?;
    m.add_class::<Svg>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;

    #[rstest]
    #[case(5000.0, 0.0, Point { x:100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, Point { x: 400.2, y: 598.0, connected:true  })]
    #[case(0.0, 29900.0, Point { x: 0.0, y: -598.0, connected:true  })]
    fn test_calc_point(#[case] x: f32, #[case] y: f32, #[case] expected: Point) {
        let result = calc_point(x, y);
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(100, 100, (-100.0, -100.0, 200.0, 150.0), Point { x: 2.0, y: -2.0, connected: false })]
    #[case(-64000, -64000, (0.0, 0.0, 1000.0, 1000.0), Point { x: 0.0, y: 1000.0, connected: false })]
    #[case(64000, 64000, (0.0, 0.0, 1000.0, 1000.0), Point { x: 1000.0, y: 0.0, connected: false })]
    #[case(0, 1000, (-500.0, -500.0, 1000.0, 1000.0), Point { x: 0.0, y: -20.0, connected: false })]
    fn test_calc_point_in_viewbox(
        #[case] x: i32,
        #[case] y: i32,
        #[case] viewbox: (f32, f32, f32, f32),
        #[case] expected: Point,
    ) {
        let result = calc_point_in_viewbox(x, y, viewbox);
        assert_eq!(result, expected);
    }

    #[test]
    fn test_add_trace_points_empty() {
        assert!(add_trace_points(&[]).is_none());
    }

    #[rstest]
    #[case(vec![TracePoint{x:16, y:256, connected:true}], "<path d=\"M16 256\" fill=\"none\" stroke=\"#fff\" stroke-linejoin=\"round\" stroke-width=\"1.5\" transform=\"scale(0.2-0.2)\" vector-effect=\"non-scaling-stroke\"/>")]
    #[case(vec![
        TracePoint{x:-215, y:-70, connected:false},
        TracePoint{x:-215, y:-70, connected:true},
        TracePoint{x:-212, y:-73, connected:true},
        TracePoint{x:-213, y:-73, connected:true},
        TracePoint{x:-227, y:-72, connected:true},
        TracePoint{x:-227, y:-70, connected:true},
        TracePoint{x:-227, y:-70, connected:true},
        TracePoint{x:-256, y:-69, connected:false},
        TracePoint{x:-260, y:-80, connected:true},
    ], "<path d=\"M-215-70l3-3h-1l-14 1v2m-29 1l-4-11\" fill=\"none\" stroke=\"#fff\" stroke-linejoin=\"round\" stroke-width=\"1.5\" transform=\"scale(0.2-0.2)\" vector-effect=\"non-scaling-stroke\"/>")]
    fn test_add_trace_points(#[case] points: Vec<TracePoint>, #[case] expected: String) {
        let trace = add_trace_points(&points);
        assert_eq!(trace.unwrap().to_string(), expected);
    }
}
