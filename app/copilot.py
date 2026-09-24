"""Core engine: triage a support ticket and draft a grounded reply.

One function, `run(ticket, model_key)`, returns the model's structured answer plus
latency and token usage, so the same code powers the demo app and the evaluation.
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mistralai.client import Mistral

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Display name -> (vendor, API model id, extra settings)
MODELS = {
    "Gemini 3.5 Flash-Lite": ("gemini", "gemini-3.5-flash-lite", {}),
    "Gemini 3.5 Flash": ("gemini", "gemini-3.5-flash", {}),
    "Ministral 14B": ("mistral", "ministral-14b-latest", {}),
}

CATEGORIES = {
    "ACCOUNT": "sign-up, creating/deleting accounts, adding users, changing plan, updating account details",
    "INVOICE": "finding, viewing or downloading invoices/bills, invoice details",
    "PAYMENT": "payment methods, failed or problematic payments",
    "REFUND": "refund policy, requesting a refund, refund status",
    "NEWSLETTER": "subscribing to or unsubscribing from the newsletter",
    "CANCEL": "cancellation, cancellation or early exit fees/penalties",
    "CONTACT": "reaching a human agent, support hours, contact channels",
    "FEEDBACK": "leaving reviews or feedback, making complaints",
}
PRIORITIES = ["H", "M", "L"]
SENTIMENTS = ["positive", "neutral", "frustrated", "angry"]
CONFIDENCE = ["high", "medium", "low"]

RUBRIC = (ROOT / "docs" / "priority-rubric.md").read_text()
KB_FILES = sorted((ROOT / "data" / "kb").glob("KB*.md"))
KB_TEXT = "\n\n".join(f.read_text() for f in KB_FILES)
KB_IDS = [f.name.split("-")[0] for f in KB_FILES] + ["NONE"]

# Field order matters: the model writes its reasoning before committing to a priority.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "priority_reason": {"type": "string", "description": "One sentence citing the rubric rule applied."},
        "priority": {"type": "string", "enum": PRIORITIES},
        "sentiment": {"type": "string", "enum": SENTIMENTS},
        "confidence": {"type": "string", "enum": CONFIDENCE},
        "kb_article": {"type": "string", "enum": KB_IDS},
        "reply": {"type": "string"},
    },
    "required": ["category", "priority_reason", "priority", "sentiment", "confidence", "kb_article", "reply"],
}

SYSTEM_PROMPT = f"""You are a support triage assistant for Nimbus CRM, a B2B SaaS company.
For each customer ticket, classify it and draft a reply for a human agent to review.

## Categories
{chr(10).join(f"- {k}: {v}" for k, v in CATEGORIES.items())}

## Priority rubric (apply exactly as written)
{RUBRIC}

## Help centre (the ONLY source of facts you may use)
{KB_TEXT}

## Reply rules
- Use only facts stated in the help centre above. Never invent policies, prices, timelines, links or menu paths.
- If the help centre does not answer the question, say a specialist will follow up, and set kb_article to "NONE".
- Be concise (under 120 words), friendly and professional. Address the customer directly. No sign-off name.
- Set kb_article to the ID (e.g. "KB04") of the article you used most.
- confidence: how sure you are about the category and priority ("low" if the ticket is ambiguous).

Respond with a JSON object with exactly these fields:
{json.dumps(OUTPUT_SCHEMA["properties"], indent=1)}
"""

_gemini = None
_mistral = None


# Clients are cached per key, so a key added later (e.g. via app secrets) is picked up.
def _gemini_client():
    global _gemini
    key = os.getenv("GEMINI_API_KEY", "")
    if _gemini is None or _gemini[0] != key:
        _gemini = (key, genai.Client(api_key=key))
    return _gemini[1]


def _mistral_client():
    global _mistral
    key = os.getenv("MISTRAL_API_KEY", "")
    if _mistral is None or _mistral[0] != key:
        _mistral = (key, Mistral(api_key=key))
    return _mistral[1]


def _call_gemini(model_id, ticket, settings):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_json_schema=OUTPUT_SCHEMA,
    )
    if "thinking_level" in settings:
        config.thinking_config = types.ThinkingConfig(thinking_level=settings["thinking_level"])
    r = _gemini_client().models.generate_content(model=model_id, contents=ticket, config=config)
    u = r.usage_metadata
    return r.text, {
        "input_tokens": u.prompt_token_count or 0,
        "output_tokens": u.candidates_token_count or 0,
        "thinking_tokens": u.thoughts_token_count or 0,
    }


def _call_mistral(model_id, ticket, settings):
    r = _mistral_client().chat.complete(
        model=model_id,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": ticket}],
        # Strict schema mode: plain JSON mode once returned the schema itself instead of an answer (T049).
        response_format={"type": "json_schema",
                         "json_schema": {"name": "triage", "schema": OUTPUT_SCHEMA, "strict": True}},
    )
    return r.choices[0].message.content, {
        "input_tokens": r.usage.prompt_tokens,
        "output_tokens": r.usage.completion_tokens,
        "thinking_tokens": 0,
    }


def _is_rate_limit(e):
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    return code in (429, 503) or "429" in str(e) or "503" in str(e)


def needs_human(result):
    """Business rule, deliberately in code rather than left to the model."""
    return result["priority"] == "H" or result["sentiment"] == "angry" or result["confidence"] == "low"


def run(ticket, model_key, max_retries=5):
    vendor, model_id, settings = MODELS[model_key]
    call = _call_gemini if vendor == "gemini" else _call_mistral
    for attempt in range(max_retries):
        start = time.time()
        try:
            raw, usage = call(model_id, ticket, settings)
            latency = time.time() - start
            break
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt * 3)  # 3s, 6s, 12s, 24s
                continue
            return {"model": model_key, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"model": model_key, "error": "invalid JSON", "raw": raw, "latency_s": latency, **usage}

    # Normalise and validate against the allowed values
    problems = []
    for field, allowed in [("category", CATEGORIES), ("priority", PRIORITIES), ("sentiment", SENTIMENTS),
                           ("confidence", CONFIDENCE), ("kb_article", KB_IDS)]:
        value = str(result.get(field, "")).strip()
        value = value.upper() if field in ("category", "priority", "kb_article") else value.lower()
        result[field] = value
        if value not in allowed:
            problems.append(f"{field}={value!r}")
    result["needs_human"] = needs_human(result)
    return {"model": model_key, "latency_s": round(latency, 2), **usage, **result,
            "schema_errors": ", ".join(problems)}


# Primary model -> backup from the other vendor, so one provider's outage doesn't stop triage.
FALLBACK = {"Ministral 14B": "Gemini 3.5 Flash-Lite", "Gemini 3.5 Flash-Lite": "Ministral 14B",
            "Gemini 3.5 Flash": "Ministral 14B"}


def run_with_fallback(ticket, model_key):
    result = run(ticket, model_key, max_retries=2)
    if "error" in result and model_key in FALLBACK:
        backup = run(ticket, FALLBACK[model_key], max_retries=2)
        backup["fallback_from"] = model_key
        backup["primary_error"] = result["error"]
        return backup
    return result
