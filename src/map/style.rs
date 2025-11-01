use std::{collections::HashMap, sync::OnceLock};

#[cfg(test)]
use strum_macros::EnumIter;

#[derive(Eq, PartialEq, Hash, Copy, Clone)]
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
    WallBase,
    VirtualWall,
    NoMoppingWall,
}

// Visual style to match the background image look & feel
fn get_styles() -> &'static HashMap<CSSClass, CSSEntry> {
    static STYLES: OnceLock<HashMap<CSSClass, CSSEntry>> = OnceLock::new();
    STYLES.get_or_init(|| {
        HashMap::from([
            (CSSClass::Path, CSSEntry{
                identifier: "path",
                value: "stroke-width: 1.5; vector-effect: non-scaling-stroke",
                class_name: "path",
            }),
            (CSSClass::FillNone, CSSEntry {
                identifier: ".f",
                value: "fill: none",
                class_name: "f",
            }),
            (CSSClass::OutlineStroke, CSSEntry {
                identifier: ".o path",
                value: "stroke: #4e96e2; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3",
                class_name: "o",
            }),
            (CSSClass::RoomUnknown, CSSEntry {
                identifier: ".u",
                value: "fill: #edf3fb",
                class_name: "u",
            }),
            (CSSClass::RoomUnreachable, CSSEntry {
                identifier: ".r",
                value: "fill: url(#ds); mix-blend-mode: multiply;",
                class_name: "r",
            }),
            (CSSClass::RoomColor1, CSSEntry {
                identifier: ".r1",
                value: "fill: #a2bce7",
                class_name: "r1",
            }),
            (CSSClass::RoomColor2, CSSEntry {
                identifier: ".r2",
                value: "fill: #ecd099",
                class_name: "r2",
            }),
            (CSSClass::RoomColor3, CSSEntry {
                identifier: ".r3",
                value: "fill: #9bd4da",
                class_name: "r3",
            }),
            (CSSClass::RoomColor4, CSSEntry {
                identifier: ".r4",
                value: "fill: #ecc6c9",
                class_name: "r4",
            }),
            (CSSClass::WallBase, CSSEntry {
                identifier: ".w path",
                value: "stroke-dasharray: 4; stroke-width: 3",
                class_name: "w",
            }),
            (CSSClass::VirtualWall, CSSEntry {
                identifier: ".v",
                value: "stroke: #f00000; fill: #f0000030",
                class_name: "v",
            }),
            (CSSClass::NoMoppingWall, CSSEntry {
                identifier: ".m",
                value: "stroke: #ffa500; fill: #ffa50030",
                class_name: "m",
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
}
