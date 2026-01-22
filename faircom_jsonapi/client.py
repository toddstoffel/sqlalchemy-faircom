"""
FairCom JSON API Client - Pure Python HTTP-based client
"""
import json
import requests


class FairComClientException(Exception):
    pass


class FairComClient:
    """Client for FairCom Database JSON API"""
    
    def __init__(self, url, debug=False):
        self.url = url
        self.isopen = False
        self.id = 0
        self.api_version = "1.0"
        self.debug = debug
        self.auth_token = None

    def _make_request(self, method, api, params):
        """Make a JSON API request"""
        if params is None:
            params = {}

        request = {
            "schema": "jsonCommand.org/v1",
            "requestId": self.id,
            "api": api,
            "apiVersion": self.api_version,
            "action": method,
            "params": params
        }
        self.id += 1
        
        if self.auth_token:
            request['authToken'] = self.auth_token

        if self.debug:
            print(json.dumps(request))

        result = requests.post(self.url, json=request, timeout=30, verify=False)

        if self.debug:
            print(result.text)
            
        result = result.json()
        
        if result.get('errorCode', 0) != 0:
            raise FairComClientException(result.get('errorMessage', 'Unknown error'))
        
        return result.get('result', {})

    def login(self, user, password):
        """Login and create a session"""
        result = self._make_request("createSession", 'admin', {
            "username": user, 
            "password": password
        })
        self.auth_token = result.get('authToken')
        return result

    def execute_sql(self, database_name, sql, params=None):
        """Execute SQL query and return results (SELECT statements only)"""
        if params is None:
            params = []
            
        return self._make_request("getRecordsUsingSQL", 'db', {
            "databaseName": database_name,
            "sql": sql,
            "sqlParams": params
        })

    def run_sql_statements(self, database_name, sql, params=None):
        """Execute SQL statements (DDL/DML operations like INSERT, UPDATE, DELETE, CREATE, etc.)"""
        # Note: runSqlStatements requires 'sqlStatements' as an array
        # and may not support parameterized queries via sqlParams
        if params and len(params) > 0:
            # TODO: Handle parameterized DDL/DML queries
            # For now, we'll pass the SQL as-is and let the API handle it
            pass
            
        return self._make_request("runSqlStatements", 'db', {
            "databaseName": database_name,
            "sqlStatements": [sql]  # Must be an array
        })

    def close(self):
        """Close the session"""
        if self.auth_token:
            try:
                self._make_request("closeSession", 'admin', {})
            except:
                pass
            finally:
                self.auth_token = None
