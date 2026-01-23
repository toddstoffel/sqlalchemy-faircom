# Changelog

All notable changes to sqlalchemy-faircom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.14] - 2026-01-23

### Improved
- Enhanced `_get_limit_or_offset_value()` method for better robustness and edge case handling
- Removed unreachable code from value extraction method
- Added comprehensive value extraction test suite (8 new tests)
- Improved error handling with try/except for edge cases
- Better documentation of value extraction for SQLAlchemy 2.0+ compatibility

### Added
- Test suite for value extraction (`tests/test_value_extraction.py`)
- Tests for various offset/limit combinations (0, 5, 10, 20, 50, 100, 1000)
- Tests for integer passthrough
- Tests verifying SQL output contains correct values

### Technical
- Method now checks for integer type first (more efficient)
- Added support for `_orig` attribute (SQLAlchemy 2.0+ BindParameter)
- Added support for `_element` attribute for literal values
- Improved fallback logic with proper exception handling
- All 25 tests passing

## [0.1.13] - 2026-01-23

### Fixed
- **Critical:** Fixed SKIP keyword positioning in SQL queries. SKIP is now correctly placed immediately after SELECT/TOP and before the column list, as required by FairCom SQL syntax specification.
  - Previously: `SELECT * FROM table ORDER BY id SKIP 5` ❌ (Syntax error)
  - Now: `SELECT SKIP 5 * FROM table ORDER BY id` ✅ (Works correctly)
- Removed unsupported `FETCH FIRST/NEXT ... ROWS ONLY` clause generation
- Fixed pagination queries that use both LIMIT and OFFSET (e.g., `select(table).limit(5).offset(10)`)
- Fixed OFFSET-only queries (e.g., `select(table).offset(10)`)

### Changed
- Moved SKIP generation from `limit_clause()` to `get_select_precolumns()` method
- Updated `limit_clause()` to return empty string (FairCom uses TOP/SKIP in SELECT clause, not at end)
- Enhanced documentation in code comments to reference official FairCom SQL syntax

### Added
- Comprehensive test suite for SKIP/TOP syntax (`tests/test_skip_syntax.py`)
- 12 new unit tests covering all pagination scenarios
- Test verification script (`test_skip_fix.py`)
- Detailed fix summary documentation (`SKIP_FIX_SUMMARY.md`)

### Impact
This fix enables:
- ✅ All SQLAlchemy queries with `.offset()`
- ✅ All pagination queries with `.limit().offset()`
- ✅ Apache Superset pagination support
- ✅ ORM result set pagination
- ✅ "Load more" / infinite scroll implementations

## [0.1.12] - 2026-01-XX

### Known Issues
- ❌ SKIP keyword incorrectly positioned at end of query (causes syntax errors)
- ❌ OFFSET queries fail with "Syntax error near or at 'skip'"
- ❌ Pagination broken for queries with LIMIT + OFFSET

## [0.1.11] - 2026-01-XX

### Added
- Initial release of SQLAlchemy dialect for FairCom JSON API
- Basic query support
- TOP clause support for LIMIT-only queries
- Type mapping for common data types
- DDL support with IDENTITY for autoincrement

### Working
- ✅ Simple LIMIT queries (without OFFSET)
- ✅ Basic SELECT/INSERT/UPDATE/DELETE operations
- ✅ Connection via JSON API
- ✅ Type conversions
