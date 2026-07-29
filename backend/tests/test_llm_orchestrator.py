"""Provider chain fallthrough (gemini -> openai -> deepseek by default)."""
import pytest
from app.llm.orchestrator import _ChainProvider


class _Fake:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.calls = 0

    def complete(self, system, user, json_mode=False, pro=False):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return f"ok:{self.name}"

    def complete_json(self, system, user, pro=False):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return {"from": self.name}


def test_first_provider_succeeds_no_fallthrough():
    a, b = _Fake("a"), _Fake("b")
    chain = _ChainProvider([a, b])
    assert chain.complete("s", "u") == "ok:a"
    assert a.calls == 1 and b.calls == 0


def test_falls_through_to_next_on_failure():
    a, b, c = _Fake("a", fail=True), _Fake("b", fail=True), _Fake("c")
    chain = _ChainProvider([a, b, c])
    assert chain.complete("s", "u") == "ok:c"
    assert a.calls == 1 and b.calls == 1 and c.calls == 1


def test_raises_last_error_when_all_fail():
    a, b = _Fake("a", fail=True), _Fake("b", fail=True)
    chain = _ChainProvider([a, b])
    with pytest.raises(RuntimeError, match="b down"):
        chain.complete("s", "u")


def test_complete_json_falls_through_too():
    a, b = _Fake("a", fail=True), _Fake("b")
    chain = _ChainProvider([a, b])
    assert chain.complete_json("s", "u") == {"from": "b"}
