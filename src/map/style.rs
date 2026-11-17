use itertools::Itertools;
use ordermap::OrderSet;
use std::{collections::HashMap, sync::OnceLock};
use svg::node::element::{Circle, Line, Pattern};

#[cfg(test)]
use strum_macros::EnumIter;

// Additional objects definitions
#[derive(Eq, PartialEq, Hash, Copy, Clone)]
#[cfg_attr(test, derive(EnumIter))]
pub(super) enum Definition {
    DiagonalStripes,
    CarpetDots,
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
        HashMap::from([
            (
                Definition::CarpetDots,
                DefinitionEntry::new("cd", |id| -> Box<dyn svg::node::Node> {
                    Box::new(
                        Pattern::new()
                            .set("id", id)
                            .set("width", 3)
                            .set("height", 3)
                            .set("patternUnits", "userSpaceOnUse")
                            .set("patternTransform", "rotate(45)")
                            .add(
                                Circle::new()
                                    .set("cx", 1.5)
                                    .set("cy", 1.5)
                                    .set("r", 0.55)
                                    .set("fill", "rgba(0, 0, 0, 0.28)"),
                            ),
                    )
                }),
            ),
            (
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
            ),
        ])
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

    Furniture,
    Carpet,

    TracePath,
    TraceCleaned,
    TraceLine,

    RoomLabels,
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
            dark_value: None,
            identifier: concat!(".", $class_name),
        }
    };
    ($class_name:literal, $value:literal) => {
        CSSEntry {
            value: $value,
            class_name: $class_name,
            required_def: None,
            dark_value: None,
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
    ($variant:ident, $color:literal, $dark_color:literal) => {
        (
            CSSClass::$variant,
            CSSEntry {
                class_name: concat!("r", room_num!($variant)),
                value: concat!("fill: ", $color),
                required_def: None,
                dark_value: Some(concat!("fill: ", $dark_color)),
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
                    dark_value: None,
                },
            ),
            (CSSClass::FillNone, css_entry!("f", "fill: none")),
            (
                CSSClass::StrokeWidth2,
                CSSEntry {
                    class_name: "s2",
                    value: "stroke-width: 2",
                    required_def: None,
                    dark_value: None,
                    identifier: ".s2 path",
                },
            ),
            (
                CSSClass::OutlineStroke,
                CSSEntry {
                    class_name: "o",
                    value: "stroke: #666666; stroke-linecap: round; stroke-linejoin: round",
                    required_def: None,
                    dark_value: Some("stroke: #a9afb8"),
                    identifier: ".o path",
                },
            ),
            (
                CSSClass::RoomUnknown,
                CSSEntry {
                    dark_value: Some("fill: #3b4350"),
                    ..css_entry!("u", "fill: #edf3fb")
                },
            ),
            (
                CSSClass::RoomUnreachable,
                css_entry!(
                    "ru",
                    "fill: url(#ds); mix-blend-mode: multiply;",
                    Definition::DiagonalStripes
                ),
            ),
            room_color_entry!(RoomColor0, "#a2bce7", "#5f7fb8"),
            room_color_entry!(RoomColor1, "#ecd099", "#b08f4d"),
            room_color_entry!(RoomColor2, "#9bd4da", "#4f9aa2"),
            room_color_entry!(RoomColor3, "#ecc6c9", "#b47a80"),
            room_color_entry!(RoomColor4, "#d7bce3", "#9273a6"),
            room_color_entry!(RoomColor5, "#c3e2b6", "#739a63"),
            (
                CSSClass::WallBase,
                CSSEntry {
                    class_name: "w",
                    value: "stroke-dasharray: 4",
                    required_def: None,
                    dark_value: None,
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
            (
                CSSClass::Furniture,
                CSSEntry {
                    dark_value: Some("fill: #0000004d; stroke: #ffffff80"),
                    ..css_entry!(
                        "fi",
                        "fill: #ffffff80; stroke: #00000066; stroke-width: 1; stroke-linejoin: round"
                    )
                },
            ),
            (
                CSSClass::Carpet,
                CSSEntry {
                    dark_value: Some("stroke: #ffffff59"),
                    ..css_entry!(
                        "ca",
                        "fill: url(#cd); stroke: #00000040; stroke-width: 1; stroke-linejoin: round",
                        Definition::CarpetDots
                    )
                },
            ),
            (
                // The trace path is defined once and used twice (cleaned area and line).
                // The stroke is therefore taken from the element using it.
                CSSClass::TracePath,
                css_entry!(
                    "t",
                    "fill: none; stroke-width: inherit; vector-effect: inherit; stroke-linejoin: round; stroke-linecap: round"
                ),
            ),
            (
                // 34 trace units are 34 cm, which is about the width cleaned by the bot
                CSSClass::TraceCleaned,
                css_entry!(
                    "tc",
                    "stroke: #fff; stroke-opacity: 0.35; stroke-width: 34; vector-effect: none"
                ),
            ),
            (
                CSSClass::TraceLine,
                css_entry!(
                    "tl",
                    "stroke: #fff; stroke-width: 1.5; vector-effect: non-scaling-stroke"
                ),
            ),
            (
                CSSClass::RoomLabels,
                CSSEntry {
                    dark_value: Some("fill: #f2f2f2; stroke: #000"),
                    ..css_entry!(
                        "l",
                        "font: 600 5px sans-serif; text-anchor: middle; dominant-baseline: central; fill: #2b2b2b; stroke: #fff; stroke-width: 1.4; stroke-opacity: 0.75; stroke-linejoin: round; paint-order: stroke"
                    )
                },
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
    /// Value used instead, when the viewer prefers a dark color scheme
    pub dark_value: Option<&'static str>,

    pub identifier: &'static str,
}

/// Build the content of the style element for the given classes
pub(super) fn get_stylesheet(css_classes: &OrderSet<CSSClass>) -> String {
    let mut light = String::new();
    let mut dark = String::new();
    for css_class in css_classes {
        let css = get_style(css_class);
        light.push_str(css.identifier);
        light.push('{');
        light.push_str(css.value);
        light.push('}');
        if let Some(dark_value) = css.dark_value {
            dark.push_str(css.identifier);
            dark.push('{');
            dark.push_str(dark_value);
            dark.push('}');
        }
    }
    if !dark.is_empty() {
        light.push_str("@media (prefers-color-scheme: dark){");
        light.push_str(&dark);
        light.push('}');
    }
    light
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
