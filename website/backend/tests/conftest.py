import os
from uuid import uuid4
import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

@pytest.fixture
def practice_database_url():
    dsn=os.getenv('TEST_DATABASE_URL')
    if not dsn:pytest.skip('Set TEST_DATABASE_URL to a real PostgreSQL test database')
    schema='practice_test_'+uuid4().hex
    with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:yield make_conninfo(dsn,options=f'-c search_path={schema}')
    finally:
        with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
