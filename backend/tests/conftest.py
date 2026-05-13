import pytest

from services import query_cache
from services.conversation_context import clear_memory


@pytest.fixture
def sample_query() -> str:
    return "Show me all orders from customer X in the last month"


@pytest.fixture(autouse=True)
def clear_query_cache():
    query_cache.clear_all()
    clear_memory()
    yield
    query_cache.clear_all()
    clear_memory()
