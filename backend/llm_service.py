import os
import time
import hashlib
import json

from dotenv import load_dotenv
from litellm import completion

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "gemini/gemini-3-flash-preview")

API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

ENABLE_FAILURE_SIMULATION = (
    os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
)

# In-memory response cache
CACHE = {}


def get_cache_key(messages):
    payload = {
        "model": MODEL,
        "messages": messages
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(serialized.encode()).hexdigest()


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


def generate_reply(messages, simulate_failure=None):
    start_request = time.perf_counter()

    cache_key = get_cache_key(messages)

    # Cache hit
    if cache_key in CACHE:
        cached = CACHE[cache_key]

        latency_ms = int(
            (time.perf_counter() - start_request) * 1000
        )

        return {
            "reply": cached["reply"],
            "metadata": {
                "resolution_source": "LLM_CACHE",
                "model": cached["model"],
                "latency_ms": latency_ms,
                "input_tokens": cached["input_tokens"],
                "output_tokens": cached["output_tokens"],
                "key_id": None,
                "fallback_attempts": 0
            }
        }

    failures = parse_failure_header(simulate_failure)

    last_error = None
    fallback_attempts = 0

    for index, api_key in enumerate(API_KEYS):
        key_id = f"key_{index + 1}"

        # Simulated failure
        if "*" in failures or key_id in failures:
            status = failures.get(key_id, failures.get("*"))

            print(
                f"Simulating failure for {key_id}: HTTP {status}"
            )

            last_error = RuntimeError(
                f"simulated provider failure {status}"
            )

            fallback_attempts += 1
            continue

        try:
            response = completion(
                model=MODEL,
                messages=messages,
                api_key=api_key
            )

            latency_ms = int(
                (time.perf_counter() - start_request) * 1000
            )

            usage = response.usage

            input_tokens = int(
                getattr(usage, "prompt_tokens", 0) or 0
            )

            output_tokens = int(
                getattr(usage, "completion_tokens", 0) or 0
            )

            reply = response.choices[0].message.content

            result = {
                "reply": reply,
                "metadata": {
                    "resolution_source": "LIVE_INFERENCE",
                    "model": MODEL,
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "key_id": key_id,
                    "fallback_attempts": fallback_attempts
                }
            }

            CACHE[cache_key] = {
                "reply": reply,
                "model": MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }

            return result

        except Exception as exc:
            print(
                f"{key_id} provider failure: "
                f"{type(exc).__name__}: {exc}"
            )

            last_error = exc
            fallback_attempts += 1
            continue

    raise RuntimeError(
        "all providers unavailable"
    ) from last_error