# Using sqlalchemy-faircom with Apache Superset

This guide explains how to connect Apache Superset to FairCom Database using the `sqlalchemy-faircom` connector.

## Prerequisites

- Apache Superset installed and running
- FairCom Database server running with JSON/REST API enabled
- FairCom server credentials (username and password)
- The `sqlalchemy-faircom` connector installed in your Superset environment

## Installation

The `sqlalchemy-faircom` connector must be installed in the same Python environment where Superset is running.

### Step 1: Install the Connector

```bash
pip install sqlalchemy-faircom
```

### Step 2: Configure Superset for FairCom

**IMPORTANT**: Superset requires additional configuration files to properly parse FairCom's T-SQL syntax.

#### Required Configuration Files

Two files must be added to your Superset pythonpath:

1. **`faircom_engine_spec.py`** - Engine specification for Superset
2. **`superset_config.py`** - Registers FairCom with sqlglot parser

These files are included with the package in `examples/superset/`. Find them in your Python site-packages:

```bash
# Find the examples directory
python -c "import os, sqlalchemy_faircom; print(os.path.dirname(sqlalchemy_faircom.__file__))"

# Look for: ../examples/superset/
```

Or download from GitHub:
- [faircom_engine_spec.py](https://github.com/toddstoffel/sqlalchemy-faircom/blob/main/examples/superset/faircom_engine_spec.py)
- [superset_config.py](https://github.com/toddstoffel/sqlalchemy-faircom/blob/main/examples/superset/superset_config.py)

#### Installation Methods

**Option A: Docker Deployment**

Add to your Dockerfile:
```dockerfile
FROM apache/superset:latest

# Install sqlalchemy-faircom
RUN pip install sqlalchemy-faircom

# Copy FairCom configuration files
COPY faircom_engine_spec.py /app/pythonpath/
COPY superset_config.py /app/pythonpath/
```

Or copy to running container:
```bash
docker cp faircom_engine_spec.py superset:/app/pythonpath/
docker cp superset_config.py superset:/app/pythonpath/
docker restart superset
```

Or mount as volumes in docker-compose.yml:
```yaml
services:
  superset:
    volumes:
      - ./faircom_engine_spec.py:/app/pythonpath/faircom_engine_spec.py
      - ./superset_config.py:/app/pythonpath/superset_config.py
```

**Option B: Local Installation**

```bash
# Find your Superset config directory
superset config

# Copy files (typically to ~/.superset/)
cp faircom_engine_spec.py ~/.superset/
cp superset_config.py ~/.superset/
```

### Step 3: Verify Installation

After restarting Superset, check the logs for:

```
✓ FairCom engine spec registered successfully
```

If you see this message, FairCom is properly configured. If not, ensure both files are in the same directory and in your PYTHONPATH.

**Why These Files Are Needed:**

Superset uses **sqlglot** to parse and validate SQL queries. By default, sqlglot doesn't recognize FairCom's T-SQL dialect (TOP, SKIP syntax). These configuration files:
- Register FairCom with sqlglot's T-SQL parser  
- Provide connection string templates
- Enable proper syntax highlighting and query validation

Without these files, you'll see SQL parsing errors when using Superset's query builder.

**For system administrators**: If you manage Superset's deployment, ensure this package is included in your Superset environment dependencies. The connector will automatically register itself with SQLAlchemy via entry points.

## Connection Configuration

### Connection String Format

```
faircom://username:password@host:port/database?protocol=http
```

### Example Connection Strings

**HTTP Connection (local server):**
```
faircom://ADMIN:ADMIN@localhost:8080/mydb?protocol=http
```

**HTTP Connection (remote server):**
```
faircom://ADMIN:ADMIN@faircom-server.example.com:8080/mydb?protocol=http
```

**HTTPS Connection:**
```
faircom://ADMIN:ADMIN@secure.example.com:8443/mydb?protocol=https
```

### Important: Case-Sensitive Credentials

⚠️ **FairCom credentials are case-sensitive!**

The default FairCom credentials are:
- **Username**: `ADMIN` (uppercase)
- **Password**: `ADMIN` (uppercase)

Using lowercase `admin:admin` will result in authentication errors like:
```
Invalid password
```

Always verify your credentials match the exact case configured in your FairCom server.

## Adding FairCom Database in Superset

### Step 1: Navigate to Databases

1. Log into Superset
2. Click **Settings** (gear icon) → **Database Connections**
3. Click **+ Database** button

### Step 2: Select Database Type

- **Display Name**: Enter a friendly name (e.g., "FairCom Production")
- **SQLAlchemy URI**: Enter your connection string

Example:
```
faircom://ADMIN:ADMIN@your-server.example.com:8080/your_database?protocol=http
```

Replace `your-server.example.com`, `8080`, and `your_database` with your actual FairCom server details.

### Step 3: Test Connection

Click **Test Connection** to verify:
- ✅ Server is reachable
- ✅ Credentials are correct
- ✅ Database exists
- ✅ Connector is properly installed

### Step 4: Advanced Settings (Optional)

Under **Advanced** → **SQL Lab**:
- Enable **Expose database in SQL Lab** to query directly
- Enable **Allow CREATE TABLE AS** for creating tables from queries
- Enable **Allow CREATE VIEW AS** for creating views

Under **Advanced** → **Performance**:
- Set **Chart cache timeout** (default: 0 for no caching)
- Configure **Connection pool settings** if needed

### Step 5: Save

Click **Connect** to save the database connection.

## Using FairCom with SQL Lab

Once connected, you can use SQL Lab to query your FairCom database:

1. Click **SQL** → **SQL Lab**
2. Select your FairCom database from the **Database** dropdown
3. Write your query:

```sql
SELECT * FROM employees LIMIT 100
```

![SQL Lab Example](images/sqllab.png)

### SQL Compatibility Notes

The `sqlalchemy-faircom` connector automatically handles SQL dialect differences:

- **Standard SQL**: Write queries using standard `LIMIT` and `OFFSET` syntax
- **Automatic Conversion**: The connector transparently converts to FairCom's `TOP` and `SKIP` syntax
- **Nested Queries**: Properly handles `LIMIT` clauses in subqueries

Example query with pagination:
```sql
SELECT emp_id, name, salary 
FROM employees 
WHERE dept = 'Engineering'
ORDER BY salary DESC
LIMIT 50 OFFSET 100
```

This automatically converts to FairCom's native syntax internally.

## Creating Charts and Dashboards

### Step 1: Create a Dataset

1. Click **Data** → **Datasets**
2. Click **+ Dataset**
3. Select your FairCom database
4. Choose a table
5. Click **Create Dataset and Create Chart**

### Step 2: Build Your Chart

Use Superset's chart builder to visualize your FairCom data:
- Choose chart type (Bar, Line, Pie, Table, etc.)
- Configure metrics and dimensions
- Apply filters
- Customize styling

### Step 3: Add to Dashboard

![Chart Example](images/chart.png)

Once your chart is saved, add it to a dashboard for monitoring and analysis.

## Troubleshooting

### Error: "Can't load plugin: sqlalchemy.dialects:faircom"

**Cause**: The connector is not installed or Superset hasn't been restarted after installation.

**Solution**:
1. Verify the connector is installed in Superset's Python environment:
   ```bash
   pip show sqlalchemy-faircom
   ```

2. If not installed, install it:
   ```bash
   pip install sqlalchemy-faircom
   ```

3. Restart Superset completely

4. If the issue persists, contact your Superset administrator to ensure the package is installed in the correct Python environment

### Error: "Invalid password"

**Cause**: Credentials are case-sensitive and may not match.

**Solution**: 
- Verify credentials with your FairCom administrator
- Default credentials are `ADMIN:ADMIN` (uppercase)
- Check connection string: `faircom://ADMIN:ADMIN@host:port/db?protocol=http`

### Error: "Connection refused" or "Timeout"

**Cause**: Cannot reach FairCom server or wrong port/protocol.

**Solution**:
- Verify FairCom server is running
- Check firewall rules allow access to the port
- Verify protocol is correct (`http` vs `https`)
- Test connectivity: `curl http://host:port/api/system/health`

### Error: Database not found

**Cause**: Database name in connection string doesn't exist.

**Solution**:
- List available databases in FairCom
- Verify database name spelling is correct
- Check user has permissions to access the database

### Debug Logging

To enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

This will show all SQL queries being executed.

## Performance Tips

### Connection Pooling

SQLAlchemy automatically handles connection pooling. For high-traffic scenarios, configure pool settings:

```python
# In Superset's superset_config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

### Query Optimization

- Use `LIMIT` clauses to reduce result set size
- Create indexes on frequently queried columns in FairCom
- Use SQL Lab to test query performance before creating charts
- Leverage Superset's caching for frequently accessed data

### Chart Caching

Enable caching in Superset to improve dashboard performance:

1. Configure cache backend in `superset_config.py`
2. Set cache timeout per chart or globally
3. Use Superset's cache warming for scheduled dashboard refreshes

## Additional Resources

- **sqlalchemy-faircom GitHub**: https://github.com/toddstoffel/sqlalchemy-faircom
- **PyPI Package**: https://pypi.org/project/sqlalchemy-faircom/
- **Apache Superset Documentation**: https://superset.apache.org/
- **FairCom Database Documentation**: https://docs.faircom.com/

## Version Compatibility

- **sqlalchemy-faircom**: 0.1.19+
- **SQLAlchemy**: 1.4+
- **Apache Superset**: 2.0+
- **Python**: 3.7+

## Support

For issues specific to the `sqlalchemy-faircom` connector:
- GitHub Issues: https://github.com/toddstoffel/sqlalchemy-faircom/issues
- FairCom Support: support@faircom.com

For Apache Superset issues:
- Superset GitHub: https://github.com/apache/superset
- Superset Community: https://superset.apache.org/community

---

**Last Updated**: January 2026  
**Connector Version**: 0.1.19
