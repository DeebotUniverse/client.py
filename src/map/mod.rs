mod background_image;
mod common;
mod map_info;
mod points;
mod style;

use background_image::{BackgroundImage, MAP_MAX_SIZE};
use common::round;
use map_info::MapInfo;
use ordermap::OrderSet;
use points::{Point, TracePoints, points_to_svg_path};
use style::{CSSClass, get_class_names, get_style, get_used_definitions};

use super::util::decompress_base64_data;
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::{
    Circle, Definitions, Group, Image, Path, RadialGradient, Stop, Style, Use,
};
use svg::{Document, Node};

const PIXEL_WIDTH: f32 = 50.0;
const ROUND_TO_DIGITS: usize = 3;
const MAP_OFFSET: i16 = MAP_MAX_SIZE as i16 / 2;

#[inline]
fn calc_point(x: f32, y: f32, rotation: RotationAngle) -> Point {
    let (px, py) = match rotation {
        RotationAngle::Deg0 => (x / PIXEL_WIDTH, -y / PIXEL_WIDTH),
        RotationAngle::Deg90 => (y / PIXEL_WIDTH, x / PIXEL_WIDTH),
        RotationAngle::Deg180 => (-x / PIXEL_WIDTH, y / PIXEL_WIDTH),
        RotationAngle::Deg270 => (-y / PIXEL_WIDTH, -x / PIXEL_WIDTH),
    };
    Point {
        x: round(px, ROUND_TO_DIGITS),
        y: round(py, ROUND_TO_DIGITS),
        connected: true,
    }
}

fn get_svg_subset(subset: &MapSubset, rotation: RotationAngle) -> PyResult<(CSSClass, Path)> {
    debug!("Adding subset: {subset:?}");

    // Estimate capacity: each point consists of an x and y coordinate, separated by commas.
    // So, the number of points is half the number of comma-separated values.
    let num_coords = subset.coordinates.split(',').count();
    let mut points = Vec::with_capacity(num_coords / 2);

    let mut numbers = subset.coordinates.split(',').filter_map(|s| {
        let s = s.trim_matches(|c: char| !c.is_numeric() && c != '-' && c != '.');
        if s.is_empty() {
            debug!("Skipping empty coordinate in subset: {subset:?}");
            None
        } else {
            s.parse::<f32>().ok()
        }
    });

    while let (Some(x), Some(y)) = (numbers.next(), numbers.next()) {
        points.push(calc_point(x, y, rotation));
    }

    let css_key = match subset.set_type.as_str() {
        "vw" => CSSClass::VirtualWall,
        "mw" => CSSClass::NoMoppingWall,
        _ => return Err(PyValueError::new_err("Invalid set type")),
    };
    let css_obj = get_style(&css_key);

    let svg_object = points_to_svg_path(&points, points.len() > 2, false)
        .unwrap()
        .set("class", css_obj.class_name);

    Ok((css_key, svg_object))
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
    #[inline]
    fn order(&self) -> i32 {
        match self {
            PositionType::Deebot => 0,
            PositionType::Charger => 1,
        }
    }

    #[inline]
    fn svg_use_id(&self) -> &'static str {
        match self {
            PositionType::Deebot => "d",
            PositionType::Charger => "c",
        }
    }
}

#[pyclass(eq, eq_int, frozen, hash)]
#[derive(Default, PartialEq, Debug, Clone, Copy, Hash)]
pub(super) enum RotationAngle {
    #[pyo3(name = "DEG_0")]
    #[default]
    Deg0 = 0,
    #[pyo3(name = "DEG_90")]
    Deg90 = 90,
    #[pyo3(name = "DEG_180")]
    Deg180 = 180,
    #[pyo3(name = "DEG_270")]
    Deg270 = 270,
}

#[pymethods]
impl RotationAngle {
    #[staticmethod]
    fn from_int(value: i16) -> PyResult<Self> {
        match value {
            0 => Ok(RotationAngle::Deg0),
            90 => Ok(RotationAngle::Deg90),
            180 => Ok(RotationAngle::Deg180),
            270 => Ok(RotationAngle::Deg270),
            _ => Err(PyValueError::new_err(format!(
                "Invalid rotation angle: {}. Valid values are 0, 90, 180, 270.",
                value
            ))),
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

#[inline]
fn calc_point_in_viewbox(x: i32, y: i32, viewbox: &ViewBox, rotation: RotationAngle) -> Point {
    let point = calc_point(x as f32, y as f32, rotation);
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
    #[pyo3(get)]
    map_info: Py<MapInfo>,
}

#[pymethods]
impl MapData {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        Ok(MapData {
            trace_points: Py::new(py, TracePoints::new())?,
            background_image: Py::new(py, BackgroundImage::new())?,
            map_info: Py::new(py, MapInfo::new())?,
        })
    }

    fn generate_svg(
        &self,
        py: Python<'_>,
        subsets: Vec<MapSubset>,
        positions: Vec<Position>,
        rotation: RotationAngle,
    ) -> PyResult<Option<String>> {
        let mut defs = Definitions::new()
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

        let mut styles = OrderSet::new();
        styles.insert(CSSClass::Path);

        let mut document = Document::new();

        // Create map from MapInfo, if exists, or generate background image
        let viewbox = match self.map_info.borrow(py).generate(rotation) {
            Some((map_elements, viewbox, info_styles)) => {
                // Append all map background elements to document
                map_elements.into_iter().for_each(|e| document.append(e));
                styles.extend(info_styles);
                viewbox
            }
            _ => {
                if let Some((base64_image, viewbox)) =
                    self.background_image
                        .borrow(py)
                        .generate()
                        .map_err(|err| PyValueError::new_err(err.to_string()))?
                {
                    let image = Image::new()
                        .set("x", viewbox.min_x)
                        .set("y", viewbox.min_y)
                        .set("width", viewbox.width)
                        .set("height", viewbox.height)
                        .set("style", "image-rendering: pixelated")
                        .set("href", format!("data:image/png;base64,{base64_image}"));
                    document.append(image);
                    viewbox
                } else {
                    return Ok(None);
                }
            }
        };

        // Add required definitions based on used CSS classes
        get_used_definitions(&styles)
            .into_iter()
            .for_each(|def| defs.append(def));

        document = document.add(defs).set("viewBox", viewbox.to_svg_viewbox());

        if !subsets.is_empty() {
            let group_css = [CSSClass::WallBase, CSSClass::StrokeWidth2];
            let mut group = Group::new().set("class", get_class_names(&group_css));
            styles.extend(group_css);

            for subset in &subsets {
                let (css, subset) = get_svg_subset(subset, rotation)?;
                styles.insert(css);
                group = group.add(subset);
            }
            document.append(group);
        }
        if let Some(trace) = self.trace_points.borrow(py).get_path(rotation) {
            document.append(trace);
        }
        for position in get_svg_positions(&positions, &viewbox, rotation) {
            document.append(position);
        }

        let mut style_string = String::new();
        for k in styles {
            let css = get_style(&k);
            style_string.push_str(css.identifier);
            style_string.push('{');
            style_string.push_str(css.value);
            style_string.push('}');
        }

        let style = Style::new(style_string);
        document.append(style);

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

    #[inline]
    fn to_svg_viewbox(&self) -> String {
        format!(
            "{} {} {} {}",
            self.min_x, self.min_y, self.width, self.height
        )
    }
}

type ImageGenrationType = Option<(String, ViewBox)>;

fn get_svg_positions(
    positions: &[Position],
    viewbox: &ViewBox,
    rotation: RotationAngle,
) -> Vec<Use> {
    if positions.is_empty() {
        return Vec::new();
    }

    // Create indices and sort them instead of collecting references
    let mut indices: Vec<usize> = (0..positions.len()).collect();
    indices.sort_by_key(|&i| positions[i].position_type.order());

    debug!("Adding positions: {positions:?}");

    let mut svg_positions = Vec::with_capacity(positions.len());

    for &i in &indices {
        let position = &positions[i];
        let pos = calc_point_in_viewbox(position.x, position.y, viewbox, rotation);

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
    m.add_class::<RotationAngle>()?;
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
    #[case(5000.0, 0.0, RotationAngle::Deg0, Point { x:100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg0, Point { x: 400.2, y: 598.0, connected:true  })]
    #[case(0.0, 29900.0, RotationAngle::Deg0, Point { x: 0.0, y: -598.0, connected:true  })]
    #[case(5000.0, 0.0, RotationAngle::Deg90, Point { x:0.0, y:100.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg90, Point { x: -598.0, y: 400.2, connected:true  })]
    #[case(5000.0, 0.0, RotationAngle::Deg180, Point { x:-100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg180, Point { x: -400.2, y: -598.0, connected:true  })]
    #[case(5000.0, 0.0, RotationAngle::Deg270, Point { x:0.0, y:-100.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg270, Point { x: 598.0, y: -400.2, connected:true  })]
    fn test_calc_point(
        #[case] x: f32,
        #[case] y: f32,
        #[case] rotation: RotationAngle,
        #[case] expected: Point,
    ) {
        let result = calc_point(x, y, rotation);
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(100, 100, (-100, -100, 200, 150), RotationAngle::Deg0, Point { x: 2.0, y: -2.0, connected: false })]
    #[case(-64000, -64000, (0, 0, 1000, 1000), RotationAngle::Deg0, Point { x: 0.0, y: 1000.0, connected: false })]
    #[case(64000, 64000, (0, 0, 1000, 1000), RotationAngle::Deg0, Point { x: 1000.0, y: 0.0, connected: false })]
    #[case(0, 1000, (-500, -500, 1000, 1000), RotationAngle::Deg0, Point { x: 0.0, y: -20.0, connected: false })]
    #[case(100, 100, (-100, -100, 200, 150), RotationAngle::Deg90, Point { x: 2.0, y: 2.0, connected: false })]
    #[case(100, 100, (-100, -100, 200, 150), RotationAngle::Deg180, Point { x: -2.0, y: 2.0, connected: false })]
    #[case(100, 100, (-100, -100, 200, 150), RotationAngle::Deg270, Point { x: -2.0, y: -2.0, connected: false })]
    fn test_calc_point_in_viewbox(
        #[case] x: i32,
        #[case] y: i32,
        #[case] viewbox: (i16, i16, u16, u16),
        #[case] rotation: RotationAngle,
        #[case] expected: Point,
    ) {
        let result = calc_point_in_viewbox(x, y, &tuple_2_view_box(viewbox), rotation);
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(&[Position{position_type:PositionType::Deebot, x:5000, y:-55000}], RotationAngle::Deg0, "<use href=\"#d\" x=\"100\" y=\"500\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:15000, y:15000}], RotationAngle::Deg0, "<use href=\"#d\" x=\"300\" y=\"-300\"/>")]
    #[case(&[Position{position_type:PositionType::Charger, x:25000, y:55000}, Position{position_type:PositionType::Deebot, x:-5000, y:-50000}], RotationAngle::Deg0, "<use href=\"#d\" x=\"-100\" y=\"500\"/><use href=\"#c\" x=\"500\" y=\"-500\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:-10000, y:10000}, Position{position_type:PositionType::Charger, x:50000, y:5000}], RotationAngle::Deg0, "<use href=\"#d\" x=\"-200\" y=\"-200\"/><use href=\"#c\" x=\"500\" y=\"-100\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:5000, y:-55000}], RotationAngle::Deg90, "<use href=\"#d\" x=\"-500\" y=\"100\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:5000, y:-55000}], RotationAngle::Deg180, "<use href=\"#d\" x=\"-100\" y=\"-500\"/>")]
    #[case(&[Position{position_type:PositionType::Deebot, x:5000, y:-55000}], RotationAngle::Deg270, "<use href=\"#d\" x=\"500\" y=\"-100\"/>")]
    fn test_get_svg_positions(
        #[case] positions: &[Position],
        #[case] rotation: RotationAngle,
        #[case] expected: String,
    ) {
        let viewbox = (-500, -500, 1000, 1000);
        let result = get_svg_positions(positions, &tuple_2_view_box(viewbox), rotation)
            .iter()
            .map(|u| u.to_string())
            .collect::<Vec<String>>()
            .join("");
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg0, "<path class=\"v\" d=\"M-78-13.36h35.34\"/>")]
    #[case(MapSubset{set_type:"mw".to_string(), coordinates:"[-442,2910,-442,982,1214,982,1214,2910]".to_string()}, RotationAngle::Deg0, "<path class=\"m\" d=\"M-8.84-58.2v38.56h33.12v-38.56z\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', '12135', '-6720']".to_string()}, RotationAngle::Deg0, "<path class=\"v\" d=\"M240.46-39.58l2.24 173.98\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', , '', '12135', '-6720']".to_string()}, RotationAngle::Deg0, "<path class=\"v\" d=\"M240.46-39.58l2.24 173.98\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg90, "<path class=\"v\" d=\"M13.36-78v35.34\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg180, "<path class=\"v\" d=\"M78 13.36h-35.34\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg270, "<path class=\"v\" d=\"M-13.36 78v-35.34\"/>")]
    fn test_get_svg_subset(
        #[case] subset: MapSubset,
        #[case] rotation: RotationAngle,
        #[case] expected: String,
    ) {
        let (_, node) = get_svg_subset(&subset, rotation).unwrap();

        assert_eq!(node.to_string(), expected);
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

    #[rstest]
    #[case(0, RotationAngle::Deg0)]
    #[case(90, RotationAngle::Deg90)]
    #[case(180, RotationAngle::Deg180)]
    #[case(270, RotationAngle::Deg270)]
    fn test_rotation_angle_from_int_valid(#[case] value: i16, #[case] expected: RotationAngle) {
        let result = RotationAngle::from_int(value).unwrap();
        assert_eq!(result, expected);
    }

    #[rstest]
    #[case(45)]
    #[case(360)]
    #[case(-90)]
    #[case(100)]
    fn test_rotation_angle_from_int_invalid(#[case] value: i16) {
        let result = RotationAngle::from_int(value);
        assert!(result.is_err());
    }

    #[test]
    fn test_rotation_angle_default() {
        let rotation = RotationAngle::default();
        assert_eq!(rotation, RotationAngle::Deg0);
    }
}
