from app.schemas.memory import MemorySuggestRequest
from app.services.memory_service import suggest_memories


def test_suggest_memories_preference_type() -> None:
    suggestions = suggest_memories(MemorySuggestRequest(text="I prefer concise responses"))
    assert suggestions
    assert suggestions[0].memory_type.value == "preference"
    assert suggestions[0].confidence >= 0.8


def test_suggest_memories_task_type() -> None:
    suggestions = suggest_memories(MemorySuggestRequest(text="I need to finish this task today"))
    assert suggestions[0].memory_type.value == "task"
