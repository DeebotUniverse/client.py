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

type DefinitionFactory = fn(&'static str) -> Box<dyn svg::node::Node>;

struct DefinitionEntry {
    id: &'static str,
    factory: DefinitionFactory,
}

fn get_definitions() -> &'static HashMap<Definition, DefinitionEntry> {
    static DEFINITIONS: OnceLock<HashMap<Definition, DefinitionEntry>> = OnceLock::new();
    DEFINITIONS.get_or_init(|| {
        HashMap::from([(
            Definition::DiagonalStripes,
            DefinitionEntry {
                id: "ds",
                factory: (|id| -> Box<dyn svg::node::Node> {
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
            },
        )])
    })
}

pub(super) fn get_definition(def: &Definition) -> Box<dyn svg::node::Node> {
    let entry = get_definitions().get(def).unwrap();
    (entry.factory)(entry.id)
}

#[derive(Debug, Eq, PartialEq, Hash, Copy, Clone)]
#[cfg_attr(test, derive(EnumIter))]
pub(super) enum CSSClass {
    Path,
    FillNone,
    OutlineStroke,
    RoomUnreachable,
    RoomUnknown,
    RoomColor1,
    RoomColor2,
    RoomColor3,
    RoomColor4,
    RoomColor5,
    RoomColor6,
    WallBase,
    VirtualWall,
    NoMoppingWall,
}

fn get_styles() -> &'static HashMap<CSSClass, CSSEntry> {
    static STYLES: OnceLock<HashMap<CSSClass, CSSEntry>> = OnceLock::new();
    STYLES.get_or_init(|| {
        HashMap::from([
            (CSSClass::Path, CSSEntry{
                identifier: "path",
                value: "stroke-width: 1.5; vector-effect: non-scaling-stroke",
                class_name: "path",
                required_def: None,
            }),
            (CSSClass::FillNone, CSSEntry {
                identifier: ".f",
                value: "fill: none",
                class_name: "f",
                required_def: None,
            }),
            (CSSClass::OutlineStroke, CSSEntry {
                identifier: ".o path",
                value: "stroke: #666666; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3",
                class_name: "o",
                required_def: None,
            }),
            (CSSClass::RoomUnknown, CSSEntry {
                identifier: ".u",
                value: "fill: #edf3fb",
                class_name: "u",
                required_def: None,
            }),
            (CSSClass::RoomUnreachable, CSSEntry {
                identifier: ".r",
                value: "fill: url(#ds); mix-blend-mode: multiply;",
                class_name: "r",
                required_def: Some(Definition::DiagonalStripes),
            }),
            (CSSClass::RoomColor1, CSSEntry {
                identifier: ".r1",
                value: "fill: #a2bce7",
                class_name: "r1",
                required_def: None,
            }),
            (CSSClass::RoomColor2, CSSEntry {
                identifier: ".r2",
                value: "fill: #ecd099",
                class_name: "r2",
                required_def: None,
            }),
            (CSSClass::RoomColor3, CSSEntry {
                identifier: ".r3",
                value: "fill: #9bd4da",
                class_name: "r3",
                required_def: None,
            }),
            (CSSClass::RoomColor4, CSSEntry {
                identifier: ".r4",
                value: "fill: #ecc6c9",
                class_name: "r4",
                required_def: None,
            }),
            (CSSClass::RoomColor5, CSSEntry {
                identifier: ".r5",
                value: "fill: #d7bce3",
                class_name: "r5",
                required_def: None,
            }),
            (CSSClass::RoomColor6, CSSEntry {
                identifier: ".r6",
                value: "fill: #c3e2b6",
                class_name: "r6",
                required_def: None,
            }),
            (CSSClass::WallBase, CSSEntry {
                identifier: ".w path",
                value: "stroke-dasharray: 4; stroke-width: 3",
                class_name: "w",
                required_def: None,
            }),
            (CSSClass::VirtualWall, CSSEntry {
                identifier: ".v",
                value: "stroke: #f00000; fill: #f0000030",
                class_name: "v",
                required_def: None,
            }),
            (CSSClass::NoMoppingWall, CSSEntry {
                identifier: ".m",
                value: "stroke: #ffa500; fill: #ffa50030",
                class_name: "m",
                required_def: None,
            }),
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
    pub identifier: &'static str,
    pub value: &'static str,
    pub class_name: &'static str,
    pub required_def: Option<Definition>,
}

pub(super) fn get_required_definitions(css_classes: &OrderSet<CSSClass>) -> OrderSet<Definition> {
    css_classes
        .iter()
        .filter_map(|css_class| get_style(css_class).required_def)
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
