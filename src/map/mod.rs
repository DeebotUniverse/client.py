mod background_image;
mod common;
mod points;

use background_image::{BackgroundImage, MAP_MAX_SIZE};
use common::round;
use points::{points_to_svg_path, Point, TracePoints};

use super::util::decompress_base64_data;
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::{
    Circle, Definitions, Group, Image, Path, Polygon, RadialGradient, Stop, Use,
};
use svg::{Document, Node};

const PIXEL_WIDTH: f32 = 50.0;
const ROUND_TO_DIGITS: usize = 3;
const MAP_OFFSET: i16 = MAP_MAX_SIZE as i16 / 2;

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
    debug!("Adding subset: {subset:?}");
    let mut numbers = subset.coordinates.split(',').filter_map(|s| {
        let s = s.trim_matches(|c: char| !c.is_numeric() && c != '-' && c != '.');
        if s.is_empty() {
            debug!("Skipping empty coordinate in subset: {subset:?}");
            None
        } else {
            s.parse::<f32>().ok()
        }
    });

    let mut points = Vec::with_capacity(subset.coordinates.len() / 2);
    while let (Some(x), Some(y)) = (numbers.next(), numbers.next()) {
        points.push(calc_point(x, y));
    }

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
        let mut coords = Vec::with_capacity(points.len() * 2);
        for p in points {
            coords.push(p.x);
            coords.push(p.y);
        }
        Ok(Box::new(
            Polygon::new()
                .set("fill", format!("{color}30"))
                .set("stroke", color)
                .set("stroke-width", 1.5)
                .set("stroke-dasharray", "4")
                .set("vector-effect", "non-scaling-stroke")
                .set("points", coords),
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

fn calc_point_in_viewbox(x: i32, y: i32, viewbox: &ViewBox) -> Point {
    let point = calc_point(x as f32, y as f32);
    Point {
        x: point.x.max(viewbox.min_x as f32).min(viewbox.max_x as f32),
        y: point.y.max(viewbox.min_y as f32).min(viewbox.max_y as f32),
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
    #[pyo3(get)]
    trace_points: Py<TracePoints>,
    #[pyo3(get)]
    background_image: Py<BackgroundImage>,
}

#[pymethods]
impl MapData {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        Ok(MapData {
            trace_points: Py::new(py, TracePoints::new())?,
            background_image: Py::new(py, BackgroundImage::new())?,
        })
    }

    fn generate_svg(
        &self,
        py: Python<'_>,
        subsets: Vec<MapSubset>,
        positions: Vec<Position>,
    ) -> PyResult<Option<String>> {
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
        let (base64_image, viewbox) = match self
            .background_image
            .borrow(py)
            .generate()
            .map_err(|err| PyValueError::new_err(err.to_string()))?
        {
            Some(data) => data,
            None => return Ok(None),
        };
        let image = Image::new()
            .set("x", viewbox.min_x)
            .set("y", viewbox.min_y)
            .set("width", viewbox.width)
            .set("height", viewbox.height)
            .set("style", "image-rendering: pixelated")
            .set("href", format!("data:image/png;base64,{base64_image}"));

        let mut document = Document::new()
            .set("viewBox", viewbox.to_svg_viewbox())
            .add(defs)
            .add(image);

        for subset in &subsets {
            document.append(get_svg_subset(subset)?);
        }
        if let Some(trace) = self.trace_points.borrow(py).get_path() {
            document.append(trace);
        }
        for position in get_svg_positions(&positions, &viewbox) {
            document.append(position);
        }
        Ok(Some(document.to_string().replace('\n', "")))
    }
}

#[derive(Debug)]
struct ViewBox {
    min_x: i16,
    min_y: i16,
    max_x: i16,
    max_y: i16,
    width: u16,
    height: u16,
}

impl ViewBox {
    fn new(min_x: u16, min_y: u16, max_x: u16, max_y: u16) -> Self {
        let new_min_x = min_x as i16 - MAP_OFFSET;
        let new_min_y = min_y as i16 - MAP_OFFSET;
        let width = max_x - min_x + 1;
        let height = max_y - min_y + 1;
        ViewBox {
            min_x: new_min_x,
            min_y: new_min_y,
            max_x: new_min_x + width as i16,
            max_y: new_min_y + height as i16,
            width,
            height,
        }
    }

    fn to_svg_viewbox(&self) -> String {
        format!(
            "{} {} {} {}",
            self.min_x, self.min_y, self.width, self.height
        )
    }
}

type ImageGenrationType = Option<(String, ViewBox)>;

fn get_svg_positions<'a>(positions: &'a [Position], viewbox: &ViewBox) -> Vec<Use> {
    let mut positions: Vec<&'a Position> = positions.iter().collect();
    positions.sort_by_key(|d| d.position_type.order());
    debug!("Adding positions: {positions:?}");

    let mut svg_positions = Vec::with_capacity(positions.len());

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

    fn tuple_2_view_box(tuple: (i16, i16, u16, u16)) -> ViewBox {
        ViewBox {
            min_x: tuple.0,
            min_y: tuple.1,
            max_x: tuple.0 + tuple.2 as i16,
            max_y: tuple.1 + tuple.3 as i16,
            width: tuple.2,
            height: tuple.3,
        }
    }

    #[rstest]
    #[case((-100, -100, 200, 150))]
    #[case((0, 0, 1000, 1000))]
    #[case( (0, 0, 1000, 1000))]
    #[case( (-500, -500, 1000, 1000))]
    fn test_tuple_2_view_box(#[case] input: (i16, i16, u16, u16)) {
        let result = tuple_2_view_box(input);
        assert_eq!(
            input,
            (result.min_x, result.min_y, result.width, result.height,)
        );
    }

    #[rstest]
    #[case(5000.0, 0.0, Point { x:100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, Point { x: 400.2, y: 598.0, connected:true  })]
    #[case(0.0, 29900.0, Point { x: 0.0, y: -598.0, connected:true  })]
    fn test_calc_point(#[case] x: f32, #[case] y: f32, #[case] expected: Point) {
        let result = calc_point(x, y);
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(100, 100, (-100, -100, 200, 150), Point { x: 2.0, y: -2.0, connected: false })]
    #[case(-64000, -64000, (0, 0, 1000, 1000), Point { x: 0.0, y: 1000.0, connected: false })]
    #[case(64000, 64000, (0, 0, 1000, 1000), Point { x: 1000.0, y: 0.0, connected: false })]
    #[case(0, 1000, (-500, -500, 1000, 1000), Point { x: 0.0, y: -20.0, connected: false })]
    fn test_calc_point_in_viewbox(
        #[case] x: i32,
        #[case] y: i32,
        #[case] viewbox: (i16, i16, u16, u16),
        #[case] expected: Point,
    ) {
        let result = calc_point_in_viewbox(x, y, &tuple_2_view_box(viewbox));
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(&[Position{position_type:PositionType::Deebot, x:5000, y:-55000}], "<use href=\"#d\" x=\"100\" y=\"500\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:15000, y:15000}], "<use href=\"#d\" x=\"300\" y=\"-300\"/>")]
    #[case(&[Position{position_type:PositionType::Charger, x:25000, y:55000}, Position{position_type:PositionType::Deebot, x:-5000, y:-50000}], "<use href=\"#d\" x=\"-100\" y=\"500\"/><use href=\"#c\" x=\"500\" y=\"-500\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:-10000, y:10000}, Position{position_type:PositionType::Charger, x:50000, y:5000}], "<use href=\"#d\" x=\"-200\" y=\"-200\"/><use href=\"#c\" x=\"500\" y=\"-100\"/>")]
    fn test_get_svg_positions(#[case] positions: &[Position], #[case] expected: String) {
        let viewbox = (-500, -500, 1000, 1000);
        let result = get_svg_positions(positions, &tuple_2_view_box(viewbox))
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
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', , '', '12135', '-6720']".to_string()}, "<path d=\"M240.46-39.58l2.24 173.98\" stroke=\"#f00000\" stroke-dasharray=\"4\" stroke-width=\"1.5\" vector-effect=\"non-scaling-stroke\"/>")]
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
}
