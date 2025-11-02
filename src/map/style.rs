use itertools::Itertools;
use ordermap::OrderSet;
use std::{collections::HashMap, sync::OnceLock};
use svg::node::element::{Line, Pattern};

#[cfg(test)]
use strum_macros::EnumIter;

// Additional objects definitions
#[derive(Eq, PartialEq, Hash, Copy, Clone)]
#[cfg_attr(test, derive(EnumIter))]
pub(super) enum Definition {
    DiagonalStripes,
}

struct DefinitionEntry {
    #[cfg(test)]
    id: &'static str,
    definition: Box<dyn svg::node::Node>,
}

impl DefinitionEntry {
    fn new(id: &'static str, factory: fn(&'static str) -> Box<dyn svg::node::Node>) -> Self {
        Self {
            #[cfg(test)]
            id,
            definition: factory(id),
        }
    }
}

fn get_definitions() -> &'static HashMap<Definition, DefinitionEntry> {
    static DEFINITIONS: OnceLock<HashMap<Definition, DefinitionEntry>> = OnceLock::new();
    DEFINITIONS.get_or_init(|| {
        HashMap::from([(
            Definition::DiagonalStripes,
            DefinitionEntry::new("ds", |id| -> Box<dyn svg::node::Node> {
                Box::new(
                    Pattern::new()
                        .set("id", id)
                        .set("x", 0)
                        .set("y", 0)
                        .set("width", 2)
                        .set("height", 2)
                        .set("patternUnits", "userSpaceOnUse")
                        .set("patternTransform", "rotate(45)")
                        .add(
                            Line::new()
                                .set("x1", 0)
                                .set("y1", 0)
                                .set("x2", 0)
                                .set("y2", 2)
                                .set("stroke", "rgba(0, 0, 0, 0.2)")
                                .set("stroke-width", 1),
                        ),
                )
            }),
        )])
    })
}

fn get_definition(def: Definition) -> Box<dyn svg::node::Node> {
    let entry = get_definitions().get(&def).unwrap();
    entry.definition.clone()
}

#[derive(Debug, Eq, PartialEq, Hash, Copy, Clone)]
#[cfg_attr(test, derive(EnumIter))]
pub(super) enum CSSClass {
    Path,

    FillNone,
    StrokeWidth2,

    OutlineStroke,

    RoomUnreachable,
    RoomUnknown,
    RoomColor0,
    RoomColor1,
    RoomColor2,
    RoomColor3,
    RoomColor4,
    RoomColor5,

    WallBase,
    VirtualWall,
    NoMoppingWall,
}

pub(super) const ROOM_COLORS: [CSSClass; 6] = [
    CSSClass::RoomColor0,
    CSSClass::RoomColor1,
    CSSClass::RoomColor2,
    CSSClass::RoomColor3,
    CSSClass::RoomColor4,
    CSSClass::RoomColor5,
];

macro_rules! css_entry {
    ($class_name:literal, $value:literal, $required_def:expr) => {
        CSSEntry {
            value: $value,
            class_name: $class_name,
            required_def: Some($required_def),
            identifier: concat!(".", $class_name),
        }
    };
    ($class_name:literal, $value:literal) => {
        CSSEntry {
            value: $value,
            class_name: $class_name,
            required_def: None,
            identifier: concat!(".", $class_name),
        }
    };
}

macro_rules! room_num {
    (RoomColor0) => {
        "0"
    };
    (RoomColor1) => {
        "1"
    };
    (RoomColor2) => {
        "2"
    };
    (RoomColor3) => {
        "3"
    };
    (RoomColor4) => {
        "4"
    };
    (RoomColor5) => {
        "5"
    };
}

macro_rules! room_color_entry {
    ($variant:ident, $color:literal) => {
        (
            CSSClass::$variant,
            CSSEntry {
                class_name: concat!("r", room_num!($variant)),
                value: concat!("fill: ", $color),
                required_def: None,
                identifier: concat!(".", "r", room_num!($variant)),
            },
        )
    };
}

fn get_styles() -> &'static HashMap<CSSClass, CSSEntry> {
    static STYLES: OnceLock<HashMap<CSSClass, CSSEntry>> = OnceLock::new();
    STYLES.get_or_init(|| {
        HashMap::from([
            (
                CSSClass::Path,
                CSSEntry {
                    identifier: "path",
                    value: "stroke-width: 1.5; vector-effect: non-scaling-stroke",
                    class_name: "path",
                    required_def: None,
                },
            ),
            (CSSClass::FillNone, css_entry!("f", "fill: none")),
            (
                CSSClass::StrokeWidth2,
                CSSEntry {
                    class_name: "s2",
                    value: "stroke-width: 2",
                    required_def: None,
                    identifier: ".s2 path",
                },
            ),
            (
                CSSClass::OutlineStroke,
                CSSEntry {
                    class_name: "o",
                    value: "stroke: #666666; stroke-linecap: round; stroke-linejoin: round",
                    required_def: None,
                    identifier: ".o path",
                },
            ),
            (CSSClass::RoomUnknown, css_entry!("u", "fill: #edf3fb")),
            (
                CSSClass::RoomUnreachable,
                css_entry!(
                    "ru",
                    "fill: url(#ds); mix-blend-mode: multiply;",
                    Definition::DiagonalStripes
                ),
            ),
            room_color_entry!(RoomColor0, "#a2bce7"),
            room_color_entry!(RoomColor1, "#ecd099"),
            room_color_entry!(RoomColor2, "#9bd4da"),
            room_color_entry!(RoomColor3, "#ecc6c9"),
            room_color_entry!(RoomColor4, "#d7bce3"),
            room_color_entry!(RoomColor5, "#c3e2b6"),
            (
                CSSClass::WallBase,
                CSSEntry {
                    class_name: "w",
                    value: "stroke-dasharray: 4",
                    required_def: None,
                    identifier: ".w path",
                },
            ),
            (
                CSSClass::VirtualWall,
                css_entry!("v", "stroke: #f00000; fill: #f0000030"),
            ),
            (
                CSSClass::NoMoppingWall,
                css_entry!("m", "stroke: #ffa500; fill: #ffa50030"),
            ),
        ])
    })
}

pub(super) fn get_style(css: &CSSClass) -> &'static CSSEntry {
    get_styles().get(css).unwrap()
}

pub(super) fn get_class_names(css: &[CSSClass]) -> String {
    css.iter()
        .map(|e| get_style(e).class_name)
        .collect::<Vec<&'static str>>()
        .join(" ")
}

pub(super) struct CSSEntry {
    pub class_name: &'static str,
    pub value: &'static str,
    pub required_def: Option<Definition>,

    pub identifier: &'static str,
}

pub(super) fn get_used_definitions(
    css_classes: &OrderSet<CSSClass>,
) -> Vec<Box<dyn svg::node::Node>> {
    css_classes
        .iter()
        .filter_map(|css_class| get_style(css_class).required_def)
        .unique()
        .map(|def| get_definition(def))
        .collect()
}

#[cfg(test)]
mod tests {
    use std::collections::HashSet;

    use super::*;
    use strum::IntoEnumIterator;

    #[test]
    fn test_get_styles_has_all_members() {
        let mut identifiers = HashSet::new();
        for variant in CSSClass::iter() {
            let style = get_style(&variant);
            assert!(
                identifiers.insert(style.identifier),
                "Identifiers are not unique: {}",
                style.identifier
            );
        }
    }

    #[test]
    fn test_get_definitions_has_all_members() {
        let mut identifiers = HashSet::new();
        for variant in Definition::iter() {
            let definition = get_definitions().get(&variant).unwrap();
            assert!(
                identifiers.insert(definition.id),
                "Definition IDs are not unique: {}",
                definition.id
            );
        }
    }
}
