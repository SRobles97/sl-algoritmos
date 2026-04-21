import atexit
import threading
from typing import Any

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sshtunnel import SSHTunnelForwarder

from .config import settings

_lock = threading.Lock()
_tunnel: SSHTunnelForwarder | None = None
_engine: Engine | None = None


def get_engine() -> Engine:
    """Abre el túnel SSH (una sola vez) y devuelve un motor de SQLAlchemy cacheado."""
    global _tunnel, _engine
    if _engine is not None:
        return _engine

    with _lock:
        if _engine is not None:
            return _engine

        try:
            tunnel = SSHTunnelForwarder(
                (settings.VPS_IP, settings.VPS_SSH_PORT),
                ssh_username=settings.SSH_USER,
                ssh_password=settings.SSH_PASSWORD,
                remote_bind_address=("localhost", settings.POSTGRES_REMOTE_PORT),
                local_bind_address=("localhost", 0),
                allow_agent=False,
                host_pkey_directories=[],
            )
            tunnel.start()
        except Exception as e:
            raise RuntimeError(
                "No se pudo abrir el túnel SSH — revisá las credenciales SSH y que el VPS sea alcanzable"
            ) from e

        local_port = tunnel.local_bind_port
        url = (
            f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@127.0.0.1:{local_port}/{settings.POSTGRES_DB}"
        )
        engine = create_engine(url, pool_pre_ping=True)

        _tunnel = tunnel
        _engine = engine
        return _engine


def query(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Ejecuta SQL y devuelve un DataFrame de pandas."""
    engine = get_engine()
    return pd.read_sql_query(text(sql), engine, params=params)


def close() -> None:
    """Cierra el motor y detiene el túnel SSH. Es seguro llamarla varias veces."""
    global _tunnel, _engine
    with _lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
        if _tunnel is not None:
            try:
                _tunnel.stop()
            except Exception:
                pass
            _tunnel = None


atexit.register(close)
