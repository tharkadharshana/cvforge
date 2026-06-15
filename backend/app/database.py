from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from .config import settings

if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, pool_pre_ping=True
    )
else:
    # Postgres via Supabase's Supavisor transaction-mode pooler (port 6543): the
    # pooler already manages connection pooling, so an additional in-app pool
    # would exhaust connections under serverless concurrency. NullPool opens
    # one connection per request and closes it when the session is done.
    # prepare_threshold=None disables psycopg's server-side prepared statements -
    # required in transaction-pooling mode, where a "connection" can be backed by
    # a different Postgres server process per transaction, so a prepared
    # statement from one transaction may not exist (or may collide by name) in
    # the next.
    engine = create_engine(
        settings.database_url, poolclass=NullPool, pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
