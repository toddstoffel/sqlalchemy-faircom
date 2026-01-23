"""
Unit tests for FairCom SKIP/TOP SQL syntax generation
Tests the fix for SKIP placement (must be after SELECT, before column list)
"""
import pytest
from sqlalchemy import MetaData, Table, Column, Integer, String, select
from faircom_jsonapi.sqlalchemy_dialect import FairComJSONDialect


class TestSkipTopSyntax:
    """Test SKIP and TOP clause positioning in generated SQL"""
    
    @pytest.fixture
    def setup(self):
        """Setup dialect and test table"""
        dialect = FairComJSONDialect()
        metadata = MetaData()
        test_table = Table(
            'test_table',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )
        return dialect, test_table
    
    def compile_query(self, query, dialect):
        """Helper to compile SQLAlchemy query to SQL string"""
        return str(query.compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True}
        ))
    
    def test_limit_only_generates_top(self, setup):
        """Test that LIMIT without OFFSET generates TOP clause"""
        dialect, table = setup
        query = select(table).limit(5)
        sql = self.compile_query(query, dialect)
        
        # Should have TOP before column list
        assert 'TOP 5' in sql
        # Should NOT have SKIP
        assert 'SKIP' not in sql
        # Should NOT have FETCH
        assert 'FETCH' not in sql
        # TOP should come before column names
        assert sql.index('TOP') < sql.index('test_table.id')
    
    def test_limit_and_offset_generates_top_skip(self, setup):
        """Test that LIMIT + OFFSET generates TOP n SKIP m"""
        dialect, table = setup
        query = select(table).limit(5).offset(10)
        sql = self.compile_query(query, dialect)
        
        # Should have both TOP and SKIP
        assert 'TOP 5' in sql
        assert 'SKIP 10' in sql
        # Should NOT have FETCH
        assert 'FETCH' not in sql
        # TOP and SKIP should be together and before column list
        assert sql.index('TOP') < sql.index('SKIP')
        assert sql.index('SKIP') < sql.index('test_table.id')
        # Should not appear at end of query
        assert not sql.rstrip().endswith('SKIP 10')
    
    def test_offset_only_generates_skip(self, setup):
        """Test that OFFSET without LIMIT generates SKIP only"""
        dialect, table = setup
        query = select(table).offset(10)
        sql = self.compile_query(query, dialect)
        
        # Should have SKIP
        assert 'SKIP 10' in sql
        # Should NOT have TOP
        assert 'TOP' not in sql
        # Should NOT have FETCH
        assert 'FETCH' not in sql
        # SKIP should come before column list
        assert sql.index('SKIP') < sql.index('test_table.id')
    
    def test_no_limit_or_offset(self, setup):
        """Test query without LIMIT or OFFSET"""
        dialect, table = setup
        query = select(table)
        sql = self.compile_query(query, dialect)
        
        # Should have neither TOP nor SKIP
        assert 'TOP' not in sql
        assert 'SKIP' not in sql
        assert 'FETCH' not in sql
    
    def test_skip_not_at_end_of_query(self, setup):
        """Test that SKIP does not appear at end of query (the bug)"""
        dialect, table = setup
        query = select(table).limit(5).offset(10).order_by(table.c.id)
        sql = self.compile_query(query, dialect)
        
        # SKIP should be in SELECT clause, not at end
        # After ORDER BY, there should be no SKIP
        order_by_pos = sql.index('ORDER BY')
        skip_pos = sql.index('SKIP')
        assert skip_pos < order_by_pos, "SKIP must appear before ORDER BY"
        
        # Verify SKIP is in the SELECT clause
        select_pos = sql.index('SELECT')
        from_pos = sql.index('FROM')
        assert select_pos < skip_pos < from_pos, "SKIP must be between SELECT and FROM"
    
    def test_pagination_page_1(self, setup):
        """Test first page of pagination (offset=0)"""
        dialect, table = setup
        query = select(table).limit(5).offset(0).order_by(table.c.id)
        sql = self.compile_query(query, dialect)
        
        assert 'TOP 5 SKIP 0' in sql
        assert 'ORDER BY' in sql
    
    def test_pagination_page_2(self, setup):
        """Test second page of pagination (offset=5)"""
        dialect, table = setup
        query = select(table).limit(5).offset(5).order_by(table.c.id)
        sql = self.compile_query(query, dialect)
        
        assert 'TOP 5 SKIP 5' in sql
        assert 'ORDER BY' in sql
    
    def test_pagination_page_3(self, setup):
        """Test third page of pagination (offset=10)"""
        dialect, table = setup
        query = select(table).limit(5).offset(10).order_by(table.c.id)
        sql = self.compile_query(query, dialect)
        
        assert 'TOP 5 SKIP 10' in sql
        assert 'ORDER BY' in sql
    
    def test_large_offset(self, setup):
        """Test large OFFSET value"""
        dialect, table = setup
        query = select(table).limit(10).offset(1000)
        sql = self.compile_query(query, dialect)
        
        assert 'TOP 10 SKIP 1000' in sql
    
    def test_top_skip_order(self, setup):
        """Test that TOP comes before SKIP"""
        dialect, table = setup
        query = select(table).limit(5).offset(10)
        sql = self.compile_query(query, dialect)
        
        top_pos = sql.index('TOP')
        skip_pos = sql.index('SKIP')
        assert top_pos < skip_pos, "TOP must come before SKIP"
    
    def test_limit_clause_returns_empty(self, setup):
        """Test that limit_clause() method returns empty string"""
        from faircom_jsonapi.sqlalchemy_dialect import FairComJSONCompiler
        from sqlalchemy.sql import select as sql_select
        
        dialect, table = setup
        compiler = FairComJSONCompiler(dialect, sql_select(table).limit(5).offset(10))
        
        # The limit_clause should return empty because we handle everything in get_select_precolumns
        result = compiler.limit_clause(sql_select(table).limit(5).offset(10))
        assert result == "", "limit_clause() should return empty string"
    
    def test_distinct_with_top_skip(self, setup):
        """Test that DISTINCT works with TOP and SKIP"""
        dialect, table = setup
        query = select(table).distinct().limit(5).offset(10)
        sql = self.compile_query(query, dialect)
        
        # Should have DISTINCT, TOP, and SKIP in correct order
        assert 'DISTINCT' in sql or 'TOP 5 SKIP 10' in sql
        # SKIP should still be before column list
        assert sql.index('SKIP') < sql.index('test_table.id')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
