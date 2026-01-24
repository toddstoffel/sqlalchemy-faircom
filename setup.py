"""
Setup for FairCom JSON API SQLAlchemy dialect
"""
from setuptools import setup, find_packages

setup(
    name="sqlalchemy-faircom",
    version='0.1.19',
    description="SQLAlchemy dialect for FairCom Database via JSON API",
    long_description="Pure Python SQLAlchemy dialect for FairCom Database using the JSON/REST API",
    author="Custom Implementation",
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[
        'sqlalchemy>=1.4',
        'requests>=2.25.0',
        'python-dotenv>=0.19.0',
        'sqlparse>=0.4.0'
    ],
    entry_points={
        "sqlalchemy.dialects": [
            "faircom = faircom_jsonapi.sqlalchemy_dialect:FairComJSONDialect",
        ]
    },
    python_requires='>=3.7',
)
