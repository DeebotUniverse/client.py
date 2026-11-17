use super::style::{CSSClass, ROOM_COLORS, get_class_names, get_style};
use super::{RotationAngle, ViewBox, calc_point, decompress_base64_data};

use super::points::{Point, points_to_svg_path};
use log::debug;
use ordermap::OrderSet;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde::{Deserialize, Deserializer};
use std::collections::HashMap;
use std::hash::Hash;
use svg::node::element::Group;

/// Result of the map info rendering
pub(super) struct MapInfoGenerated {
    pub elements: Vec<Box<dyn svg::node::Node>>,
    pub viewbox: ViewBox,
    pub styles: OrderSet<CSSClass>,
    /// Center of each room polygon (already rotated), keyed by the room id
    pub room_centers: HashMap<u32, (f32, f32)>,
}

#[derive(Debug, PartialEq)]
struct MapInfoTypeDataEntry {
    /// Area id, when the entry belongs to a room
    id: Option<u32>,
    points: Vec<Point>,
    close_path: bool,
}

/// Assign a color index to each room id.
///
/// The color depends on the room id and not on the position in the list, so it stays the same
/// between updates. Colors are used evenly and rooms next to each other get different colors
/// when the neighbors are known.
fn assign_room_colors(
    ids: impl Iterator<Item = u32>,
    neighbors: &HashMap<u32, Vec<u32>>,
) -> HashMap<u32, usize> {
    let color_count = ROOM_COLORS.len();
    let mut known: Vec<u32> = ids.collect();
    known.sort_unstable();
    known.dedup();

    let are_neighbors = |a: &u32, b: &u32| {
        neighbors.get(a).is_some_and(|n| n.contains(b))
            || neighbors.get(b).is_some_and(|n| n.contains(a))
    };

    let mut assigned: HashMap<u32, usize> = HashMap::with_capacity(known.len());
    let mut usage = vec![0usize; color_count];
    for id in known {
        let preferred = id as usize % color_count;
        // Starting with the preferred one, take the least used color, which no neighbor has
        let color = (0..color_count)
            .map(|offset| (preferred + offset) % color_count)
            .filter(|candidate| {
                !assigned
                    .iter()
                    .any(|(other, color)| color == candidate && are_neighbors(&id, other))
            })
            .min_by_key(|candidate| usage[*candidate])
            .unwrap_or(preferred);
        usage[color] += 1;
        assigned.insert(id, color);
    }

    assigned
}

#[derive(Debug, PartialEq, Hash, Eq, Clone, Copy)]
enum MapInfoType {
    Outline,
    Room,
    Unknown5, // Give it a better name if we know what it is
    BlockLine,
    /// Layer type, which is not known and therefore ignored
    Unknown,
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

#[derive(Debug)]
struct MapInfoLayer {
    map_info_type: MapInfoType,
    css: Vec<CSSClass>,
    force_connected: bool,
    colorize: bool,
}

impl<'de> Deserialize<'de> for MapInfoTypeEntry {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let raw: Vec<String> = Vec::deserialize(deserializer)?;

        if let Some((first, rest)) = raw.split_first() {
            let Ok(map_info_type) = MapInfoType::try_from(first.as_str()) else {
                // Newer firmwares send layers we don't know (yet). Ignore them instead of
                // rejecting the whole map.
                debug!("Skipping unknown map info layer type: {first}");
                return Ok(MapInfoTypeEntry(MapInfoType::Unknown, Vec::new()));
            };
            Ok(MapInfoTypeEntry(
                map_info_type,
                match map_info_type {
                    MapInfoType::Outline => process_map_info_outline_entries(rest),
                    MapInfoType::Room => process_map_info_room_entries(rest),
                    MapInfoType::BlockLine => process_map_info_room_entries(rest),
                    MapInfoType::Unknown5 | MapInfoType::Unknown => Vec::new(),
                },
            ))
        } else {
            Err(serde::de::Error::custom("Empty map info entry"))
        }
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

    pub(super) fn generate(
        &self,
        rotation: RotationAngle,
        neighbors: &HashMap<u32, Vec<u32>>,
    ) -> Option<MapInfoGenerated> {
        let mut viewbox = None;
        let mut room_centers = HashMap::new();
        let order = self.get_order();
        let mut svg_elements: Vec<Box<dyn svg::node::Node>> = Vec::with_capacity(order.len());
        let mut used_styles = OrderSet::new();
        // Based on the ids of all layers, so a room has the same color in each of them
        let room_colors = assign_room_colors(
            [MapInfoType::Room, MapInfoType::BlockLine]
                .iter()
                .filter_map(|map_info_type| self.data.get(map_info_type))
                .flatten()
                .filter_map(|entry| entry.id),
            neighbors,
        );

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
                            id: entry.id,
                            points,
                            close_path: entry.close_path,
                        }
                    })
                    .collect();

                if layer.map_info_type == MapInfoType::Room && room_centers.is_empty() {
                    for entry in &entries {
                        let mut bounds = None;
                        minmax_points(entry.points.iter(), &mut bounds);
                        if let (Some(id), Some((min_x, min_y, max_x, max_y))) = (entry.id, bounds) {
                            room_centers.insert(id, ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0));
                        }
                    }
                }

                let mut group = Group::new().set("class", get_class_names(&layer.css));
                for (index, entry) in entries.iter().enumerate() {
                    if let Some(path) =
                        points_to_svg_path(&entry.points, entry.close_path, layer.force_connected)
                    {
                        let path = if layer.colorize {
                            // Entries without id fall back to their position
                            let color = entry
                                .id
                                .and_then(|id| room_colors.get(&id).copied())
                                .unwrap_or(index % ROOM_COLORS.len());
                            let color_class = ROOM_COLORS[color];
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

        Some(MapInfoGenerated {
            elements: svg_elements,
            viewbox: viewbox?,
            styles: used_styles,
            room_centers,
        })
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
        let entries: Vec<MapInfoTypeEntry> = serde_json::from_slice(&raw)
            .map_err(|err| PyValueError::new_err(format!("Invalid map info: {err}")))?;
        entries.into_iter().for_each(|MapInfoTypeEntry(t, v)| {
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
        let mut parts = entry.split(';').filter(|s| !s.is_empty());
        let id = parts.next().and_then(|s| s.trim().parse::<u32>().ok());
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
            id,
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
        let mut parts = entry.split(';').filter(|s| !s.is_empty());
        let id = parts.next().and_then(|s| s.trim().parse::<u32>().ok());
        let poly_points: Vec<Point> = parts
            .filter_map(parse_coords)
            .map(|(x, y)| Point {
                x,
                y,
                connected: true,
            })
            .collect();

        if poly_points.len() >= 3 {
            rooms.push(MapInfoTypeDataEntry {
                id,
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
    fn test_deserialize_unknown_layer_is_skipped() {
        let data = r#"[["3","0;1,1;2,2;3,3"],["2","4;0,0;100,0;100,100"]]"#.as_bytes();
        let entries: Vec<MapInfoTypeEntry> = serde_json::from_slice(data).unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].0, MapInfoType::Unknown);
        assert!(entries[0].1.is_empty());
        assert_eq!(entries[1].0, MapInfoType::Room);
        assert_eq!(entries[1].1[0].id, Some(4));
    }

    #[rstest]
    // Ids in order get the colors in order
    #[case(&[0, 1, 2], &[], &[0, 1, 2])]
    // The color depends on the id, not on the position
    #[case(&[3, 4], &[], &[3, 4])]
    #[case(&[4, 3], &[], &[4, 3])]
    // An id, which is listed more than once, is counted once
    #[case(&[0, 1, 7, 0, 7], &[], &[0, 1, 2, 0, 2])]
    // 7 would prefer the color of 1, but an unused color is taken first
    #[case(&[0, 1, 7], &[], &[0, 1, 2])]
    // All colors are used once, so 7 gets its preferred one ...
    #[case(&[0, 1, 2, 3, 4, 5, 7], &[], &[0, 1, 2, 3, 4, 5, 1])]
    // ... unless a neighbor has it already
    #[case(&[0, 1, 2, 3, 4, 5, 7], &[(7, 1)], &[0, 1, 2, 3, 4, 5, 2])]
    // Neighbors are symmetric, even if only one side lists the other
    #[case(&[0, 1, 2, 3, 4, 5, 7], &[(1, 7)], &[0, 1, 2, 3, 4, 5, 2])]
    fn test_assign_room_colors(
        #[case] ids: &[u32],
        #[case] neighbors: &[(u32, u32)],
        #[case] expected: &[usize],
    ) {
        let neighbors: HashMap<u32, Vec<u32>> = neighbors
            .iter()
            .map(|(id, other)| (*id, vec![*other]))
            .collect();
        let colors = assign_room_colors(ids.iter().copied(), &neighbors);
        let colors: Vec<usize> = ids.iter().map(|id| colors[id]).collect();
        assert_eq!(colors, expected);
    }

    #[test]
    fn test_deserialize_empty_entry() {
        let data = "[[],[\"1\"]]".as_bytes();
        let entries: serde_json::Result<Vec<MapInfoTypeEntry>> = serde_json::from_slice(data);
        assert!(entries.is_err());
        assert_eq!(
            entries.unwrap_err().to_string(),
            "Empty map info entry at line 1 column 4"
        );
    }

    #[test]
    fn test_generate_skips_empty_layers_and_entries_without_path() {
        let point = |x, y| Point {
            x,
            y,
            connected: true,
        };
        let map_info = MapInfo {
            data: HashMap::from([
                (MapInfoType::Room, Vec::new()),
                (
                    MapInfoType::Outline,
                    vec![
                        MapInfoTypeDataEntry {
                            id: None,
                            points: vec![point(0.0, 0.0)],
                            close_path: false,
                        },
                        MapInfoTypeDataEntry {
                            id: None,
                            points: vec![point(0.0, 0.0), point(5000.0, 5000.0)],
                            close_path: false,
                        },
                    ],
                ),
            ]),
        };

        let elements = map_info
            .generate(RotationAngle::Deg0, &HashMap::new())
            .unwrap()
            .elements;

        // Empty room layer is skipped; both outline layers only contain the valid entry
        assert_eq!(elements.len(), 2);
        for element in elements {
            assert_eq!(element.to_string().matches("<path").count(), 1);
        }
    }

    #[test]
    fn test_generate_same_room_color_in_all_layers() {
        let entry = |id| MapInfoTypeDataEntry {
            id,
            points: [(0.0, 0.0), (5000.0, 0.0), (5000.0, 5000.0)]
                .iter()
                .map(|(x, y)| Point {
                    x: *x,
                    y: *y,
                    connected: true,
                })
                .collect(),
            close_path: true,
        };
        let map_info = MapInfo {
            data: HashMap::from([
                (
                    MapInfoType::Room,
                    vec![entry(Some(0)), entry(Some(1)), entry(Some(7))],
                ),
                // Not all rooms have block lines and entries without id are possible
                (
                    MapInfoType::BlockLine,
                    vec![entry(Some(7)), entry(Some(0)), entry(None)],
                ),
                (MapInfoType::Outline, vec![entry(None)]),
            ]),
        };

        let elements = map_info
            .generate(RotationAngle::Deg0, &HashMap::new())
            .unwrap()
            .elements;
        let path_classes = |index: usize| -> Vec<String> {
            elements[index]
                .to_string()
                .split("<path")
                .skip(1)
                .map(|path| {
                    let class = path.split("class=\"").nth(1).unwrap();
                    class.split('"').next().unwrap().to_string()
                })
                .collect()
        };
        let class_name = |color: usize| get_style(&ROOM_COLORS[color]).class_name.to_string();

        // Layers: rooms, unreachable rooms, block lines, outline
        assert_eq!(elements.len(), 4);
        assert_eq!(
            path_classes(0),
            vec![class_name(0), class_name(1), class_name(2)]
        );
        // Entries without id fall back to their position
        assert_eq!(
            path_classes(2),
            vec![class_name(2), class_name(0), class_name(2)]
        );
    }
}
