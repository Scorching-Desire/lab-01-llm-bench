from google.genai import types
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ConfigDict

from bench import clients
from bench.schema import TicketLabel


class FakeOpenAI:
    """Підроблений клієнт OpenAI SDK: повертає задані відповіді й запам'ятовує запити."""

    def __init__(self, *messages):
        self.replies, self.requests = list(messages), []
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        message = self.replies.pop(0)
        return ChatCompletion.model_validate({
            "id": "x", "object": "chat.completion", "created": 0, "model": "fake-model",
            "choices": [{"index": 0, "message": message,
                         "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70,
                      "completion_tokens_details": {"reasoning_tokens": 12}}})


def use_fake(monkeypatch, fake):
    monkeypatch.setattr(clients, "_client", lambda spec: fake)
    return fake




def test_schema_invalid_extra_field(monkeypatch):
    use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": '{"label": "оплата", "why": "бо"}'}))
    turn = clients.chat("local", [{"role": "user", "content": "x"}], schema=TicketLabel)
    assert turn.schema_valid is False and turn.parsed is None



def test_unknown_extra_content_is_passed_back_unchanged(monkeypatch):
    extra = {"google": {"thought_signature": "c2lnbmF0dXJl"}}
    call = {"id": "c1", "type": "function", "extra_content": extra,
            "function": {"name": "lookup_order", "arguments": '{"order_id": "A-1001"}'}}
    fake = use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": None, "tool_calls": [call]},
                                            {"role": "assistant", "content": '{"label": "оплата"}'}))
    history = [{"role": "user", "content": "Що з A-1001?"}]
    turn = clients.chat("local", history)
    history += [turn.raw_assistant_message,
                {"role": "tool", "tool_call_id": "c1", "name": "lookup_order", "content": "очікує оплати"}]
    clients.chat("local", history)
    sent = fake.requests[1]["messages"][1]
    assert sent["tool_calls"][0]["extra_content"] == extra

class FakeGemini:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.models = self

    def generate_content(self, model, contents, config):
        self.requests.append({"contents": list(contents), "config": config})
        return self.responses.pop(0)


def gemini_response(*parts):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)), finish_reason="STOP")],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=40, candidates_token_count=10, thoughts_token_count=30))


def test_gemini_manual_tool_loop_keeps_content(monkeypatch):
    call_part = types.Part(function_call=types.FunctionCall(id="f1", name="lookup_order", args={"order_id": "A-1001"}),
                           thought_signature=b"sig")
    fake = use_fake(monkeypatch, FakeGemini(gemini_response(call_part), gemini_response(types.Part(text="оплата"))))
    history = [{"role": "system", "content": "Класифікуй."}, {"role": "user", "content": "Що з A-1001?"}]
    turn = clients.chat("gemini-native", history, tools=[{"type": "function", "function": {
        "name": "lookup_order", "description": "d", "parameters": {"type": "object", "properties": {}}}}])
    assert turn.tool_calls[0].arguments == {"order_id": "A-1001"}
    assert (turn.usage.output, turn.usage.reasoning) == (40, 30)  # output включає міркування
    assert fake.requests[0]["config"].automatic_function_calling.disable is True
    history += [turn.raw_assistant_message,
                {"role": "tool", "tool_call_id": "f1", "name": "lookup_order", "content": "очікує оплати"}]
    final = clients.chat("gemini-native", history)
    contents = fake.requests[1]["contents"]
    assert contents[1] is turn.raw_assistant_message["gemini_content"]       # без змін
    assert contents[1].parts[0].thought_signature == b"sig"
    assert contents[2].parts[0].function_response.id == "f1"
    assert final.text == "оплата" and final.finish_reason == "stop"


def test_text_usage_and_overrides(monkeypatch):
    fake = use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": "ремонт"}))
    turn = clients.chat("local", [{"role": "user", "content": "x"}], temperature=1)
    assert turn.text == "ремонт" and turn.schema_valid is None and turn.tool_calls == []
    assert (turn.usage.input, turn.usage.output, turn.usage.reasoning) == (50, 20, 12)
    assert fake.requests[0]["temperature"] == 1 and fake.requests[0]["seed"] == 7


def test_strict_schema_valid(monkeypatch):
    fake = use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": '{"label":"ремонт"}'}))
    turn = clients.chat("local", [{"role": "user", "content": "x"}], schema=TicketLabel)
    assert turn.schema_valid is True and turn.parsed.label == "ремонт"
    spec = fake.requests[0]["response_format"]["json_schema"]
    assert spec["strict"] is True and spec["schema"]["additionalProperties"] is False


def test_invalid_tool_json(monkeypatch):
    use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c", "type": "function", "function": {"name": "x", "arguments": "{oops"}}]}))
    turn = clients.chat("local", [{"role": "user", "content": "x"}])
    assert turn.tool_calls[0].arguments is None and turn.tool_calls[0].parse_error


def test_openrouter_requires_parameters(monkeypatch):
    fake = use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": "інше"}))
    clients.chat("openrouter", [{"role": "user", "content": "x"}])
    assert fake.requests[0]["extra_body"]["provider"] == {"require_parameters": True}


def test_nested_strict_schema():
    class Inner(BaseModel):
        model_config = ConfigDict(extra="forbid")
        note: str | None

    class Outer(BaseModel):
        model_config = ConfigDict(extra="forbid")
        item: Inner

    schema = clients.to_strict_schema(Outer)
    assert schema["additionalProperties"] is False and schema["required"] == ["item"]
    assert schema["$defs"]["Inner"]["additionalProperties"] is False
    assert schema["$defs"]["Inner"]["required"] == ["note"]


def test_none_parameter_omitted(monkeypatch):
    fake = use_fake(monkeypatch, FakeOpenAI({"role": "assistant", "content": "інше"}))
    clients.chat("local", [{"role": "user", "content": "x"}], seed=None)
    assert "seed" not in fake.requests[0]


def test_native_schema_valid(monkeypatch):
    fake = use_fake(monkeypatch, FakeGemini(gemini_response(types.Part(text='{"label":"доступ"}'))))
    turn = clients.chat("gemini-native", [{"role": "user", "content": "x"}], schema=TicketLabel)
    assert turn.schema_valid and turn.parsed.label == "доступ"
    config = fake.requests[0]["config"]
    assert config.response_json_schema["additionalProperties"] is False
    assert config.response_mime_type == "application/json"
