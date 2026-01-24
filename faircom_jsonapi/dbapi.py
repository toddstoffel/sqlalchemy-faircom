"""
DB-API 2.0 compliant interface for FairCom JSON API
This allows the driver to work with SQLAlchemy and other tools expecting DB-API interface.
"""
from .client import FairComClient, FairComClientException
import re
import sqlparse
from sqlparse.sql import Token, TokenList
from sqlparse.tokens import Keyword

# DB-API 2.0 module attributes
apilevel = '2.0'
threadsafety = 1  # Threads may share the module, but not connections
paramstyle = 'qmark'  # Question mark style, e.g. ...WHERE name=?

# Set to True to enable detailed SQL logging
DEBUG_SQL = False


class Error(Exception):
    pass


class DatabaseError(Error):
    pass


class IntegrityError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class Cursor:
    """DB-API 2.0 compliant cursor"""
    
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self.rowcount = -1
        self._results = []
        self._result_index = 0
        self.arraysize = 1
    
    def _convert_limit_to_top(self, sql):
        """Convert LIMIT/OFFSET to TOP/SKIP using proper SQL parsing.
        
        This uses sqlparse to properly handle nested queries, comments, and strings.
        Much more robust than regex-based approaches.
        """
        import sys
        
        # Parse the SQL into tokens
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql
        
        # Process each statement (usually just one)
        converted_statements = []
        for statement in parsed:
            converted = self._convert_statement_limit_to_top(statement)
            converted_statements.append(str(converted))
        
        return ''.join(converted_statements)
    
    def _convert_statement_limit_to_top(self, statement):
        """Recursively convert LIMIT/OFFSET in a SQL statement."""
        import sys
        
        # Find LIMIT and OFFSET values by scanning tokens
        limit_value = None
        offset_value = None
        
        tokens = list(statement.flatten())
        for i, token in enumerate(tokens):
            if token.ttype is Keyword and token.value.upper() == 'LIMIT':
                # Next non-whitespace token should be the limit value
                for j in range(i + 1, len(tokens)):
                    if not tokens[j].is_whitespace:
                        limit_value = tokens[j].value
                        break
            elif token.ttype is Keyword and token.value.upper() == 'OFFSET':
                # Next non-whitespace token should be the offset value
                for j in range(i + 1, len(tokens)):
                    if not tokens[j].is_whitespace:
                        offset_value = tokens[j].value
                        break
        
        # If we found LIMIT, convert to TOP
        if limit_value:
            # Rebuild the SQL
            sql_str = str(statement)
            
            # Find SELECT keyword and insert TOP after it
            select_match = re.search(r'\bSELECT\b', sql_str, re.IGNORECASE)
            if select_match:
                select_pos = select_match.end()
                
                # Build the TOP/SKIP clause
                if offset_value:
                    top_clause = f" TOP {limit_value} SKIP {offset_value}"
                    print(f"[DBAPI] Converted LIMIT {limit_value} OFFSET {offset_value} to TOP/SKIP", file=sys.stderr)
                else:
                    top_clause = f" TOP {limit_value}"
                    print(f"[DBAPI] Converted LIMIT {limit_value} to TOP", file=sys.stderr)
                
                # Remove LIMIT and OFFSET clauses from the end
                sql_str = re.sub(r'\s+LIMIT\s+\d+', '', sql_str, flags=re.IGNORECASE)
                sql_str = re.sub(r'\s+OFFSET\s+\d+', '', sql_str, flags=re.IGNORECASE)
                
                # Insert TOP clause after SELECT
                sql_str = sql_str[:select_pos] + top_clause + sql_str[select_pos:]
                
                return sqlparse.parse(sql_str)[0]
        
        return statement
    
    def _quote_reserved_words(self, sql_str):
        """Quote T-SQL reserved words used as identifiers in SQL.
        
        This handles cases where column aliases or identifiers use reserved words like 'count',
        which FairCom SQL engine rejects. Common pattern: COUNT(*) AS count
        """
        # T-SQL reserved words that commonly appear as column aliases
        common_reserved = {
            'count', 'sum', 'avg', 'min', 'max', 'date', 'time', 'timestamp',
            'user', 'table', 'view', 'index', 'key', 'value', 'default', 'order'
        }
        
        # Pattern: AS <word> (where word is a reserved word not already quoted)
        # Matches: AS count, AS sum, etc. but not AS "count" or AS [count]
        for word in common_reserved:
            # Match AS <word> in various positions (after SELECT, in ORDER BY, etc.)
            # Use word boundaries to avoid matching partial words
            pattern = r'\bAS\s+(' + word + r')\b(?!\s*["\[])'
            replacement = r'AS "' + word + r'"'
            sql_str = re.sub(pattern, replacement, sql_str, flags=re.IGNORECASE)
            
            # Also handle ORDER BY <word> (unquoted reserved word)
            pattern = r'\bORDER\s+BY\s+(' + word + r')\b(?!\s*["\[])'
            replacement = r'ORDER BY "' + word + r'"'
            sql_str = re.sub(pattern, replacement, sql_str, flags=re.IGNORECASE)
            
            # Handle GROUP BY <word>
            pattern = r'\bGROUP\s+BY\s+(' + word + r')\b(?!\s*["\[])'
            replacement = r'GROUP BY "' + word + r'"'
            sql_str = re.sub(pattern, replacement, sql_str, flags=re.IGNORECASE)
        
        return sql_str

    def execute(self, operation, parameters=None):
        """Execute a database operation (query or command)"""
        if parameters is None:
            parameters = []
        
        # Log original SQL for debugging
        import sys
        print(f"[DBAPI] ===== ORIGINAL SQL =====", file=sys.stderr)
        print(operation, file=sys.stderr)
        print(f"[DBAPI] ===== END ORIGINAL =====", file=sys.stderr)
        
        # CONVERT LIMIT/OFFSET TO TOP/SKIP FOR FAIRCOM COMPATIBILITY
        # Use proper SQL parsing instead of fragile regex
        operation = self._convert_limit_to_top(operation)
        
        # QUOTE RESERVED WORDS used as identifiers
        # This handles cases like: COUNT(*) AS count, ORDER BY count
        operation = self._quote_reserved_words(operation)
        
        print(f"[DBAPI] ===== FINAL SQL =====", file=sys.stderr)
        print(operation, file=sys.stderr)
        print(f"[DBAPI] ===== END FINAL =====", file=sys.stderr)
            
        try:
            # Determine if this is a SELECT query or a DDL/DML statement
            sql_upper = operation.strip().upper()
            is_select = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
            
            if is_select:
                # Use getRecordsUsingSQL for SELECT queries
                result = self.connection.client.execute_sql(
                    self.connection.database,
                    operation,
                    parameters
                )
            else:
                # Use runSqlStatements for DDL/DML (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)
                result = self.connection.client.run_sql_statements(
                    self.connection.database,
                    operation,
                    parameters
                )
            
            # Build description from fields
            fields = result.get('fields', [])
            if fields:
                self.description = [
                    (
                        field['name'],  # name
                        field['type'],  # type_code
                        None,  # display_size
                        None,  # internal_size
                        None,  # precision
                        None,  # scale
                        None   # null_ok
                    )
                    for field in fields
                ]
            else:
                self.description = None
            
            # Store results
            self._results = result.get('data', [])
            self._result_index = 0
            # For DDL/DML operations, use affectedRecordCount if available
            self.rowcount = result.get('affectedRecordCount', result.get('returnedRecordCount', len(self._results)))
            
        except FairComClientException as e:
            raise DatabaseError(str(e))

    def executemany(self, operation, seq_of_parameters):
        """Execute a database operation multiple times"""
        for parameters in seq_of_parameters:
            self.execute(operation, parameters)

    def fetchone(self):
        """Fetch the next row of a query result set"""
        if self._result_index >= len(self._results):
            return None
        row = self._results[self._result_index]
        self._result_index += 1
        # Convert dict to tuple based on description order
        if self.description:
            return tuple(row.get(col[0]) for col in self.description)
        return tuple(row.values())

    def fetchmany(self, size=None):
        """Fetch the next set of rows of a query result"""
        if size is None:
            size = self.arraysize
        results = []
        for _ in range(size):
            row = self.fetchone()
            if row is None:
                break
            results.append(row)
        return results

    def fetchall(self):
        """Fetch all remaining rows of a query result"""
        results = []
        while True:
            row = self.fetchone()
            if row is None:
                break
            results.append(row)
        return results

    def close(self):
        """Close the cursor"""
        self._results = []
        self.description = None

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class Connection:
    """DB-API 2.0 compliant connection"""
    
    def __init__(self, host, port=8080, username='ADMIN', password='ADMIN', 
                 database='ctreeSQL', protocol='http', debug=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.protocol = protocol
        self.debug = debug
        
        url = f"{protocol}://{host}:{port}/api/db"
        self.client = FairComClient(url, debug=debug)
        self.client.login(username, password)

    def cursor(self):
        """Return a new Cursor Object using the connection"""
        return Cursor(self)

    def commit(self):
        """Commit any pending transaction (not applicable for read operations)"""
        pass

    def rollback(self):
        """Rollback to the start of any pending transaction"""
        pass

    def close(self):
        """Close the connection"""
        self.client.close()


def connect(host, port=8080, username='ADMIN', password='ADMIN', 
            database='ctreeSQL', protocol='http', debug=False):
    """
    Create a connection to the FairCom database via JSON API
    
    Args:
        host: Database host
        port: JSON API port (default 8080)
        username: Database username
        password: Database password
        database: Database name (default 'ctreeSQL')
        protocol: 'http' or 'https' (default 'http')
        debug: Enable debug output
    """
    return Connection(host, port, username, password, database, protocol, debug)
