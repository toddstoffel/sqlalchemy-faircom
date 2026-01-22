"""
DB-API 2.0 compliant interface for FairCom JSON API
This allows the driver to work with SQLAlchemy and other tools expecting DB-API interface.
"""
from .client import FairComClient, FairComClientException
import re

# DB-API 2.0 module attributes
apilevel = '2.0'
threadsafety = 1  # Threads may share the module, but not connections
paramstyle = 'qmark'  # Question mark style, e.g. ...WHERE name=?


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

    def execute(self, operation, parameters=None):
        """Execute a database operation (query or command)"""
        if parameters is None:
            parameters = []
        
        # CONVERT LIMIT TO TOP FOR FAIRCOM COMPATIBILITY
        # FairCom does not support LIMIT syntax, only TOP
        # This handles raw SQL queries from tools like Superset
        limit_match = re.search(r'\s+LIMIT\s+(\d+)\s*$', operation, re.IGNORECASE | re.DOTALL)
        
        if limit_match:
            limit_value = limit_match.group(1)
            # Remove LIMIT clause
            operation = re.sub(r'\s+LIMIT\s+\d+\s*$', '', operation, flags=re.IGNORECASE | re.DOTALL)
            
            # Add TOP if not already present
            if not re.search(r'SELECT\s+TOP\s+\d+', operation, re.IGNORECASE):
                operation = re.sub(r'(SELECT)\s+', rf'\1 TOP {limit_value} ', operation, count=1, flags=re.IGNORECASE)
            
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
