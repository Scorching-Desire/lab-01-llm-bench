"""Реєстр моделей v1 (крок 02): псевдонім → форма API, ID моделі, ключ і параметри."""
import os
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    api: str                 # "openai_chat" | "gemini_native" | "anthropic"
    model: str               # ID моделі у провайдера
    base_url: str | None     # для openai_chat
    key_env: str | None      # назва змінної з ключем
    api_key_default: str | None = None   # напр. "ollama" для локального сервера
    num_ctx: int | None = None
    params: dict = field(default_factory=dict)   # temperature, seed, reasoning_effort, thinking_level, max_tokens …
    caps: dict = field(default_factory=dict)     # {"tools": bool, "json_schema": bool, "reasoning_control": bool}
    price_in: float = 0.0    # USD за 1 млн вхідних токенів
    price_out: float = 0.0   # USD за 1 млн вихідних
    price_src: str = ""
    price_date: str = ""
    free_tier: bool = False
    trains_on_data: bool | None = None


MODELS: dict[str, ModelSpec] = {
    "local-fast": ModelSpec(
        alias="local-fast", api="openai_chat", model="qwen3:0.6b",
        base_url="http://localhost:11434/v1", key_env=None, api_key_default="ollama",
        num_ctx=16384, params={"temperature": 0, "seed": 7, "reasoning_effort": "none", "max_tokens": 512},
        caps={"tools": True, "json_schema": True, "reasoning_control": True},
        price_src="https://ollama.com/library/qwen3", price_date="2026-10-27", trains_on_data=False,
    ),
    "local-large": ModelSpec(
        alias="local-large", api="openai_chat", model="qwen3:4b",
        base_url="http://localhost:11434/v1", key_env=None, api_key_default="ollama",
        num_ctx=16384, params={"temperature": 0, "seed": 7, "reasoning_effort": "high", "max_tokens": 4096},
        caps={"tools": True, "json_schema": True, "reasoning_control": True},
        price_src="https://ollama.com/library/qwen3", price_date="2026-10-27", trains_on_data=False,
    ),
    # Локальний сервер: Ollama (для LM Studio змініть LOCAL_BASE_URL у .env)
    "local": ModelSpec(
        alias="local", api="openai_chat", model="qwen3:1.7b",
        base_url="http://localhost:11434/v1", key_env=None, api_key_default="ollama",
        num_ctx=16384, params={"temperature": 0, "seed": 7, "reasoning_effort": "none", "max_tokens": 512},
        caps={"tools": True, "json_schema": True, "reasoning_control": True},
        price_src="https://ollama.com/library/qwen3", price_date="2026-10-27", trains_on_data=False,
    ),
    # Gemini через OpenAI-сумісну адресу (beta)
    "gemini": ModelSpec(
        alias="gemini", api="openai_chat", model="gemini-3.8-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/", key_env="GEMINI_API_KEY",
        params={"reasoning_effort": "low", "max_tokens": 4096},  # без застарілих параметрів вибірки
        caps={"tools": True, "json_schema": True, "reasoning_control": True},
        price_in=0.75, price_out=3.75, price_src="https://ai.google.dev/gemini-api/docs/pricing",
        price_date="2026-10-27", free_tier=True, trains_on_data=True,
    ),
    "gemini-native": ModelSpec(
        alias="gemini-native", api="gemini_native", model="gemini-3.8-flash", base_url=None,
        key_env="GEMINI_API_KEY", params={"thinking_level": "low", "max_tokens": 4096},
        caps={"tools": True, "json_schema": True, "reasoning_control": True},
        price_in=0.75, price_out=3.75, price_src="https://ai.google.dev/gemini-api/docs/pricing",
        price_date="2026-10-27", free_tier=True, trains_on_data=True,
    ),
    "openrouter": ModelSpec(
        alias="openrouter", api="openai_chat", model="", base_url="https://openrouter.ai/api/v1",
        key_env="OPENROUTER_API_KEY", params={"max_tokens": 4096}, free_tier=True,
    ),
}


def get(alias: str) -> ModelSpec:
    """Повертає специфікацію з урахуванням змінних середовища (.env)."""
    if alias not in MODELS:
        raise KeyError(f"невідомий псевдонім {alias!r}; доступні: {', '.join(MODELS)}")
    spec = MODELS[alias]
    env = os.environ.get
    if alias in ("local", "local-large"):
        spec = replace(spec, model=env("LOCAL_MODEL") or spec.model,
                       base_url=env("LOCAL_BASE_URL") or spec.base_url,
                       num_ctx=int(env("LOCAL_NUM_CTX") or spec.num_ctx))
        if alias == "local-large":
            spec = replace(spec, model=env("LOCAL_LARGE_MODEL") or "qwen3:4b")
    elif alias == "openrouter":
        spec = replace(spec, model=env("OPENROUTER_MODEL") or spec.model)
    elif alias == "local-fast":
        spec = replace(spec, base_url=env("LOCAL_BASE_URL") or spec.base_url,
                       num_ctx=int(env("LOCAL_NUM_CTX") or spec.num_ctx))
    return spec
