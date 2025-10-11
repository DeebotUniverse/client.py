use super::{calc_point, decompress_base64_data, ViewBox};

use super::points::{points_to_svg_path, Point};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::{Group, Polygon};

const MAP_INFO_TYPE_OUTLINE: &str = "1";
const MAP_INFO_TYPE_ROOM: &str = "2";
const MAP_INFO_TYPE_BLOCK_LINE: &str = "6";

// Visual style to match the background image look & feel
const STYLE_OUTLINE_KEY: &str = "o";
const STYLE_OUTLINE_CSS_IDENTIFIER: &str = ".o path";
const STYLE_OUTLINE_VALUE: &str =
    "fill: none; stroke: #4e96e2; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3";
const STYLE_ROOMS_KEY: &str = "r";
const STYLE_ROOMS_CSS_IDENTIFIER: &str = ".r";
const STYLE_ROOMS_VALUE: &str = "fill: #edf3fb";
const STYLE_BLOCK_LINES_KEY: &str = "b";
const STYLE_BLOCK_LINES_CSS_IDENTIFIER: &str = ".b";
const STYLE_BLOCK_LINES_VALUE: &str = "fill: #badaff";

type MapV2Info = Vec<Vec<String>>;
type MapInfoGenerateResult = Option<(
    Vec<Box<dyn svg::node::Node>>,
    ViewBox,
    Vec<(&'static str, &'static str)>,
)>;

#[pyclass]
pub(super) struct MapInfo {
    outlines: Vec<Vec<Point>>,
    areas: Vec<Vec<Point>>,
    block_lines: Vec<Vec<Point>>,
}

impl MapInfo {
    pub(super) fn new() -> Self {
        MapInfo {
            outlines: Vec::new(),
            areas: Vec::new(),
            block_lines: Vec::new(),
        }
    }

    pub(super) fn generate(&self) -> MapInfoGenerateResult {
        let viewbox = self.viewbox_from_outlines()?;
        let mut svg_elements: Vec<Box<dyn svg::node::Node>> = Vec::new();
        let mut styles = Vec::new();

        if !self.areas.is_empty() {
            // Add entire rooms as unreachable and overlay reachable sections
            let mut group = Group::new().set("class", STYLE_ROOMS_KEY);
            for polygon in add_polygons_to_svg(&self.areas) {
                group = group.add(polygon);
            }
            svg_elements.push(Box::new(group));
            styles.push((STYLE_ROOMS_CSS_IDENTIFIER, STYLE_ROOMS_VALUE));
        }

        if !self.block_lines.is_empty() {
            let mut group = Group::new().set("class", STYLE_BLOCK_LINES_KEY);
            for polygon in add_polygons_to_svg(&self.block_lines) {
                group = group.add(polygon);
            }
            svg_elements.push(Box::new(group));
            styles.push((STYLE_BLOCK_LINES_CSS_IDENTIFIER, STYLE_BLOCK_LINES_VALUE));
        }

        // Add map outline on top
        if !self.outlines.is_empty() {
            let mut outline_group = Group::new().set("class", STYLE_OUTLINE_KEY);
            for outline in &self.outlines {
                if let Some(path) = points_to_svg_path(outline) {
                    outline_group = outline_group.add(path);
                }
            }
            svg_elements.push(Box::new(outline_group));
            styles.push((STYLE_OUTLINE_CSS_IDENTIFIER, STYLE_OUTLINE_VALUE));
        }

        Some((svg_elements, viewbox, styles))
    }

    fn viewbox_from_outlines(&self) -> Option<ViewBox> {
        let mut bounds = None;
        self.outlines
            .iter()
            .for_each(|path| minmax_points(path.iter(), &mut bounds));

        let (min_x_f, min_y_f, max_x_f, max_y_f) = bounds?;
        let (min_x, min_y) = (min_x_f.round() as i16, min_y_f.round() as i16);
        let (max_x, max_y) = (max_x_f.round() as i16, max_y_f.round() as i16);
        let (width, height) = ((max_x - min_x).max(1) as u16, (max_y - min_y).max(1) as u16);

        Some(ViewBox {
            min_x,
            min_y,
            max_x,
            max_y,
            width,
            height,
        })
    }

    fn parse_map_info(&mut self, info: MapV2Info) {
        for group in &info {
            let Some(first) = group.first() else { continue };
            match first.as_str() {
                MAP_INFO_TYPE_OUTLINE => self.outlines = process_map_info_outline_entries(group),
                MAP_INFO_TYPE_ROOM => self.areas = process_map_info_polygon_entries(group),
                MAP_INFO_TYPE_BLOCK_LINE => {
                    self.block_lines = process_map_info_polygon_entries(group)
                }
                _ => {}
            }
        }
    }
}

#[pymethods]
impl MapInfo {
    fn set(&mut self, base64_data: String) -> PyResult<()> {
        let raw = decompress_base64_data(&base64_data)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let info: MapV2Info = serde_json::from_slice(&raw)
            .map_err(|err| PyValueError::new_err(format!("Invalid map info: {err}")))?;
        self.parse_map_info(info);
        Ok(())
    }
}

fn process_map_info_outline_entries(group: &[String]) -> Vec<Vec<Point>> {
    let mut outlines = Vec::new();

    for entry in group.iter().skip(1).filter(|e| !e.is_empty()) {
        let parts = entry.split(';').filter(|s| !s.is_empty()).skip(1); // skip the outline ID
        let mut path_points = Vec::new();

        for spec in parts {
            let mut coords = spec.splitn(3, ','); // coordinates are "x,y,type"
            if let (Some(x_str), Some(y_str)) = (coords.next(), coords.next()) {
                if let (Ok(x), Ok(y)) = (x_str.parse::<f32>(), y_str.parse::<f32>()) {
                    let mut p = calc_point(x, y);
                    p.connected = coords.next().unwrap_or("1").trim() != "3-1-0"; // lines to points of type "3-1-0" are not displayed
                    path_points.push(p);
                }
            }
        }

        // close the path back to the first point, if it should be connected
        if let Some(first) = path_points.first().filter(|p| p.connected) {
            path_points.push(Point {
                x: first.x,
                y: first.y,
                connected: true,
            });
        }
        outlines.push(path_points);
    }

    outlines
}

fn parse_coords(s: &str) -> Option<(f32, f32)> {
    let mut it = s.splitn(2, ',');
    let x = it.next()?.parse::<f32>().ok()?;
    let y = it.next()?.parse::<f32>().ok()?;
    Some((x, y))
}

fn process_map_info_polygon_entries(group: &[String]) -> Vec<Vec<Point>> {
    let mut polygons = Vec::new();

    for entry in group.iter().skip(1).filter(|e| !e.is_empty()) {
        let poly_points: Vec<Point> = entry
            .split(';')
            .filter(|s| !s.is_empty())
            .skip(1) // skip the area ID
            .filter_map(parse_coords)
            .map(|(x, y)| calc_point(x, y))
            .collect();

        if poly_points.len() >= 3 {
            polygons.push(poly_points);
        }
    }

    polygons
}

fn minmax_points<'a, I: Iterator<Item = &'a Point>>(
    iter: I,
    bounds: &mut Option<(f32, f32, f32, f32)>,
) {
    for p in iter {
        match bounds {
            Some((min_x, min_y, max_x, max_y)) => {
                *min_x = min_x.min(p.x);
                *min_y = min_y.min(p.y);
                *max_x = max_x.max(p.x);
                *max_y = max_y.max(p.y);
            }
            None => *bounds = Some((p.x, p.y, p.x, p.y)),
        }
    }
}

fn add_polygons_to_svg<'a>(polygons: &'a [Vec<Point>]) -> impl Iterator<Item = Polygon> + 'a {
    polygons.iter().filter_map(move |p| {
        if p.len() >= 3 {
            let coords: Vec<f32> = p.iter().flat_map(|p| vec![p.x, p.y]).collect();
            Some(Polygon::new().set("points", coords))
        } else {
            None
        }
    })
}
