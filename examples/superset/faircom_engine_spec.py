"""
FairCom Database Engine Spec for Apache Superset

This file should be placed in your Superset pythonpath directory.
For Docker deployments: /app/pythonpath/faircom_engine_spec.py
For local installations: PYTHONPATH directory configured in superset_config.py
"""
from superset.db_engine_specs.base import BaseEngineSpec
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class FairComEngineSpec(BaseEngineSpec):
    """Engine spec for FairCom database via JSON API"""
    
    engine = "faircom"
    engine_name = "FairCom Database"
    default_driver = "faircom"
    
    # Connection string template shown in Superset UI
    sqlalchemy_uri_placeholder = (
        "faircom://user:password@host:port/database?protocol=http"
    )
    
    # Security - mark password as sensitive
    encrypted_extra_sensitive_fields = frozenset(["password"])
    
    # Note: The sqlalchemy-faircom dialect handles LIMIT/OFFSET conversion automatically.
    # No need to override apply_limit_to_sql here.
