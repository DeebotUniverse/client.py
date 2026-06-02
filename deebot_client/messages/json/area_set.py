"""Parser for getAreaSet (LZMA encoded zone names) messages."""

from __future__ import annotations

import base64
import json
import lzma
from typing import Any

from deebot_client.events import AreaName, AreaNamesEvent

from .base import JsonMessageParser


class AreaSetParser(JsonMessageParser):
    """Parse getAreaSet messages for mowers."""

    name = "getAreaSet"

    def parse(self, payload: dict[str, Any]) -> AreaNamesEvent | None:
        """Parse the payload."""
        body = payload.get("body", {})
        data = body.get("data", {})
        
        # We only care about Area/Room type ("ar") that contains subsets
        if data.get("type") != "ar" or "subsets" not in data:
            return None

        try:
            raw_data = base64.b64decode(data["subsets"])
            
            # Fix Ecovacs custom LZMA header (9-bytes vs standard 13-bytes)
            properties_and_dict_size = raw_data[:5]
            uncompressed_size_32bit = raw_data[5:9]
            compressed_stream = raw_data[9:]
            uncompressed_size_64bit = uncompressed_size_32bit + b"\x00\x00\x00\x00"
            fixed_data = properties_and_dict_size + uncompressed_size_64bit + compressed_stream

            decompressed = lzma.decompress(fixed_data, format=lzma.FORMAT_ALONE)
            area_list = json.loads(decompressed.decode("utf-8"))

            areas = []
            for item in area_list:
                # Structure: ["mapID", "areaID", "Name", "type", "x", "y", "unknown"]
                # Example: ["1", "4", "Østkanten", "1", "250", "-19800", "0-0"]
                if len(item) >= 3:
                    area_id = int(item[1])
                    name = item[2]
                    if name:  # Only add if a custom name is actually set
                        areas.append(AreaName(area_id=area_id, name=name))

            return AreaNamesEvent(areas=areas)
        except Exception:
            # Silently ignore parsing errors for unsupported formats
            return None
