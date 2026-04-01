"""NGIOT map state aggregation.

This module stores a per-map snapshot assembled from multiple NGIOT field-based
responses. It keeps raw values intact, exposes normalized views for later
rendering, and tolerates partial updates arriving in any order.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ngiot_map_parser import (
    NgiotArea,
    NgiotBaseMap,
    NgiotMapInfo,
    NgiotOverlay,
    NgiotPose,
    NgiotPoint,
    NgiotTrace,
    normalize_point,
    normalize_polygon,
    normalize_pose,
)


@dataclass(slots=True)
class NgiotMapSnapshot:
    """Aggregated state for a single NGIOT map ID."""

    map_info: NgiotMapInfo | None = None
    base_map: NgiotBaseMap | None = None
    pose: NgiotPose | None = None
    trace: NgiotTrace | None = None
    areas: list[NgiotArea] = field(default_factory=list)
    overlays: list[NgiotOverlay] = field(default_factory=list)

    @property
    def map_id(self) -> str | None:
        if self.map_info is not None:
            return self.map_info.map_id
        if self.base_map is not None:
            return self.base_map.map_id
        return None

    @property
    def charge_pos(self) -> NgiotPoint | None:
        if self.map_info is not None:
            return self.map_info.charge_pos
        return None

    def has_background(self) -> bool:
        """Return True when a decoded/normalizable base-map payload is present."""
        return self.base_map is not None

    def has_geometry(self) -> bool:
        """Return True when enough geometry/state exists to render a useful map.

        Geometry-map V1 intentionally does not require a base map.
        """
        return bool(
            self.areas
            or self.overlays
            or self.pose is not None
            or self.charge_pos is not None
            or (
                self.trace is not None
                and (
                    self.trace.total_count > 0
                    or bool(self.trace.encoded)
                )
            )
        )

    def is_renderable(self) -> bool:
        """Return True when the snapshot can produce a visible map.

        For geometry-map V1, either:
        - a base map is present, or
        - enough geometry/state exists to render without a background
        """
        return self.has_background() or self.has_geometry()


class NgiotMapStateStore:
    """Per-device NGIOT map state store keyed by map_id."""

    def __init__(self) -> None:
        self._maps: dict[str, NgiotMapSnapshot] = {}
        self._active_map_id: str | None = None

    @property
    def active_map_id(self) -> str | None:
        return self._active_map_id

    @property
    def map_ids(self) -> tuple[str, ...]:
        return tuple(self._maps.keys())

    def clear(self) -> None:
        self._maps.clear()
        self._active_map_id = None

    def has_map(self, map_id: str) -> bool:
        return map_id in self._maps

    def get(self, map_id: str) -> NgiotMapSnapshot:
        if map_id not in self._maps:
            self._maps[map_id] = NgiotMapSnapshot()
        return self._maps[map_id]

    def get_if_present(self, map_id: str) -> NgiotMapSnapshot | None:
        return self._maps.get(map_id)

    def get_active(self) -> NgiotMapSnapshot | None:
        if self._active_map_id is None:
            return None
        return self._maps.get(self._active_map_id)

    def get_active_renderable(self) -> NgiotMapSnapshot | None:
        """Return the active snapshot only if it is renderable."""
        snapshot = self.get_active()
        if snapshot is None or not snapshot.is_renderable():
            return None
        return snapshot

    def set_active_map_id(self, map_id: str | None) -> None:
        if map_id:
            self._active_map_id = map_id
            self.get(map_id)

    def update_map_info(self, info: NgiotMapInfo) -> NgiotMapSnapshot:
        snapshot = self.get(info.map_id)
        snapshot.map_info = info
        if info.using:
            self._active_map_id = info.map_id
        elif self._active_map_id is None:
            self._active_map_id = info.map_id
        return snapshot

    def update_map_infos(self, infos: list[NgiotMapInfo]) -> None:
        for info in infos:
            self.update_map_info(info)

    def update_base_map(self, base_map: NgiotBaseMap) -> NgiotMapSnapshot:
        snapshot = self.get(base_map.map_id)
        snapshot.base_map = base_map
        if self._active_map_id is None:
            self._active_map_id = base_map.map_id
        return snapshot

    def update_pose(self, map_id: str, pose: NgiotPose) -> NgiotMapSnapshot:
        snapshot = self.get(map_id)
        snapshot.pose = pose
        return snapshot

    def update_trace(self, map_id: str, trace: NgiotTrace) -> NgiotMapSnapshot:
        snapshot = self.get(map_id)
        snapshot.trace = trace
        return snapshot

    def update_areas(self, map_id: str, areas: list[NgiotArea]) -> NgiotMapSnapshot:
        snapshot = self.get(map_id)
        snapshot.areas = areas
        return snapshot

    def update_overlays(
        self, map_id: str, overlays: list[NgiotOverlay]
    ) -> NgiotMapSnapshot:
        snapshot = self.get(map_id)
        snapshot.overlays = overlays
        return snapshot

    def get_normalized(self, map_id: str | None = None) -> NgiotMapSnapshot | None:
        """Return a normalized copy of the snapshot for rendering.

        If the snapshot has no base map yet, the raw snapshot is returned.
        """
        resolved_map_id = map_id or self._active_map_id
        if resolved_map_id is None:
            return None

        snapshot = self._maps.get(resolved_map_id)
        if snapshot is None:
            return None

        if snapshot.base_map is None:
            return NgiotMapSnapshot(
                map_info=snapshot.map_info,
                base_map=snapshot.base_map,
                pose=snapshot.pose,
                trace=snapshot.trace,
                areas=list(snapshot.areas),
                overlays=list(snapshot.overlays),
            )

        base_map = snapshot.base_map

        normalized_map_info = snapshot.map_info
        if snapshot.map_info is not None and snapshot.map_info.charge_pos is not None:
            normalized_map_info = NgiotMapInfo(
                map_id=snapshot.map_info.map_id,
                name=snapshot.map_info.name,
                using=snapshot.map_info.using,
                angle=snapshot.map_info.angle,
                charge_pos=normalize_point(snapshot.map_info.charge_pos, base_map),
            )

        normalized_pose = (
            normalize_pose(snapshot.pose, base_map) if snapshot.pose is not None else None
        )

        normalized_areas = [
            NgiotArea(
                area_id=area.area_id,
                name=area.name,
                polygon=normalize_polygon(area.polygon, base_map),
                raw=area.raw,
            )
            for area in snapshot.areas
        ]

        normalized_overlays = [
            NgiotOverlay(
                overlay_type=overlay.overlay_type,
                overlay_id=overlay.overlay_id,
                polygon=normalize_polygon(overlay.polygon, base_map),
                raw=overlay.raw,
            )
            for overlay in snapshot.overlays
        ]

        return NgiotMapSnapshot(
            map_info=normalized_map_info,
            base_map=base_map,
            pose=normalized_pose,
            trace=snapshot.trace,
            areas=normalized_areas,
            overlays=normalized_overlays,
        )