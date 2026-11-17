import pytest
from pydantic import ValidationError

from bench.schema_fields import DocFields
from bench.score import compare_field


def test_field_normalization_and_missing_states():
    assert compare_field("total", 1200.5, "1 200,50 грн") == "ok"
    assert compare_field("issued_on", "2026-10-20", "20 жовтня 2026 р.") == "ok"
    assert compare_field("issued_on", "2026-10-20", "31 лютого 2026") == "wrong"
    assert compare_field("items", ["Ролик", "Фільтр"], ["фільтр", "ролик"]) == "ok"
    assert compare_field("items", ["Ролик"], ["Ролик", "Ролик"]) == "wrong"
    assert compare_field("note", None, None) == "empty_ok"
    assert compare_field("note", None, "не знайдено") == "spurious"
    assert compare_field("note", "Примітка", None) == "missing"


def test_schema_rejects_extra_keys():
    record = dict(doc_no="MS-1234", total=120, issued_on="2026-10-20", items=["Ролик"], note=None, label="ремонт")
    DocFields.model_validate(record)
    with pytest.raises(ValidationError):
        DocFields.model_validate({**record, "unexpected": True})
