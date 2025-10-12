use std::{collections::HashMap, sync::OnceLock};

#[cfg(test)]
use strum_macros::EnumIter;

#[derive(Eq, PartialEq, Hash)]
#[cfg_attr(test, derive(EnumIter))]
pub(super) enum CSSClass {
    Path,
    Outline,
    RoomUnreachable,
    RoomReachable,
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
                value: "stroke-width: 1.5; vector-effect: non-scaling-stroke;",
                class_name: "path",
            }),
            (CSSClass::Outline, CSSEntry {
                identifier: ".o path",
                value: "fill: none; stroke: #4e96e2; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3",
                class_name: "o",
            }),
            (CSSClass::RoomUnreachable, CSSEntry {
                identifier: ".u",
                value: "fill: #edf3fb",
                class_name: "u",
            }),
            (CSSClass::RoomReachable, CSSEntry {
                identifier: ".r",
                value: "fill: #badaff",
                class_name: "r",
            }),
            (CSSClass::VirtualWall, CSSEntry {
                identifier: ".v",
                value: "stroke: #f00000; fill: #f0000030; stroke-dasharray: 4;",
                class_name: "v",
            }),
            (CSSClass::NoMoppingWall, CSSEntry {
                identifier: ".m",
                value: "stroke: #ffa500; fill: #ffa50030; stroke-dasharray: 4;",
                class_name: "m",
            }),
        ])
    })
}

pub(super) fn get_style(css: &CSSClass) -> &'static CSSEntry {
    get_styles().get(css).unwrap()
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
