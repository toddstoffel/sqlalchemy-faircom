"""
Unit tests for FairCom JSON API SQLAlchemy dialect
"""
import pytest
from sqlalchemy import create_engine, text
from faircom_jsonapi.dbapi import connect, Connection, Cursor
from faircom_jsonapi.client import FairComClient


class TestDBAPI:
    """Test DB-API 2.0 interface"""
    
    def test_module_attributes(self):
        """Test DB-API required module attributes"""
        from faircom_jsonapi import dbapi
        assert dbapi.apilevel == '2.0'
        assert dbapi.threadsafety == 1
        assert dbapi.paramstyle == 'qmark'
    
    def test_connection_creation(self):
        """Test connection object creation"""
        # This is a basic test - actual connection requires server
        conn = Connection.__new__(Connection)
        assert hasattr(conn, 'cursor')
        assert hasattr(conn, 'commit')
        assert hasattr(conn, 'rollback')
        assert hasattr(conn, 'close')


class TestSQLAlchemy:
    """Test SQLAlchemy dialect"""
    
    def test_connection_string_parsing(self):
        """Test connection string parsing"""
        from faircom_jsonapi.sqlalchemy_dialect import FairComJSONDialect
        from sqlalchemy.engine import url
        
        dialect = FairComJSONDialect()
        connection_url = url.make_url(
            'faircom+jsonapi://user:pass@localhost:8080/ctreeSQL?protocol=http'
        )
        
        args, kwargs = dialect.create_connect_args(connection_url)
        
        assert kwargs['host'] == 'localhost'
        assert kwargs['port'] == 8080
        assert kwargs['username'] == 'user'
        assert kwargs['password'] == 'pass'
        assert kwargs['database'] == 'ctreeSQL'
        assert kwargs['protocol'] == 'http'
    
    def test_dialect_attributes(self):
        """Test dialect has required attributes"""
        from faircom_jsonapi.sqlalchemy_dialect import FairComJSONDialect
        
        dialect = FairComJSONDialect()
        assert dialect.name == 'faircom'
        assert dialect.driver == 'jsonapi'
        assert dialect.supports_alter is True
        assert dialect.supports_unicode_statements is True


class TestClient:
    """Test FairCom JSON API client"""
    
    def test_client_creation(self):
        """Test client instantiation"""
        client = FairComClient("http://localhost:8080/api/db", debug=False)
        assert client.url == "http://localhost:8080/api/db"
        assert client.debug is False
        assert client.auth_token is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
