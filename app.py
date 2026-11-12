import os
import re
import time
import uuid
import json
import sqlite3
import hashlib
import secrets
import traceback
import threading
import urllib.robotparser
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    request,
    render_template_string,
    session,
    redirect,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

try:
    import stripe
except Exception:
    stripe = None

load_dotenv()


# ============================================================
# APP
# ============================================================

APP_NAME = "Veya"
APP_VERSION = "10.0"

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "CHANGE_THIS_IN_PRODUCTION"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.getenv("COOKIE_SECURE", "false").lower() == "true"
    ),
)

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "120")
)

MAX_HISTORY = int(
    os.getenv("MAX_HISTORY", "30")
)

MAX_INPUT_CHARS = int(
    os.getenv("MAX_INPUT_CHARS", "30000")
)

MAX_OUTPUT_TOKENS = int(
    os.getenv("MAX_OUTPUT_TOKENS", "8192")
)

FREE_MAX_MODEL_CALLS = int(
    os.getenv("FREE_MAX_MODEL_CALLS", "1")
)

PRO_MAX_MODEL_CALLS = int(
    os.getenv("PRO_MAX_MODEL_CALLS", "8")
)

PREMIUM_PRICE_USD = 20


# ============================================================
# ENV HELPERS
# ============================================================

def env(name, default=""):
    return os.getenv(name, default).strip()


def bool_env(name, default=False):
    return (
        env(name, str(default)).lower()
        in {"1", "true", "yes", "on"}
    )


def now_ms():
    return int(time.time() * 1000)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def truncate(value, limit=12000):
    text = (
        value
        if isinstance(value, str)
        else str(value)
    )

    if len(text) <= limit:
        return text

    return text[:limit] + "\n...[truncated]"


# ============================================================
# DATABASE
# ============================================================

DB_PATH = env(
    "DATABASE_PATH",
    "veya.db"
)

DB_LOCK = threading.Lock()


def db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    with DB_LOCK:

        conn = db()

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id)
                    REFERENCES chats(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chats_user
                ON chats(user_id);

            CREATE INDEX IF NOT EXISTS idx_messages_chat
                ON messages(chat_id);

            CREATE TABLE IF NOT EXISTS webhook_events (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            """
        )

        conn.commit()
        conn.close()


init_db()


# ============================================================
# AUTH
# ============================================================

def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def login_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if not current_user():

            return jsonify({
                "error": "login_required"
            }), 401

        return fn(*args, **kwargs)

    return wrapper


def pro_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        user = current_user()

        if not user:

            return jsonify({
                "error": "login_required"
            }), 401

        if user["plan"] != "pro":

            return jsonify({
                "error": "pro_subscription_required",
                "message": (
                    "This feature requires an active "
                    "Veya Pro subscription."
                ),
                "upgrade_required": True,
            }), 402

        return fn(*args, **kwargs)

    return wrapper


def get_user_by_id(user_id):

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


# ============================================================
# MODEL CATALOG
#
# IMPORTANT:
# Models are configuration-driven.
#
# To replace a model later:
#
# OPENAI_MODEL_1=gpt-7-new-id
#
# No routing code needs to change.
# ============================================================

MODEL_CATALOG = {

    "openai": {
        "company": "OpenAI",
        "kind": "openai",
        "key": "OPENAI_API_KEY",
        "base": env(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1"
        ),

        "premium": [
            env("OPENAI_MODEL_1", "gpt-6-astra"),
            env("OPENAI_MODEL_2", "gpt-6.1-sol"),
            env("OPENAI_MODEL_3", "gpt-6.1-terra"),
            env("OPENAI_MODEL_4", "gpt-6-luna"),
            env("OPENAI_MODEL_5", "gpt-6-sol"),
        ],

        "free": [
            env("OPENAI_FREE_MODEL", "gpt-5.4-mini")
        ],
    },


    "anthropic": {
        "company": "Anthropic",
        "kind": "anthropic",
        "key": "ANTHROPIC_API_KEY",
        "base": env(
            "ANTHROPIC_BASE_URL",
            "https://api.anthropic.com"
        ),

        "premium": [
            env("ANTHROPIC_MODEL_1", "claude-fable-5-2"),
            env("ANTHROPIC_MODEL_2", "claude-opus-5-5"),
            env("ANTHROPIC_MODEL_3", "claude-sonnet-5-5"),
            env("ANTHROPIC_MODEL_4", "claude-haiku-5-5"),
            env("ANTHROPIC_MODEL_5", ""),
        ],

        "free": [
            env(
                "ANTHROPIC_FREE_MODEL",
                "claude-haiku-5-5"
            )
        ],
    },


    "google": {
        "company": "Google Gemini",
        "kind": "google",
        "key": "GEMINI_API_KEY",
        "base": env(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta"
        ),

        "premium": [
            env("GEMINI_MODEL_1", "gemini-3.8-flash"),
            env("GEMINI_MODEL_2", "gemini-3.6-flash"),
            env(
                "GEMINI_MODEL_3",
                "gemini-3.1-pro-preview"
            ),
            env(
                "GEMINI_MODEL_4",
                "gemini-3.5-flash-lite"
            ),
            env(
                "GEMINI_MODEL_5",
                "gemini-3.1-flash-lite"
            ),
        ],

        "free": [
            env(
                "GEMINI_FREE_MODEL",
                "gemini-3.1-flash-lite"
            )
        ],
    },


    "microsoft": {
        "company": "Microsoft Foundry",
        "kind": "azure",
        "key": "AZURE_OPENAI_API_KEY",
        "base": env(
            "AZURE_OPENAI_ENDPOINT"
        ),

        "premium": [
            env("MICROSOFT_MODEL_1", "gpt-6.1-sol"),
            env("MICROSOFT_MODEL_2", "gpt-6.1-terra"),
            env("MICROSOFT_MODEL_3", "gpt-6-astra"),
            env("MICROSOFT_MODEL_4", "gpt-6-luna"),
            env("MICROSOFT_MODEL_5", "gpt-6-sol"),
        ],

        "free": [
            env(
                "MICROSOFT_FREE_MODEL",
                "gpt-5.4-mini"
            )
        ],
    },


    "nvidia": {
        "company": "NVIDIA NIM",
        "kind": "compatible",
        "key": "NVIDIA_API_KEY",
        "base": env(
            "NVIDIA_BASE_URL",
            "https://integrate.api.nvidia.com/v1"
        ),

        "premium": [
            env(
                "NVIDIA_MODEL_1",
                "nvidia/nemotron-3-ultra-550b-a55b"
            ),
            env(
                "NVIDIA_MODEL_2",
                "nvidia/nemotron-3-super-120b-a12b"
            ),
            env(
                "NVIDIA_MODEL_3",
                "nvidia/nemotron-3.5-super-vl-120b-a12b"
            ),
            env(
                "NVIDIA_MODEL_4",
                "nvidia/nemotron-3.5-lightning"
            ),
            env(
                "NVIDIA_MODEL_5",
                "nvidia/nemotron-3-nano"
            ),
        ],

        "free": [
            env(
                "NVIDIA_FREE_MODEL",
                "nvidia/nemotron-3-nano"
            )
        ],
    },


    "xai": {
        "company": "xAI",
        "kind": "compatible",
        "key": "XAI_API_KEY",
        "base": env(
            "XAI_BASE_URL",
            "https://api.x.ai/v1"
        ),

        "premium": [
            env("XAI_MODEL_1", "grok-4.7"),
            env("XAI_MODEL_2", ""),
            env("XAI_MODEL_3", ""),
            env("XAI_MODEL_4", ""),
            env("XAI_MODEL_5", ""),
        ],

        "free": [
            env("XAI_FREE_MODEL", "")
        ],
    },


    "mistral": {
        "company": "Mistral",
        "kind": "compatible",
        "key": "MISTRAL_API_KEY",
        "base": env(
            "MISTRAL_BASE_URL",
            "https://api.mistral.ai/v1"
        ),

        "premium": [
            env(
                "MISTRAL_MODEL_1",
                "mistral-large-4"
            ),
            env(
                "MISTRAL_MODEL_2",
                "mistral-small-4"
            ),
            env(
                "MISTRAL_MODEL_3",
                "ministral-3-14b"
            ),
            env(
                "MISTRAL_MODEL_4",
                "ministral-3-8b"
            ),
            env(
                "MISTRAL_MODEL_5",
                "ministral-3-3b"
            ),
        ],

        "free": [
            env(
                "MISTRAL_FREE_MODEL",
                "mistral-small-4"
            )
        ],
    },


    "deepseek": {
        "company": "DeepSeek",
        "kind": "compatible",
        "key": "DEEPSEEK_API_KEY",
        "base": env(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com"
        ),

        "premium": [
            env(
                "DEEPSEEK_MODEL_1",
                "deepseek-v4-pro"
            ),
            env(
                "DEEPSEEK_MODEL_2",
                "deepseek-flash"
            ),
            env("DEEPSEEK_MODEL_3", ""),
            env("DEEPSEEK_MODEL_4", ""),
            env("DEEPSEEK_MODEL_5", ""),
        ],

        "free": [
            env(
                "DEEPSEEK_FREE_MODEL",
                "deepseek-flash"
            )
        ],
    },


    # Optional local model.
    # This can be used when you want to reduce
    # external API cost.
    "local": {
        "company": "Local / Ollama",
        "kind": "ollama",
        "key": "",
        "base": env(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434"
        ),

        "premium": [],
        "free": [
            env(
                "OLLAMA_MODEL",
                "qwen3.5:4b"
            )
        ],
    },
}


# ============================================================
# MODEL TAGS
# ============================================================

MODEL_TAGS = {

    "openai": {
        "reasoning",
        "coding",
        "agents",
        "multimodal",
        "computer_use",
    },

    "anthropic": {
        "reasoning",
        "coding",
        "agents",
        "tool_use",
        "vision",
    },

    "google": {
        "reasoning",
        "coding",
        "agents",
        "research",
        "multimodal",
    },

    "microsoft": {
        "reasoning",
        "coding",
        "enterprise",
        "agents",
        "computer_use",
    },

    "nvidia": {
        "reasoning",
        "coding",
        "science",
        "inference",
        "agents",
    },

    "xai": {
        "reasoning",
        "coding",
        "agents",
        "tool_use",
    },

    "mistral": {
        "reasoning",
        "coding",
        "agents",
        "multimodal",
        "tool_use",
    },

    "deepseek": {
        "reasoning",
        "coding",
        "agents",
        "math",
        "tool_use",
    },

    "local": {
        "general",
        "coding",
        "reasoning",
    },
}


# ============================================================
# VEYA AGENT SYSTEM
#
# These are Veya's agents powered by provider models.
# They are NOT falsely claimed to be proprietary hosted
# agents belonging to each company.
# ============================================================

AGENT_ROLES = [
    "Reasoning Agent",
    "Coding Agent",
    "Research Agent",
    "Planning Agent",
    "Verification Agent",
]


AGENT_FIELD_MAP = {

    "Reasoning Agent": [
        "reasoning",
        "general",
    ],

    "Coding Agent": [
        "coding",
    ],

    "Research Agent": [
        "research",
    ],

    "Planning Agent": [
        "planner",
        "general",
    ],

    "Verification Agent": [
        "critic",
        "judge",
        "verification",
    ],
}


# ============================================================
# TASK ROUTING
# ============================================================

KEYWORDS = {

    "coding": [
        "code",
        "coding",
        "python",
        "javascript",
        "typescript",
        "java",
        "rust",
        "programming",
        "debug",
        "bug",
        "software",
        "api",
        "sql",
        "docker",
        "kubernetes",
    ],

    "math": [
        "math",
        "mathematics",
        "calculate",
        "equation",
        "algebra",
        "geometry",
        "calculus",
        "probability",
        "statistics",
    ],

    "science": [
        "physics",
        "chemistry",
        "biology",
        "science",
        "quantum",
        "molecule",
        "atom",
        "experiment",
    ],

    "research": [
        "research",
        "latest",
        "today",
        "current",
        "study",
        "paper",
        "evidence",
        "sources",
        "investigate",
        "news",
        "website",
        "web",
        "search",
    ],

    "writing": [
        "write",
        "rewrite",
        "essay",
        "story",
        "email",
        "letter",
        "article",
        "grammar",
        "translation",
    ],

    "security": [
        "security",
        "cybersecurity",
        "secure",
        "vulnerability",
        "defensive",
        "audit",
    ],

    "enterprise": [
        "enterprise",
        "microsoft",
        "azure",
        "foundry",
        "governance",
    ],
}


FIELD_PRIORITY = {

    "coding": [
        "anthropic",
        "openai",
        "deepseek",
        "google",
        "mistral",
        "xai",
        "nvidia",
    ],

    "math": [
        "openai",
        "deepseek",
        "google",
        "anthropic",
    ],

    "science": [
        "google",
        "openai",
        "anthropic",
        "deepseek",
        "nvidia",
    ],

    "research": [
        "google",
        "openai",
        "anthropic",
        "xai",
        "deepseek",
    ],

    "writing": [
        "anthropic",
        "openai",
        "mistral",
        "google",
    ],

    "security": [
        "anthropic",
        "openai",
        "deepseek",
        "nvidia",
    ],

    "enterprise": [
        "microsoft",
        "openai",
        "nvidia",
        "anthropic",
    ],

    "general": [
        "openai",
        "anthropic",
        "google",
        "xai",
        "deepseek",
        "mistral",
        "nvidia",
    ],
}


def classify_task(text):

    lower = text.lower()

    scores = {
        key: 0
        for key in KEYWORDS
    }

    for field, words in KEYWORDS.items():

        for word in words:

            if word in lower:
                scores[field] += 1

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    fields = [
        field
        for field, score in ranked
        if score > 0
    ]

    return fields or ["general"]


# ============================================================
# ENABLEMENT
# ============================================================

def provider_has_key(provider):

    cfg = MODEL_CATALOG[provider]

    if provider == "local":
        return True

    return bool(
        env(cfg["key"])
    )


def configured_models(
    provider,
    premium=False
):

    cfg = MODEL_CATALOG[provider]

    if not provider_has_key(provider):
        return []

    models = (
        cfg["premium"]
        if premium
        else cfg["free"]
    )

    return [
        model
        for model in models
        if model
    ]


def provider_enabled(
    provider,
    premium=False
):

    return bool(
        configured_models(
            provider,
            premium
        )
    )


# ============================================================
# RESULT
# ============================================================

@dataclass
class ModelResult:

    provider: str
    company: str
    model: str
    text: str
    latency_ms: int
    usage: dict
    success: bool
    error: str = None


# ============================================================
# OPENAI
# ============================================================

class OpenAIAdapter:

    def __init__(self, model):
        self.model = model

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        from openai import OpenAI

        client = OpenAI(
            api_key=env(
                "OPENAI_API_KEY"
            ),
            base_url=env(
                "OPENAI_BASE_URL",
                "https://api.openai.com/v1"
            ),
            timeout=REQUEST_TIMEOUT,
        )

        input_items = []

        if system:

            input_items.append({
                "role": "system",
                "content": system,
            })

        input_items.extend(messages)

        response = client.responses.create(
            model=self.model,
            input=input_items,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        text = getattr(
            response,
            "output_text",
            ""
        ) or ""

        usage_obj = getattr(
            response,
            "usage",
            None
        )

        input_tokens = int(
            getattr(
                usage_obj,
                "input_tokens",
                0
            ) or 0
        )

        output_tokens = int(
            getattr(
                usage_obj,
                "output_tokens",
                0
            ) or 0
        )

        total_tokens = int(
            getattr(
                usage_obj,
                "total_tokens",
                input_tokens + output_tokens
            ) or 0
        )

        return ModelResult(
            provider="openai",
            company="OpenAI",
            model=self.model,
            text=text,
            latency_ms=now_ms() - started,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            success=True,
        )


# ============================================================
# ANTHROPIC
# ============================================================

class AnthropicAdapter:

    def __init__(self, model):
        self.model = model

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        import anthropic

        client = anthropic.Anthropic(
            api_key=env(
                "ANTHROPIC_API_KEY"
            ),
            base_url=env(
                "ANTHROPIC_BASE_URL",
                "https://api.anthropic.com"
            ),
            timeout=REQUEST_TIMEOUT,
        )

        response = client.messages.create(
            model=self.model,
            system=system or "",
            messages=messages,
            max_tokens=MAX_OUTPUT_TOKENS,
        )

        parts = []

        for block in response.content:

            text = getattr(
                block,
                "text",
                None
            )

            if text:
                parts.append(text)

        usage_obj = getattr(
            response,
            "usage",
            None
        )

        input_tokens = int(
            getattr(
                usage_obj,
                "input_tokens",
                0
            ) or 0
        )

        output_tokens = int(
            getattr(
                usage_obj,
                "output_tokens",
                0
            ) or 0
        )

        return ModelResult(
            provider="anthropic",
            company="Anthropic",
            model=self.model,
            text="\n".join(parts),
            latency_ms=now_ms() - started,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": (
                    input_tokens +
                    output_tokens
                ),
            },
            success=True,
        )


# ============================================================
# GOOGLE
# ============================================================

class GoogleAdapter:

    def __init__(self, model):
        self.model = model

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=env(
                "GEMINI_API_KEY"
            )
        )

        contents = []

        for message in messages:

            role = (
                "model"
                if message.get("role")
                == "assistant"
                else "user"
            )

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part(
                            text=str(
                                message.get(
                                    "content",
                                    ""
                                )
                            )
                        )
                    ],
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=(
                system or ""
            ),
            max_output_tokens=(
                MAX_OUTPUT_TOKENS
            ),
        )

        response = (
            client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        )

        text = getattr(
            response,
            "text",
            ""
        ) or ""

        usage_obj = getattr(
            response,
            "usage_metadata",
            None
        )

        input_tokens = int(
            getattr(
                usage_obj,
                "prompt_token_count",
                0
            ) or 0
        )

        output_tokens = int(
            getattr(
                usage_obj,
                "candidates_token_count",
                0
            ) or 0
        )

        total_tokens = int(
            getattr(
                usage_obj,
                "total_token_count",
                input_tokens + output_tokens
            ) or 0
        )

        return ModelResult(
            provider="google",
            company="Google Gemini",
            model=self.model,
            text=text,
            latency_ms=now_ms() - started,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            success=True,
        )


# ============================================================
# OPENAI-COMPATIBLE
# ============================================================

def extract_text(payload):

    if isinstance(
        payload.get("output_text"),
        str
    ):
        return payload["output_text"]

    choices = payload.get(
        "choices"
    ) or []

    if choices:

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content"
        )

        if isinstance(
            content,
            str
        ):
            return content

        if isinstance(
            content,
            list
        ):

            chunks = []

            for item in content:

                if isinstance(
                    item,
                    dict
                ):

                    text = item.get(
                        "text"
                    )

                    if text:
                        chunks.append(text)

            return "\n".join(chunks)

    return ""


def usage_from_payload(payload):

    usage = payload.get(
        "usage"
    ) or {}

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or 0
    )

    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or 0
    )

    total_tokens = (
        usage.get("total_tokens")
        or int(input_tokens)
        + int(output_tokens)
    )

    return {
        "input_tokens": int(
            input_tokens
        ),
        "output_tokens": int(
            output_tokens
        ),
        "total_tokens": int(
            total_tokens
        ),
    }


class CompatibleAdapter:

    def __init__(
        self,
        provider,
        model
    ):

        self.provider = provider
        self.model = model
        self.cfg = MODEL_CATALOG[
            provider
        ]

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        final_messages = []

        if system:

            final_messages.append({
                "role": "system",
                "content": system,
            })

        final_messages.extend(
            messages
        )

        url = (
            self.cfg["base"].rstrip("/")
            + "/chat/completions"
        )

        response = requests.post(
            url,
            headers={
                "Authorization": (
                    "Bearer "
                    + env(
                        self.cfg["key"]
                    )
                ),
                "Content-Type":
                    "application/json",
            },
            json={
                "model": self.model,
                "messages": final_messages,
                "max_tokens":
                    MAX_OUTPUT_TOKENS,
            },
            timeout=REQUEST_TIMEOUT,
        )

        data = (
            response.json()
            if response.content
            else {}
        )

        if not response.ok:

            raise RuntimeError(
                f"{self.cfg['company']} "
                f"{self.model} "
                f"HTTP {response.status_code}: "
                f"{truncate(data, 3000)}"
            )

        return ModelResult(
            provider=self.provider,
            company=self.cfg["company"],
            model=self.model,
            text=extract_text(data),
            latency_ms=(
                now_ms() - started
            ),
            usage=usage_from_payload(
                data
            ),
            success=True,
        )


# ============================================================
# MICROSOFT
# ============================================================

class MicrosoftAdapter:

    def __init__(self, model):
        self.model = model

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        endpoint = env(
            "AZURE_OPENAI_ENDPOINT"
        ).rstrip("/")

        if not endpoint:

            raise RuntimeError(
                "AZURE_OPENAI_ENDPOINT missing"
            )

        url = (
            endpoint
            + "/openai/v1/chat/completions"
        )

        final_messages = []

        if system:

            final_messages.append({
                "role": "system",
                "content": system,
            })

        final_messages.extend(
            messages
        )

        response = requests.post(
            url,
            headers={
                "api-key": env(
                    "AZURE_OPENAI_API_KEY"
                ),
                "Content-Type":
                    "application/json",
            },
            json={
                "model": self.model,
                "messages": final_messages,
                "max_tokens":
                    MAX_OUTPUT_TOKENS,
            },
            timeout=REQUEST_TIMEOUT,
        )

        data = (
            response.json()
            if response.content
            else {}
        )

        if not response.ok:

            raise RuntimeError(
                f"Microsoft Foundry "
                f"{self.model} "
                f"HTTP {response.status_code}: "
                f"{truncate(data, 3000)}"
            )

        return ModelResult(
            provider="microsoft",
            company="Microsoft Foundry",
            model=self.model,
            text=extract_text(data),
            latency_ms=(
                now_ms() - started
            ),
            usage=usage_from_payload(
                data
            ),
            success=True,
        )


# ============================================================
# OLLAMA
# ============================================================

class OllamaAdapter:

    def __init__(self, model):
        self.model = model

    def generate(
        self,
        messages,
        system
    ):

        started = now_ms()

        final_messages = []

        if system:

            final_messages.append({
                "role": "system",
                "content": system,
            })

        final_messages.extend(
            messages
        )

        url = (
            env(
                "OLLAMA_BASE_URL",
                "http://127.0.0.1:11434"
            ).rstrip("/")
            + "/api/chat"
        )

        response = requests.post(
            url,
            json={
                "model": self.model,
                "messages": final_messages,
                "stream": False,
            },
            timeout=REQUEST_TIMEOUT,
        )

        data = response.json()

        if not response.ok:

            raise RuntimeError(
                f"Ollama HTTP "
                f"{response.status_code}: "
                f"{truncate(data, 3000)}"
            )

        message = data.get(
            "message",
            {}
        )

        return ModelResult(
            provider="local",
            company="Local / Ollama",
            model=self.model,
            text=message.get(
                "content",
                ""
            ),
            latency_ms=(
                now_ms() - started
            ),
            usage={
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            success=True,
        )


# ============================================================
# FACTORY
# ============================================================

def call_model(
    provider,
    model,
    messages,
    system
):

    try:

        if provider == "openai":

            adapter = OpenAIAdapter(
                model
            )

        elif provider == "anthropic":

            adapter = AnthropicAdapter(
                model
            )

        elif provider == "google":

            adapter = GoogleAdapter(
                model
            )

        elif provider == "microsoft":

            adapter = MicrosoftAdapter(
                model
            )

        elif provider == "local":

            adapter = OllamaAdapter(
                model
            )

        elif provider in {
            "nvidia",
            "xai",
            "mistral",
            "deepseek",
        }:

            adapter = CompatibleAdapter(
                provider,
                model
            )

        else:

            raise RuntimeError(
                f"Unsupported provider: "
                f"{provider}"
            )

        return adapter.generate(
            messages,
            system
        )

    except Exception as exc:

        return ModelResult(
            provider=provider,
            company=MODEL_CATALOG[
                provider
            ]["company"],
            model=model,
            text="",
            latency_ms=0,
            usage={
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            success=False,
            error=str(exc),
        )


# ============================================================
# WEB RESEARCH
# ============================================================

WEB_SEARCH_ENABLED = bool_env(
    "WEB_SEARCH_ENABLED",
    True
)

WEB_SEARCH_PROVIDER = env(
    "WEB_SEARCH_PROVIDER",
    "serper"
)

WEB_SEARCH_TIMEOUT = int(
    env(
        "WEB_SEARCH_TIMEOUT",
        "20"
    )
)

MAX_SEARCH_RESULTS = int(
    env(
        "MAX_SEARCH_RESULTS",
        "5"
    )
)

MAX_FETCHED_PAGES = int(
    env(
        "MAX_FETCHED_PAGES",
        "4"
    )
)


def search_web(query):

    if not WEB_SEARCH_ENABLED:
        return []

    provider = WEB_SEARCH_PROVIDER.lower()

    if provider == "serper":

        key = env(
            "SERPER_API_KEY"
        )

        if not key:
            return []

        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": key,
                "Content-Type":
                    "application/json",
            },
            json={
                "q": query,
                "num": MAX_SEARCH_RESULTS,
            },
            timeout=WEB_SEARCH_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get(
            "organic",
            []
        )[:MAX_SEARCH_RESULTS]:

            results.append({
                "title": item.get(
                    "title",
                    ""
                ),
                "url": item.get(
                    "link",
                    ""
                ),
                "snippet": item.get(
                    "snippet",
                    ""
                ),
            })

        return results

    if provider == "tavily":

        key = env(
            "TAVILY_API_KEY"
        )

        if not key:
            return []

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "max_results":
                    MAX_SEARCH_RESULTS,
                "search_depth": "advanced",
            },
            timeout=WEB_SEARCH_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        return [
            {
                "title": item.get(
                    "title",
                    ""
                ),
                "url": item.get(
                    "url",
                    ""
                ),
                "snippet": item.get(
                    "content",
                    ""
                ),
            }
            for item in data.get(
                "results",
                []
            )[:MAX_SEARCH_RESULTS]
        ]

    return []


def allowed_url(url):

    try:

        parsed = urlparse(url)

        return parsed.scheme in {
            "http",
            "https",
        }

    except Exception:

        return False


def robots_allowed(url):

    try:

        parsed = urlparse(url)

        robots_url = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}/robots.txt"
        )

        rp = urllib.robotparser.RobotFileParser()

        rp.set_url(
            robots_url
        )

        rp.read()

        return rp.can_fetch(
            "VeyaBot/1.0",
            url
        )

    except Exception:

        return True


def fetch_page(url):

    if not allowed_url(url):
        return None

    if not robots_allowed(url):
        return None

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                    "VeyaBot/1.0"
            },
            timeout=WEB_SEARCH_TIMEOUT,
            allow_redirects=True,
        )

        if not response.ok:
            return None

        content_type = response.headers.get(
            "content-type",
            ""
        ).lower()

        if "text/html" not in content_type:
            return None

        html = response.text[:2_000_000]

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
        ]):

            tag.decompose()

        text = soup.get_text(
            "\n",
            strip=True
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return truncate(
            text,
            18000
        )

    except Exception:

        return None


def web_research(query):

    results = search_web(
        query
    )

    if not results:
        return {
            "results": [],
            "sources_text": "",
        }

    fetched = []

    for result in results:

        if len(fetched) >= MAX_FETCHED_PAGES:
            break

        page_text = fetch_page(
            result["url"]
        )

        fetched.append({
            **result,
            "page_text": page_text or "",
        })

    source_blocks = []

    for item in fetched:

        source_blocks.append(
            f"""
SOURCE:
{item['title']}
URL:
{item['url']}

SEARCH SNIPPET:
{item['snippet']}

PAGE CONTENT:
{truncate(item['page_text'], 12000)}
"""
        )

    return {
        "results": fetched,
        "sources_text": "\n".join(
            source_blocks
        ),
    }


# ============================================================
# SYSTEM PROMPT
# ============================================================

BASE_SYSTEM = """
You are Veya, a multi-model AI orchestration platform.

You are one specialist in a larger AI network.

Rules:

- Be accurate.
- Never fabricate facts.
- Never fabricate citations.
- Distinguish facts from assumptions.
- Do not claim a website was visited unless it was actually fetched.
- Do not claim a search was performed unless the web-search layer actually ran.
- Use supplied web sources when available.
- Prefer recent information for current questions.
- Verify calculations.
- Never expose API keys or secrets.
- Answer in the user's language.
"""


def build_system(
    fields,
    web_context=""
):

    parts = [
        BASE_SYSTEM
    ]

    if "coding" in fields:

        parts.append(
            """
Act as a senior software engineer.
Prioritize correctness, security,
maintainability and production readiness.
"""
        )

    if "math" in fields:

        parts.append(
            """
Act as an expert mathematician.
Check calculations carefully.
"""
        )

    if "science" in fields:

        parts.append(
            """
Use scientific reasoning.
Separate established facts from uncertainty.
"""
        )

    if "research" in fields:

        parts.append(
            """
Act as a research specialist.
Compare sources and identify contradictions.
"""
        )

    if "security" in fields:

        parts.append(
            """
Focus on defensive cybersecurity,
secure design and remediation.
"""
        )

    if "writing" in fields:

        parts.append(
            """
Act as an expert writer and editor.
"""
        )

    if web_context:

        parts.append(
            f"""
WEB RESEARCH RESULTS:

{web_context}

Use these sources when relevant.
Do not invent information beyond them.
When mentioning a source, identify it clearly.
"""
        )

    return "\n\n".join(
        parts
    )


# ============================================================
# MODEL SELECTION
# ============================================================

def select_models(
    fields,
    premium
):

    max_calls = (
        PRO_MAX_MODEL_CALLS
        if premium
        else FREE_MAX_MODEL_CALLS
    )

    candidates = []

    if premium:

        for field in fields:

            for provider in FIELD_PRIORITY.get(
                field,
                FIELD_PRIORITY["general"]
            ):

                if not provider_enabled(
                    provider,
                    premium=True
                ):
                    continue

                models = configured_models(
                    provider,
                    premium=True
                )

                if models:

                    # Use the best configured
                    # model for that provider first.
                    candidates.append({
                        "provider": provider,
                        "model": models[0],
                    })

    else:

        # Cheap/free path:
        # choose one configured low-cost
        # model rather than fanning out
        # across expensive models.

        for provider in [
            "local",
            "google",
            "deepseek",
            "mistral",
            "anthropic",
            "openai",
            "microsoft",
            "nvidia",
            "xai",
        ]:

            if not provider_enabled(
                provider,
                premium=False
            ):
                continue

            models = configured_models(
                provider,
                premium=False
            )

            if models:

                candidates.append({
                    "provider": provider,
                    "model": models[0],
                })

    unique = []

    seen = set()

    for item in candidates:

        key = (
            item["provider"],
            item["model"]
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique[:max_calls]


# ============================================================
# EXECUTION
# ============================================================

def run_models(
    models,
    messages,
    system
):

    if not models:
        return []

    results = []

    workers = min(
        len(models),
        PRO_MAX_MODEL_CALLS
    )

    with ThreadPoolExecutor(
        max_workers=max(
            1,
            workers
        )
    ) as executor:

        futures = {
            executor.submit(
                call_model,
                item["provider"],
                item["model"],
                messages,
                system,
            ): item
            for item in models
        }

        for future in as_completed(
            futures
        ):

            item = futures[future]

            try:

                result = future.result()

            except Exception as exc:

                result = ModelResult(
                    provider=item[
                        "provider"
                    ],
                    company=MODEL_CATALOG[
                        item["provider"]
                    ]["company"],
                    model=item[
                        "model"
                    ],
                    text="",
                    latency_ms=0,
                    usage={
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                    },
                    success=False,
                    error=str(exc),
                )

            results.append(
                result
            )

    return results


# ============================================================
# JUDGE
# ============================================================

def choose_judge(results):

    priority = [
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "xai",
        "mistral",
        "microsoft",
        "nvidia",
    ]

    for provider in priority:

        for result in results:

            if (
                result.success
                and result.provider
                == provider
            ):

                return result

    return None


def judge_results(
    question,
    results,
    premium
):

    successful = [
        result
        for result in results
        if result.success
        and result.text.strip()
    ]

    if not successful:
        return None

    if len(successful) == 1:
        return successful[0]

    reports = []

    for result in successful:

        reports.append(
            f"""
MODEL:
{result.model}

COMPANY:
{result.company}

ANSWER:
{truncate(result.text, 7000)}
"""
        )

    judge = choose_judge(
        successful
    )

    if not judge:
        return successful[0]

    prompt = f"""
You are Veya's final verification judge.

USER QUESTION:
{question}

CANDIDATE ANSWERS:
{"".join(reports)}

Compare the answers.

Resolve contradictions.
Prefer accurate reasoning.
Do not blindly vote.
Do not invent evidence.

Return one final answer.
"""

    final = call_model(
        judge.provider,
        judge.model,
        [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        BASE_SYSTEM,
    )

    return (
        final
        if final.success
        else successful[0]
    )


# ============================================================
# CHAT STORAGE
# ============================================================

def create_chat(
    user_id,
    title
):

    chat_id = str(
        uuid.uuid4()
    )

    with DB_LOCK:

        conn = db()

        conn.execute(
            """
            INSERT INTO chats
            (
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
                title[:100],
                utc_now(),
                utc_now(),
            ),
        )

        conn.commit()
        conn.close()

    return chat_id


def get_chat(
    user_id,
    chat_id
):

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM chats
        WHERE id = ?
        AND user_id = ?
        """,
        (
            chat_id,
            user_id,
        ),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def save_message(
    user_id,
    chat_id,
    role,
    content
):

    with DB_LOCK:

        conn = db()

        conn.execute(
            """
            INSERT INTO messages
            (
                chat_id,
                user_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                user_id,
                role,
                content,
                utc_now(),
            ),
        )

        conn.execute(
            """
            UPDATE chats
            SET updated_at = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                utc_now(),
                chat_id,
                user_id,
            ),
        )

        conn.commit()
        conn.close()


def get_messages(
    user_id,
    chat_id
):

    conn = db()

    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        AND user_id = ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (
            chat_id,
            user_id,
            MAX_HISTORY,
        ),
    ).fetchall()

    conn.close()

    return [
        {
            "role": row["role"],
            "content": row["content"],
        }
        for row in rows
    ]


# ============================================================
# AUTH API
# ============================================================

@app.post("/api/auth/signup")
def signup():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip().lower()

    password = str(
        data.get(
            "password",
            ""
        )
    )

    if not email or "@" not in email:

        return jsonify({
            "error": "valid email required"
        }), 400

    if len(password) < 8:

        return jsonify({
            "error": (
                "password must contain "
                "at least 8 characters"
            )
        }), 400

    password_hash = (
        generate_password_hash(
            password
        )
    )

    try:

        with DB_LOCK:

            conn = db()

            cursor = conn.execute(
                """
                INSERT INTO users
                (
                    email,
                    password_hash,
                    plan,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, 'free', ?, ?)
                """,
                (
                    email,
                    password_hash,
                    utc_now(),
                    utc_now(),
                ),
            )

            user_id = cursor.lastrowid

            conn.commit()
            conn.close()

        session["user_id"] = user_id
        session.permanent = True

        return jsonify({
            "success": True
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "error": "email already registered"
        }), 409


@app.post("/api/auth/login")
def login():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip().lower()

    password = str(
        data.get(
            "password",
            ""
        )
    )

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    conn.close()

    if (
        not row
        or not check_password_hash(
            row["password_hash"],
            password
        )
    ):

        return jsonify({
            "error": "invalid credentials"
        }), 401

    session["user_id"] = row["id"]
    session.permanent = True

    return jsonify({
        "success": True
    })


@app.post("/api/auth/logout")
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


@app.get("/api/auth/me")
def me():

    user = current_user()

    if not user:

        return jsonify({
            "authenticated": False
        })

    return jsonify({
        "authenticated": True,
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "pro": user["plan"] == "pro",
    })


# ============================================================
# STRIPE
# ============================================================

STRIPE_SECRET_KEY = env(
    "STRIPE_SECRET_KEY"
)

STRIPE_WEBHOOK_SECRET = env(
    "STRIPE_WEBHOOK_SECRET"
)

STRIPE_PRICE_ID = env(
    "STRIPE_PRICE_ID"
)

PUBLIC_BASE_URL = env(
    "PUBLIC_BASE_URL",
    "http://localhost:10000"
)


if stripe and STRIPE_SECRET_KEY:

    stripe.api_key = (
        STRIPE_SECRET_KEY
    )


def set_user_subscription(
    user_id,
    plan,
    customer_id=None,
    subscription_id=None
):

    with DB_LOCK:

        conn = db()

        conn.execute(
            """
            UPDATE users
            SET
                plan = ?,
                stripe_customer_id =
                    COALESCE(?, stripe_customer_id),
                stripe_subscription_id =
                    COALESCE(
                        ?,
                        stripe_subscription_id
                    ),
                updated_at = ?
            WHERE id = ?
            """,
            (
                plan,
                customer_id,
                subscription_id,
                utc_now(),
                user_id,
            ),
        )

        conn.commit()
        conn.close()


@app.post("/api/billing/checkout")
@login_required
def create_checkout():

    if not stripe:

        return jsonify({
            "error": (
                "Stripe package is not installed."
            )
        }), 500

    if not STRIPE_SECRET_KEY:

        return jsonify({
            "error": (
                "STRIPE_SECRET_KEY is not configured."
            )
        }), 500

    if not STRIPE_PRICE_ID:

        return jsonify({
            "error": (
                "STRIPE_PRICE_ID is not configured."
            )
        }), 500

    user = current_user()

    if user["plan"] == "pro":

        return jsonify({
            "error": "already_pro"
        }), 400

    checkout = stripe.checkout.Session.create(

        mode="subscription",

        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],

        customer_email=user["email"],

        client_reference_id=str(
            user["id"]
        ),

        metadata={
            "user_id": str(
                user["id"]
            ),
            "plan": "pro",
        },

        success_url=(
            PUBLIC_BASE_URL
            + "/?payment=success"
        ),

        cancel_url=(
            PUBLIC_BASE_URL
            + "/?payment=cancelled"
        ),
    )

    return jsonify({
        "url": checkout.url
    })


@app.post("/api/billing/portal")
@login_required
def billing_portal():

    if not stripe:

        return jsonify({
            "error": "Stripe unavailable"
        }), 500

    user = current_user()

    customer_id = (
        user["stripe_customer_id"]
    )

    if not customer_id:

        return jsonify({
            "error": (
                "No Stripe customer found."
            )
        }), 400

    portal = (
        stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=PUBLIC_BASE_URL,
        )
    )

    return jsonify({
        "url": portal.url
    })


@app.post("/api/billing/webhook")
def stripe_webhook():

    if not stripe:

        return "Stripe unavailable", 500

    payload = request.data

    signature = request.headers.get(
        "Stripe-Signature"
    )

    try:

        event = (
            stripe.Webhook.construct_event(
                payload,
                signature,
                STRIPE_WEBHOOK_SECRET,
            )
        )

    except Exception as exc:

        return (
            f"Webhook verification failed: "
            f"{exc}",
            400,
        )

    event_id = event.get(
        "id"
    )

    if event_id:

        with DB_LOCK:

            conn = db()

            exists = conn.execute(
                """
                SELECT id
                FROM webhook_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()

            if exists:

                conn.close()

                return jsonify({
                    "received": True
                })

            conn.execute(
                """
                INSERT INTO webhook_events
                (
                    id,
                    created_at
                )
                VALUES (?, ?)
                """,
                (
                    event_id,
                    utc_now(),
                ),
            )

            conn.commit()
            conn.close()

    event_type = event.get(
        "type",
        ""
    )

    obj = (
        event.get(
            "data",
            {}
        ).get(
            "object",
            {}
        )
    )

    if event_type == (
        "checkout.session.completed"
    ):

        user_id = (
            obj.get(
                "metadata",
                {}
            ).get(
                "user_id"
            )
            or obj.get(
                "client_reference_id"
            )
        )

        if user_id:

            set_user_subscription(
                int(user_id),
                "pro",
                obj.get(
                    "customer"
                ),
                obj.get(
                    "subscription"
                ),
            )

    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:

        customer_id = obj.get(
            "customer"
        )

        status = obj.get(
            "status",
            ""
        )

        active = status in {
            "active",
            "trialing",
        }

        conn = db()

        row = conn.execute(
            """
            SELECT id
            FROM users
            WHERE stripe_customer_id = ?
            """,
            (customer_id,),
        ).fetchone()

        conn.close()

        if row:

            set_user_subscription(
                row["id"],
                "pro" if active else "free",
                customer_id,
                obj.get("id"),
            )

    return jsonify({
        "received": True
    })


# ============================================================
# CHAT API
# ============================================================

@app.post("/api/chat")
@login_required
def chat():

    started = now_ms()

    try:

        user = current_user()

        is_pro = (
            user["plan"] == "pro"
        )

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        user_text = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        if not user_text:

            return jsonify({
                "error": "message is required"
            }), 400

        if len(user_text) > MAX_INPUT_CHARS:

            return jsonify({
                "error": "message too long"
            }), 413

        chat_id = str(
            data.get(
                "chat_id",
                ""
            )
        ).strip()

        if chat_id:

            chat = get_chat(
                user["id"],
                chat_id
            )

            if not chat:

                return jsonify({
                    "error": "chat not found"
                }), 404

        else:

            title = (
                user_text[:80]
                .replace("\n", " ")
            )

            chat_id = create_chat(
                user["id"],
                title
            )

        history = get_messages(
            user["id"],
            chat_id
        )

        messages = (
            history
            + [
                {
                    "role": "user",
                    "content": user_text,
                }
            ]
        )

        fields = classify_task(
            user_text
        )

        needs_web = (
            "research" in fields
            or any(
                word in user_text.lower()
                for word in [
                    "latest",
                    "today",
                    "current",
                    "search",
                    "website",
                    "news",
                    "source",
                    "web",
                ]
            )
        )

        web_data = {
            "results": [],
            "sources_text": "",
        }

        if needs_web:

            web_data = web_research(
                user_text
            )

        system = build_system(
            fields,
            web_data["sources_text"]
        )

        selected = select_models(
            fields,
            premium=is_pro
        )

        if not selected:

            return jsonify({
                "error": (
                    "No configured models "
                    "are available."
                )
            }), 503

        results = run_models(
            selected,
            messages,
            system
        )

        final_result = judge_results(
            user_text,
            results,
            premium=is_pro
        )

        if not final_result:

            return jsonify({
                "error": (
                    "All configured models failed."
                ),
                "models": [
                    asdict(result)
                    for result in results
                ],
            }), 502

        answer = (
            final_result.text.strip()
        )

        save_message(
            user["id"],
            chat_id,
            "user",
            user_text
        )

        save_message(
            user["id"],
            chat_id,
            "assistant",
            answer
        )

        successful = [
            result
            for result in results
            if result.success
        ]

        return jsonify({

            "app": APP_NAME,
            "version": APP_VERSION,

            "chat_id": chat_id,

            "answer": answer,

            "plan": (
                "pro"
                if is_pro
                else "free"
            ),

            "routing": {

                "fields": fields,

                "web_research": bool(
                    web_data["results"]
                ),

                "selected_models":
                    selected,

                "successful_models": [
                    {
                        "provider":
                            result.provider,
                        "company":
                            result.company,
                        "model":
                            result.model,
                    }
                    for result in successful
                ],

                "judge": {
                    "provider":
                        final_result.provider,
                    "model":
                        final_result.model,
                },
            },

            "sources": [
                {
                    "title":
                        item["title"],
                    "url":
                        item["url"],
                    "snippet":
                        item["snippet"],
                }
                for item
                in web_data["results"]
            ],

            "models": [
                asdict(result)
                for result in results
            ],

            "total_latency_ms":
                now_ms() - started,
        })

    except Exception as exc:

        traceback.print_exc()

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/api/chats")
@login_required
def chats():

    user = current_user()

    conn = db()

    rows = conn.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM chats
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user["id"],),
    ).fetchall()

    conn.close()

    return jsonify({
        "chats": [
            dict(row)
            for row in rows
        ]
    })


@app.get("/api/chats/<chat_id>")
@login_required
def chat_detail(chat_id):

    user = current_user()

    chat = get_chat(
        user["id"],
        chat_id
    )

    if not chat:

        return jsonify({
            "error": "chat not found"
        }), 404

    return jsonify({
        "chat": chat,
        "messages": get_messages(
            user["id"],
            chat_id
        ),
    })


@app.delete("/api/chats/<chat_id>")
@login_required
def delete_chat(chat_id):

    user = current_user()

    with DB_LOCK:

        conn = db()

        conn.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user["id"],
            ),
        )

        conn.execute(
            """
            DELETE FROM chats
            WHERE id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user["id"],
            ),
        )

        conn.commit()
        conn.close()

    return jsonify({
        "success": True
    })


# ============================================================
# PROVIDERS / MODELS / AGENTS
# ============================================================

@app.get("/api/providers")
def providers():

    output = {}

    for provider_id, cfg in MODEL_CATALOG.items():

        premium_models = configured_models(
            provider_id,
            premium=True
        )

        free_models = configured_models(
            provider_id,
            premium=False
        )

        output[provider_id] = {

            "company":
                cfg["company"],

            "premium_enabled":
                bool(premium_models),

            "free_enabled":
                bool(free_models),

            "premium_models":
                premium_models,

            "free_models":
                free_models,

            "tags":
                sorted(
                    MODEL_TAGS.get(
                        provider_id,
                        set()
                    )
                ),
        }

    return jsonify(output)


@app.get("/api/models")
def models():

    user = current_user()

    is_pro = bool(
        user
        and user["plan"] == "pro"
    )

    output = []

    for provider_id, cfg in MODEL_CATALOG.items():

        models = configured_models(
            provider_id,
            premium=is_pro
        )

        for model in models:

            output.append({
                "provider":
                    provider_id,

                "company":
                    cfg["company"],

                "model":
                    model,

                "tier":
                    "premium"
                    if is_pro
                    else "free",

                "tags":
                    sorted(
                        MODEL_TAGS.get(
                            provider_id,
                            set()
                        )
                    ),
            })

    return jsonify({
        "tier":
            "pro"
            if is_pro
            else "free",

        "count":
            len(output),

        "models":
            output,
    })


@app.get("/api/agents")
def agents():

    user = current_user()

    is_pro = bool(
        user
        and user["plan"] == "pro"
    )

    registry = []

    for provider_id, cfg in MODEL_CATALOG.items():

        models = configured_models(
            provider_id,
            premium=is_pro
        )

        for index, role in enumerate(
            AGENT_ROLES
        ):

            model = (
                models[index]
                if index < len(models)
                else None
            )

            registry.append({

                "agent":
                    role,

                "provider":
                    provider_id,

                "company":
                    cfg["company"],

                "model":
                    model,

                "available":
                    bool(model),

                "tier":
                    "pro"
                    if is_pro
                    else "free",
            })

    return jsonify({
        "tier":
            "pro"
            if is_pro
            else "free",

        "agents":
            registry,
    })


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    user = current_user()

    return jsonify({

        "app":
            APP_NAME,

        "version":
            APP_VERSION,

        "status":
            "ok",

        "authenticated":
            bool(user),

        "plan":
            user["plan"]
            if user
            else "anonymous",

        "premium_billing":
            bool(
                STRIPE_SECRET_KEY
                and STRIPE_PRICE_ID
            ),

        "web_search":
            WEB_SEARCH_ENABLED,

        "database":
            DB_PATH,
    })


# ============================================================
# FRONTEND
# ============================================================

HTML = r"""
<!doctype html>

<html>

<head>

<meta charset="utf-8">

<meta
name="viewport"
content="width=device-width,initial-scale=1"
/>

<title>Veya AI</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: #09090b;
    color: #f4f4f5;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

button,
textarea,
input {
    font: inherit;
}

button {
    cursor: pointer;
}

.app {
    height: 100vh;
    display: flex;
}

.sidebar {
    width: 290px;
    background: #0c0c0f;
    border-right: 1px solid #27272a;
    display: flex;
    flex-direction: column;
    transition: .2s;
    z-index: 20;
}

.sidebar.hidden {
    width: 0;
    overflow: hidden;
    border: 0;
}

.sidebar-top {
    padding: 16px;
    border-bottom: 1px solid #27272a;
}

.brand {
    font-size: 22px;
    font-weight: 800;
}

.plan-badge {
    margin-top: 8px;
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    background: #18181b;
    color: #a1a1aa;
    font-size: 11px;
}

.history {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
}

.chat-item {
    width: 100%;
    border: 0;
    background: transparent;
    color: #d4d4d8;
    text-align: left;
    padding: 11px;
    border-radius: 10px;
    margin-bottom: 4px;
}

.chat-item:hover {
    background: #18181b;
}

.sidebar-bottom {
    padding: 12px;
    border-top: 1px solid #27272a;
}

.small-button {
    width: 100%;
    padding: 10px;
    border: 1px solid #3f3f46;
    background: #18181b;
    color: white;
    border-radius: 10px;
    margin-bottom: 7px;
}

.main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.header {
    height: 62px;
    border-bottom: 1px solid #27272a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px;
}

.left-header {
    display: flex;
    align-items: center;
    gap: 10px;
}

.menu {
    width: 42px;
    height: 42px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: white;
    font-size: 24px;
}

.menu:hover {
    background: #18181b;
}

.title {
    font-weight: 700;
}

.upgrade {
    border: 0;
    border-radius: 999px;
    padding: 10px 16px;
    background: white;
    color: black;
    font-weight: 800;
}

.upgrade.pro {
    background: #18181b;
    color: white;
    border: 1px solid #3f3f46;
}

.chat {
    flex: 1;
    overflow-y: auto;
    padding: 30px 16px 150px;
}

.messages {
    max-width: 900px;
    margin: auto;
}

.empty {
    text-align: center;
    margin-top: 15vh;
}

.empty h1 {
    font-size: 42px;
    margin-bottom: 8px;
}

.empty p {
    color: #a1a1aa;
}

.message {
    display: flex;
    gap: 12px;
    margin: 28px 0;
}

.avatar {
    width: 34px;
    height: 34px;
    min-width: 34px;
    display: grid;
    place-items: center;
    border-radius: 10px;
    background: #18181b;
    font-size: 11px;
    font-weight: 800;
}

.user .avatar {
    background: white;
    color: black;
}

.content {
    line-height: 1.72;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.user .content {
    background: #18181b;
    padding: 11px 14px;
    border-radius: 14px;
}

.meta {
    color: #71717a;
    font-size: 10px;
    margin-top: 7px;
}

.sources {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.source {
    color: #a1a1aa;
    font-size: 11px;
    text-decoration: none;
}

.source:hover {
    color: white;
}

.composer-wrap {
    position: fixed;
    left: 290px;
    right: 0;
    bottom: 0;
    padding: 18px;
    background:
        linear-gradient(
            transparent,
            #09090b 35%
        );
}

.sidebar.hidden ~ .main .composer-wrap {
    left: 0;
}

.composer {
    max-width: 900px;
    margin: auto;
    background: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 18px;
    padding: 9px;
    display: flex;
    gap: 8px;
}

textarea {
    flex: 1;
    resize: none;
    min-height: 50px;
    max-height: 180px;
    outline: 0;
    border: 0;
    background: transparent;
    color: white;
    padding: 10px;
}

.send {
    width: 45px;
    height: 45px;
    border: 0;
    border-radius: 12px;
    background: white;
    color: black;
    font-weight: 900;
}

.overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.7);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
    padding: 18px;
}

.modal {
    width: min(460px, 100%);
    background: #111113;
    border: 1px solid #3f3f46;
    border-radius: 22px;
    padding: 24px;
}

.modal h2 {
    margin-top: 0;
}

.modal input {
    width: 100%;
    margin: 7px 0;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #3f3f46;
    background: #18181b;
    color: white;
    outline: 0;
}

.modal button {
    width: 100%;
    margin-top: 9px;
    padding: 12px;
    border: 0;
    border-radius: 10px;
}

.primary {
    background: white;
    color: black;
    font-weight: 800;
}

.secondary {
    background: #18181b;
    color: white;
    border: 1px solid #3f3f46 !important;
}

.pro-card {
    border: 1px solid #3f3f46;
    border-radius: 18px;
    padding: 18px;
    background:
        linear-gradient(
            145deg,
            #18181b,
            #0f0f11
        );
}

.pro-card strong {
    font-size: 25px;
}

.pro-list {
    color: #d4d4d8;
    line-height: 1.8;
    padding-left: 20px;
}

@media(max-width:760px) {

    .sidebar {
        position: fixed;
        top: 0;
        bottom: 0;
        left: 0;
    }

    .sidebar.hidden {
        width: 0;
    }

    .composer-wrap {
        left: 0;
    }

    .empty h1 {
        font-size: 30px;
    }
}

</style>

</head>

<body>

<div class="app">

<aside
class="sidebar"
id="sidebar"
>

<div class="sidebar-top">

<div class="brand">
Veya
</div>

<div
class="plan-badge"
id="planBadge"
>
Free
</div>

</div>

<div
class="history"
id="history"
></div>

<div class="sidebar-bottom">

<button
class="small-button"
onclick="newChat()"
>
＋ New chat
</button>

<button
class="small-button"
onclick="openAccount()"
>
Account
</button>

</div>

</aside>

<main class="main">

<header class="header">

<div class="left-header">

<button
class="menu"
onclick="toggleSidebar()"
>
☰
</button>

<div class="title">
Veya
</div>

</div>

<button
id="upgradeButton"
class="upgrade"
onclick="openUpgrade()"
>
Upgrade
</button>

</header>

<section
class="chat"
id="chat"
>

<div
class="empty"
id="empty"
>

<h1>
What can I help with?
</h1>

<p>
Ask Veya anything.
</p>

</div>

<div
class="messages"
id="messages"
></div>

</section>

<div class="composer-wrap">

<form
class="composer"
onsubmit="sendMessage(event)"
>

<textarea
id="input"
placeholder="Message Veya..."
></textarea>

<button
class="send"
type="submit"
>
↑
</button>

</form>

</div>

</main>

</div>


<!-- AUTH -->

<div
class="overlay"
id="authModal"
>

<div class="modal">

<h2>
Login to Veya
</h2>

<input
id="authEmail"
type="email"
placeholder="Email"
/>

<input
id="authPassword"
type="password"
placeholder="Password"
/>

<button
class="primary"
onclick="login()"
>
Login
</button>

<button
class="secondary"
onclick="signup()"
>
Create account
</button>

<button
class="secondary"
onclick="closeModals()"
>
Close
</button>

</div>

</div>


<!-- UPGRADE -->

<div
class="overlay"
id="upgradeModal"
>

<div class="modal">

<div class="pro-card">

<h2>
Veya Pro
</h2>

<strong>
$20 / month
</strong>

<ul class="pro-list">

<li>
Premium model routing
</li>

<li>
Advanced multi-model reasoning
</li>

<li>
Veya verification/judge layer
</li>

<li>
Advanced research mode
</li>

<li>
Web research and source collection
</li>

<li>
Premium agent network
</li>

<li>
Persistent chat history
</li>

</ul>

<button
class="primary"
onclick="startCheckout()"
>
Upgrade to Pro
</button>

<button
class="secondary"
onclick="closeModals()"
>
Not now
</button>

</div>

</div>

</div>


<!-- ACCOUNT -->

<div
class="overlay"
id="accountModal"
>

<div class="modal">

<h2>
Account
</h2>

<div id="accountInfo"></div>

<button
class="primary"
onclick="manageBilling()"
>
Manage subscription
</button>

<button
class="secondary"
onclick="logout()"
>
Log out
</button>

<button
class="secondary"
onclick="closeModals()"
>
Close
</button>

</div>

</div>


<script>

let currentChatId = null;
let isPro = false;


function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function toggleSidebar() {

    document
        .getElementById("sidebar")
        .classList.toggle("hidden");
}


function openModal(id) {

    document
        .getElementById(id)
        .style.display = "flex";
}


function closeModals() {

    document
        .querySelectorAll(".overlay")
        .forEach(x => {
            x.style.display = "none";
        });
}


async function api(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            {
                credentials: "same-origin",
                ...options
            }
        );

    const data =
        await response.json();

    if (!response.ok) {

        const error =
            new Error(
                data.error ||
                data.message ||
                "Request failed"
            );

        error.data = data;

        throw error;
    }

    return data;
}


async function loadMe() {

    try {

        const data =
            await api(
                "/api/auth/me"
            );

        if (!data.authenticated) {

            isPro = false;

            document
                .getElementById(
                    "planBadge"
                )
                .textContent = "Free";

            document
                .getElementById(
                    "upgradeButton"
                )
                .textContent = "Upgrade";

            return false;
        }

        isPro =
            data.pro;

        document
            .getElementById(
                "planBadge"
            )
            .textContent =
                isPro
                ? "PRO"
                : "Free";

        const button =
            document.getElementById(
                "upgradeButton"
            );

        if (isPro) {

            button.textContent =
                "Pro";

            button.classList.add(
                "pro"
            );

        } else {

            button.textContent =
                "Upgrade";

            button.classList.remove(
                "pro"
            );
        }

        return true;

    } catch (error) {

        return false;
    }
}


function openAuth() {

    openModal(
        "authModal"
    );
}


async function login() {

    try {

        await api(
            "/api/auth/login",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body:
                    JSON.stringify({
                        email:
                            document
                            .getElementById(
                                "authEmail"
                            ).value,

                        password:
                            document
                            .getElementById(
                                "authPassword"
                            ).value
                    })
            }
        );

        closeModals();

        await loadMe();
        await loadHistory();

    } catch (error) {

        alert(
            error.message
        );
    }
}


async function signup() {

    try {

        await api(
            "/api/auth/signup",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body:
                    JSON.stringify({
                        email:
                            document
                            .getElementById(
                                "authEmail"
                            ).value,

                        password:
                            document
                            .getElementById(
                                "authPassword"
                            ).value
                    })
            }
        );

        closeModals();

        await loadMe();
        await loadHistory();

    } catch (error) {

        alert(
            error.message
        );
    }
}


async function logout() {

    await api(
        "/api/auth/logout",
        {
            method: "POST"
        }
    );

    currentChatId = null;

    document
        .getElementById(
            "messages"
        ).innerHTML = "";

    document
        .getElementById(
            "empty"
        )
        .style.display = "block";

    await loadMe();

    closeModals();

    await loadHistory();
}


function openUpgrade() {

    if (!isPro) {

        openModal(
            "upgradeModal"
        );

    } else {

        openAccount();
    }
}


async function startCheckout() {

    try {

        const data =
            await api(
                "/api/billing/checkout",
                {
                    method: "POST"
                }
            );

        window.location.href =
            data.url;

    } catch (error) {

        if (
            error.data &&
            error.data.error ===
                "login_required"
        ) {

            closeModals();
            openAuth();
            return;
        }

        alert(
            error.message
        );
    }
}


async function manageBilling() {

    try {

        const data =
            await api(
                "/api/billing/portal",
                {
                    method: "POST"
                }
            );

        window.location.href =
            data.url;

    } catch (error) {

        alert(
            error.message
        );
    }
}


async function openAccount() {

    const logged =
        await loadMe();

    if (!logged) {

        openAuth();
        return;
    }

    const data =
        await api(
            "/api/auth/me"
        );

    document
        .getElementById(
            "accountInfo"
        )
        .innerHTML = `
            <p>
                <b>${escapeHtml(
                    data.email
                )}</b>
            </p>

            <p>
                Plan:
                <b>${escapeHtml(
                    data.plan
                )}</b>
            </p>
        `;

    openModal(
        "accountModal"
    );
}


async function loadHistory() {

    const logged =
        await loadMe();

    if (!logged) {

        document
            .getElementById(
                "history"
            ).innerHTML = `
                <button
                    class="chat-item"
                    onclick="openAuth()"
                >
                    Login to save chats
                </button>
            `;

        return;
    }

    try {

        const data =
            await api(
                "/api/chats"
            );

        const box =
            document.getElementById(
                "history"
            );

        box.innerHTML = "";

        for (
            const chat
            of data.chats
        ) {

            const button =
                document.createElement(
                    "button"
                );

            button.className =
                "chat-item";

            button.textContent =
                chat.title;

            button.onclick =
                () => openChat(
                    chat.id
                );

            box.appendChild(
                button
            );
        }

    } catch (error) {

        console.error(error);
    }
}


async function openChat(id) {

    try {

        const data =
            await api(
                "/api/chats/"
                + encodeURIComponent(id)
            );

        currentChatId =
            id;

        const box =
            document.getElementById(
                "messages"
            );

        box.innerHTML = "";

        document
            .getElementById(
                "empty"
            )
            .style.display = "none";

        for (
            const message
            of data.messages
        ) {

            addMessage(
                message.role,
                message.content
            );
        }

        document
            .getElementById(
                "chat"
            )
            .scrollTop =
            document
            .getElementById(
                "chat"
            ).scrollHeight;

    } catch (error) {

        alert(
            error.message
        );
    }
}


function newChat() {

    currentChatId = null;

    document
        .getElementById(
            "messages"
        ).innerHTML = "";

    document
        .getElementById(
            "empty"
        )
        .style.display = "block";

    document
        .getElementById(
            "input"
        )
        .focus();
}


function addMessage(
    role,
    text,
    meta = "",
    sources = []
) {

    document
        .getElementById(
            "empty"
        )
        .style.display = "none";

    const box =
        document.getElementById(
            "messages"
        );

    const el =
        document.createElement(
            "div"
        );

    el.className =
        "message " + role;

    let sourceHtml = "";

    if (
        sources &&
        sources.length
    ) {

        sourceHtml = `
            <div class="sources">
                ${
                    sources.map(
                        source => `
                            <a
                                class="source"
                                href="${escapeHtml(
                                    source.url
                                )}"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                ${escapeHtml(
                                    source.title
                                    || source.url
                                )}
                            </a>
                        `
                    ).join("")
                }
            </div>
        `;
    }

    el.innerHTML = `
        <div class="avatar">
            ${
                role === "user"
                ? "U"
                : "V"
            }
        </div>

        <div>

            <div class="content">
                ${escapeHtml(text)}
            </div>

            ${
                meta
                ? `
                    <div class="meta">
                        ${escapeHtml(meta)}
                    </div>
                `
                : ""
            }

            ${sourceHtml}

        </div>
    `;

    box.appendChild(
        el
    );

    const chat =
        document.getElementById(
            "chat"
        );

    chat.scrollTop =
        chat.scrollHeight;
}


async function sendMessage(
    event
) {

    event.preventDefault();

    const input =
        document.getElementById(
            "input"
        );

    const text =
        input.value.trim();

    if (!text) return;

    const logged =
        await loadMe();

    if (!logged) {

        openAuth();
        return;
    }

    addMessage(
        "user",
        text
    );

    input.value = "";

    try {

        const data =
            await api(
                "/api/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            chat_id:
                                currentChatId,

                            message:
                                text
                        })
                }
            );

        currentChatId =
            data.chat_id;

        const successful =
            (data.models || [])
                .filter(
                    x => x.success
                )
                .map(
                    x => x.model
                )
                .join(", ");

        addMessage(
            "assistant",
            data.answer,

            (
                data.plan.toUpperCase()
                + " • "
                + successful
                + " • "
                + data.total_latency_ms
                + " ms"
            ),

            data.sources || []
        );

        await loadHistory();

    } catch (error) {

        if (
            error.data &&
            error.data.upgrade_required
        ) {

            openUpgrade();

            return;
        }

        addMessage(
            "assistant",
            "Veya could not complete the request.\n\n"
            + error.message
        );
    }
}


document
    .getElementById("input")
    .addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter"
                &&
                !event.shiftKey
            ) {

                event.preventDefault();

                document
                    .querySelector(
                        ".composer"
                    )
                    .requestSubmit();
            }
        }
    );


loadMe();
loadHistory();

</script>

</body>

</html>
"""


@app.get("/")
def home():

    return render_template_string(
        HTML
    )


# ============================================================
# LOCAL
# ============================================================

if __name__ == "__main__":

    port = int(
        env(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )