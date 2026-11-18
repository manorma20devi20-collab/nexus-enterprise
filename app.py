import os
import uuid
import sqlite3
import hashlib
import hmac
import time
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, make_response, render_template_string
from flask_cors import CORS


# ============================================================
# VEYA V17
# Dynamic Multi-Provider AI Platform
#
# IMPORTANT:
# - Never put API keys in this file.
# - Put all secrets in server Environment Variables.
# - Model IDs are validated against live provider APIs.
# - User-supplied model names are NOT blindly trusted.
# ============================================================

APP_NAME = "Veya"
VERSION = "17.0"

PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DATABASE_PATH", "veya.db")

SECRET_KEY = (
    os.getenv("SECRET_KEY", "").strip()
    or os.urandom(32).hex()
)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

CORS(app)


# ============================================================
# ENV HELPERS
# ============================================================

def env(name, default=""):
    return os.getenv(name, default).strip()


def env_list(name):
    value = env(name)
    if not value:
        return []

    return [
        x.strip()
        for x in value.split(",")
        if x.strip()
    ]


# ============================================================
# PROVIDERS
# ============================================================

PROVIDERS = [
    "openai",
    "anthropic",
    "google",
    "xai",
    "deepseek",
    "mistral",
    "nvidia",
    "microsoft",
    "meta",
    "groq",
]


API_KEYS = {
    "openai": env("OPENAI_API_KEY"),
    "anthropic": env("ANTHROPIC_API_KEY"),
    "google": env("GOOGLE_API_KEY"),
    "xai": env("XAI_API_KEY"),
    "deepseek": env("DEEPSEEK_API_KEY"),
    "mistral": env("MISTRAL_API_KEY"),
    "nvidia": env("NVIDIA_API_KEY"),
    "microsoft": env("MICROSOFT_API_KEY"),
    "meta": env("META_API_KEY"),
    "groq": env("GROQ_API_KEY"),
}


BASE_URLS = {
    "openai": env(
        "OPENAI_BASE_URL",
        "https://api.openai.com/v1",
    ),

    "anthropic": env(
        "ANTHROPIC_BASE_URL",
        "https://api.anthropic.com",
    ),

    "google": env(
        "GOOGLE_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    ),

    "xai": env(
        "XAI_BASE_URL",
        "https://api.x.ai/v1",
    ),

    "deepseek": env(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    ),

    "mistral": env(
        "MISTRAL_BASE_URL",
        "https://api.mistral.ai/v1",
    ),

    "nvidia": env(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    ),

    "microsoft": env(
        "MICROSOFT_BASE_URL",
    ),

    "meta": env(
        "META_BASE_URL",
    ),

    "groq": env(
        "GROQ_BASE_URL",
        "https://api.groq.com/openai/v1",
    ),
}


# ============================================================
# VERIFIED FALLBACKS
# ============================================================

# These are fallbacks only.
# They are still checked against the provider's live model list
# whenever possible.

GOOGLE_FREE_FALLBACKS = [
    env(
        "GOOGLE_FREE_MODEL",
        "gemini-3.8-flash",
    ),
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]


# ============================================================
# MODEL OVERRIDES
# ============================================================

MODEL_OVERRIDES = {
    provider: env_list(
        f"{provider.upper()}_MODELS"
    )
    for provider in PROVIDERS
}


# ============================================================
# MODEL CACHE
# ============================================================

MODEL_CACHE = {}
CACHE_SECONDS = int(
    env(
        "MODEL_CACHE_SECONDS",
        "300",
    )
)


def cache_get(provider):
    item = MODEL_CACHE.get(provider)

    if not item:
        return None

    timestamp, models = item

    if time.time() - timestamp >= CACHE_SECONDS:
        return None

    return models


def cache_set(provider, models):
    MODEL_CACHE[provider] = (
        time.time(),
        models,
    )


def cache_clear(provider=None):
    if provider:
        MODEL_CACHE.pop(provider, None)
    else:
        MODEL_CACHE.clear()


# ============================================================
# TIME
# ============================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    connection = db()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            plan TEXT NOT NULL DEFAULT 'free',
            created_at TEXT NOT NULL,
            subscription_id TEXT,
            subscription_status TEXT
        );

        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            agent_role TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            agent_role TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# PLANS
# ============================================================

PLANS = {
    "free": {
        "name": "Veya Free",
        "price_inr": 0,
        "daily_messages": 20,
        "monthly_provider_budget_usd": 0.10,
        "providers": ["google"],
        "slots": 1,
        "model_picker": False,
    },

    "core": {
        "name": "Veya Core",
        "price_inr": 399,
        "daily_messages": 100,
        "monthly_provider_budget_usd": 1.75,
        "providers": [
            "openai",
            "google",
            "anthropic",
        ],
        "slots": 1,
        "model_picker": True,
    },

    "all_ai": {
        "name": "Veya All AI",
        "price_inr": 999,
        "daily_messages": 300,
        "monthly_provider_budget_usd": 5.00,
        "providers": PROVIDERS,
        "slots": 5,
        "model_picker": True,
    },

    "ultra": {
        "name": "Veya Ultra",
        "price_inr": 2499,
        "daily_messages": 1000,
        "monthly_provider_budget_usd": 12.00,
        "providers": PROVIDERS,
        "slots": 5,
        "model_picker": True,
    },
}


# ============================================================
# USER
# ============================================================

def get_user_id():
    user_id = request.cookies.get(
        "veya_user"
    )

    if not user_id:
        user_id = str(uuid.uuid4())

    connection = db()

    row = connection.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if not row:
        connection.execute(
            """
            INSERT INTO users(
                id,
                plan,
                created_at
            )
            VALUES (?, 'free', ?)
            """,
            (
                user_id,
                utc_now(),
            ),
        )

        connection.commit()

    connection.close()

    return user_id


def get_plan(user_id):
    connection = db()

    row = connection.execute(
        """
        SELECT plan
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    if not row:
        return "free"

    if row["plan"] not in PLANS:
        return "free"

    return row["plan"]


# ============================================================
# HTTP
# ============================================================

def request_json(
    method,
    url,
    headers=None,
    params=None,
    payload=None,
    timeout=60,
):
    response = requests.request(
        method,
        url,
        headers=headers or {},
        params=params or {},
        json=payload,
        timeout=timeout,
    )

    if not response.ok:
        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    if not response.text.strip():
        return {}

    return response.json()


# ============================================================
# PROVIDER STATUS
# ============================================================

def provider_configured(provider):

    if provider == "local":
        return bool(
            env("LOCAL_BASE_URL")
        )

    if not API_KEYS.get(provider):
        return False

    if provider in (
        "microsoft",
        "meta",
    ):
        return bool(
            BASE_URLS.get(provider)
        )

    return True


def provider_headers(provider):

    key = API_KEYS.get(
        provider,
        "",
    )

    if provider == "anthropic":
        return {
            "x-api-key": key,
            "anthropic-version":
                "2023-06-01",
            "Content-Type":
                "application/json",
        }

    if provider == "microsoft":
        return {
            "api-key": key,
            "Content-Type":
                "application/json",
        }

    return {
        "Authorization":
            f"Bearer {key}",
        "Content-Type":
            "application/json",
    }


# ============================================================
# MODEL FILTER
# ============================================================

NON_CHAT_TERMS = (
    "embedding",
    "embed",
    "rerank",
    "moderation",
    "whisper",
    "tts",
    "transcrib",
    "speech-only",
    "audio-only",
    "image-generation",
)


def looks_like_chat_model(model):

    name = model.lower()

    return not any(
        term in name
        for term in NON_CHAT_TERMS
    )


# ============================================================
# GOOGLE MODEL DISCOVERY
# ============================================================

def discover_google_models():

    provider = "google"

    cached = cache_get(provider)

    if cached is not None:
        return cached

    if not provider_configured(
        provider
    ):
        return []

    url = (
        BASE_URLS[provider].rstrip("/")
        + "/models"
    )

    data = request_json(
        "GET",
        url,
        params={
            "key":
                API_KEYS["google"]
        },
        timeout=30,
    )

    models = []

    for item in data.get(
        "models",
        [],
    ):

        name = item.get(
            "name",
            "",
        )

        if name.startswith(
            "models/"
        ):
            name = name[7:]

        methods = item.get(
            "supportedGenerationMethods",
            [],
        )

        if not name:
            continue

        if (
            methods
            and
            "generateContent"
            not in methods
        ):
            continue

        if not looks_like_chat_model(
            name
        ):
            continue

        models.append(name)

    models = list(
        dict.fromkeys(models)
    )

    cache_set(
        provider,
        models,
    )

    return models


# ============================================================
# ANTHROPIC DISCOVERY
# ============================================================

def discover_anthropic_models():

    provider = "anthropic"

    cached = cache_get(provider)

    if cached is not None:
        return cached

    if not provider_configured(
        provider
    ):
        return []

    data = request_json(
        "GET",
        BASE_URLS[
            provider
        ].rstrip("/")
        + "/v1/models",
        headers=provider_headers(
            provider
        ),
        timeout=30,
    )

    models = []

    for item in data.get(
        "data",
        [],
    ):
        model_id = item.get(
            "id"
        )

        if (
            model_id
            and
            looks_like_chat_model(
                model_id
            )
        ):
            models.append(
                model_id
            )

    models = list(
        dict.fromkeys(models)
    )

    cache_set(
        provider,
        models,
    )

    return models


# ============================================================
# OPENAI-COMPATIBLE DISCOVERY
# ============================================================

def discover_compatible_models(
    provider
):

    cached = cache_get(provider)

    if cached is not None:
        return cached

    if not provider_configured(
        provider
    ):
        return []

    base = BASE_URLS.get(
        provider,
        "",
    ).rstrip("/")

    if not base:
        return []

    data = request_json(
        "GET",
        base + "/models",
        headers=provider_headers(
            provider
        ),
        timeout=30,
    )

    models = []

    for item in data.get(
        "data",
        [],
    ):

        model_id = item.get(
            "id"
        )

        if (
            model_id
            and
            looks_like_chat_model(
                model_id
            )
        ):
            models.append(
                model_id
            )

    models = list(
        dict.fromkeys(models)
    )

    cache_set(
        provider,
        models,
    )

    return models


# ============================================================
# UNIVERSAL DISCOVERY
# ============================================================

def discover_models(
    provider
):

    try:

        if provider == "google":
            live = discover_google_models()

        elif provider == "anthropic":
            live = discover_anthropic_models()

        else:
            live = discover_compatible_models(
                provider
            )

    except Exception:
        live = []

    override = MODEL_OVERRIDES.get(
        provider,
        [],
    )

    # Never blindly trust an override when
    # a live provider catalogue exists.
    if live:

        if override:

            verified = [
                model
                for model in override
                if model in live
            ]

            if verified:
                return verified

        return live

    # Microsoft/Meta/NVIDIA may require
    # provider-specific deployment configuration.
    return override


# ============================================================
# GOOGLE FREE MODEL SELECTION
# ============================================================

def choose_google_free_model():

    live = discover_google_models()

    if not live:
        return None

    # First choice:
    # efficient Flash models.
    preferred = []

    for wanted in GOOGLE_FREE_FALLBACKS:

        for live_model in live:

            if live_model == wanted:
                preferred.append(
                    live_model
                )

    if preferred:
        return preferred[0]

    # Then any available Flash model.
    flash = [
        model
        for model in live
        if "flash" in model.lower()
    ]

    if flash:
        return flash[0]

    # Final verified generation-capable model.
    return live[0]


# ============================================================
# MODEL SCORING
# ============================================================

def model_score(
    provider,
    model,
    task="general",
):

    name = model.lower()

    score = 0

    high_value = (
        "pro",
        "opus",
        "large",
        "reason",
        "thinking",
        "frontier",
        "flagship",
        "max",
        "ultra",
    )

    for word in high_value:

        if word in name:
            score += 10

    if task == "coding":

        for word in (
            "code",
            "coder",
            "reason",
            "thinking",
            "pro",
        ):

            if word in name:
                score += 15

    elif task == "research":

        for word in (
            "research",
            "reason",
            "thinking",
            "pro",
            "large",
        ):

            if word in name:
                score += 15

    elif task == "math":

        for word in (
            "reason",
            "thinking",
            "pro",
            "large",
        ):

            if word in name:
                score += 15

    elif task == "writing":

        for word in (
            "opus",
            "sonnet",
            "pro",
            "large",
        ):

            if word in name:
                score += 15

    return score


def rank_models(
    provider,
    models,
    task="general",
):

    return sorted(
        models,
        key=lambda model: (
            model_score(
                provider,
                model,
                task,
            ),
            len(model),
        ),
        reverse=True,
    )


# ============================================================
# AGENT ROLES
# ============================================================

PREMIUM_ROLES = [
    (
        "reasoning",
        "Deep Reasoning",
    ),
    (
        "coding",
        "Advanced Coding",
    ),
    (
        "research",
        "Research & Analysis",
    ),
    (
        "creative",
        "Creative Intelligence",
    ),
    (
        "verifier",
        "Verification",
    ),
]


def provider_agents(
    provider,
    limit=5,
    task="general",
):

    models = rank_models(
        provider,
        discover_models(
            provider
        ),
        task,
    )

    if not models:
        return []

    result = []

    for index in range(
        min(limit, len(models))
    ):

        role_id, role_name = (
            PREMIUM_ROLES[
                index
            ]
        )

        result.append({
            "provider":
                provider,

            "slot":
                index + 1,

            "agent_id":
                f"{provider}-"
                f"{role_id}-"
                f"{index + 1}",

            "agent_name":
                role_name,

            "agent_role":
                role_id,

            "model":
                models[index],

            "verified_live_model":
                True,

            "shared_model":
                False,
        })

    return result


def premium_catalog(
    plan,
    task="general",
):

    if plan not in PLANS:
        return []

    output = []

    for provider in PLANS[
        plan
    ]["providers"]:

        if not provider_configured(
            provider
        ):
            continue

        output.extend(
            provider_agents(
                provider,
                PLANS[
                    plan
                ]["slots"],
                task,
            )
        )

    return output


# ============================================================
# TASK ROUTER
# ============================================================

def route_task(text):

    value = text.lower()

    if any(
        word in value
        for word in (
            "python",
            "javascript",
            "typescript",
            "coding",
            "code",
            "debug",
            "docker",
            "api",
            "program",
            "github",
            "software",
        )
    ):
        return "coding"

    if any(
        word in value
        for word in (
            "calculate",
            "equation",
            "math",
            "mathematics",
            "proof",
            "algebra",
        )
    ):
        return "math"

    if any(
        word in value
        for word in (
            "research",
            "latest",
            "current",
            "today",
            "compare",
            "analysis",
        )
    ):
        return "research"

    if any(
        word in value
        for word in (
            "write",
            "story",
            "article",
            "email",
            "essay",
            "rewrite",
        )
    ):
        return "writing"

    return "general"


# ============================================================
# PROMPTS
# ============================================================

SYSTEM_PROMPT = """
You are Veya.

You are an orchestration layer over configured AI providers.

Never claim that you are OpenAI, Google, Anthropic,
xAI, Meta, NVIDIA, Mistral, Microsoft, DeepSeek or Groq.

Never claim a model is available unless Veya has
verified that model through the configured provider.

Virtual agents are orchestration roles, not separate
foundation models.

Be accurate and transparent.
"""


def role_instruction(role):

    instructions = {

        "reasoning": """
Think carefully.
Separate facts from assumptions.
Check important conclusions.
""",

        "coding": """
Act as a careful software engineer.
Check architecture, dependencies, syntax and edge cases.
""",

        "research": """
Act as a research and analysis specialist.
Do not invent sources or facts.
""",

        "creative": """
Act as a creative specialist while remaining accurate.
""",

        "verifier": """
Check the answer for contradictions,
unsupported claims and technical errors.
""",
    }

    return instructions.get(
        role,
        instructions["reasoning"],
    )


# ============================================================
# OPENAI
# ============================================================

def call_openai(
    model,
    messages,
):

    data = request_json(
        "POST",
        BASE_URLS[
            "openai"
        ].rstrip("/")
        + "/responses",
        headers=provider_headers(
            "openai"
        ),
        payload={
            "model":
                model,
            "input":
                messages,
        },
        timeout=180,
    )

    answer = data.get(
        "output_text",
        "",
    )

    if not answer:

        parts = []

        for item in data.get(
            "output",
            [],
        ):

            for content in item.get(
                "content",
                [],
            ):

                if (
                    content.get(
                        "type"
                    )
                    == "output_text"
                ):

                    parts.append(
                        content.get(
                            "text",
                            "",
                        )
                    )

        answer = "\n".join(
            parts
        ).strip()

    usage = data.get(
        "usage",
        {},
    )

    return (
        answer
        or
        "The model returned no text.",
        int(
            usage.get(
                "input_tokens",
                0,
            )
        ),
        int(
            usage.get(
                "output_tokens",
                0,
            )
        ),
    )


# ============================================================
# ANTHROPIC
# ============================================================

def call_anthropic(
    model,
    messages,
):

    system = []

    clean = []

    for message in messages:

        if message["role"] == "system":

            system.append(
                message["content"]
            )

        else:

            clean.append({
                "role":
                    message["role"],
                "content":
                    message["content"],
            })

    payload = {
        "model":
            model,
        "max_tokens":
            4096,
        "messages":
            clean,
    }

    if system:

        payload["system"] = "\n".join(
            system
        )

    data = request_json(
        "POST",
        BASE_URLS[
            "anthropic"
        ].rstrip("/")
        + "/v1/messages",
        headers=provider_headers(
            "anthropic"
        ),
        payload=payload,
        timeout=180,
    )

    parts = []

    for block in data.get(
        "content",
        [],
    ):

        if block.get(
            "type"
        ) == "text":

            parts.append(
                block.get(
                    "text",
                    "",
                )
            )

    usage = data.get(
        "usage",
        {},
    )

    return (
        "\n".join(
            parts
        ).strip()
        or
        "The model returned no text.",
        int(
            usage.get(
                "input_tokens",
                0,
            )
        ),
        int(
            usage.get(
                "output_tokens",
                0,
            )
        ),
    )


# ============================================================
# GOOGLE
# ============================================================

def call_google(
    model,
    messages,
):

    contents = []
    system_parts = []

    for message in messages:

        if message["role"] == "system":

            system_parts.append(
                message["content"]
            )

            continue

        role = message["role"]

        if role == "assistant":
            role = "model"

        contents.append({
            "role":
                role,
            "parts": [
                {
                    "text":
                        message[
                            "content"
                        ]
                }
            ],
        })

    payload = {
        "contents":
            contents,

        "generationConfig": {
            "maxOutputTokens":
                4096,
        },
    }

    if system_parts:

        payload[
            "systemInstruction"
        ] = {
            "parts": [
                {
                    "text":
                        "\n".join(
                            system_parts
                        )
                }
            ]
        }

    data = request_json(
        "POST",
        BASE_URLS[
            "google"
        ].rstrip("/")
        + "/models/"
        + model
        + ":generateContent",
        params={
            "key":
                API_KEYS[
                    "google"
                ]
        },
        headers={
            "Content-Type":
                "application/json"
        },
        payload=payload,
        timeout=180,
    )

    parts = []

    for candidate in data.get(
        "candidates",
        [],
    ):

        content = candidate.get(
            "content",
            {},
        )

        for part in content.get(
            "parts",
            [],
        ):

            if part.get(
                "text"
            ):

                parts.append(
                    part["text"]
                )

    usage = data.get(
        "usageMetadata",
        {},
    )

    return (
        "\n".join(
            parts
        ).strip()
        or
        "The model returned no text.",
        int(
            usage.get(
                "promptTokenCount",
                0,
            )
        ),
        int(
            usage.get(
                "candidatesTokenCount",
                0,
            )
        ),
    )


# ============================================================
# OPENAI-COMPATIBLE PROVIDERS
# ============================================================

def call_compatible(
    provider,
    model,
    messages,
):

    base = BASE_URLS.get(
        provider,
        "",
    ).rstrip("/")

    if not base:
        raise RuntimeError(
            f"{provider} base URL is not configured."
        )

    data = request_json(
        "POST",
        base
        + "/chat/completions",
        headers=provider_headers(
            provider
        ),
        payload={
            "model":
                model,
            "messages":
                messages,
            "max_tokens":
                4096,
        },
        timeout=180,
    )

    choices = data.get(
        "choices",
        [],
    )

    if not choices:
        raise RuntimeError(
            f"{provider} returned no choices."
        )

    content = choices[
        0
    ].get(
        "message",
        {},
    ).get(
        "content",
        "",
    )

    if isinstance(
        content,
        list,
    ):

        content = "\n".join(
            item.get(
                "text",
                "",
            )
            for item in content
            if isinstance(
                item,
                dict,
            )
        )

    usage = data.get(
        "usage",
        {},
    )

    return (
        content
        or
        "The model returned no text.",
        int(
            usage.get(
                "prompt_tokens",
                0,
            )
        ),
        int(
            usage.get(
                "completion_tokens",
                0,
            )
        ),
    )


# ============================================================
# UNIFIED CALL
# ============================================================

def call_provider(
    provider,
    model,
    messages,
):

    if provider == "openai":

        return call_openai(
            model,
            messages,
        )

    if provider == "anthropic":

        return call_anthropic(
            model,
            messages,
        )

    if provider == "google":

        return call_google(
            model,
            messages,
        )

    return call_compatible(
        provider,
        model,
        messages,
    )


# ============================================================
# CHAT STORAGE
# ============================================================

def create_chat(
    user_id,
    title="New chat",
):

    chat_id = str(
        uuid.uuid4()
    )

    timestamp = utc_now()

    connection = db()

    connection.execute(
        """
        INSERT INTO chats(
            id,
            user_id,
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            user_id,
            title,
            timestamp,
            timestamp,
        ),
    )

    connection.commit()
    connection.close()

    return chat_id


def ensure_chat(
    user_id,
    chat_id,
):

    connection = db()

    row = connection.execute(
        """
        SELECT id
        FROM chats
        WHERE id = ?
        AND user_id = ?
        """,
        (
            chat_id,
            user_id,
        ),
    ).fetchone()

    connection.close()

    if not row:
        raise RuntimeError(
            "Chat not found."
        )


def save_message(
    chat_id,
    role,
    content,
    provider=None,
    model=None,
    agent_role=None,
):

    timestamp = utc_now()

    connection = db()

    connection.execute(
        """
        INSERT INTO messages(
            chat_id,
            role,
            content,
            provider,
            model,
            agent_role,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            role,
            content,
            provider,
            model,
            agent_role,
            timestamp,
        ),
    )

    connection.execute(
        """
        UPDATE chats
        SET updated_at = ?
        WHERE id = ?
        """,
        (
            timestamp,
            chat_id,
        ),
    )

    connection.commit()
    connection.close()


def get_messages(
    chat_id,
    limit=30,
):

    connection = db()

    rows = connection.execute(
        """
        SELECT
            role,
            content,
            provider,
            model,
            agent_role,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            chat_id,
            limit,
        ),
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in reversed(rows)
    ]


# ============================================================
# USAGE
# ============================================================

def daily_message_count(
    user_id
):

    today = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d"
    )

    connection = db()

    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM messages m
        JOIN chats c
        ON c.id = m.chat_id
        WHERE c.user_id = ?
        AND m.role = 'user'
        AND substr(
            m.created_at,
            1,
            10
        ) = ?
        """,
        (
            user_id,
            today,
        ),
    ).fetchone()

    connection.close()

    return int(
        row[0] or 0
    )


def monthly_cost(
    user_id
):

    month = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m"
    )

    connection = db()

    row = connection.execute(
        """
        SELECT COALESCE(
            SUM(estimated_cost_usd),
            0
        )
        FROM usage
        WHERE user_id = ?
        AND substr(
            created_at,
            1,
            7
        ) = ?
        """,
        (
            user_id,
            month,
        ),
    ).fetchone()

    connection.close()

    return float(
        row[0] or 0
    )


def estimate_cost(
    input_tokens,
    output_tokens,
):

    input_price = float(
        env(
            "DEFAULT_INPUT_COST_USD_PER_M",
            "2",
        )
    )

    output_price = float(
        env(
            "DEFAULT_OUTPUT_COST_USD_PER_M",
            "8",
        )
    )

    return (
        input_tokens
        / 1_000_000
        * input_price
        +
        output_tokens
        / 1_000_000
        * output_price
    )


def record_usage(
    user_id,
    provider,
    model,
    agent_role,
    input_tokens,
    output_tokens,
):

    cost = estimate_cost(
        input_tokens,
        output_tokens,
    )

    connection = db()

    connection.execute(
        """
        INSERT INTO usage(
            user_id,
            provider,
            model,
            agent_role,
            input_tokens,
            output_tokens,
            estimated_cost_usd,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            provider,
            model,
            agent_role,
            input_tokens,
            output_tokens,
            cost,
            utc_now(),
        ),
    )

    connection.commit()
    connection.close()

    return cost


# ============================================================
# 5000 VIRTUAL ORCHESTRATION ROLES
# ============================================================

BASE_ROLES = [
    "reasoning",
    "coding",
    "research",
    "mathematics",
    "science",
    "writing",
    "editing",
    "planning",
    "analysis",
    "fact_checking",
    "criticism",
    "summarization",
    "translation",
    "teaching",
    "product_design",
    "business_analysis",
    "security_review",
    "data_analysis",
    "architecture",
    "strategy",
]


VIRTUAL_AGENTS = []

for index in range(5000):

    role = BASE_ROLES[
        index % len(BASE_ROLES)
    ]

    number = (
        index
        // len(BASE_ROLES)
        + 1
    )

    VIRTUAL_AGENTS.append({
        "id":
            f"veya-agent-{index + 1:04d}",

        "role":
            f"{role}-{number}",

        "index":
            index + 1,
    })


# ============================================================
# MODEL CHOICE
# ============================================================

def choose_model(
    plan,
    task,
    requested_provider=None,
    requested_model=None,
):

    catalog = premium_catalog(
        plan,
        task,
    )

    if not catalog:

        raise RuntimeError(
            "No verified live model is available "
            "for this plan."
        )

    if (
        requested_provider
        and requested_model
    ):

        for item in catalog:

            if (
                item["provider"]
                == requested_provider
                and
                item["model"]
                == requested_model
            ):

                return item

        raise RuntimeError(
            "The selected model is not currently "
            "available through the provider."
        )

    return max(
        catalog,
        key=lambda item:
            model_score(
                item["provider"],
                item["model"],
                task,
            ),
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({
        "ok": True,
        "app": APP_NAME,
        "version": VERSION,
        "time": utc_now(),
    })


# ============================================================
# ME
# ============================================================

@app.get("/api/me")
def me():

    user_id = get_user_id()
    plan = get_plan(user_id)

    response = jsonify({
        "user_id":
            user_id,

        "plan":
            plan,

        "plan_info":
            PLANS[plan],

        "daily_used":
            daily_message_count(
                user_id
            ),

        "monthly_cost_usd":
            monthly_cost(
                user_id
            ),
    })

    response.set_cookie(
        "veya_user",
        user_id,
        httponly=True,
        samesite="Lax",
    )

    return response


# ============================================================
# PLANS
# ============================================================

@app.get("/api/plans")
def plans():

    return jsonify(
        PLANS
    )


# ============================================================
# PROVIDERS
# ============================================================

@app.get("/api/providers")
def providers():

    result = []

    for provider in PROVIDERS:

        configured = (
            provider_configured(
                provider
            )
        )

        models = []

        if configured:

            try:
                models = discover_models(
                    provider
                )

            except Exception:
                models = []

        result.append({
            "provider":
                provider,

            "configured":
                configured,

            "model_count":
                len(models),

            "models":
                models,
        })

    return jsonify(
        result
    )


# ============================================================
# MODELS
# ============================================================

@app.get("/api/models")
def models():

    user_id = get_user_id()
    plan = get_plan(user_id)

    task = request.args.get(
        "task",
        "general",
    )

    return jsonify({

        "plan":
            plan,

        "models":
            premium_catalog(
                plan,
                task,
            ),

        "providers":
            PLANS[plan][
                "providers"
            ],

        "slots":
            PLANS[plan][
                "slots"
            ],

        "free_google_fallback":
            GOOGLE_FREE_FALLBACKS,
    })


# ============================================================
# AGENTS
# ============================================================

@app.get("/api/agents")
def agents():

    return jsonify({

        "count":
            5000,

        "agents":
            VIRTUAL_AGENTS[:100],

        "premium_roles": [
            {
                "id":
                    role_id,

                "name":
                    role_name,
            }

            for role_id, role_name
            in PREMIUM_ROLES
        ],

        "note":
            "These are virtual orchestration "
            "roles, not 5000 independent foundation models.",
    })


# ============================================================
# CHATS
# ============================================================

@app.get("/api/chats")
def chats():

    user_id = get_user_id()

    connection = db()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM chats
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (
            user_id,
        ),
    ).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.post("/api/chats/new")
def new_chat():

    return jsonify({
        "chat_id":
            create_chat(
                get_user_id()
            )
    })


@app.get("/api/chats/<chat_id>")
def chat_detail(
    chat_id
):

    user_id = get_user_id()

    ensure_chat(
        user_id,
        chat_id,
    )

    return jsonify({
        "chat_id":
            chat_id,

        "messages":
            get_messages(
                chat_id
            ),
    })


# ============================================================
# MAIN CHAT
# ============================================================

@app.post("/api/chat")
def chat():

    user_id = get_user_id()
    plan = get_plan(user_id)

    plan_data = PLANS[plan]

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    text = str(
        body.get(
            "message",
            "",
        )
    ).strip()

    if not text:

        return jsonify({
            "error":
                "Message is required."
        }), 400

    if len(text) > 30000:

        return jsonify({
            "error":
                "Message is too long."
        }), 400

    if (
        daily_message_count(
            user_id
        )
        >= plan_data[
            "daily_messages"
        ]
    ):

        return jsonify({
            "error":
                "Daily message limit reached."
        }), 429

    chat_id = body.get(
        "chat_id"
    )

    if not chat_id:

        chat_id = create_chat(
            user_id,
            text[:60],
        )

    ensure_chat(
        user_id,
        chat_id,
    )

    task = route_task(
        text
    )

    requested_provider = body.get(
        "provider"
    )

    requested_model = body.get(
        "model"
    )

    # --------------------------------------------------------
    # FREE GOOGLE ROUTING
    # --------------------------------------------------------

    if plan == "free":

        try:

            provider = "google"

            model = choose_google_free_model()

            if not model:

                raise RuntimeError(
                    "No Google generation model "
                    "is currently available for "
                    "this API project."
                )

            agent_role = (
                "free-google-router"
            )

        except Exception as exc:

            return jsonify({
                "error":
                    str(exc),

                "hint":
                    "Check GOOGLE_API_KEY "
                    "and the models returned "
                    "by /api/providers.",
            }), 503

    # --------------------------------------------------------
    # PAID
    # --------------------------------------------------------

    else:

        try:

            selected = choose_model(
                plan,
                task,
                requested_provider,
                requested_model,
            )

            provider = selected[
                "provider"
            ]

            model = selected[
                "model"
            ]

            agent_role = selected[
                "agent_id"
            ]

        except Exception as exc:

            return jsonify({
                "error":
                    str(exc)
            }), 503

    # --------------------------------------------------------
    # BUDGET
    # --------------------------------------------------------

    budget = plan_data[
        "monthly_provider_budget_usd"
    ]

    if (
        budget > 0
        and
        monthly_cost(
            user_id
        ) >= budget
    ):

        return jsonify({
            "error":
                "Monthly AI usage budget reached."
        }), 402

    role_name = "reasoning"

    for role_id, _ in PREMIUM_ROLES:

        if role_id in str(
            agent_role
        ):

            role_name = role_id

            break

    messages = [
        {
            "role":
                "system",

            "content":
                SYSTEM_PROMPT
                + "\n\n"
                + role_instruction(
                    role_name
                ),
        }
    ]

    history = get_messages(
        chat_id,
        20,
    )

    for item in history:

        if item["role"] in (
            "user",
            "assistant",
        ):

            messages.append({
                "role":
                    item["role"],

                "content":
                    item["content"],
            })

    messages.append({
        "role":
            "user",

        "content":
            text,
    })

    # --------------------------------------------------------
    # PROVIDER CALL
    # --------------------------------------------------------

    try:

        (
            answer,
            input_tokens,
            output_tokens,
        ) = call_provider(
            provider,
            model,
            messages,
        )

    except Exception as first_error:

        cache_clear(
            provider
        )

        # Re-discover live models.
        fresh_models = rank_models(
            provider,
            discover_models(
                provider
            ),
            task,
        )

        alternatives = [
            candidate
            for candidate in fresh_models
            if candidate != model
        ]

        success = False

        last_error = first_error

        for candidate in alternatives[:3]:

            try:

                (
                    answer,
                    input_tokens,
                    output_tokens,
                ) = call_provider(
                    provider,
                    candidate,
                    messages,
                )

                model = candidate

                success = True

                break

            except Exception as exc:

                last_error = exc

        if not success:

            # For FREE Google, try the next
            # verified Google model.
            if provider == "google":

                for candidate in (
                    GOOGLE_FREE_FALLBACKS
                ):

                    if (
                        candidate == model
                    ):
                        continue

                    if (
                        candidate
                        not in fresh_models
                    ):
                        continue

                    try:

                        (
                            answer,
                            input_tokens,
                            output_tokens,
                        ) = call_provider(
                            "google",
                            candidate,
                            messages,
                        )

                        model = candidate

                        success = True

                        break

                    except Exception as exc:

                        last_error = exc

        if not success:

            return jsonify({

                "error":
                    f"{provider}/{model} "
                    f"failed.",

                "details":
                    str(last_error),

                "hint":
                    "Use /api/providers to "
                    "see models actually "
                    "available to your API key.",
            }), 502

    cost = record_usage(
        user_id,
        provider,
        model,
        agent_role,
        input_tokens,
        output_tokens,
    )

    save_message(
        chat_id,
        "user",
        text,
    )

    save_message(
        chat_id,
        "assistant",
        answer,
        provider,
        model,
        agent_role,
    )

    return jsonify({

        "chat_id":
            chat_id,

        "answer":
            answer,

        "provider":
            provider,

        "model":
            model,

        "agent":
            agent_role,

        "task":
            task,

        "usage": {
            "input_tokens":
                input_tokens,

            "output_tokens":
                output_tokens,

            "estimated_cost_usd":
                cost,

            "monthly_cost_usd":
                monthly_cost(
                    user_id
                ),

            "monthly_budget_usd":
                budget,
        },
    })


# ============================================================
# MODEL HEALTH TEST
# ============================================================

@app.post("/api/test-model")
def test_model():

    user_id = get_user_id()
    plan = get_plan(user_id)

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    provider = body.get(
        "provider"
    )

    model = body.get(
        "model"
    )

    if not provider or not model:

        return jsonify({
            "ok":
                False,

            "error":
                "provider and model are required.",
        }), 400

    if model not in discover_models(
        provider
    ):

        return jsonify({
            "ok":
                False,

            "error":
                "Model is not present in "
                "the provider's live catalogue.",
        }), 403

    try:

        (
            answer,
            input_tokens,
            output_tokens,
        ) = call_provider(
            provider,
            model,
            [
                {
                    "role":
                        "system",

                    "content":
                        "Reply exactly OK.",
                },
                {
                    "role":
                        "user",

                    "content":
                        "OK",
                },
            ],
        )

        return jsonify({

            "ok":
                True,

            "provider":
                provider,

            "model":
                model,

            "answer":
                answer,

            "input_tokens":
                input_tokens,

            "output_tokens":
                output_tokens,
        })

    except Exception as exc:

        return jsonify({

            "ok":
                False,

            "provider":
                provider,

            "model":
                model,

            "error":
                str(exc),
        }), 502


# ============================================================
# PAYMENT CONFIGURATION
# ============================================================
#
# IMPORTANT:
# These values are SERVER-SIDE ONLY.
# Never send them to the browser.
#
# Because Veya is being developed by a minor, actual merchant
# onboarding/payment collection must be done through a legally
# eligible adult/guardian or business account.
#
# ============================================================

RAZORPAY_KEY_ID = env(
    "RAZORPAY_KEY_ID"
)

RAZORPAY_KEY_SECRET = env(
    "RAZORPAY_KEY_SECRET"
)

RAZORPAY_WEBHOOK_SECRET = env(
    "RAZORPAY_WEBHOOK_SECRET"
)

RAZORPAY_PLAN_CORE = env(
    "RAZORPAY_PLAN_CORE"
)

RAZORPAY_PLAN_ALL_AI = env(
    "RAZORPAY_PLAN_ALL_AI"
)

RAZORPAY_PLAN_ULTRA = env(
    "RAZORPAY_PLAN_ULTRA"
)


# PhonePe values are deliberately kept
# server-side and are NOT rendered anywhere.

PHONEPE_MERCHANT_ID = env(
    "PHONEPE_MERCHANT_ID"
)

PHONEPE_CLIENT_ID = env(
    "PHONEPE_CLIENT_ID"
)

PHONEPE_CLIENT_SECRET = env(
    "PHONEPE_CLIENT_SECRET"
)

PHONEPE_MERCHANT_NUMBER = env(
    "PHONEPE_MERCHANT_NUMBER"
)


# ============================================================
# PAYMENT STATUS
# ============================================================

@app.get("/api/payment/status")
def payment_status():

    # Never return credentials.
    return jsonify({

        "razorpay_configured":
            bool(
                RAZORPAY_KEY_ID
                and RAZORPAY_KEY_SECRET
            ),

        "phonepe_configured":
            bool(
                PHONEPE_MERCHANT_ID
                and PHONEPE_CLIENT_ID
                and PHONEPE_CLIENT_SECRET
            ),

        "credentials_exposed":
            False,
    })


# ============================================================
# PAYMENT ENDPOINT
# ============================================================
#
# This endpoint intentionally does NOT expose or accept
# payment secrets from the browser.
#
# Connect an eligible adult/business-owned merchant account
# through the provider's official server-side integration.
#
# ============================================================

@app.post("/api/upgrade")
def upgrade():

    return jsonify({

        "enabled":
            False,

        "message":
            "Payment collection is not enabled in this "
            "development build. Configure the merchant "
            "integration through a legally eligible "
            "account owner and the provider's official "
            "server-side integration.",

        "credentials_exposed":
            False,
    }), 403


# ============================================================
# HOME
# ============================================================

HTML = """
<!doctype html>

<html>

<head>

<meta charset="utf-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>Veya</title>

<style>

*{
    box-sizing:border-box;
}

html,
body{
    margin:0;
    width:100%;
    height:100%;
    font-family:
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background:#f7f9fc;
    color:#111827;
}

button,
textarea,
select{
    font:inherit;
}

button{
    cursor:pointer;
}

#app{
    width:100%;
    height:100vh;
    display:flex;
    overflow:hidden;
}

#sidebar{
    position:fixed;
    left:0;
    top:0;
    bottom:0;
    width:300px;
    background:#fff;
    border-right:1px solid #e5e7eb;
    transform:translateX(-100%);
    transition:.25s;
    z-index:50;
    display:flex;
    flex-direction:column;
}

#sidebar.open{
    transform:translateX(0);
}

#overlay{
    display:none;
    position:fixed;
    inset:0;
    background:rgba(15,23,42,.35);
    z-index:40;
}

#overlay.show{
    display:block;
}

.sidebar-brand{
    padding:22px;
    font-size:24px;
    font-weight:850;
}

.new-chat{
    margin:0 16px 12px;
    width:calc(100% - 32px);
    border:1px solid #dbe3ef;
    border-radius:14px;
    padding:13px;
    background:#fff;
    font-weight:750;
}

.history{
    flex:1;
    overflow:auto;
    padding:10px;
}

.history-item{
    padding:12px;
    border-radius:11px;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}

.history-item:hover{
    background:#eef2f7;
}

#main{
    width:100%;
    height:100vh;
    display:flex;
    flex-direction:column;
}

.topbar{
    height:70px;
    display:flex;
    align-items:center;
    gap:12px;
    padding:10px 18px;
    background:rgba(255,255,255,.94);
    border-bottom:1px solid #e5e7eb;
}

.menu{
    width:44px;
    height:44px;
    border:0;
    background:transparent;
    border-radius:12px;
    font-size:25px;
}

.brand{
    font-size:22px;
    font-weight:850;
}

.spacer{
    flex:1;
}

.plan{
    font-size:12px;
    padding:7px 11px;
    border-radius:20px;
    background:#eef2ff;
    color:#4f46e5;
    font-weight:750;
}

.chat{
    flex:1;
    overflow:auto;
    padding:45px 18px 150px;
}

.welcome{
    max-width:850px;
    margin:8vh auto;
    text-align:center;
}

.welcome h1{
    font-size:
        clamp(38px,7vw,70px);
    line-height:1;
    letter-spacing:-3px;
}

.gradient{
    background:
        linear-gradient(
            90deg,
            #2563eb,
            #7c3aed,
            #db2777
        );
    -webkit-background-clip:text;
    color:transparent;
}

.welcome p{
    color:#64748b;
    font-size:17px;
}

.message{
    max-width:900px;
    margin:0 auto 24px;
    line-height:1.7;
    white-space:pre-wrap;
}

.user{
    max-width:720px;
    margin-left:auto;
    background:#eef2f7;
    border-radius:20px;
    padding:14px 17px;
}

.tag{
    color:#64748b;
    font-size:11px;
    font-weight:750;
    margin-bottom:7px;
}

.composer-wrap{
    position:fixed;
    left:0;
    right:0;
    bottom:0;
    padding:16px;
    background:
        linear-gradient(
            transparent,
            #f7f9fc 30%
        );
}

.composer{
    max-width:900px;
    margin:auto;
    background:#fff;
    border:1px solid #dbe2ec;
    border-radius:24px;
    padding:8px;
    box-shadow:
        0 15px 45px
        rgba(15,23,42,.10);
}

.row{
    display:flex;
    gap:8px;
    align-items:end;
}

textarea{
    flex:1;
    min-height:45px;
    max-height:150px;
    resize:none;
    border:0;
    outline:0;
    padding:12px 5px;
}

.send{
    width:44px;
    height:44px;
    border:0;
    border-radius:50%;
    background:#111827;
    color:#fff;
    font-size:19px;
}

.picker{
    display:none;
    padding:8px;
    border-bottom:1px solid #eef2f7;
}

.picker.show{
    display:block;
}

select{
    width:100%;
    border:1px solid #dbe2ec;
    border-radius:12px;
    padding:10px;
    background:#fff;
}

@media(max-width:700px){

    .welcome h1{
        letter-spacing:-2px;
    }

}

</style>

</head>

<body>

<div id="app">

<aside id="sidebar">

<div class="sidebar-brand">
Veya
</div>

<button
class="new-chat"
onclick="newChat()">
＋ New chat
</button>

<div
id="history"
class="history">
</div>

</aside>

<div
id="overlay"
onclick="toggleSidebar()">
</div>

<main id="main">

<header class="topbar">

<button
class="menu"
onclick="toggleSidebar()">
☰
</button>

<div class="brand">
Veya
</div>

<div class="spacer">
</div>

<div
id="plan"
class="plan">
Free
</div>

</header>

<section
id="chat"
class="chat">

<div
id="welcome"
class="welcome">

<h1>
One workspace.<br>
<span class="gradient">
Many AI minds.
</span>
</h1>

<p>
Veya dynamically verifies available models
and routes your task to a configured AI provider.
</p>

</div>

</section>

<div class="composer-wrap">

<div class="composer">

<div
id="picker"
class="picker">

<select
id="modelSelect">
</select>

</div>

<div class="row">

<textarea
id="input"
placeholder="Message Veya..."
onkeydown="handleKey(event)">
</textarea>

<button
class="send"
onclick="sendMessage()">
↑
</button>

</div>

</div>

</div>

</main>

</div>

<script>

let currentChat = null;
let currentPlan = "free";
let models = [];


async function api(
    url,
    options = {}
){

    const response =
        await fetch(
            url,
            {
                credentials:
                    "same-origin",
                ...options,
                headers:{
                    "Content-Type":
                        "application/json",
                    ...(options.headers || {})
                }
            }
        );

    const data =
        await response.json();

    if(!response.ok){

        throw new Error(
            data.error
            || data.message
            || "Request failed"
        );
    }

    return data;
}


function toggleSidebar(){

    document
        .getElementById(
            "sidebar"
        )
        .classList.toggle(
            "open"
        );

    document
        .getElementById(
            "overlay"
        )
        .classList.toggle(
            "show"
        );
}


async function loadMe(){

    const data =
        await api(
            "/api/me"
        );

    currentPlan =
        data.plan;

    document
        .getElementById(
            "plan"
        )
        .textContent =
        data.plan_info.name;

    await loadModels();
}


async function loadModels(){

    const data =
        await api(
            "/api/models"
        );

    models =
        data.models || [];

    const select =
        document.getElementById(
            "modelSelect"
        );

    select.innerHTML = "";

    if(
        !data.models
        || !data.models.length
    ){

        const option =
            document.createElement(
                "option"
            );

        option.textContent =
            "Automatic model routing";

        select.appendChild(
            option
        );

        return;
    }

    for(
        const item
        of data.models
    ){

        const option =
            document.createElement(
                "option"
            );

        option.value =
            JSON.stringify({
                provider:
                    item.provider,
                model:
                    item.model
            });

        option.textContent =
            item.provider.toUpperCase()
            + " — "
            + item.agent_name
            + " — "
            + item.model;

        select.appendChild(
            option
        );
    }
}


function togglePicker(){

    if(
        currentPlan === "free"
    ){

        return;
    }

    document
        .getElementById(
            "picker"
        )
        .classList.toggle(
            "show"
        );
}


async function loadHistory(){

    const data =
        await api(
            "/api/chats"
        );

    const history =
        document.getElementById(
            "history"
        );

    history.innerHTML = "";

    for(
        const item
        of data
    ){

        const div =
            document.createElement(
                "div"
            );

        div.className =
            "history-item";

        div.textContent =
            item.title;

        div.onclick =
            () => openChat(
                item.id
            );

        history.appendChild(
            div
        );
    }
}


async function newChat(){

    const data =
        await api(
            "/api/chats/new",
            {
                method:
                    "POST"
            }
        );

    currentChat =
        data.chat_id;

    document
        .getElementById(
            "chat"
        )
        .innerHTML = "";

    await loadHistory();
}


async function openChat(id){

    currentChat = id;

    const data =
        await api(
            "/api/chats/"
            + id
        );

    const chat =
        document.getElementById(
            "chat"
        );

    chat.innerHTML = "";

    for(
        const message
        of data.messages
    ){

        addMessage(
            message.role,
            message.content,
            message.provider,
            message.model,
            message.agent_role
        );
    }
}


function addMessage(
    role,
    content,
    provider,
    model,
    agent
){

    const welcome =
        document.getElementById(
            "welcome"
        );

    if(welcome){
        welcome.remove();
    }

    const chat =
        document.getElementById(
            "chat"
        );

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "message "
        + (
            role === "user"
            ? "user"
            : "assistant"
        );

    if(
        role === "assistant"
        && provider
        && model
    ){

        const tag =
            document.createElement(
                "div"
            );

        tag.className =
            "tag";

        tag.textContent =
            provider.toUpperCase()
            + " · "
            + model
            + (
                agent
                ? " · " + agent
                : ""
            );

        wrapper.appendChild(
            tag
        );
    }

    const body =
        document.createElement(
            "div"
        );

    body.textContent =
        content;

    wrapper.appendChild(
        body
    );

    chat.appendChild(
        wrapper
    );

    chat.scrollTop =
        chat.scrollHeight;
}


function handleKey(event){

    if(
        event.key === "Enter"
        && !event.shiftKey
    ){

        event.preventDefault();

        sendMessage();
    }
}


async function sendMessage(){

    const input =
        document.getElementById(
            "input"
        );

    const text =
        input.value.trim();

    if(!text){
        return;
    }

    input.value = "";

    addMessage(
        "user",
        text
    );

    let selected = null;

    if(
        currentPlan !== "free"
        && models.length
    ){

        try{

            selected =
                JSON.parse(
                    document
                        .getElementById(
                            "modelSelect"
                        )
                        .value
                );

        }catch(
            error
        ){

            selected = null;
        }
    }

    try{

        const data =
            await api(
                "/api/chat",
                {
                    method:
                        "POST",

                    body:
                        JSON.stringify({

                            chat_id:
                                currentChat,

                            message:
                                text,

                            provider:
                                selected
                                ? selected.provider
                                : null,

                            model:
                                selected
                                ? selected.model
                                : null,
                        })
                }
            );

        currentChat =
            data.chat_id;

        addMessage(
            "assistant",
            data.answer,
            data.provider,
            data.model,
            data.agent
        );

        await loadHistory();

    }catch(error){

        addMessage(
            "assistant",
            "Error: "
            + error.message
        );
    }
}


async function boot(){

    try{

        await loadMe();

        await loadHistory();

    }catch(error){

        addMessage(
            "assistant",
            "Startup error: "
            + error.message
        );
    }
}


boot();

</script>

</body>

</html>
"""


# ============================================================
# HOME ROUTE
# ============================================================

@app.get("/")
def home():

    user_id = get_user_id()

    response = make_response(
        render_template_string(
            HTML
        )
    )

    response.set_cookie(
        "veya_user",
        user_id,
        httponly=True,
        samesite="Lax",
    )

    return response


# ============================================================
# STARTUP
# ============================================================

init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
    )