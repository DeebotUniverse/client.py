use std::error::Error;
use std::io::Cursor;

use super::util::decompress_base64_data;
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
            let mut cursor = Cursor::new(&chunk[0..4]);
            let x = cursor.read_i16::<LittleEndian>()?;
            let y = cursor.read_i16::<LittleEndian>()?;
            let connected = ((chunk[4] >> 7) & 1) == 0;
            Ok(TracePoint { x, y, connected })
        })
        .collect()
}

fn extract_trace_points(value: String) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_base64_data(value)?;
    process_trace_points(&decompressed_data)
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

fn points_to_svg_path(points: &[Point]) -> Option<String> {
    // Until https://github.com/bodoni/svg/issues/68 is not implemented
    // we need to generate the path manually to avoid the extra spaces/characters which can be omitted
    if points.len() < 2 {
        // Not enough points to generate a path
        return None;
    }

    let mut svg_path = String::new();
    let mut last_command = SvgPathCommand::MoveTo;

    let first_p = points.first().unwrap();
    let space = if 0.0 < first_p.y { " " } else { "" };
    svg_path.push_str(&format!("M{}{}{}", first_p.x, space, first_p.y));

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

    Some(svg_path)
}

fn get_trace_path(trace_points: &[TracePoint]) -> Option<Path> {
    if trace_points.is_empty() {
        return None;
    }

    let path_data =
        points_to_svg_path(&trace_points.iter().map(Into::into).collect::<Vec<Point>>())?;
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

fn get_color(set_type: &str) -> PyResult<&'static str> {
    match set_type {
        "vw" => Ok("#f00000"),
        "mw" => Ok("#ffa500"),
        _ => Err(PyValueError::new_err("Invalid set type")),
    }
}

fn get_svg_subset(subset: &MapSubset) -> PyResult<Box<dyn Node>> {
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
        Ok(Box::new(
            Path::new()
                .set("stroke", get_color(&subset.set_type)?)
                .set("stroke-width", 1.5)
                .set("stroke-dasharray", "4")
                .set("vector-effect", "non-scaling-stroke")
                .set("d", points_to_svg_path(&points).unwrap()),
        ))
    } else {
        // More than 2 points: use a Polygon
        let color = get_color(&subset.set_type)?;
        Ok(Box::new(
            Polygon::new()
                .set("fill", format!("{}30", color))
                .set("stroke", color)
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
        ))
    }
}

#[pyclass(eq, eq_int)]
#[derive(PartialEq, Debug, Clone)]
enum PositionType {
    #[pyo3(name = "DEEBOT")]
    Deebot,
    #[pyo3(name = "CHARGER")]
    Charger,
}

impl TryFrom<&str> for PositionType {
    type Error = &'static str;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            "deebotPos" => Ok(PositionType::Deebot),
            "chargePos" => Ok(PositionType::Charger),
            _ => Err("Invalid position type"),
        }
    }
}

#[pymethods]
impl PositionType {
    #[staticmethod]
    fn from_str(value: &str) -> PyResult<Self> {
        PositionType::try_from(value).map_err(PyErr::new::<PyValueError, _>)
    }
}

impl PositionType {
    fn order(&self) -> i32 {
        match self {
            PositionType::Deebot => 0,
            PositionType::Charger => 1,
        }
    }

    fn svg_use_id(&self) -> &'static str {
        match self {
            PositionType::Deebot => "d",
            PositionType::Charger => "c",
        }
    }
}

/// Position type
#[derive(FromPyObject, Debug)]
struct Position {
    #[pyo3(attribute("type"))]
    position_type: PositionType,
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
struct MapData {
    trace_points: Vec<TracePoint>,
}

#[pymethods]
impl MapData {
    #[new]
    fn new() -> Self {
        MapData {
            trace_points: Vec::new(),
        }
    }

    fn add_trace_points(&mut self, value: String) -> Result<(), PyErr> {
        self.trace_points.extend(
            extract_trace_points(value).map_err(|err| PyValueError::new_err(err.to_string()))?,
        );
        Ok(())
    }

    fn clear_trace_points(&mut self) {
        self.trace_points.clear();
    }

    fn generate_svg(
        &self,
        viewbox: (f32, f32, f32, f32),
        image: Vec<u8>,
        subsets: Vec<MapSubset>,
        positions: Vec<Position>,
    ) -> PyResult<String> {
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
                    .set("id", PositionType::Deebot.svg_use_id())
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
                    .set("id", PositionType::Charger.svg_use_id())
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
        let base64_image = general_purpose::STANDARD.encode(&image);
        let image = Image::new()
            .set("x", viewbox.0)
            .set("y", viewbox.1)
            .set("width", viewbox.2)
            .set("height", viewbox.3)
            .set("style", "image-rendering: pixelated")
            .set("href", format!("data:image/png;base64,{}", base64_image));

        let mut document = Document::new().set("viewBox", viewbox).add(defs).add(image);

        for subset in subsets.iter() {
            document.append(get_svg_subset(subset)?);
        }
        if let Some(trace) = get_trace_path(self.trace_points.as_slice()) {
            document.append(trace);
        }
        for position in get_svg_positions(positions, viewbox) {
            document.append(position);
        }

        Ok(document.to_string().replace("\n", ""))
    }
}

fn get_svg_positions(positions: Vec<Position>, viewbox: (f32, f32, f32, f32)) -> Vec<Use> {
    let mut positions: Vec<&Position> = positions.iter().to_owned().collect();
    positions.sort_by_key(|d| -> i32 { d.position_type.order() });
    debug!("Adding positions: {:?}", positions);

    let mut svg_positions = Vec::new();

    for position in positions {
        let pos = calc_point_in_viewbox(position.x, position.y, viewbox);

        svg_positions.push(
            Use::new()
                .set("href", format!("#{}", position.position_type.svg_use_id()))
                .set("x", pos.x)
                .set("y", pos.y),
        );
    }
    svg_positions
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MapData>()?;
    m.add_class::<PositionType>()?;
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
    fn test_get_trace_points_path() {
        assert!(get_trace_path(&[]).is_none());
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
        let trace = get_trace_path(&points);
        assert_eq!(trace.unwrap().to_string(), expected);
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

    #[rstest]
    #[case(vec![Position{position_type:PositionType::Deebot, x:5000, y:-55000}], "<use href=\"#d\" x=\"100\" y=\"500\"/>")]
    #[case( vec![Position{position_type:PositionType::Deebot, x:15000, y:15000}], "<use href=\"#d\" x=\"300\" y=\"-300\"/>")]
    #[case(vec![Position{position_type:PositionType::Charger, x:25000, y:55000}, Position{position_type:PositionType::Deebot, x:-5000, y:-50000}], "<use href=\"#d\" x=\"-100\" y=\"500\"/><use href=\"#c\" x=\"500\" y=\"-500\"/>")]
    #[case(vec![Position{position_type:PositionType::Deebot, x:-10000, y:10000}, Position{position_type:PositionType::Charger, x:50000, y:5000}], "<use href=\"#d\" x=\"-200\" y=\"-200\"/><use href=\"#c\" x=\"500\" y=\"-100\"/>")]
    fn test_get_svg_positions(#[case] positions: Vec<Position>, #[case] expected: String) {
        let viewbox = (-500.0, -500.0, 1000.0, 1000.0);
        let result = get_svg_positions(positions, viewbox)
            .iter()
            .map(|u| u.to_string())
            .collect::<Vec<String>>()
            .join("");
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, "<path d=\"M-78-13.36h35.34\" stroke=\"#f00000\" stroke-dasharray=\"4\" stroke-width=\"1.5\" vector-effect=\"non-scaling-stroke\"/>")]
    #[case(MapSubset{set_type:"mw".to_string(), coordinates:"[-442,2910,-442,982,1214,982,1214,2910]".to_string()}, "<polygon fill=\"#ffa50030\" points=\"-8.84 -58.2 -8.84 -19.64 24.28 -19.64 24.28 -58.2\" stroke=\"#ffa500\" stroke-dasharray=\"4\" stroke-width=\"1.5\" vector-effect=\"non-scaling-stroke\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', '12135', '-6720']".to_string()}, "<path d=\"M240.46-39.58l2.24 173.98\" stroke=\"#f00000\" stroke-dasharray=\"4\" stroke-width=\"1.5\" vector-effect=\"non-scaling-stroke\"/>")]
    fn test_get_svg_subset(#[case] subset: MapSubset, #[case] expected: String) {
        let result = get_svg_subset(&subset).unwrap().to_string();
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case("deebotPos", PositionType::Deebot)]
    #[case("chargePos", PositionType::Charger)]
    fn test_position_type_from_str(#[case] value: &str, #[case] expected: PositionType) {
        let result = PositionType::from_str(value).unwrap();
        assert_eq!(result, expected);
    }

    #[test]
    fn test_position_type_from_str_invalid() {
        let result = PositionType::from_str("invalid");
        assert!(result.is_err());
    }

    #[test]
    fn test_get_color() {
        assert_eq!(get_color("vw").unwrap(), "#f00000");
        assert_eq!(get_color("mw").unwrap(), "#ffa500");
        assert!(get_color("invalid").is_err());
    }

    #[test]
    fn test_extract_trace_points_success() {
        let input = "XQAABACvAAAAAAAAAEINQkt4BfqEvt9Pow7YU9KWRVBcSBosIDAOtACCicHy+vmfexxcutQUhqkAPQlBawOeXo/VSrOqF7yhdJ1JPICUs3IhIebU62Qego0vdk8oObiLh3VY/PVkqQyvR4dHxUDzMhX7HAguZVn3yC17+cQ18N4kaydN3LfSUtV/zejrBM4=";
        let result = extract_trace_points(input.to_string()).unwrap();
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
