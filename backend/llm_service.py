import os
import time
import json

import litellm
from dotenv import load_dotenv
from litellm import completion
from litellm.caching.caching import Cache

load_dotenv()

MODEL = os.getenv(
    "LLM_MODEL",
    "gemini/gemini-3-flash-preview"
)

API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

ENABLE_FAILURE_SIMULATION = (
    os.getenv(
        "ENABLE_FAILURE_SIMULATION",
        "false"
    ).lower() == "true"
)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer the user's question directly and concisely. "
    "For simple factual questions, answer in one or two sentences. "
    "Do not add unrelated information."
)

# LiteLLM built-in in-memory cache
litellm.cache = Cache(type="local")


def prepare_messages(messages):
    if messages and messages[0].get("role") == "system":
        return messages

    return [
        {
            "role": "system",
            "content": DEFAULT_SYSTEM_PROMPT
        },
        *messages
    ]


def parse_failure_header(header_value):
    failures = {}

    if not header_value or not ENABLE_FAILURE_SIMULATION:
        return failures

    for item in header_value.split(","):
        item = item.strip()

        if "=" not in item:
            continue

        key_id, status = item.split("=", 1)
        key_id = key_id.strip()

        try:
            status = int(status.strip())
        except ValueError:
            continue

        if status in {429, 500, 502, 503}:
            failures[key_id] = status

    return failures


def _response_was_cached(response):
    hidden = getattr(response, "_hidden_params", {}) or {}

    return bool(
        hidden.get("cache_hit")
        or hidden.get("cached_response")
    )


def generate_reply(messages, simulate_failure=None):
    request_start = time.perf_counter()

    final_messages = prepare_messages(messages)
    failures = parse_failure_header(simulate_failure)

    last_error = None
    fallback_attempts = 0

    for index, api_key in enumerate(API_KEYS):
        key_id = f"key_{index + 1}"

        # Failure simulation happens before provider call.
        if "*" in failures or key_id in failures:
            status = failures.get(
                key_id,
                failures.get("*")
            )

            print(
                f"Simulating {status} failure for {key_id}"
            )

            last_error = RuntimeError(
                f"simulated provider failure {status}"
            )

            fallback_attempts += 1
            continue

        try:
            response = completion(
                model=MODEL,
                messages=final_messages,
                api_key=api_key,
                temperature=0.2,
                max_tokens=300,
                caching=True
            )

            latency_ms = int(
                (time.perf_counter() - request_start) * 1000
            )

            usage = response.usage

            input_tokens = int(
                getattr(usage, "prompt_tokens", 0) or 0
            )

            output_tokens = int(
                getattr(usage, "completion_tokens", 0) or 0
            )

            reply = response.choices[0].message.content

            cache_hit = _response_was_cached(response)

            return {
                "reply": reply,
                "metadata": {
                    "resolution_source": (
                        "LLM_CACHE"
                        if cache_hit
                        else "LIVE_INFERENCE"
                    ),
                    "model": MODEL,
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "key_id": (
                        None if cache_hit else key_id
                    ),
                    "fallback_attempts": (
                        0
                        if cache_hit
                        else fallback_attempts
                    )
                }
            }

        except Exception as exc:
            print(
                f"{key_id} provider failure: "
                f"{type(exc).__name__}: {exc}"
            )

            last_error = exc
            fallback_attempts += 1

    raise RuntimeError(
        "all providers unavailable"
    ) from last_error