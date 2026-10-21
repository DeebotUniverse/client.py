use super::style::{CSSClass, ROOM_COLORS, get_class_names, get_style};
use super::{RotationAngle, ViewBox, calc_point, decompress_base64_data};

use super::points::{Point, points_to_svg_path};
use ordermap::OrderSet;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde::{Deserialize, Deserializer};
use std::collections::HashMap;
use std::hash::Hash;
use svg::node::element::Group;

type MapInfoGenerateResult = Option<(Vec<Box<dyn svg::node::Node>>, ViewBox, OrderSet<CSSClass>)>;

#[derive(Debug, PartialEq)]
struct MapInfoTypeDataEntry {
    points: Vec<Point>,
    close_path: bool,
}

#[derive(Debug, PartialEq, Hash, Eq, Clone, Copy)]
enum MapInfoType {
    Outline,
    Room,
    Unknown5, // Give it a better name if we know what it is
    BlockLine,
}

impl TryFrom<&str> for MapInfoType {
    type Error = &'static str;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            // 0 means all entries
            "1" => Ok(MapInfoType::Outline),
            "2" => Ok(MapInfoType::Room),
            // 3, 4 are unknown
            "5" => Ok(MapInfoType::Unknown5),
            "6" => Ok(MapInfoType::BlockLine),
            _ => Err("Invalid map info type"),
        }
    }
}

#[derive(Debug)]
struct MapInfoTypeEntry(MapInfoType, Vec<MapInfoTypeDataEntry>);

/// Map info entry, `None` if the layer type is unknown
#[derive(Debug)]
struct MaybeMapInfoTypeEntry(Option<MapInfoTypeEntry>);

#[derive(Debug)]
struct MapInfoLayer {
    map_info_type: MapInfoType,
    css: Vec<CSSClass>,
    force_connected: bool,
    colorize: bool,
}

impl<'de> Deserialize<'de> for MaybeMapInfoTypeEntry {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let raw: Vec<String> = Vec::deserialize(deserializer)?;

        let Some((first, rest)) = raw.split_first() else {
            return Err(serde::de::Error::custom("Empty map info entry"));
        };

        let Ok(map_info_type) = MapInfoType::try_from(first.as_str()) else {
            return Ok(MaybeMapInfoTypeEntry(None));
        };

        Ok(MaybeMapInfoTypeEntry(Some(MapInfoTypeEntry(
            map_info_type,
            match map_info_type {
                MapInfoType::Outline => process_map_info_outline_entries(rest),
                MapInfoType::Room => process_map_info_room_entries(rest),
                MapInfoType::BlockLine => process_map_info_room_entries(rest),
                MapInfoType::Unknown5 => Vec::new(),
            },
        ))))
    }
}

#[pyclass]
pub(super) struct MapInfo {
    data: HashMap<MapInfoType, Vec<MapInfoTypeDataEntry>>,
}

impl MapInfo {
    pub(super) fn new() -> Self {
        MapInfo {
            data: HashMap::new(),
        }
    }

    pub(super) fn generate(&self, rotation: RotationAngle) -> MapInfoGenerateResult {
        let mut viewbox = None;
        let order = self.get_order();
        let mut svg_elements: Vec<Box<dyn svg::node::Node>> = Vec::with_capacity(order.len());
        let mut used_styles = OrderSet::new();

        for layer in order {
            if let Some(entries) = self.data.get(&layer.map_info_type) {
                if entries.is_empty() {
                    continue;
                }

                // Normalize and rotate points
                let entries: Vec<MapInfoTypeDataEntry> = entries
                    .iter()
                    .map(|entry| {
                        let points = entry
                            .points
                            .iter()
                            .map(|point| {
                                let mut p = calc_point(point.x, point.y, rotation);
                                p.connected = point.connected;
                                p
                            })
                            .collect();
                        MapInfoTypeDataEntry {
                            points,
                            close_path: entry.close_path,
                        }
                    })
                    .collect();

                let mut group = Group::new().set("class", get_class_names(&layer.css));
                for (index, entry) in entries.iter().enumerate() {
                    if let Some(path) =
                        points_to_svg_path(&entry.points, entry.close_path, layer.force_connected)
                    {
                        let path = if layer.colorize {
                            let color_class = ROOM_COLORS[index % ROOM_COLORS.len()];
                            used_styles.insert(color_class);
                            path.set("class", get_style(&color_class).class_name)
                        } else {
                            path
                        };
                        group = group.add(path);
                    }
                }
                svg_elements.push(Box::new(group));
                used_styles.extend(layer.css);
                if layer.map_info_type == MapInfoType::Outline {
                    viewbox = calc_viewbox(&entries);
                }
            }
        }

        Some((svg_elements, viewbox?, used_styles))
    }

    fn get_order(&self) -> Vec<MapInfoLayer> {
        if self.data.contains_key(&MapInfoType::BlockLine) {
            vec![
                MapInfoLayer {
                    map_info_type: MapInfoType::Room,
                    css: vec![],
                    force_connected: false,
                    colorize: true,
                },
                MapInfoLayer {
                    map_info_type: MapInfoType::Room,
                    css: vec![CSSClass::RoomUnreachable],
                    force_connected: false,
                    colorize: false,
                },
                MapInfoLayer {
                    map_info_type: MapInfoType::BlockLine,
                    css: vec![],
                    force_connected: false,
                    colorize: true,
                },
                MapInfoLayer {
                    map_info_type: MapInfoType::Outline,
                    css: vec![
                        CSSClass::FillNone,
                        CSSClass::OutlineStroke,
                        CSSClass::StrokeWidth2,
                    ],
                    force_connected: false,
                    colorize: false,
                },
            ]
        } else {
            vec![
                MapInfoLayer {
                    map_info_type: MapInfoType::Outline,
                    css: vec![CSSClass::RoomUnknown],
                    force_connected: true,
                    colorize: false,
                },
                MapInfoLayer {
                    map_info_type: MapInfoType::Room,
                    css: vec![CSSClass::OutlineStroke],
                    force_connected: false,
                    colorize: true,
                },
                MapInfoLayer {
                    map_info_type: MapInfoType::Outline,
                    css: vec![
                        CSSClass::FillNone,
                        CSSClass::OutlineStroke,
                        CSSClass::StrokeWidth2,
                    ],
                    force_connected: false,
                    colorize: false,
                },
            ]
        }
    }
}

#[pymethods]
impl MapInfo {
    fn set(&mut self, base64_data: String) -> PyResult<()> {
        let raw = decompress_base64_data(&base64_data)
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        let entries: Vec<MaybeMapInfoTypeEntry> = serde_json::from_slice(&raw)
            .map_err(|err| PyValueError::new_err(format!("Invalid map info: {err}")))?;
        entries
            .into_iter()
            .filter_map(|MaybeMapInfoTypeEntry(entry)| entry)
            .for_each(|MapInfoTypeEntry(t, v)| {
                if !v.is_empty() {
                    self.data.insert(t, v);
                }
            });
        Ok(())
    }
}

fn process_map_info_outline_entries(data: &[String]) -> Vec<MapInfoTypeDataEntry> {
    // Pre-allocate with estimated capacity
    let filtered_count = data.iter().filter(|e| !e.is_empty()).count();
    let mut outlines = Vec::with_capacity(filtered_count);

    for entry in data.iter().filter(|e| !e.is_empty()) {
        let parts = entry.split(';').filter(|s| !s.is_empty()).skip(1); // skip the outline ID
        let mut path_points = Vec::new();

        for spec in parts {
            let mut coords = spec.splitn(3, ','); // coordinates are "x,y,type"
            if let (Some(x_str), Some(y_str)) = (coords.next(), coords.next())
                && let (Ok(x), Ok(y)) = (x_str.parse::<f32>(), y_str.parse::<f32>())
            {
                path_points.push(Point {
                    x,
                    y,
                    connected: coords.next().unwrap_or("1").trim() != "3-1-0",
                });
            }
        }

        // close the path back to the first point, if it should be connected
        // cannot use close_path here, because some outlines have multiple sub-paths (move commands)
        if let Some(first) = path_points.first().filter(|p| p.connected) {
            path_points.push(Point {
                x: first.x,
                y: first.y,
                connected: true,
            });
        }

        outlines.push(MapInfoTypeDataEntry {
            close_path: false,
            points: path_points,
        });
    }

    outlines
}

#[inline]
fn parse_coords(s: &str) -> Option<(f32, f32)> {
    let mut it = s.splitn(2, ',');
    let x = it.next()?.parse::<f32>().ok()?;
    let y = it.next()?.parse::<f32>().ok()?;
    Some((x, y))
}

fn process_map_info_room_entries(data: &[String]) -> Vec<MapInfoTypeDataEntry> {
    // Pre-allocate with estimated capacity
    let filtered_count = data.iter().filter(|e| !e.is_empty()).count();
    let mut rooms = Vec::with_capacity(filtered_count);

    for entry in data.iter().filter(|e| !e.is_empty()) {
        let poly_points: Vec<Point> = entry
            .split(';')
            .filter(|s| !s.is_empty())
            .skip(1) // skip the area ID
            .filter_map(parse_coords)
            .map(|(x, y)| Point {
                x,
                y,
                connected: true,
            })
            .collect();

        if poly_points.len() >= 3 {
            rooms.push(MapInfoTypeDataEntry {
                close_path: true,
                points: poly_points,
            });
        }
    }

    rooms
}

#[inline]
fn calc_viewbox(outlines: &[MapInfoTypeDataEntry]) -> Option<ViewBox> {
    let mut bounds = None;
    outlines
        .iter()
        .for_each(|e| minmax_points(e.points.iter(), &mut bounds));

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

#[inline]
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

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;

    #[rstest]
    #[case("1", Ok(MapInfoType::Outline))]
    #[case("2", Ok(MapInfoType::Room))]
    #[case("5", Ok(MapInfoType::Unknown5))]
    #[case("6", Ok(MapInfoType::BlockLine))]
    #[case("invalid", Err("Invalid map info type"))]
    fn test_map_info_type_try_from(
        #[case] input: &str,
        #[case] expected: Result<MapInfoType, &str>,
    ) {
        assert_eq!(MapInfoType::try_from(input), expected);
    }

    #[test]
    fn test_deserialize_empty_entry() {
        let data = "[[],[\"1\"]]".as_bytes();
        let entries: serde_json::Result<Vec<MaybeMapInfoTypeEntry>> = serde_json::from_slice(data);
        assert!(entries.is_err());
        assert_eq!(
            entries.unwrap_err().to_string(),
            "Empty map info entry at line 1 column 4"
        );
    }

    #[rstest]
    #[case("3")]
    #[case("4")]
    #[case("7")]
    #[case("99")]
    #[case("unexpected")]
    fn test_deserialize_skips_unknown_type(#[case] unknown_type: &str) {
        let data =
            format!("[[\"1\",\"0;0,0,2;100,0,2;100,100,2\"],[\"{unknown_type}\",\"1;5,5;6,6\"]]");
        let entries: Vec<MaybeMapInfoTypeEntry> =
            serde_json::from_slice(data.as_bytes()).expect("unknown type must not fail parsing");

        let known: Vec<MapInfoTypeEntry> = entries.into_iter().filter_map(|e| e.0).collect();
        assert_eq!(known.len(), 1);
        assert_eq!(known[0].0, MapInfoType::Outline);
    }

    #[test]
    fn test_set_keeps_known_layers_alongside_unknown() {
        let mut map_info = MapInfo::new();
        let entries: Vec<MaybeMapInfoTypeEntry> = serde_json::from_slice(
            b"[[\"1\",\"0;0,0,2;100,0,2;100,100,2\"],[\"7\",\"1;5,5;6,6\"],[\"2\",\"1;0,0;50,0;50,50\"]]",
        )
        .expect("unknown type must not fail parsing");
        entries
            .into_iter()
            .filter_map(|MaybeMapInfoTypeEntry(entry)| entry)
            .for_each(|MapInfoTypeEntry(t, v)| {
                if !v.is_empty() {
                    map_info.data.insert(t, v);
                }
            });

        assert!(map_info.data.contains_key(&MapInfoType::Outline));
        assert!(map_info.data.contains_key(&MapInfoType::Room));
        assert_eq!(map_info.data.len(), 2);
    }
}
