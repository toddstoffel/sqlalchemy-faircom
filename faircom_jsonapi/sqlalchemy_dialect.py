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
    
    # FairCom uses T-SQL syntax - add T-SQL reserved words
    # This ensures SQLAlchemy quotes identifiers that conflict with reserved words
    reserved_words = {
        'add', 'all', 'alter', 'and', 'any', 'as', 'asc', 'authorization',
        'backup', 'begin', 'between', 'break', 'browse', 'bulk', 'by',
        'cascade', 'case', 'check', 'checkpoint', 'close', 'clustered', 'coalesce',
        'collate', 'column', 'commit', 'compute', 'constraint', 'contains',
        'containstable', 'continue', 'convert', 'count', 'create', 'cross',
        'current', 'current_date', 'current_time', 'current_timestamp',
        'current_user', 'cursor', 'database', 'dbcc', 'deallocate',
        'declare', 'default', 'delete', 'deny', 'desc', 'disk', 'distinct',
        'distributed', 'double', 'drop', 'dump', 'else', 'end', 'errlvl',
        'escape', 'except', 'exec', 'execute', 'exists', 'exit', 'external',
        'fetch', 'file', 'fillfactor', 'for', 'foreign', 'freetext',
        'freetexttable', 'from', 'full', 'function', 'goto', 'grant', 'group',
        'having', 'holdlock', 'identity', 'identity_insert', 'identitycol',
        'if', 'in', 'index', 'inner', 'insert', 'intersect', 'into', 'is',
        'join', 'key', 'kill', 'left', 'like', 'lineno', 'load', 'merge',
        'national', 'nocheck', 'nonclustered', 'not', 'null', 'nullif', 'of',
        'off', 'offsets', 'on', 'open', 'opendatasource', 'openquery',
        'openrowset', 'openxml', 'option', 'or', 'order', 'outer', 'over',
        'percent', 'pivot', 'plan', 'precision', 'primary', 'print', 'proc',
        'procedure', 'public', 'raiserror', 'read', 'readtext', 'reconfigure',
        'references', 'replication', 'restore', 'restrict', 'return', 'revert',
        'revoke', 'right', 'rollback', 'rowcount', 'rowguidcol', 'rule', 'save',
        'schema', 'securityaudit', 'select', 'semantickeyphrasetable',
        'semanticsimilaritydetailstable', 'semanticsimilaritytable', 'session_user',
        'set', 'setuser', 'shutdown', 'some', 'statistics', 'sum', 'system_user',
        'table', 'tablesample', 'textsize', 'then', 'to', 'top', 'tran',
        'transaction', 'trigger', 'truncate', 'try_convert', 'tsequal',
        'union', 'unique', 'unpivot', 'update', 'updatetext', 'use', 'user',
        'values', 'varying', 'view', 'waitfor', 'when', 'where', 'while',
        'with', 'withingroup', 'writetext'
    }
    
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
    
    def _get_username_from_connection(self, connection):
        """Extract username from the connection.
        
        Returns the username that authenticated the connection,
        which is used as the schema name in FairCom's Oracle-style naming.
        """
        try:
            # Get the underlying DBAPI connection
            dbapi_conn = connection.connection
            if hasattr(dbapi_conn, 'username'):
                return dbapi_conn.username
        except Exception:
            pass
        # Default fallback
        return 'ADMIN'
    
    def get_schema_names(self, connection, **kw):
        """Return a list of schema names available in the database.
        FairCom uses Oracle-style schema.table naming where schema = username.
        Return the authenticated username as the schema."""
        username = self._get_username_from_connection(connection)
        return [username]
    
    def get_table_names(self, connection, schema=None, **kw):
        """Return a list of table names for the given schema.
        
        FairCom uses Oracle-style schema.table naming where the schema is the username.
        """
        try:
            # Get the username to query the correct schema's systables
            username = schema if schema else self._get_username_from_connection(connection)
            
            # Query username.systables (username must match connection credentials)
            result = connection.execute(
                text(f"SELECT tbl FROM {username}.systables WHERE tbltype = 'T' ORDER BY tbl")
            )
            return [row[0] for row in result]
        except Exception:
            # If query fails, return empty list
            return []
    
    def get_view_names(self, connection, schema=None, **kw):
        """Return a list of view names for the given schema.
        
        FairCom views are also stored in systables with tbltype = 'V'.
        """
        try:
            # Get the username to query the correct schema's systables
            username = schema if schema else self._get_username_from_connection(connection)
            
            result = connection.execute(
                text(f"SELECT tbl FROM {username}.systables WHERE tbltype = 'V' ORDER BY tbl")
            )
            return [row[0] for row in result]
        except Exception:
            # If query fails, return empty list (no views)
            return []
    
    def get_columns(self, connection, table_name, schema=None, **kw):
        """Return column information for the given table.
        
        Query the table directly to introspect column structure.
        If schema is provided, use schema.table format (Oracle-style).
        """
        try:
            # Build table reference - use schema.table if schema provided
            if schema and schema.upper() != 'ADMIN':
                # If non-ADMIN schema, use qualified name
                table_ref = f"{schema}.{table_name}"
            else:
                # ADMIN schema or no schema - just use table name
                table_ref = table_name
            
            # Query one row to get column structure
            result = connection.execute(text(f"SELECT TOP 1 * FROM {table_ref}"))
            
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
    
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        """Return primary key constraint information.
        
        FairCom doesn't expose PK metadata easily via JSON API.
        Return empty dict to indicate no PK info available.
        """
        return {'constrained_columns': [], 'name': None}
    
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        """Return foreign key information.
        
        FairCom doesn't expose FK metadata easily via JSON API.
        Return empty list to indicate no FK info available.
        """
        return []
    
    def get_indexes(self, connection, table_name, schema=None, **kw):
        """Return index information.
        
        FairCom doesn't expose index metadata easily via JSON API.
        Return empty list to indicate no index info available.
        """
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
