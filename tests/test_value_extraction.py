"""
Unit tests for _get_limit_or_offset_value() method
Ensures correct value extraction from various SQLAlchemy clause types
"""
import pytest
from sqlalchemy import MetaData, Table, Column, Integer, String, select
from faircom_jsonapi.sqlalchemy_dialect import FairComJSONDialect, FairComJSONCompiler


class TestValueExtraction:
    """Test the _get_limit_or_offset_value method"""
    
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
    
    def test_extract_offset_zero(self, setup):
        """Test extracting offset value of 0"""
        dialect, table = setup
        stmt = select(table).offset(0)
        compiler = FairComJSONCompiler(dialect, stmt)
        
        value = compiler._get_limit_or_offset_value(stmt._offset_clause)
        assert value == 0
    
    def test_extract_offset_positive(self, setup):
        """Test extracting positive offset values"""
        dialect, table = setup
        
        for expected in [1, 5, 10, 20, 50, 100, 1000]:
            stmt = select(table).offset(expected)
            compiler = FairComJSONCompiler(dialect, stmt)
            
            value = compiler._get_limit_or_offset_value(stmt._offset_clause)
            assert value == expected, f"Expected {expected} but got {value}"
    
    def test_extract_limit_values(self, setup):
        """Test extracting limit values"""
        dialect, table = setup
        
        for expected in [1, 5, 10, 25, 50, 100]:
            stmt = select(table).limit(expected)
            compiler = FairComJSONCompiler(dialect, stmt)
            
            value = compiler._get_limit_or_offset_value(stmt._limit_clause)
            assert value == expected, f"Expected {expected} but got {value}"
    
    def test_extract_combined_limit_offset(self, setup):
        """Test extracting both limit and offset from same query"""
        dialect, table = setup
        
        test_cases = [
            (5, 0),
            (5, 5),
            (10, 20),
            (25, 100),
        ]
        
        for limit_val, offset_val in test_cases:
            stmt = select(table).limit(limit_val).offset(offset_val)
            compiler = FairComJSONCompiler(dialect, stmt)
            
            extracted_limit = compiler._get_limit_or_offset_value(stmt._limit_clause)
            extracted_offset = compiler._get_limit_or_offset_value(stmt._offset_clause)
            
            assert extracted_limit == limit_val, f"Limit: expected {limit_val} but got {extracted_limit}"
            assert extracted_offset == offset_val, f"Offset: expected {offset_val} but got {extracted_offset}"
    
    def test_sql_output_has_correct_values(self, setup):
        """Test that the generated SQL contains the correct SKIP/TOP values"""
        dialect, table = setup
        
        test_cases = [
            (5, 0, "TOP 5 SKIP 0"),
            (5, 5, "TOP 5 SKIP 5"),
            (10, 20, "TOP 10 SKIP 20"),
            (25, 100, "TOP 25 SKIP 100"),
        ]
        
        for limit_val, offset_val, expected_clause in test_cases:
            stmt = select(table).limit(limit_val).offset(offset_val)
            sql = str(stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
            
            assert expected_clause in sql, f"Expected '{expected_clause}' in SQL but got: {sql}"
    
    def test_offset_only_sql(self, setup):
        """Test SQL output for offset-only queries"""
        dialect, table = setup
        
        for offset_val in [5, 10, 20, 50]:
            stmt = select(table).offset(offset_val)
            sql = str(stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
            
            expected = f"SKIP {offset_val}"
            assert expected in sql, f"Expected '{expected}' in SQL but got: {sql}"
            # Should not have TOP when there's no LIMIT
            assert "TOP" not in sql or sql.index("SKIP") < sql.index("TOP")
    
    def test_limit_only_sql(self, setup):
        """Test SQL output for limit-only queries"""
        dialect, table = setup
        
        for limit_val in [5, 10, 25, 50]:
            stmt = select(table).limit(limit_val)
            sql = str(stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
            
            expected = f"TOP {limit_val}"
            assert expected in sql, f"Expected '{expected}' in SQL but got: {sql}"
            # Should not have SKIP when there's no OFFSET
            assert "SKIP" not in sql
    
    def test_integer_passthrough(self, setup):
        """Test that integer values are passed through directly"""
        dialect, table = setup
        compiler = FairComJSONCompiler(dialect, select(table))
        
        # Test with direct integer values
        assert compiler._get_limit_or_offset_value(0) == 0
        assert compiler._get_limit_or_offset_value(5) == 5
        assert compiler._get_limit_or_offset_value(100) == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
