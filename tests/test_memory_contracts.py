import pytest
from pydantic import ValidationError
from atlas.memory.contracts import MemoryRecord


def test_memory_record_accepts_valid_record():
    record = MemoryRecord(kind="semantic", content="Prefere respostas objetivas", source="user")
    assert record.kind == "semantic"
    assert record.confidence == 1.0


def test_memory_record_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        MemoryRecord(kind="semantic", content="x", source="user", confidence=1.5)
