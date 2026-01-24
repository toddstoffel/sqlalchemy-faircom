"""
SQLAlchemy dialect for FairCom JSON API
Allows SQLAlchemy to connect via the JSON API instead of native libraries
"""
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler
from sqlalchemy import types as sqltypes
from sqlalchemy import text
from . import dbapi


class FairComJSONCompiler(compiler.SQLCompiler):
    """SQL compiler for FairCom - generates standard SQL with LIMIT/OFFSET
    
    The dbapi layer (dbapi.py) automatically converts LIMIT to TOP for FairCom compatibility.
    This keeps the dialect simple and compatible with SQL parsing tools like Superset.
    """
    
    # Use default SQLCompiler behavior for LIMIT/OFFSET
    # The dbapi.Cursor.execute() method handles conversion to TOP/SKIP syntax
    
    def visit_concat_op_binary(self, binary, operator, **kw):
        """Use T-SQL + operator for string concatenation instead of ||"""
        return f"{self.process(binary.left, **kw)} + {self.process(binary.right, **kw)}"
    
    def visit_mod_binary(self, binary, operator, **kw):
        """Handle modulo operator (keep default)"""
        return self.process(binary.left, **kw) + " % " + self.process(binary.right, **kw)
    
    def visit_concat_op_cliprecedence_3(self, element, **kw):
        """Handle CONCAT function - convert to + operator chain for T-SQL"""
        clauses = element.clauses._all_objects()
        return " + ".join(self.process(c, **kw) for c in clauses)


class FairComJSONTypeCompiler(compiler.GenericTypeCompiler):
    """Type compiler for FairCom - maps SQLAlchemy types to T-SQL types"""
    
    def visit_BOOLEAN(self, type_, **kw):
        """Map Boolean to BIT for T-SQL compatibility"""
        return "BIT"
    
    def visit_boolean(self, type_, **kw):
        """Map boolean to BIT for T-SQL compatibility"""
        return "BIT"


class FairComJSONDDLCompiler(compiler.DDLCompiler):
    """DDL compiler for FairCom - handles T-SQL specific DDL syntax"""
    
    def get_column_specification(self, column, **kwargs):
        """Override to use IDENTITY for autoincrement columns"""
        colspec = self.preparer.format_column(column)
        colspec += " " + self.dialect.type_compiler.process(column.type, type_expression=column)
        
        # Handle IDENTITY for autoincrement columns (T-SQL style)
        if column.primary_key and column.autoincrement:
            colspec += " IDENTITY(1,1)"
        
        # Handle default values
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default
        
        # Handle NOT NULL
        if not column.nullable:
            colspec += " NOT NULL"
        
        return colspec


class FairComJSONDialect(default.DefaultDialect):
    """SQLAlchemy dialect for FairCom JSON API"""
    
    name = 'faircom'
    driver = 'jsonapi'
    
    @classmethod
    def dbapi(cls):
        """Return the DB-API module"""
        return dbapi
    
    # Disable statement caching to prevent limit/offset values from being cached
    # FairCom requires literal integers in TOP/SKIP, and caching interferes with this
    supports_statement_cache = False
    
    supports_alter = True
    supports_unicode_statements = True
    supports_unicode_binds = True
    returns_unicode_strings = True
    description_encoding = None
    
    statement_compiler = FairComJSONCompiler
    type_compiler = FairComJSONTypeCompiler
    ddl_compiler = FairComJSONDDLCompiler
    
    @classmethod
    def import_dbapi(cls):
        """Import the DB-API module"""
        return dbapi
    
    def create_connect_args(self, url):
        """Build connection arguments from URL"""
        opts = url.translate_connect_args(username='username')
        opts.update(url.query)
        
        # Parse host and port
        if url.host:
            opts['host'] = url.host
        if url.port:
            opts['port'] = url.port
        
        # Get database name from URL path
        if url.database:
            opts['database'] = url.database
        
        # Handle protocol from query string or default to http
        protocol = opts.pop('protocol', 'http')
        opts['protocol'] = protocol
        
        return [[], opts]
    
    def do_rollback(self, dbapi_connection):
        """Rollback implementation"""
        pass
    
    def do_commit(self, dbapi_connection):
        """Commit implementation"""
        pass
    
    def get_schema_names(self, connection, **kw):
        """Return a list of schema names available in the database.
        FairCom doesn't have schemas, so return None (default schema)."""
        return [None]
    
    def get_table_names(self, connection, schema=None, **kw):
        """Return a list of table names for the given schema.
        
        FairCom uses admin.systables to store table metadata.
        """
        try:
            result = connection.execute(
                text("SELECT tbl FROM admin.systables WHERE tbltype = 'T' ORDER BY tbl")
            )
            return [row[0] for row in result]
        except Exception:
            # If query fails, return empty list
            return []
    
    def get_columns(self, connection, table_name, schema=None, **kw):
        """Return column information for the given table.
        
        Query the table directly to introspect column structure.
        """
        try:
            # Query one row to get column structure
            result = connection.execute(text(f"SELECT TOP 1 * FROM {table_name}"))
            
            # Get column names from cursor description
            columns = []
            if hasattr(result, 'cursor') and hasattr(result.cursor, 'description'):
                for col_desc in result.cursor.description:
                    col_name = col_desc[0]
                    
                    columns.append({
                        'name': col_name,
                        'type': sqltypes.VARCHAR(length=255),  # Default type
                        'nullable': True,
                        'default': None
                    })
            
            return columns
        except Exception as e:
            # Table doesn't exist or can't be queried
            return []
    
    def has_table(self, connection, table_name, schema=None, **kw):
        """Check if a table exists."""
        # Try to query the table directly - if it exists, no error
        try:
            connection.execute(text(f"SELECT TOP 1 * FROM {table_name}"))
            return True
        except Exception:
            return False


# Register the dialect with SQLAlchemy
dialect = FairComJSONDialect
