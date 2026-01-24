"""
Superset Configuration for FairCom Database

Add this to your superset_config.py file to enable FairCom database support.
For Docker: /app/pythonpath/superset_config.py
For local: Your SUPERSET_CONFIG_PATH location
"""

# Register FairCom dialect with sqlglot
# This is REQUIRED for Superset's SQL parser to understand T-SQL syntax (TOP, SKIP, etc.)
try:
    import sys
    from sqlglot.dialects.dialect import Dialects
    from superset.sql import parse
    
    # Map 'faircom' dialect to T-SQL parser (FairCom uses T-SQL syntax)
    parse.SQLGLOT_DIALECTS["faircom"] = Dialects.TSQL
    
    # Register the FairCom engine spec
    from faircom_engine_spec import FairComEngineSpec
    DB_ENGINE_SPECS = {
        FairComEngineSpec.engine: FairComEngineSpec
    }
    
    print(f"✓ FairCom engine spec registered successfully", file=sys.stderr)
    
except ImportError as e:
    print(f"⚠ WARNING: Could not load FairCom engine spec: {e}", file=sys.stderr)
    print(f"  Make sure faircom_engine_spec.py is in your PYTHONPATH", file=sys.stderr)

# Allow FairCom database connections
PREVENT_UNSAFE_DB_CONNECTIONS = False

# Optional: Enable SQL Lab features
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
}

# Optional: Increase query timeout for large datasets
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
