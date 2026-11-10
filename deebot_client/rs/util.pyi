def decompress_base64_data(value: str) -> bytes:
    """Decompress base64 decoded 7z compressed string by using lzma or zstd."""

def parse_csv_ints(value: str) -> list[int]:
    """Parse comma-separated integers from a string.

    Empty strings are filtered out automatically.

    Example: "1,2,3,," -> [1, 2, 3]
    """

def parse_csv_ints_via_float(value: str) -> list[int]:
    """Parse comma-separated integers from a string, converting via float first.

    This matches Python's behavior: int(float(x))
    Empty strings are filtered out automatically.

    Example: "1.5,2.7,3.0,," -> [1, 2, 3]
    """
