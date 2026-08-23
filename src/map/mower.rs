use ordermap::OrderSet;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use svg::node::element::Group;

use super::points::{Point, points_to_svg_path};
use super::style::{CSSClass, ROOM_COLORS, get_class_names, get_style};
use super::{ROUND_TO_DIGITS, ViewBox, common::round};

type MowerGenerateResult = Option<(Vec<Box<dyn svg::node::Node>>, ViewBox, OrderSet<CSSClass>)>;

#[derive(FromPyObject, Clone, Debug, PartialEq)]
pub(super) struct MowerMapTraceSegment {
    points: Vec<(i32, i32)>,
    #[allow(dead_code)]
    raw: Option<String>,
}

#[derive(FromPyObject, Clone, Debug, PartialEq)]
pub(super) struct MowerMapTraceGroup {
    group_id: String,
    segments: Vec<MowerMapTraceSegment>,
}

#[derive(FromPyObject, Clone, Debug, PartialEq)]
pub(super) struct MowerStaticMap {
    mid: String,
    groups: Vec<MowerMapTraceGroup>,
    step_size: i32,
}

#[derive(FromPyObject, Clone, Debug, PartialEq)]
pub(super) struct MowerWorkArea {
    #[allow(dead_code)]
    name: String,
    geometry: MowerMapTraceGroup,
}

#[derive(FromPyObject, Clone, Debug, PartialEq)]
pub(super) struct MowerWorkAreas {
    mid: String,
    areas: Vec<MowerWorkArea>,
    step_size: i32,
}

#[derive(Clone, Debug, PartialEq)]
pub(super) struct MowerMapSnapshot {
    static_map: MowerStaticMap,
    work_areas: Option<MowerWorkAreas>,
}

impl MowerMapSnapshot {
    pub(super) fn new(
        static_map: MowerStaticMap,
        work_areas: Option<MowerWorkAreas>,
    ) -> PyResult<Self> {
        if static_map.step_size <= 0 {
            return Err(PyValueError::new_err(
                "Mower static-map step_size must be positive",
            ));
        }
        if let Some(areas) = &work_areas
            && (areas.mid != static_map.mid || areas.step_size != static_map.step_size)
        {
            return Err(PyValueError::new_err(
                "Mower work areas must match static-map mid and step_size",
            ));
        }
        Ok(Self {
            static_map,
            work_areas,
        })
    }

    pub(super) fn generate(&self) -> MowerGenerateResult {
        let step_size = self.static_map.step_size as f32;
        let boundary_segments = self
            .static_map
            .groups
            .iter()
            .flat_map(|group| &group.segments)
            .map(|segment| to_svg_points(segment, step_size))
            .filter(|points| points.len() >= 2)
            .collect::<Vec<_>>();
        let viewbox = calculate_viewbox(&boundary_segments)?;

        let mut elements: Vec<Box<dyn svg::node::Node>> = Vec::new();
        let mut styles = OrderSet::new();

        let mut boundary_fill =
            Group::new().set("class", get_class_names(&[CSSClass::RoomUnknown]));
        for points in &boundary_segments {
            if let Some(path) = points_to_svg_path(points, true, false) {
                boundary_fill = boundary_fill.add(path);
            }
        }
        elements.push(Box::new(boundary_fill));
        styles.insert(CSSClass::RoomUnknown);

        if let Some(work_areas) = &self.work_areas {
            let mut area_group =
                Group::new().set("class", get_class_names(&[CSSClass::OutlineStroke]));
            styles.insert(CSSClass::OutlineStroke);
            for (index, area) in work_areas.areas.iter().enumerate() {
                let color = ROOM_COLORS[index % ROOM_COLORS.len()];
                for segment in &area.geometry.segments {
                    let points = to_svg_points(segment, step_size);
                    if let Some(path) = points_to_svg_path(&points, true, false) {
                        area_group =
                            area_group.add(path.set("class", get_style(&color).class_name));
                        styles.insert(color);
                    }
                }
            }
            elements.push(Box::new(area_group));
        }

        let boundary_classes = [
            CSSClass::FillNone,
            CSSClass::OutlineStroke,
            CSSClass::StrokeWidth2,
        ];
        let mut boundary_outline = Group::new().set("class", get_class_names(&boundary_classes));
        for points in &boundary_segments {
            if let Some(path) = points_to_svg_path(points, true, false) {
                boundary_outline = boundary_outline.add(path);
            }
        }
        elements.push(Box::new(boundary_outline));
        styles.extend(boundary_classes);

        Some((elements, viewbox, styles))
    }
}

fn to_svg_points(segment: &MowerMapTraceSegment, step_size: f32) -> Vec<Point> {
    segment
        .points
        .iter()
        .map(|(x, y)| Point {
            x: round(*x as f32 / step_size, ROUND_TO_DIGITS),
            y: round(-(*y as f32) / step_size, ROUND_TO_DIGITS),
            connected: true,
        })
        .collect()
}

fn calculate_viewbox(segments: &[Vec<Point>]) -> Option<ViewBox> {
    let mut bounds: Option<(f32, f32, f32, f32)> = None;
    for point in segments.iter().flatten() {
        match &mut bounds {
            Some((min_x, min_y, max_x, max_y)) => {
                *min_x = min_x.min(point.x);
                *min_y = min_y.min(point.y);
                *max_x = max_x.max(point.x);
                *max_y = max_y.max(point.y);
            }
            None => bounds = Some((point.x, point.y, point.x, point.y)),
        }
    }
    let (min_x, min_y, max_x, max_y) = bounds?;
    let min_x = checked_i16(min_x.floor())?;
    let min_y = checked_i16(min_y.floor())?;
    let max_x = checked_i16(max_x.ceil())?;
    let max_y = checked_i16(max_y.ceil())?;
    Some(ViewBox {
        min_x,
        min_y,
        max_x,
        max_y,
        width: (max_x - min_x).max(1) as u16,
        height: (max_y - min_y).max(1) as u16,
    })
}

fn checked_i16(value: f32) -> Option<i16> {
    if value < i16::MIN as f32 || value > i16::MAX as f32 {
        None
    } else {
        Some(value as i16)
    }
}
