"""Orders, preferences, feedback and LangGraph checkpoints in PostgreSQL."""

from pathlib import Path
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from loguru import logger
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from ai_workflow.settings import settings

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
MIGRATION_LOCK_ID = 7302001  # stops two app instances from migrating at the same time
STARTUP_CONNECT_TIMEOUT_SECONDS = 10

_pool: Optional[AsyncConnectionPool] = None
_checkpointer = None


async def _run_migrations(connection) -> None:
    """Run the numbered .sql files in migrations/ that have not been applied yet."""
    await connection.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_ID,))
    try:
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cursor = await connection.execute("SELECT version FROM schema_migrations")
        applied = {row["version"] for row in await cursor.fetchall()}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            for statement in path.read_text().split(";"):
                if statement.strip():
                    await connection.execute(statement)
            await connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            logger.info("Applied migration {}", path.name)
    finally:
        await connection.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))


async def open_postgres() -> None:
    """Open the pool, apply the migrations and build the checkpointer."""
    global _pool, _checkpointer
    url = settings.POSTGRES_URL.get_secret_value()
    if not url:
        logger.warning("POSTGRES_URL is empty: using in-memory checkpoints, orders and feedback are not saved")
        _checkpointer = InMemorySaver()
        return
    _pool = AsyncConnectionPool(
        conninfo=url,
        max_size=settings.POSTGRES_POOL_MAX_SIZE,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    try:
        # Wait until the pool's minimum connections are open, so the first customer does not pay for them
        # (and so a database that is down fails here, where the startup retry can handle it)
        await _pool.open(wait=True, timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)
        async with _pool.connection() as connection:
            await _run_migrations(connection)
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
    except Exception:
        await close_postgres()
        raise
    logger.info("Postgres ready")


async def check_postgres() -> str:
    """'ok', 'down', or 'disabled' when no database is configured."""
    if _pool is None:
        return "disabled"
    try:
        async with _pool.connection() as connection:
            await connection.execute("SELECT 1")
        return "ok"
    except Exception as error:
        logger.error("Postgres health check failed: {}", error)
        return "down"


async def close_postgres() -> None:
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
    _pool = None
    _checkpointer = None


def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = InMemorySaver()
    return _checkpointer


async def save_order(order: Dict[str, Any]) -> None:
    if _pool is None:
        return
    async with _pool.connection() as connection:
        await connection.execute(
            "INSERT INTO orders (id, session_id, customer_id, items, total, payment_method,"
            " gateway, transaction_id, store, status)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                order["id"], order["session_id"], order["customer_id"], Jsonb(order["items"]),
                order["total"], order["payment_method"], order.get("gateway"),
                order.get("transaction_id"), order.get("store"), order.get("status", "confirmed"),
            ),
        )


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    if _pool is None:
        return None
    async with _pool.connection() as connection:
        cursor = await connection.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        return await cursor.fetchone()


async def save_preferences(customer_id: str, data: Dict[str, Any]) -> None:
    if _pool is None:
        return
    async with _pool.connection() as connection:
        await connection.execute(
            "INSERT INTO preferences (customer_id, data) VALUES (%s, %s)"
            " ON CONFLICT (customer_id) DO UPDATE SET data = EXCLUDED.data, updated_at = now()",
            (customer_id, Jsonb(data)),
        )


async def get_preferences(customer_id: str) -> Dict[str, Any]:
    if _pool is None:
        return {}
    async with _pool.connection() as connection:
        cursor = await connection.execute("SELECT data FROM preferences WHERE customer_id = %s", (customer_id,))
        row = await cursor.fetchone()
        return row["data"] if row else {}


async def save_feedback(session_id: str, order_id: Optional[str], rating: int) -> None:
    if _pool is None:
        return
    async with _pool.connection() as connection:
        await connection.execute(
            "INSERT INTO feedback (session_id, order_id, rating) VALUES (%s, %s, %s)",
            (session_id, order_id, rating),
        )
