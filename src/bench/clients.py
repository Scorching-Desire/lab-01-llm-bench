"""Клієнт LLM v2 (крок 04): одна функція chat() над двома формами API.

Історія — повідомлення в стилі OpenAI. Відповідь асистента кладіть в історію
як turn.raw_assistant_message — без змін (там непрозорі поля провайдера).
"""
import json
import os
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from bench import models


@dataclass
class ToolCall:
    id: str
    name: str
    arguments_raw: str
    arguments: dict | None
    parse_error: str | None


@dataclass
class Usage:
    input: int | None = None
    output: int | None = None      # УСІ вихідні токени, включно з міркуванням
    reasoning: int | None = None
    cached: int | None = None


@dataclass
class Turn:
    text: str | None
    parsed: object | None            # екземпляр schema або None
    schema_valid: bool | None        # None, якщо schema не задано
    tool_calls: list[ToolCall]
    usage: Usage
    finish_reason: str | None
    latency_ms: int
    model_reported: str | None
    raw_assistant_message: object    # додається в історію БЕЗ змін


# Стандартні параметри Chat Completions; решта йде через extra_body
OPENAI_PARAMS = {"temperature", "top_p", "seed", "max_tokens", "reasoning_effort", "stop"}
_clients: dict[str, object] = {}


def _client(spec: models.ModelSpec):
    """Фабрика: клієнт SDK створюється під час першого виклику і кешується."""
    if spec.alias not in _clients:
        if spec.api == "gemini_native":
            key = os.environ.get(spec.key_env or "")
            if not key:
                raise RuntimeError(f"задайте {spec.key_env} у .env")
            _clients[spec.alias] = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=600_000,
                retry_options=types.HttpRetryOptions(attempts=1)))
        else:
            key = os.environ.get(spec.key_env or "") or spec.api_key_default
            if not key:
                raise RuntimeError(f"задайте {spec.key_env} у .env")
            # повтори на 429/503 робить run.py, тому вбудовані повтори SDK вимкнено
            _clients[spec.alias] = OpenAI(base_url=spec.base_url, api_key=key, max_retries=0, timeout=600)
    return _clients[spec.alias]


def to_strict_schema(model: type[BaseModel]) -> dict:
    """JSON Schema для строгого режиму: additionalProperties=false і повний required."""
    schema = model.model_json_schema()

    def fix(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                fix(value)
        elif isinstance(node, list):
            for value in node:
                fix(value)

    fix(schema)
    return schema


def _tool_call(call_id: str, name: str, raw: str) -> ToolCall:
    try:
        args = json.loads(raw or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments — не JSON-об'єкт")
        return ToolCall(call_id, name, raw, args, None)
    except ValueError as e:  # JSONDecodeError теж ValueError
        return ToolCall(call_id, name, raw, None, str(e))


def _openai_chat(spec, messages, tools, schema, params) -> Turn:
    kwargs = {k: v for k, v in params.items() if k in OPENAI_PARAMS}
    extra = {k: v for k, v in params.items() if k not in OPENAI_PARAMS}
    if spec.alias == "openrouter":  # лише провайдери, що підтримують усі параметри запиту
        extra["provider"] = {"require_parameters": True}
    if tools:
        kwargs["tools"] = tools
    if schema is not None:  # режим B: нативна схема
        kwargs["response_format"] = {"type": "json_schema", "json_schema": {
            "name": schema.__name__, "schema": to_strict_schema(schema), "strict": True}}
    start = time.perf_counter()
    r = _client(spec).chat.completions.create(
        model=spec.model, messages=messages, extra_body=extra or None, **kwargs)
    latency_ms = round((time.perf_counter() - start) * 1000)
    choice, u = r.choices[0], r.usage
    msg = choice.message
    usage = Usage(
        input=getattr(u, "prompt_tokens", None),
        output=getattr(u, "completion_tokens", None),
        reasoning=getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", None),
        cached=getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", None),
    )
    calls = [_tool_call(tc.id, tc.function.name, tc.function.arguments) for tc in msg.tool_calls or []]
    return Turn(msg.content, None, None, calls, usage, choice.finish_reason, latency_ms, r.model,
                raw_assistant_message=msg.model_dump(exclude_none=True))  # зберігає extra_content


def _to_gemini(messages: list[dict]) -> tuple[str | None, list[types.Content]]:
    """Історія в стилі OpenAI → (system_instruction, contents) для generate_content."""
    system, contents = None, []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        elif "gemini_content" in m:  # відповідь моделі — як є (thought_signature)
            contents.append(m["gemini_content"])
        elif m["role"] == "tool":
            part = types.Part(function_response=types.FunctionResponse(
                id=m["tool_call_id"], name=m["name"], response={"result": m["content"]}))
            last = contents[-1] if contents else None
            if last and last.role == "user" and last.parts[0].function_response:
                last.parts.append(part)  # паралельні виклики — в одному повідомленні
            else:
                contents.append(types.Content(role="user", parts=[part]))
        else:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    return system, contents


def _gemini_chat(spec, messages, tools, schema, params) -> Turn:
    system, contents = _to_gemini(messages)
    config = dict(
        system_instruction=system,
        temperature=params.get("temperature"),
        seed=params.get("seed"),
        max_output_tokens=params.get("max_tokens"),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    if "thinking_level" in params:
        config["thinking_config"] = types.ThinkingConfig(thinking_level=params["thinking_level"])
    if schema is not None:  # dict, не клас: клас у response_json_schema — TypeError
        config.update(response_mime_type="application/json", response_json_schema=to_strict_schema(schema))
    if tools:
        config["tools"] = [types.Tool(function_declarations=[types.FunctionDeclaration(
            name=t["function"]["name"], description=t["function"]["description"],
            parameters_json_schema=t["function"]["parameters"]) for t in tools])]
    start = time.perf_counter()
    r = _client(spec).models.generate_content(
        model=spec.model, contents=contents, config=types.GenerateContentConfig(**config))
    latency_ms = round((time.perf_counter() - start) * 1000)
    candidate = r.candidates[0] if r.candidates else None
    content = candidate.content if candidate else None
    parts = (content.parts or []) if content else []
    text = "".join(p.text for p in parts if p.text and not p.thought) or None
    calls = [ToolCall(p.function_call.id or p.function_call.name, p.function_call.name,
                      json.dumps(p.function_call.args or {}, ensure_ascii=False),
                      dict(p.function_call.args or {}), None) for p in parts if p.function_call]
    um = r.usage_metadata
    thoughts = um.thoughts_token_count if um else None
    usage = Usage(
        input=um.prompt_token_count, output=(um.candidates_token_count or 0) + (thoughts or 0),
        reasoning=thoughts, cached=um.cached_content_token_count) if um else Usage()
    finish = candidate.finish_reason if candidate else None
    finish = str(getattr(finish, "value", finish)).lower() if finish else None
    return Turn(text, None, None, calls, usage, finish, latency_ms, r.model_version,
                raw_assistant_message={"role": "assistant", "gemini_content": content})


def chat(alias: str, messages: list[dict], tools: list[dict] | None = None,
         schema: type[BaseModel] | None = None, **params) -> Turn:
    """Один крок розмови. params перекривають spec.params; None — «не надсилати»."""
    spec = models.get(alias)
    merged = {k: v for k, v in {**spec.params, **params}.items() if v is not None}
    call = _gemini_chat if spec.api == "gemini_native" else _openai_chat
    turn = call(spec, messages, tools, schema, merged)
    if schema is not None:
        try:
            turn.parsed, turn.schema_valid = schema.model_validate_json(turn.text or ""), True
        except ValidationError:
            turn.parsed, turn.schema_valid = None, False
    if spec.num_ctx and (turn.usage.input or 0) >= 0.9 * spec.num_ctx:
        print(f"УВАГА: {turn.usage.input} вхідних токенів ≥ 90% контексту {spec.num_ctx} ({alias})")
    return turn


def generate(alias: str, system: str, user: str, schema: type[BaseModel] | None = None, **params) -> Turn:
    """Тонка обгортка: один запит system + user."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return chat(alias, messages, schema=schema, **params)
