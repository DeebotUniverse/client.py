# CI Verification Guide for Rust String Parsing Migration

This document provides guidance for verifying the Rust string parsing migration in CI.

## Changes Summary

### Files Modified
1. **`src/util.rs`** - Added two new Rust functions for CSV integer parsing
2. **`deebot_client/rs/util.pyi`** - Added type stubs for new functions
3. **`deebot_client/messages/json/stats.py`** - Migrated to use Rust parsing
4. **`deebot_client/messages/json/map/__init__.py`** - Migrated to use Rust parsing
5. **`deebot_client/commands/xml/map.py`** - Migrated to use Rust parsing
6. **`tests/rs/test_string_parsing.py`** - New comprehensive test suite

## Expected CI Checks

### 1. Rust Code Quality (`rust-code-quality`)
- **Rust format**: Should pass ✅ (verified locally)
- **Rust clippy**: Should pass (Rust code follows best practices)

**Potential Issues:**
- None expected. Code is idiomatic Rust with proper error handling.

### 2. Python Code Quality (`python-code-quality`)
- **mypy**: Should pass (type stubs are correctly defined)
- **getLogger check**: Should pass (no logger changes)

**Potential Issues:**
- If mypy fails, verify that the `.pyi` file is correctly formatted
- The new imports should be recognized by mypy through the type stubs

### 3. Prek Checks (`prek`)
- Should pass (all hooks are correctly configured)

**Potential Issues:**
- None expected

### 4. Tests (`tests`)
The main test suite includes:
- Building Rust extension with `maturin develop --uv`
- Running pytest with coverage

**Critical Tests:**
1. **`tests/rs/test_string_parsing.py`** - New test file with:
   - 12 correctness tests (edge cases, errors)
   - 12 benchmark tests (Rust vs Python baseline)
   - All benchmarks verify Rust output matches Python output

2. **`tests/messages/json/test_stats.py`** - Existing test:
   - Line 38: Expects `[0, 4, 2, 12]` from `"0,4,2,12"`
   - Should pass with Rust implementation

3. **`tests/messages/json/map/test_init.py`** - Existing test:
   - Line 146: Expects parsed integers from comma-separated string
   - Should pass with Rust implementation

4. **`tests/commands/xml/test_map.py`** - Existing test:
   - Line 158: Expects parsed map hashes
   - Should pass with Rust implementation

**Potential Issues:**
- **Build failure**: If Rust compilation fails, check:
  - Cargo.toml dependencies are correct
  - All Rust syntax is valid
  - PyO3 bindings are correctly defined
- **Test failure**: If tests fail, check:
  - Rust function output matches Python baseline exactly
  - Error handling raises correct exceptions
  - Type conversions are accurate (especially float→int truncation)

### 5. Build Tests (`build-test-native`, `build-test-musl`)
- Builds wheels for multiple platforms
- Runs tests on built wheels

**Potential Issues:**
- Platform-specific build issues unlikely (code is portable)
- All platforms should build successfully

### 6. Benchmarks (`benchmarks`)
- Runs with `pytest tests/ --codspeed`
- Uploads results to CodSpeed

**Expected Behavior:**
- Benchmarks should show 5-10x improvement for Rust implementation
- All benchmarks should pass (correctness verified in each)

**Potential Issues:**
- If benchmarks don't run, check that `--codspeed` flag is supported
- Ensure CODSPEED_TOKEN is configured in repository secrets

## Manual Verification Steps

If CI fails, developers can verify locally:

```bash
# 1. Build Rust extension
uv run maturin develop --release

# 2. Run correctness tests only (no benchmarks)
uv run pytest tests/rs/test_string_parsing.py -v -m "not benchmark"

# 3. Run all tests for modified modules
uv run pytest tests/messages/json/test_stats.py -v
uv run pytest tests/messages/json/map/test_init.py -v
uv run pytest tests/commands/xml/test_map.py -v

# 4. Run benchmarks locally
uv run pytest tests/rs/test_string_parsing.py --codspeed

# 5. Verify type checking
uv run mypy deebot_client/

# 6. Check Rust code quality
cargo fmt --check
cargo clippy --all-features
```

## Expected Performance Results

When benchmarks complete, expect to see:

| Benchmark | Python Time | Rust Time | Speedup |
|-----------|-------------|-----------|---------|
| Small (5 values) | ~0.5-1 µs | ~0.1-0.2 µs | 3-5x |
| Medium (50 values) | ~5-8 µs | ~0.8-1.5 µs | 5-8x |
| Large (200 values) | ~20-30 µs | ~2-4 µs | 8-10x |
| Real-world stats (40) | ~8-12 µs | ~1-2 µs | 6-8x |
| Real-world map (64) | ~12-18 µs | ~1.5-3 µs | 6-10x |

## Rollback Plan

If CI fails and cannot be fixed immediately:

```bash
# Revert the commit
git revert HEAD

# Or revert specific changes
git checkout HEAD~1 -- src/util.rs
git checkout HEAD~1 -- deebot_client/messages/json/stats.py
git checkout HEAD~1 -- deebot_client/messages/json/map/__init__.py
git checkout HEAD~1 -- deebot_client/commands/xml/map.py
git rm tests/rs/test_string_parsing.py
```

## Common Issues and Solutions

### Issue: Rust Compilation Fails

**Symptoms:**
```
error: failed to compile `deebot_client`
```

**Solutions:**
1. Check that all dependencies in Cargo.toml are available
2. Verify Rust version is >= 1.87
3. Check for syntax errors in `src/util.rs`

### Issue: Type Checking Fails

**Symptoms:**
```
error: Incompatible types in assignment
```

**Solutions:**
1. Verify `.pyi` file matches Rust function signatures
2. Check that return type is `list[int]` not `List[int]`
3. Ensure imports are correct in modified Python files

### Issue: Tests Fail with "Function Not Found"

**Symptoms:**
```
AttributeError: module 'deebot_client.rs.util' has no attribute 'parse_csv_ints'
```

**Solutions:**
1. Verify Rust extension was built correctly
2. Check that `init_module` registers all functions
3. Rebuild with `maturin develop --uv`

### Issue: Incorrect Parsing Results

**Symptoms:**
```
AssertionError: assert [1, 2, 3] == [1.0, 2.0, 3.0]
```

**Solutions:**
1. Check type conversion logic (float→int uses truncation, not rounding)
2. Verify whitespace trimming is working
3. Ensure empty string filtering is correct

## Success Criteria

All CI checks pass when:

✅ Rust code compiles without warnings
✅ Python type checking passes
✅ All existing tests pass (no regressions)
✅ New tests pass (correctness verified)
✅ Benchmarks run successfully
✅ Wheels build for all platforms

## Monitoring

After merge, monitor:

1. **CodSpeed Dashboard**: Performance tracking over time
2. **Codecov**: Ensure code coverage remains high
3. **GitHub Actions**: Verify builds on all platforms

## Contact

For issues with this migration, refer to:
- **Documentation**: `RUST_MIGRATION_STRING_PARSING.md`
- **Test Suite**: `tests/rs/test_string_parsing.py`
- **Implementation**: `src/util.rs`
