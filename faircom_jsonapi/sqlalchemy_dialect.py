"""
SQLAlchemy dialect for FairCom JSON API
Allows SQLAlchemy to connect via the JSON API instead of native libraries
"""
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler
from sqlalchemy import types as sqltypes
from . import dbapi


class FairComJSONCompiler(compiler.SQLCompiler):
    """SQL compiler for FairCom - uses T-SQL syntax (TOP, OFFSET/FETCH, etc.)"""
    
    def limit_clause(self, select, **kwargs):
        """Handle T-SQL pagination: OFFSET...FETCH or return empty if using TOP
        
        NOTE: FairCom requires literal integers for OFFSET/FETCH, not bind parameters.
        """
        text = ""
        
        # If we have OFFSET, we must use OFFSET...FETCH syntax (can't use TOP)
        if select._offset_clause is not None:
            # Extract the actual integer value from the offset clause
            offset_value = self._get_limit_or_offset_value(select._offset_clause)
            text = f"\nOFFSET {offset_value} ROWS"
            
            # Add FETCH if we have a limit
            if select._limit_clause is not None:
                limit_value = self._get_limit_or_offset_value(select._limit_clause)
                text += f" FETCH NEXT {limit_value} ROWS ONLY"
        
        # If no OFFSET, we use TOP syntax (handled in get_select_precolumns)
        return text
    
    def get_select_precolumns(self, select, **kwargs):
        """Add TOP clause before column list (only when no OFFSET)
        
        NOTE: FairCom requires literal integers in TOP clause, not bind parameters.
        We extract the actual integer value to avoid 'Syntax error near or at "?"'
        """
        text = ""
        
        # Use TOP only if we have a limit WITHOUT offset
        if select._limit_clause is not None and select._offset_clause is None:
            # Extract the actual integer value from the limit clause
            limit_value = self._get_limit_or_offset_value(select._limit_clause)
            text += f"TOP {limit_value} "
        
        # Get any other precolumns from parent (like DISTINCT)
        text += super().get_select_precolumns(select, **kwargs)
        
        return text
    
    def _get_limit_or_offset_value(self, clause):
        """Extract the literal integer value from a limit or offset clause.
        
        FairCom does not support parameterized TOP/OFFSET/FETCH values.
        This method extracts the actual integer value from the clause object.
        """
        # Try to get the value directly
        if hasattr(clause, 'value'):
            return clause.value
        
        # Try effective_value (for some SQLAlchemy versions)
        if hasattr(clause, 'effective_value'):
            return clause.effective_value
        
        # If it's a BindParameter, get its value
        if hasattr(clause, '_orig_val'):
            return clause._orig_val
        
        # If it's already an integer, return it
        if isinstance(clause, int):
            return clause
        
        # Last resort: try to render it with literal_binds in a subcompiler
        # Create a new compiler instance with literal_binds enabled
        from sqlalchemy.sql import visitors
        literal_compiler = self.__class__(
            self.dialect,
            None,
            compile_kwargs={'literal_binds': True}
        )
        return literal_compiler.process(clause, **{'literal_binds': True})
        
        # Get any other precolumns from parent (like DISTINCT)
        text += super().get_select_precolumns(select, **kwargs)
        
        return text
    
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
    
    # Enable statement caching for better performance
    supports_statement_cache = True
    
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


# Register the dialect with SQLAlchemy
dialect = FairComJSONDialect
