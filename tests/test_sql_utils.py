import os
import sys
import types

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

mock_openai = types.ModuleType("openai")


class _DummyAzureOpenAI:  # pragma: no cover - stub for config import
    pass


mock_openai.AzureOpenAI = _DummyAzureOpenAI
sys.modules.setdefault("openai", mock_openai)

from config import DEFAULT_YEAR_IF_MISSING
from sql_utils import sql_sanity_rewrite


def test_sql_sanity_rewrite_adds_year_for_data_entrega_month():
    original_sql = "SELECT * FROM pedidos WHERE MONTH(Data_Entrega) = 5"

    rewritten_sql = sql_sanity_rewrite(original_sql)

    expected_year_clause = f"YEAR(Data_Entrega) = {DEFAULT_YEAR_IF_MISSING}"
    assert expected_year_clause in rewritten_sql
    assert "MONTH(Data_Entrega) = 5" in rewritten_sql
