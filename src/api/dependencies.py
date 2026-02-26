from typing import AsyncIterator


async def get_db_session() -> AsyncIterator[None]:
    """Stub for Database Session (RFC-0005). To be replaced with actual AsyncPG session."""
    yield None
