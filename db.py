# db.py — conexão, schema e execução

import socket
import pandas as pd
import urllib.parse
from textwrap import dedent
from functools import lru_cache

# pyodbc opcional
try:
    import pyodbc
except Exception:
    pyodbc = None

try:
    from sqlalchemy import create_engine
except Exception:
    create_engine = None

from config import SQL_COMMAND_TIMEOUT_SECONDS

# Cache de engine — com ou sem Streamlit
try:
    import streamlit as st
    @st.cache_resource(show_spinner=False)
    def get_engine(conn_str: str):
        params = urllib.parse.quote_plus(conn_str)
        from sqlalchemy import create_engine as _ce
        return _ce(
            f"mssql+pyodbc:///?odbc_connect={params}",
            pool_pre_ping=True
        )
except Exception:
    _engine_cache = {}
    def get_engine(conn_str: str):
        if conn_str not in _engine_cache:
            from sqlalchemy import create_engine as _ce
            params = urllib.parse.quote_plus(conn_str)
            _engine_cache[conn_str] = _ce(
                f"mssql+pyodbc:///?odbc_connect={params}",
                pool_pre_ping=True
            )
        return _engine_cache[conn_str]

def test_tcp(host: str, port: int, timeout=2.0) -> (bool, str):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, "ok"
    except Exception as e:
        return False, str(e)

def odbc_conn_str_windows(server: str, db: str, driver: str) -> str:
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "MultipleActiveResultSets=yes;"
        "Connection Timeout=15;"
    )

def try_connect(conn_str: str):
    if pyodbc is None:
        raise RuntimeError("pyodbc não está instalado. Instale com: pip install pyodbc")

    # timeout= no connect é o login/connect timeout, não o de comando.
    # Mesmo assim setamos e, em seguida, tentamos ajustar o timeout da conexão.
    conn = pyodbc.connect(conn_str, timeout=SQL_COMMAND_TIMEOUT_SECONDS)

    # Algumas builds do pyodbc expõem 'timeout' na conexão (afeta operações subsequentes).
    # Em outras, não existe. Fazemos best-effort.
    try:
        conn.timeout = SQL_COMMAND_TIMEOUT_SECONDS
    except Exception:
        pass

    # Aplica guarda de bloqueio/timeout por sessão (ms). Isso evita ficar travado esperando locks.
    cur = conn.cursor()
    try:
        cur.execute(f"SET LOCK_TIMEOUT {SQL_COMMAND_TIMEOUT_SECONDS * 1000};")
        # Se desejar leituras "no lock" globalmente (avaliar consistência antes de habilitar):
        # cur.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        conn.commit()
    finally:
        cur.close()

    return conn


def fetch_tables_and_columns_cached(conn_str: str) -> pd.DataFrame:
    """INFORMATION_SCHEMA estável e cacheável externamente (se desejar)."""
    conn = try_connect(conn_str)
    q = dedent("""
        SELECT
            c.TABLE_SCHEMA,
            c.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS c
        INNER JOIN INFORMATION_SCHEMA.TABLES t
            ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
           AND c.TABLE_NAME   = t.TABLE_NAME
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION;
    """)
    df = pd.read_sql(q, conn)
    conn.close()
    return df

def run_query(conn_str: str, sql_text: str) -> pd.DataFrame:
    """
    Executa a SQL e retorna um DataFrame.
    Preferência: SQLAlchemy (evita warning do pandas). Fallback: cursor pyodbc.
    Respeita timeouts definidos em config.
    """
    sql_text = (sql_text or "").strip()
    if not sql_text:
        return pd.DataFrame()

    # Caminho 1: SQLAlchemy (se disponível)
    if create_engine is not None:
        try:
            engine = get_engine(conn_str)
            with engine.connect() as econn:
                # aplica timeout de comando via hints do driver
                return pd.read_sql_query(sql_text, econn)
        except Exception:
            pass

    # Caminho 2: Fallback pyodbc com fetch manual
    conn = try_connect(conn_str)
    cur = None
    try:
        cur = conn.cursor()
        #cur.timeout = SQL_COMMAND_TIMEOUT_SECONDS
        cur.execute(sql_text)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall() if cols else []
        df = pd.DataFrame.from_records(rows, columns=cols)
        return df
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# === Persistência opcional do histórico ===
def ensure_chat_table(conn_str: str):
    conn = try_connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables t WHERE t.name = 'chat_turns'
    )
    CREATE TABLE dbo.chat_turns (
        id INT IDENTITY(1,1) PRIMARY KEY,
        ts DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        session_id NVARCHAR(64) NOT NULL,
        role NVARCHAR(16) NOT NULL,
        type NVARCHAR(16) NOT NULL,
        content NVARCHAR(MAX) NULL,
        summary NVARCHAR(MAX) NULL
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def insert_chat_turn(conn_str: str, session_id: str, role: str, type_: str, content: str = None, summary: str = None):
    conn = try_connect(conn_str)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO dbo.chat_turns (session_id, role, type, content, summary) VALUES (?,?,?,?,?)",
        (session_id, role, type_, content, summary)
    )
    conn.commit()
    cur.close()
    conn.close()
