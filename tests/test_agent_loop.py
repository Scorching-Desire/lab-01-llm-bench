import json

from bench.agent_loop import run_agent
from bench.clients import ToolCall, Turn, Usage

USER = [{"role": "user", "content": "Що з замовленням B-201?"}]


def turn(text=None, calls=(), usage=(10, 5)):
    """Підроблений Turn; calls — список (id, name, arguments_raw)."""
    tool_calls = [ToolCall(i, n, raw, None, None) for i, n, raw in calls]
    raw = {"role": "assistant", "content": text,
           "tool_calls": [{"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in calls]}
    return Turn(text, None, None, tool_calls, Usage(*usage), "tool_calls" if calls else "stop", 1, "fake", raw)


class FakeChat:
    """Повертає відповіді по черзі (останню — повторно) і запам'ятовує історію кожного запиту."""

    def __init__(self, *turns):
        self.turns, self.histories = list(turns), []

    def __call__(self, alias, messages, tools=None, **params):
        self.histories.append(list(messages))
        return self.turns.pop(0) if len(self.turns) > 1 else self.turns[0]


def test_calls_tool_then_answers(tmp_path):
    chat = FakeChat(turn(calls=[("c1", "booking_status", '{"booking_id": "B-201"}')]), turn('{"label": "оплата"}'))
    trace = tmp_path / "trace.jsonl"
    res = run_agent("local", USER, ["booking_status"], chat=chat, run_id="r", case_id="k01", trace_path=str(trace))
    assert (res.stop_reason, res.steps, res.failures, res.tools_called) == ("final", 2, [], ["booking_status"])
    assert res.final_text == '{"label": "оплата"}' and res.usage_total.input == 20
    tool_msg = chat.histories[1][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1" and "не оплачено" in tool_msg["content"]
    lines = [json.loads(x) for x in trace.read_text(encoding="utf-8").splitlines()]
    assert [x["tool"] for x in lines] == ["booking_status", None] and lines[0]["case_id"] == "k01"


def test_stops_on_max_steps():
    chat = FakeChat(*[turn(calls=[(f"c{i}", "booking_status", json.dumps({"booking_id": f"B-20{i}"}))]) for i in range(5)])
    res = run_agent("local", USER, ["booking_status"], chat=chat, max_steps=3)
    assert res.stop_reason == "max_steps" and res.steps == 3 and res.failures == ["max_steps"]
    assert res.final_text is None


def test_token_budget():
    chat = FakeChat(turn(calls=[("c1", "booking_status", '{"booking_id":"B-201"}')], usage=(15000, 6000)))
    res = run_agent("local", USER, ["booking_status"], chat=chat, token_budget=20000)
    assert (res.stop_reason, res.steps, res.failures) == ("budget", 1, ["budget"])
    assert len(chat.histories) == 1


def test_unknown_tool_survives():
    chat = FakeChat(turn(calls=[("c1", "missing", "{}")]), turn("інше"))
    res = run_agent("local", USER, ["booking_status"], chat=chat)
    assert res.stop_reason == "final" and res.failures == ["unknown_tool"]
    assert chat.histories[1][-1]["content"].startswith("unknown tool:")


def test_bad_arguments_survive():
    chat = FakeChat(turn(calls=[("c1", "booking_status", '{"booking_id":5}')]), turn("інше"))
    res = run_agent("local", USER, ["booking_status"], chat=chat)
    assert res.stop_reason == "final" and res.failures == ["bad_args"]
    assert chat.histories[1][-1]["content"].startswith("bad arguments:")


def test_repeated_call():
    chat = FakeChat(turn(calls=[("c1", "booking_status", '{"booking_id":"B-201"}')]))
    res = run_agent("local", USER, ["booking_status"], chat=chat)
    assert res.stop_reason == "repeated_call" and res.steps == 3


def test_text_call_is_failure():
    res = run_agent("local", USER, [], chat=FakeChat(turn('{"name":"x","arguments":{}}')))
    assert res.stop_reason == "final" and res.failures == ["tool_call_in_text"]


def test_parallel_calls_preserve_ids():
    chat = FakeChat(turn(calls=[("c1", "station_status", '{"station_id":"M-101"}'),
                                ("c2", "booking_status", '{"booking_id":"B-201"}')]), turn("ремонт"))
    res = run_agent("local", USER, ["station_status", "booking_status"], chat=chat)
    assert res.tools_called == ["station_status", "booking_status"]
    assert [m["tool_call_id"] for m in chat.histories[1][-2:]] == ["c1", "c2"]


def test_tool_error_survives():
    chat = FakeChat(turn(calls=[("c1", "booking_status", '{"booking_id":"bad"}')]), turn("інше"))
    res = run_agent("local", USER, ["booking_status"], chat=chat)
    assert res.stop_reason == "final" and res.failures == ["tool_error"]


def test_provider_tool_failure_is_not_success():
    t = turn()
    t.finish_reason = "missing_thought_signature"
    res = run_agent("local", USER, [], chat=FakeChat(t))
    assert res.stop_reason == "missing_thought_signature" and res.failures == [res.stop_reason]
