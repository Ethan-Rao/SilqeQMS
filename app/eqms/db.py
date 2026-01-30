from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

from flask import Flask, g
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def init_db(app: Flask) -> None:
    db_url = app.config["DATABASE_URL"]
    is_postgres = db_url.startswith("postgres")
    engine_kwargs: dict[str, object] = {
        "future": True,
        "pool_pre_ping": True,
    }
    if is_postgres:
        engine_kwargs.update(
            {
                "pool_recycle": 1800,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
            }
        )
    engine = create_engine(db_url, **engine_kwargs)
    if app.config.get("ENV") != "production":
        @event.listens_for(engine, "checkout")
        def _receive_checkout(dbapi_connection, connection_record, connection_proxy):  # type: ignore[no-redef]
            app.logger.debug("DB connection checkout from pool")
    app.extensions["sqlalchemy_engine"] = engine
    app.extensions["sqlalchemy_sessionmaker"] = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def db_session(app: Flask | None = None) -> Session:
    """
    Request-scoped session. Use inside request handlers.
    """
    if hasattr(g, "db_session") and g.db_session is not None:
        return g.db_session
    if app is None:
        # Flask stores app on `g` only indirectly; we keep the engine in app.extensions.
        from flask import current_app

        app = current_app
    sm = app.extensions["sqlalchemy_sessionmaker"]
    g.db_session = sm()  # type: ignore[assignment]
    return g.db_session


def teardown_db_session(_exc: BaseException | None) -> None:
    s: Session | None = getattr(g, "db_session", None)
    if s is not None:
        try:
            s.close()
        except Exception:
            pass
        g.db_session = None


@contextmanager
def session_scope(app: Flask) -> Generator[Session, None, None]:
    """
    Non-request helper for scripts: yields a session and commits/rolls back.
    """
    sm = app.extensions["sqlalchemy_sessionmaker"]
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

