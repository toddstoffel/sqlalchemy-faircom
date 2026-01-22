# SQLAlchemy FairCom

A pure Python SQLAlchemy dialect for FairCom Database using the JSON/REST API. This driver works cross-platform without requiring native C libraries.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

## Features

- ✅ Pure Python implementation (no native libraries required)
- ✅ Cross-platform: Works on macOS, Linux, Windows
- ✅ SQLAlchemy compatible (1.4+)
- ✅ DB-API 2.0 compliant
- ✅ Uses FairCom JSON API over HTTP/HTTPS
- ✅ Compatible with Apache Superset, Pandas, and other SQLAlchemy-based tools

## Installation

### From PyPI

```bash
pip install sqlalchemy-faircom
```

### From Source

```bash
git clone https://github.com/toddstoffel/sqlalchemy-faircom.git
cd sqlalchemy-faircom
pip install -e .
```

### For Development

```bash
git clone https://github.com/toddstoffel/sqlalchemy-faircom.git
cd sqlalchemy-faircom
pip install -e .[dev]
pytest
```

## Connection String Format

```
faircom://username:password@host:port/database?protocol=http
```

### Parameters

- `username`: Database username (e.g., ADMIN)
- `password`: Database password
- `host`: Database server hostname
- `port`: JSON API port (typically 8080 for HTTP, 8443 for HTTPS)
- `database`: Database name (e.g., ctreeSQL)
- `protocol`: Either `http` or `https` (default: http)

## Environment Variables

Create a `.env` file in your project root:

```env
HOST=your-server.example.com
PORT=8080
USERNAME=your_username
PASSWORD=your_password
PROTOCOL=http
```

**Note**: PORT should be set to the JSON API port: 8080 for HTTP or 8443 for HTTPS.

## Usage Examples

### Basic SQLAlchemy Usage

```python
from sqlalchemy import create_engine, text

# Create connection
connection_string = 'faircom://username:password@your-server:8080/ctreeSQL?protocol=http'
engine = create_engine(connection_string, echo=True)

# Execute queries
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1 as test"))
    print(result.fetchone())
```

### Using Environment Variables

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

connection_string = f"faircom://{os.getenv('USERNAME')}:{os.getenv('PASSWORD')}@{os.getenv('HOST')}:{os.getenv('PORT')}/{os.getenv('DATABASE', 'ctreeSQL')}?protocol={os.getenv('PROTOCOL', 'http')}"
engine = create_engine(connection_string)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM my_table"))
    for row in result:
        print(row)
```

### Direct DB-API Usage

```python
from faircom_jsonapi.dbapi import connect

# Connect to database
conn = connect(
    host='your-server.example.com',
    port=8080,
    username='your_username',
    password='your_password',
    database='ctreeSQL',
    protocol='http'
)

# Create cursor and execute
cursor = conn.cursor()
cursor.execute("SELECT 1 as test")
print(cursor.fetchone())

cursor.close()
conn.close()
```

## Testing

Run the test suite:

```bash
pytest tests/
```

## Project Structure

```
sqlalchemy-faircom/
├── LICENSE                       # MIT License
├── README.md                     # This file
├── pyproject.toml               # Project metadata and dependencies
├── setup.py                     # Package setup
├── MANIFEST.in                  # Package manifest
├── faircom_jsonapi/
│   ├── __init__.py              # Package initialization
│   ├── client.py                # FairCom JSON API client
│   ├── dbapi.py                 # DB-API 2.0 implementation
│   └── sqlalchemy_dialect.py   # SQLAlchemy dialect
└── tests/
    └── test_dialect.py          # Unit tests
```

## Compatibility

- Python 3.7+
- SQLAlchemy 1.4+
- Works with any tool that uses SQLAlchemy (e.g., Apache Superset, Pandas, etc.)

## Limitations

### Database Limitations

- **OFFSET/FETCH Not Supported**: FairCom database does not support OFFSET/FETCH syntax. Use `.limit()` without `.offset()` for TOP-based pagination.
  - ❌ Does NOT work: `query.limit(10).offset(5)` 
  - ✅ Works: `query.limit(10)`
  - **Workarounds**: Use cursor-based pagination or fetch larger result sets and paginate in application code

- **Parameterized TOP Values**: FairCom requires literal integer values in TOP clauses (not bind parameters). This driver automatically extracts literal values from SQLAlchemy queries.

### API Limitations

- Read operations are fully supported
- Write operations may have limited support (depends on JSON API capabilities)
- Some advanced SQLAlchemy features may not be implemented

## For Superset Integration

This driver can be used with Apache Superset. Use the following connection string in Superset:

```
faircom://username:password@your-server:8080/ctreeSQL?protocol=http
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Publishing

To publish a new version to PyPI:

```bash
# Update version in pyproject.toml
# Clean and build
rm -rf dist/ build/ *.egg-info
python -m build

# Upload to PyPI
twine upload dist/*
```

## Troubleshooting

### Connection Refused
- Ensure the JSON API is enabled on your FairCom server
- Verify the correct port (8080 for HTTP, 8443 for HTTPS)
- Check firewall settings

### SSL Warnings
The driver currently disables SSL verification for HTTPS connections. For production use, you may want to enable proper certificate verification in `faircom_jsonapi/client.py`.

### Reserved Keywords
Some SQL keywords like "number" are reserved in FairCom. Use different column aliases if you encounter syntax errors.

## Changelog

### Version 0.1.11 (January 21, 2026)
- **Fixed:** Raw SQL text queries with LIMIT now work (e.g., from Superset)
- Added automatic LIMIT to TOP conversion in `Cursor.execute()` method
- Handles multi-line SQL queries like `SELECT\n  *\nFROM table\nLIMIT 1001`
- Fixes "Syntax error near or at" when Superset sends LIMIT queries
- Conversion happens at DB-API level, before SQL reaches FairCom
- Works alongside ORM's TOP generation in dialect

### Version 0.1.10 (January 21, 2026)
- **Breaking Change:** Removed OFFSET/FETCH support due to FairCom database limitation
- **Improved:** Clear error message when .offset() is used, guiding users to alternatives
- **Documented:** Known limitation with OFFSET queries and recommended workarounds
- OFFSET/FETCH syntax causes "Syntax error near or at" - not supported by FairCom database

### Version 0.1.9 (January 21, 2026)
- **Fixed:** CRITICAL FIX for parameterized TOP/OFFSET values
- Implemented `_get_limit_or_offset_value()` helper method to extract literal integers
- v0.1.8 fix didn't work - `literal_binds` parameter not valid for `self.process()`
- Now generates `SELECT TOP 10` instead of `SELECT TOP ?`
- Ready for Apache Superset integration with `.limit()` queries

### Version 0.1.8 (January 21, 2026)
- **Attempted Fix:** Tried to render TOP/OFFSET/FETCH as literals (didn't work)
- Used `literal_binds=True` parameter approach (not valid)

### Version 0.1.7 (January 21, 2026)
- **Added:** Comprehensive T-SQL compatibility
- OFFSET/FETCH syntax (now removed in v0.1.10 due to database limitation)
- Boolean → BIT type mapping
- IDENTITY for autoincrement columns
- String concatenation with + operator

### Version 0.1.6 (January 21, 2026)
- **Added:** TOP syntax support for `.limit()` queries

### Version 0.1.5 (January 21, 2026)
- **Fixed:** dbapi classmethod interface for SQLAlchemy compatibility

### Version 0.1.3 (January 21, 2026)
- **Fixed:** DDL/DML operations (CREATE, INSERT, UPDATE, DELETE) now work correctly
- **Fixed:** Corrected API routing - SELECT queries use `getRecordsUsingSQL`, DDL/DML use `runSqlStatements`
- **Fixed:** Request format for `runSqlStatements` now uses correct property name `sqlStatements` as an array
- **Improved:** Enhanced error handling and API compatibility
- All 7 test suite tests now passing

### Version 0.1.2 (January 2026)
- Partial fix attempt for DDL/DML routing

### Version 0.1.1 (January 2026)
- Initial release with basic SELECT query support

### Version 0.1.0 (January 2026)
- Initial development version

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- [FairCom Corporation](https://www.faircom.com)
- [FairCom Documentation](https://docs.faircom.com)
- [SQLAlchemy](https://www.sqlalchemy.org)

## Acknowledgments

- Built with SQLAlchemy
- Uses FairCom Database JSON API
- Pure Python implementation for maximum compatibility
