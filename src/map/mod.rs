mod background_image;
mod common;
mod map_info;
mod ngiot_background;
mod points;
mod style;

use background_image::{BackgroundImage, MAP_MAX_SIZE};
use common::round;
use map_info::MapInfo;
use ngiot_background::NgiotBackground;
use ordermap::OrderSet;
use points::{points_to_svg_path, Point, TracePoints};
use style::{get_class_names, get_style, get_used_definitions, CSSClass};

use super::util::decompress_base64_data;
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::{
    Circle, Definitions, Group, Image, Path, RadialGradient, Stop, Style, Use,
};
use svg::{Document, Node};

pub(super) const PIXEL_WIDTH: f32 = 50.0;
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

fn get_subset_points(subset: &MapSubset, rotation: RotationAngle) -> Vec<Point> {
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

    points
}

fn get_svg_subset(
    subset: &MapSubset,
    rotation: RotationAngle,
) -> PyResult<(Vec<CSSClass>, Path)> {
    debug!("Adding subset: {subset:?}");

    let points = get_subset_points(subset, rotation);
    let close_path = points.len() > 2;

    let css = match subset.set_type.as_str() {
        "ar" => vec![CSSClass::RoomSubset],
        "vw" => vec![
            CSSClass::WallBase,
            CSSClass::StrokeWidth2,
            CSSClass::VirtualWall,
        ],
        "mw" => vec![
            CSSClass::WallBase,
            CSSClass::StrokeWidth2,
            CSSClass::NoMoppingWall,
        ],
        "cp" => vec![CSSClass::CarpetArea],
        _ => return Err(PyValueError::new_err("Invalid set type")),
    };

    let svg_object = points_to_svg_path(&points, close_path, false)
        .ok_or_else(|| PyValueError::new_err("Subset does not contain enough points"))?
        .set("class", get_class_names(&css));

    Ok((css, svg_object))
}

#[pyclass(from_py_object, eq, eq_int)]
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

#[pyclass(from_py_object, eq, eq_int, frozen, hash)]
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

fn calc_fallback_viewbox(
    subsets: &[MapSubset],
    positions: &[Position],
    rotation: RotationAngle,
) -> Option<ViewBox> {
    let mut min_x = f32::MAX;
    let mut min_y = f32::MAX;
    let mut max_x = f32::MIN;
    let mut max_y = f32::MIN;
    let mut found = false;

    for subset in subsets {
        for point in get_subset_points(subset, rotation) {
            min_x = min_x.min(point.x);
            min_y = min_y.min(point.y);
            max_x = max_x.max(point.x);
            max_y = max_y.max(point.y);
            found = true;
        }
    }

    for position in positions {
        let point = calc_point(position.x as f32, position.y as f32, rotation);
        min_x = min_x.min(point.x);
        min_y = min_y.min(point.y);
        max_x = max_x.max(point.x);
        max_y = max_y.max(point.y);
        found = true;
    }

    if !found {
        return None;
    }

    let margin = 5.0;
    Some(ViewBox::from_extents(
        min_x.floor() - margin,
        min_y.floor() - margin,
        max_x.ceil() + margin,
        max_y.ceil() + margin,
    ))
}

#[pyclass]
struct MapData {
    #[pyo3(get)]
    trace_points: Py<TracePoints>,
    #[pyo3(get)]
    background_image: Py<BackgroundImage>,
    #[pyo3(get)]
    ngiot_background: Py<NgiotBackground>,
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
            ngiot_background: Py::new(py, NgiotBackground::new())?,
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
                Group::new()
                    .set("id", PositionType::Charger.svg_use_id())
                    .add(Path::new().set("fill", "#ffe605").set(
                        "d",
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

        let viewbox = match self.map_info.borrow(py).generate(rotation) {
            Some((map_elements, viewbox, info_styles)) => {
                map_elements.into_iter().for_each(|e| document.append(e));
                styles.extend(info_styles);
                viewbox
            }
            _ => {
                if let Some((base64_image, viewbox)) = self
                    .ngiot_background
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
                } else if let Some((base64_image, viewbox)) = self
                    .background_image
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
                } else if let Some(viewbox) = calc_fallback_viewbox(&subsets, &positions, rotation)
                {
                    viewbox
                } else {
                    return Ok(None);
                }
            }
        };

        for subset in &subsets {
            let (css_list, path) = get_svg_subset(subset, rotation)?;
            styles.extend(css_list);
            document.append(path);
        }

        if let Some(trace) = self.trace_points.borrow(py).get_path(rotation) {
            document.append(trace);
        }
        for position in get_svg_positions(&positions, &viewbox, rotation) {
            document.append(position);
        }

        get_used_definitions(&styles)
            .into_iter()
            .for_each(|def| defs.append(def));

        document = document.add(defs).set("viewBox", viewbox.to_svg_viewbox());

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

#[derive(Debug, Clone, Copy)]
struct ViewBox {
    min_x: f32,
    min_y: f32,
    max_x: f32,
    max_y: f32,
    width: f32,
    height: f32,
}

impl ViewBox {
    fn new(min_x: u16, min_y: u16, max_x: u16, max_y: u16) -> Self {
        let new_min_x = min_x as f32 - MAP_OFFSET as f32;
        let new_min_y = min_y as f32 - MAP_OFFSET as f32;
        let width = (max_x - min_x + 1) as f32;
        let height = (max_y - min_y + 1) as f32;
        ViewBox {
            min_x: new_min_x,
            min_y: new_min_y,
            max_x: new_min_x + width,
            max_y: new_min_y + height,
            width,
            height,
        }
    }

    fn from_extents(min_x: f32, min_y: f32, max_x: f32, max_y: f32) -> Self {
        let width = (max_x - min_x).max(1.0);
        let height = (max_y - min_y).max(1.0);

        ViewBox {
            min_x,
            min_y,
            max_x,
            max_y,
            width,
            height,
        }
    }

    #[inline]
    fn to_svg_viewbox(&self) -> String {
        format!(
            "{} {} {} {}",
            round(self.min_x, ROUND_TO_DIGITS),
            round(self.min_y, ROUND_TO_DIGITS),
            round(self.width, ROUND_TO_DIGITS),
            round(self.height, ROUND_TO_DIGITS)
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
            min_x: tuple.0 as f32,
            min_y: tuple.1 as f32,
            max_x: tuple.0 as f32 + tuple.2 as f32,
            max_y: tuple.1 as f32 + tuple.3 as f32,
            width: tuple.2 as f32,
            height: tuple.3 as f32,
        }
    }

    #[rstest]
    #[case((-100, -100, 200, 150))]
    #[case((0, 0, 1000, 1000))]
    #[case((0, 0, 1000, 1000))]
    #[case((-500, -500, 1000, 1000))]
    fn test_tuple_2_view_box(#[case] input: (i16, i16, u16, u16)) {
        let result = tuple_2_view_box(input);
        assert_eq!(
            input,
            (result.min_x, result.min_y, result.width, result.height,)
        );
    }

    #[rstest]
    #[case(5000.0, 0.0, RotationAngle::Deg0, Point { x:100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg0, Point { x: 400.2, y: 598.0, connected:true })]
    #[case(0.0, 29900.0, RotationAngle::Deg0, Point { x: 0.0, y: -598.0, connected:true })]
    #[case(5000.0, 0.0, RotationAngle::Deg90, Point { x:0.0, y:100.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg90, Point { x: -598.0, y: 400.2, connected:true })]
    #[case(5000.0, 0.0, RotationAngle::Deg180, Point { x:-100.0, y:0.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg180, Point { x: -400.2, y: -598.0, connected:true })]
    #[case(5000.0, 0.0, RotationAngle::Deg270, Point { x:0.0, y:-100.0, connected:true })]
    #[case(20010.0, -29900.0, RotationAngle::Deg270, Point { x: 598.0, y: -400.2, connected:true })]
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
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg0, "<path class=\"wb sw2 v\" d=\"M-78-13.36h35.34\"/>")]
    #[case(MapSubset{set_type:"mw".to_string(), coordinates:"[-442,2910,-442,982,1214,982,1214,2910]".to_string()}, RotationAngle::Deg0, "<path class=\"wb sw2 m\" d=\"M-8.84-58.2v38.56h33.12v-38.56z\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', '12135', '-6720']".to_string()}, RotationAngle::Deg0, "<path class=\"wb sw2 v\" d=\"M240.46-39.58l2.24 173.98\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"['12023', '1979', , '', '12135', '-6720']".to_string()}, RotationAngle::Deg0, "<path class=\"wb sw2 v\" d=\"M240.46-39.58l2.24 173.98\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg90, "<path class=\"wb sw2 v\" d=\"M13.36-78v35.34\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg180, "<path class=\"wb sw2 v\" d=\"M78 13.36h-35.34\"/>")]
    #[case(MapSubset{set_type:"vw".to_string(), coordinates:"[-3900,668,-2133,668]".to_string()}, RotationAngle::Deg270, "<path class=\"wb sw2 v\" d=\"M-13.36 78v-35.34\"/>")]
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