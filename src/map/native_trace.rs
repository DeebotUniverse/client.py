use super::points::TracePoint;
use base64::{Engine as _, engine::general_purpose};
use std::error::Error;
use std::fmt;

pub const MAX_TRACE_CAPACITY: usize = 640_000;
/// Fixed total ceiling: one 5-byte record per point, chunk output bounded by
/// MAX_TRACE_CAPACITY, so accumulated Vec never exceeds 128000 points.
pub const MAX_TRACE_POINTS: usize = MAX_TRACE_CAPACITY / 5;
/// Same LZ4 compress-bound derivation as raster: output bounded by
/// MAX_TRACE_CAPACITY, so raw input above this is implausible.
pub const MAX_TRACE_COMPRESSED_BYTES: usize = 643_000;
pub const MAX_TRACE_BASE64_LEN: usize = 860_000;

#[derive(Debug)]
pub enum NativeTraceError {
    CapacityExceeded(usize),
    TotalPointsExceeded(usize),
    AccumulatedExceedsMaximum {
        start: usize,
        new_points: usize,
        maximum: usize,
    },
    ChunkExceedsTotal {
        chunk_points: usize,
        start: usize,
        total: usize,
    },
    CursorStartGreaterThanTotal {
        start: usize,
        total: usize,
    },
    CursorGap {
        start: usize,
        current_len: usize,
    },
    ZeroCapacityForNonEmpty,
    Base64TooLarge(usize),
    CompressedTooLarge(usize),
    Base64(base64::DecodeError),
    Decompress(lz4_flex::block::DecompressError),
    InvalidRecordLength(usize),
}

impl fmt::Display for NativeTraceError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NativeTraceError::CapacityExceeded(cap) => {
                write!(
                    f,
                    "Trace scratch capacity {cap} exceeds maximum {MAX_TRACE_CAPACITY}"
                )
            }
            NativeTraceError::TotalPointsExceeded(total) => {
                write!(f, "Trace total {total} exceeds maximum {MAX_TRACE_POINTS}")
            }
            NativeTraceError::AccumulatedExceedsMaximum {
                start,
                new_points,
                maximum,
            } => {
                write!(
                    f,
                    "Trace accumulated points {start} + {new_points} exceed maximum {maximum}"
                )
            }
            NativeTraceError::ChunkExceedsTotal {
                chunk_points,
                start,
                total,
            } => {
                write!(
                    f,
                    "Trace chunk of {chunk_points} points at start {start} exceeds declared total {total}"
                )
            }
            NativeTraceError::CursorStartGreaterThanTotal { start, total } => {
                write!(f, "Invalid trace cursor: start ({start}) > total ({total})")
            }
            NativeTraceError::CursorGap { start, current_len } => {
                write!(
                    f,
                    "Trace cursor gap: start ({start}) exceeds current length ({current_len})"
                )
            }
            NativeTraceError::ZeroCapacityForNonEmpty => {
                write!(f, "Capacity cannot be 0 for non-empty trace payload")
            }
            NativeTraceError::Base64TooLarge(len) => write!(
                f,
                "Base64 payload length {len} exceeds maximum {MAX_TRACE_BASE64_LEN}"
            ),
            NativeTraceError::CompressedTooLarge(len) => write!(
                f,
                "LZ4 payload length {len} exceeds maximum {MAX_TRACE_COMPRESSED_BYTES}"
            ),
            NativeTraceError::Base64(err) => write!(f, "Base64 decode failed: {err}"),
            NativeTraceError::Decompress(err) => write!(f, "LZ4 decompression failed: {err}"),
            NativeTraceError::InvalidRecordLength(len) => {
                write!(
                    f,
                    "Malformed trace record length: {len} is not a multiple of 5 bytes"
                )
            }
        }
    }
}

impl Error for NativeTraceError {}

pub fn decode_native_trace_chunk(
    base64_lz4: Option<&str>,
    capacity: usize,
    start: usize,
    total: usize,
    current_len: usize,
) -> Result<Vec<TracePoint>, NativeTraceError> {
    if capacity > MAX_TRACE_CAPACITY {
        return Err(NativeTraceError::CapacityExceeded(capacity));
    }
    if total > MAX_TRACE_POINTS {
        return Err(NativeTraceError::TotalPointsExceeded(total));
    }
    if start > total {
        return Err(NativeTraceError::CursorStartGreaterThanTotal { start, total });
    }
    if start > current_len {
        return Err(NativeTraceError::CursorGap { start, current_len });
    }

    let payload = match base64_lz4 {
        Some(s) if !s.trim().is_empty() => s.trim(),
        _ => return Ok(Vec::new()),
    };

    if capacity == 0 {
        return Err(NativeTraceError::ZeroCapacityForNonEmpty);
    }
    if payload.len() > MAX_TRACE_BASE64_LEN {
        return Err(NativeTraceError::Base64TooLarge(payload.len()));
    }

    let compressed = general_purpose::STANDARD
        .decode(payload)
        .map_err(NativeTraceError::Base64)?;
    if compressed.len() > MAX_TRACE_COMPRESSED_BYTES {
        return Err(NativeTraceError::CompressedTooLarge(compressed.len()));
    }

    let mut decomp_buf = vec![0u8; capacity];
    let written = lz4_flex::decompress_into(&compressed, &mut decomp_buf)
        .map_err(NativeTraceError::Decompress)?;

    if written % 5 != 0 {
        return Err(NativeTraceError::InvalidRecordLength(written));
    }

    let points = decomp_buf[..written]
        .as_chunks::<5>()
        .0
        .iter()
        .map(|chunk| {
            let x = i16::from_le_bytes([chunk[0], chunk[1]]);
            let y = i16::from_le_bytes([chunk[2], chunk[3]]);
            let connected = ((chunk[4] >> 7) & 1) == 0;
            TracePoint { x, y, connected }
        })
        .collect();

    Ok(points)
}

pub fn apply_native_trace(
    points_buffer: &mut Vec<TracePoint>,
    base64_lz4: Option<&str>,
    capacity: usize,
    start: usize,
    total: usize,
) -> Result<bool, NativeTraceError> {
    let new_points =
        decode_native_trace_chunk(base64_lz4, capacity, start, total, points_buffer.len())?;

    if new_points.is_empty() {
        if start < points_buffer.len() {
            points_buffer.truncate(start);
            return Ok(true);
        }
        return Ok(false);
    }

    let accumulated =
        start
            .checked_add(new_points.len())
            .ok_or(NativeTraceError::AccumulatedExceedsMaximum {
                start,
                new_points: new_points.len(),
                maximum: MAX_TRACE_POINTS,
            })?;
    if accumulated > MAX_TRACE_POINTS {
        return Err(NativeTraceError::AccumulatedExceedsMaximum {
            start,
            new_points: new_points.len(),
            maximum: MAX_TRACE_POINTS,
        });
    }
    if new_points.len() > total - start {
        return Err(NativeTraceError::ChunkExceedsTotal {
            chunk_points: new_points.len(),
            start,
            total,
        });
    }

    if points_buffer.len() == start + new_points.len() && points_buffer[start..] == new_points[..] {
        return Ok(false);
    }

    points_buffer.truncate(start);
    points_buffer.extend(new_points);
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn encode_trace_points(records: &[(i16, i16, u8)]) -> (String, usize) {
        let mut raw = Vec::with_capacity(records.len() * 5);
        for &(x, y, flag) in records {
            raw.extend_from_slice(&x.to_le_bytes());
            raw.extend_from_slice(&y.to_le_bytes());
            raw.push(flag);
        }
        let comp = lz4_flex::compress(&raw);
        (general_purpose::STANDARD.encode(&comp), raw.len())
    }

    #[test]
    fn test_decode_trace_normal_and_flags() {
        // Record 0: flag 154 (0x9a) -> disconnected (bit 7 is 1)
        // Record 1: flag 0 -> connected (bit 7 is 0)
        let records = vec![(100i16, -200i16, 154u8), (105i16, -195i16, 0u8)];
        let (b64, len) = encode_trace_points(&records);

        let points = decode_native_trace_chunk(Some(&b64), len + 10, 0, 3, 0).unwrap();
        assert_eq!(points.len(), 2);
        assert_eq!(points[0].x, 100);
        assert_eq!(points[0].y, -200);
        assert!(!points[0].connected);

        assert_eq!(points[1].x, 105);
        assert_eq!(points[1].y, -195);
        assert!(points[1].connected);
    }

    #[test]
    fn test_cursor_overlap_and_deduplication() {
        let mut buf = Vec::new();

        // Packet 1: start=0, points [P0, P1]
        let rec1 = vec![(0i16, 0i16, 128u8), (5i16, 5i16, 0u8)];
        let (b64_1, len1) = encode_trace_points(&rec1);
        let updated1 = apply_native_trace(&mut buf, Some(&b64_1), len1 + 10, 0, 3).unwrap();
        assert!(updated1);
        assert_eq!(buf.len(), 2);

        // Duplicate packet: retransmission of packet 1
        let updated_dup = apply_native_trace(&mut buf, Some(&b64_1), len1 + 10, 0, 3).unwrap();
        assert!(!updated_dup);
        assert_eq!(buf.len(), 2);

        // Packet 2: overlap at start=1, points [P1, P2]
        let rec2 = vec![(5i16, 5i16, 0u8), (10i16, 10i16, 0u8)];
        let (b64_2, len2) = encode_trace_points(&rec2);
        let updated2 = apply_native_trace(&mut buf, Some(&b64_2), len2 + 10, 1, 4).unwrap();
        assert!(updated2);
        assert_eq!(buf.len(), 3);
        assert_eq!(
            buf[0],
            TracePoint {
                x: 0,
                y: 0,
                connected: false
            }
        );
        assert_eq!(
            buf[1],
            TracePoint {
                x: 5,
                y: 5,
                connected: true
            }
        );
        assert_eq!(
            buf[2],
            TracePoint {
                x: 10,
                y: 10,
                connected: true
            }
        );
    }

    #[test]
    fn test_cursor_gap_fails_without_mutation() {
        let mut buf = vec![TracePoint {
            x: 0,
            y: 0,
            connected: false,
        }];
        let rec = vec![(5i16, 5i16, 0u8)];
        let (b64, len) = encode_trace_points(&rec);

        // Gap: start = 3, but buf only has 1 point
        let err = apply_native_trace(&mut buf, Some(&b64), len + 10, 3, 5).unwrap_err();
        assert!(matches!(
            err,
            NativeTraceError::CursorGap {
                start: 3,
                current_len: 1
            }
        ));
        assert_eq!(buf.len(), 1);
    }

    #[test]
    fn test_cursor_start_greater_than_total_fails() {
        let mut buf = Vec::new();
        let err = apply_native_trace(&mut buf, None, 10, 5, 2).unwrap_err();
        assert!(matches!(
            err,
            NativeTraceError::CursorStartGreaterThanTotal { start: 5, total: 2 }
        ));
    }

    #[test]
    fn test_oversized_capacity_fails() {
        let mut buf = Vec::new();
        let err = apply_native_trace(&mut buf, None, 700_000, 0, 0).unwrap_err();
        assert!(matches!(err, NativeTraceError::CapacityExceeded(700_000)));
    }

    #[test]
    fn test_total_points_ceiling_fails_before_allocation() {
        let mut buf = Vec::new();
        let err = apply_native_trace(&mut buf, None, 100, 0, MAX_TRACE_POINTS + 1).unwrap_err();
        assert!(matches!(
            err,
            NativeTraceError::TotalPointsExceeded(t) if t == MAX_TRACE_POINTS + 1
        ));
        assert!(buf.is_empty());
    }

    #[test]
    fn test_incremental_overflow_fails_without_mutation() {
        let mut buf = vec![
            TracePoint {
                x: 0,
                y: 0,
                connected: true,
            };
            MAX_TRACE_POINTS - 1
        ];
        let rec = vec![(1i16, 1i16, 0u8), (2i16, 2i16, 0u8)];
        let (b64, len) = encode_trace_points(&rec);
        let err = apply_native_trace(
            &mut buf,
            Some(&b64),
            len + 10,
            MAX_TRACE_POINTS - 1,
            MAX_TRACE_POINTS,
        )
        .unwrap_err();
        assert!(matches!(
            err,
            NativeTraceError::AccumulatedExceedsMaximum { .. }
        ));
        assert_eq!(buf.len(), MAX_TRACE_POINTS - 1);
    }

    #[test]
    fn test_chunk_exceeding_total_fails_without_mutation() {
        let mut buf = Vec::new();
        let rec = vec![(0i16, 0i16, 0u8), (1i16, 1i16, 0u8), (2i16, 2i16, 0u8)];
        let (b64, len) = encode_trace_points(&rec);
        let err = apply_native_trace(&mut buf, Some(&b64), len + 10, 0, 2).unwrap_err();
        assert!(matches!(
            err,
            NativeTraceError::ChunkExceedsTotal {
                chunk_points: 3,
                start: 0,
                total: 2
            }
        ));
        assert!(buf.is_empty());
    }

    #[test]
    fn test_generic_bound_two_points_total_two_valid() {
        let mut buf = Vec::new();
        let rec = vec![(10i16, -5i16, 154u8), (11i16, -4i16, 0u8)];
        let (b64, len) = encode_trace_points(&rec);
        assert!(apply_native_trace(&mut buf, Some(&b64), len + 10, 0, 2).unwrap());
        assert_eq!(buf.len(), 2);
    }

    #[test]
    fn test_failed_chunk_preserves_prior_trace() {
        let mut buf = Vec::new();
        let rec = vec![(7i16, 8i16, 128u8), (9i16, 10i16, 0u8)];
        let (b64, len) = encode_trace_points(&rec);
        assert!(apply_native_trace(&mut buf, Some(&b64), len + 10, 0, 2).unwrap());
        let snapshot = buf.clone();
        let err = apply_native_trace(&mut buf, Some("!!!not-base64!!!"), 100, 2, 4).unwrap_err();
        assert!(matches!(err, NativeTraceError::Base64(_)));
        assert_eq!(buf, snapshot);
    }

    #[test]
    fn test_trace_base64_too_large() {
        let mut buf = Vec::new();
        let huge = "QUJD".repeat(MAX_TRACE_BASE64_LEN + 4);
        let err = apply_native_trace(&mut buf, Some(&huge), 100, 0, 10).unwrap_err();
        assert!(matches!(err, NativeTraceError::Base64TooLarge(_)));
        assert!(buf.is_empty());
    }

    #[test]
    fn test_trace_compressed_too_large() {
        let mut buf = Vec::new();
        let raw = vec![0xabu8; MAX_TRACE_COMPRESSED_BYTES + 1000];
        let b64 = general_purpose::STANDARD.encode(&raw);
        assert!(b64.len() <= MAX_TRACE_BASE64_LEN);
        let err = apply_native_trace(&mut buf, Some(&b64), 640_000, 0, 100).unwrap_err();
        assert!(matches!(err, NativeTraceError::CompressedTooLarge(_)));
        assert!(buf.is_empty());
    }

    #[test]
    fn test_malformed_record_length_fails() {
        let mut buf = Vec::new();
        let bad_raw = vec![0u8; 7]; // Not multiple of 5
        let comp = lz4_flex::compress(&bad_raw);
        let b64 = general_purpose::STANDARD.encode(&comp);

        let err = apply_native_trace(&mut buf, Some(&b64), 20, 0, 2).unwrap_err();
        assert!(matches!(err, NativeTraceError::InvalidRecordLength(7)));
        assert!(buf.is_empty());
    }

    #[test]
    fn test_empty_reset() {
        let mut buf = vec![TracePoint {
            x: 1,
            y: 2,
            connected: true,
        }];
        let changed = apply_native_trace(&mut buf, None, 0, 0, 0).unwrap();
        assert!(changed);
        assert!(buf.is_empty());

        let changed2 = apply_native_trace(&mut buf, None, 0, 0, 0).unwrap();
        assert!(!changed2);
    }
}
