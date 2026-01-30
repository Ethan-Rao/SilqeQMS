from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_script_engine(db_url: str):
    return create_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


@contextmanager
def script_session(db_url: str):
    engine = create_script_engine(db_url)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
        engine.dispose()
