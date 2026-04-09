from deebot_client.ngiot_map_parser import parse_base_map


def test_parse_base_map_prefers_map_field_and_captures_lz4_len() -> None:
    payload = {
        "mapId": "4",
        "mapData": {
            "mapId": "4",
            "map": "ENCODED_MAP_PAYLOAD",
            "data": "LEGACY_DATA_SHOULD_NOT_WIN",
            "lz4Len": 21168,
            "width": 144,
            "height": 147,
            "totalWidth": 800,
            "totalHeight": 800,
            "resolution": 5,
            "xMin": 383,
            "yMax": 493,
        },
    }

    base_map = parse_base_map(payload)

    assert base_map is not None
    assert base_map.map_id == "4"
    assert base_map.encoded == "ENCODED_MAP_PAYLOAD"
    assert base_map.lz4_len == 21168
    assert base_map.width == 144
    assert base_map.height == 147
    assert base_map.total_width == 800
    assert base_map.total_height == 800
    assert base_map.resolution == 5
    assert base_map.x_min == 383
    assert base_map.y_max == 493


def test_parse_base_map_falls_back_to_legacy_data_field() -> None:
    payload = {
        "mapId": "3",
        "mapData": {
            "data": "LEGACY_ONLY_PAYLOAD",
            "width": 138,
            "height": 151,
            "totalWidth": 800,
            "totalHeight": 800,
            "resolution": 5,
            "xMin": 372,
            "yMax": 491,
        },
    }

    base_map = parse_base_map(payload)

    assert base_map is not None
    assert base_map.map_id == "3"
    assert base_map.encoded == "LEGACY_ONLY_PAYLOAD"
    assert base_map.lz4_len is None