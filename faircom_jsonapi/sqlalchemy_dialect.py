"""
SQLAlchemy dialect for FairCom JSON API
Allows SQLAlchemy to connect via the JSON API instead of native libraries
"""
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler
from sqlalchemy import types as sqltypes
from . import dbapi


class FairComJSONCompiler(compiler.SQLCompiler):
    """SQL compiler for FairCom - uses TOP syntax instead of LIMIT"""
    
    def limit_clause(self, select, **kwargs):
        """FairCom uses TOP syntax, not LIMIT - return empty string"""
        return ""
    
    def get_select_precolumns(self, select, **kwargs):
        """Add TOP clause before column list"""
        text = ""
        
        # Add TOP if we have a limit
        if select._limit_clause is not None:
            text += f"TOP {self.process(select._limit_clause, **kwargs)} "
        
        # Get any other precolumns from parent (like DISTINCT)
        text += super().get_select_precolumns(select, **kwargs)
        
        return text


class FairComJSONTypeCompiler(compiler.GenericTypeCompiler):
    """Type compiler for FairCom"""
    pass


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
