import os
import json
import math
import ast
import re
import sqlite3
import uuid
import threading
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote
from ipaddress import ip_address
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import requests
from flask import Flask, jsonify, request, render_template_string, g
from flask_cors import CORS


# ============================================================
# VEYA 10.0
# MULTI-MODEL + MULTI-AGENT AI PLATFORM
# ============================================================

APP_NAME = os.getenv("APP_NAME", "Veya")
VERSION = "10.0"

PORT = int(os.getenv("PORT", "10000"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "veya.db")
SECRET_KEY = os.getenv("VEYA_SECRET_KEY", "CHANGE_THIS_SECRET")

MAX_MESSAGE_CHARS = int(
    os.getenv("MAX_MESSAGE_CHARS", "16000")
)

MAX_HISTORY_MESSAGES = int(
    os.getenv("MAX_HISTORY_MESSAGES", "40")
)

MAX_PARALLEL_MODELS = int(
    os.getenv("MAX_PARALLEL_MODELS", "4")
)

REQUEST_TIMEOUT_SECONDS = int(
    os.getenv("REQUEST_TIMEOUT_SECONDS", "90")
)

WEB_MAX_RESULTS = int(
    os.getenv("WEB_MAX_RESULTS", "6")
)

CRAWL_MAX_CHARS = int(
    os.getenv("CRAWL_MAX_CHARS", "12000")
)

PREMIUM_PRICE_USD = float(
    os.getenv("PREMIUM_PRICE_USD", "20")
)

VIRTUAL_AGENT_COUNT = int(
    os.getenv("VIRTUAL_AGENT_COUNT", "5000")
)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

CORS(app)


# ============================================================
# ENV HELPERS
# ============================================================

def env_csv(name: str, default: str = "") -> List[str]:
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


# ============================================================
# MODEL SPEC
# ============================================================

@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: str
    tier: str
    tags: Tuple[str, ...]
    base_url: str = ""
    enabled: bool = True


MODEL_CATALOG: List[ModelSpec] = []


def add_models(
    provider: str,
    tier: str,
    model_ids: List[str],
    tags: Tuple[str, ...],
    base_url: str = "",
):
    for model_id in model_ids:
        MODEL_CATALOG.append(
            ModelSpec(
                id=model_id,
                provider=provider,
                tier=tier,
                tags=tags,
                base_url=base_url,
            )
        )


# ============================================================
# MODEL CATALOG
# ============================================================
#
# IMPORTANT:
# Every model ID is environment-configurable.
#
# That means:
#
# GPT-6 -> GPT-7
# Claude -> future Claude
# Gemini -> future Gemini
#
# can be changed without rewriting the routing architecture.
#
# Do NOT assume that every slot is automatically available.
# Provider API key + account access + model availability are required.
# ============================================================


add_models(
    "openai",
    "premium",
    env_csv(
        "OPENAI_PREMIUM_MODELS",
        "gpt-6-astra,"
        "gpt-6.1-sol,"
        "gpt-6.1-terra,"
        "gpt-6-luna,"
        "gpt-6-sol",
    ),
    (
        "reasoning",
        "coding",
        "agents",
        "general",
    ),
)


add_models(
    "anthropic",
    "premium",
    env_csv(
        "ANTHROPIC_PREMIUM_MODELS",
        "claude-fable-5-2,"
        "claude-opus-5-5,"
        "claude-sonnet-5-5,"
        "claude-haiku-5-5",
    ),
    (
        "reasoning",
        "coding",
        "research",
        "general",
    ),
)


add_models(
    "google",
    "premium",
    env_csv(
        "GOOGLE_PREMIUM_MODELS",
        "gemini-3.8-flash,"
        "gemini-3.7-flash,"
        "gemini-3.6-flash,"
        "gemini-3.5-flash,"
        "gemini-3.1-pro-preview",
    ),
    (
        "reasoning",
        "multimodal",
        "research",
        "general",
    ),
)


add_models(
    "xai",
    "premium",
    env_csv(
        "XAI_PREMIUM_MODELS",
        "grok-4.7",
    ),
    (
        "reasoning",
        "coding",
        "agents",
        "web",
    ),
)


add_models(
    "mistral",
    "premium",
    env_csv(
        "MISTRAL_PREMIUM_MODELS",
        "mistral-large-4,"
        "mistral-small-4,"
        "ministral-3-14b,"
        "ministral-3-8b,"
        "ministral-3-3b",
    ),
    (
        "reasoning",
        "coding",
        "agents",
    ),
)


add_models(
    "deepseek",
    "premium",
    env_csv(
        "DEEPSEEK_PREMIUM_MODELS",
        "deepseek-v4-pro,"
        "deepseek-flash",
    ),
    (
        "reasoning",
        "coding",
        "math",
        "agents",
    ),
)


add_models(
    "nvidia",
    "premium",
    env_csv(
        "NVIDIA_PREMIUM_MODELS",
        "nvidia/nemotron-3-ultra-550b-a55b,"
        "nvidia/nemotron-3-super-120b-a12b,"
        "nvidia/nemotron-3.5-super-vl-120b-a12b,"
        "nvidia/nemotron-3.5-lightning,"
        "nvidia/nemotron-3-nano",
    ),
    (
        "reasoning",
        "coding",
        "agents",
        "multimodal",
    ),
)


add_models(
    "microsoft",
    "premium",
    env_csv(
        "MICROSOFT_PREMIUM_MODELS",
        "gpt-6.1-sol,"
        "gpt-6.1-terra,"
        "gpt-6-astra,"
        "gpt-6-luna,"
        "gpt-5.6-sol",
    ),
    (
        "enterprise",
        "reasoning",
        "coding",
        "agents",
    ),
    os.getenv("FOUNDRY_BASE_URL", ""),
)


# Free / lower-cost route.
#
# You can replace this with whatever free/cheap model
# your provider account actually gives access to.
add_models(
    "groq",
    "free",
    env_csv(
        "FREE_MODELS",
        "openai/gpt-oss-120b",
    ),
    (
        "fast",
        "general",
        "coding",
    ),
    os.getenv(
        "GROQ_BASE_URL",
        "https://api.groq.com/openai/v1",
    ),
)


# ============================================================
# API KEYS
# ============================================================

API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    "google": os.getenv("GOOGLE_API_KEY", ""),
    "xai": os.getenv("XAI_API_KEY", ""),
    "mistral": os.getenv("MISTRAL_API_KEY", ""),
    "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    "nvidia": os.getenv("NVIDIA_API_KEY", ""),
    "microsoft": (
        os.getenv("AZURE_OPENAI_API_KEY")
        or os.getenv("FOUNDRY_API_KEY", "")
    ),
    "groq": os.getenv("GROQ_API_KEY", ""),
}


# ============================================================
# PROVIDER BASE URLS
# ============================================================

BASE_URLS = {
    "xai": os.getenv(
        "XAI_BASE_URL",
        "https://api.x.ai/v1",
    ),

    "mistral": os.getenv(
        "MISTRAL_BASE_URL",
        "https://api.mistral.ai/v1",
    ),

    "deepseek": os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    ),

    "nvidia": os.getenv(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    ),

    "groq": os.getenv(
        "GROQ_BASE_URL",
        "https://api.groq.com/openai/v1",
    ),

    "microsoft": os.getenv(
        "FOUNDRY_BASE_URL",
        "",
    ),
}


# ============================================================
# DATABASE
# ============================================================

DB_LOCK = threading.Lock()


def get_db():
    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    with DB_LOCK:

        conn = get_db()

        conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                plan TEXT NOT NULL DEFAULT 'free',
                stripe_customer_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                meta_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                model TEXT,
                provider TEXT,
                tokens INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )

        conn.commit()
        conn.close()


def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# USER
# ============================================================

def get_or_create_user(user_id: str):

    with DB_LOCK:

        conn = get_db()

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:

            conn.execute(
                """
                INSERT INTO users (
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

            conn.commit()

            row = conn.execute(
                """
                SELECT *
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

        conn.close()

        return dict(row)


def current_user():

    user_id = (
        request.headers.get("X-Veya-User")
        or request.cookies.get("veya_user")
    )

    if not user_id:
        user_id = str(uuid.uuid4())

    return (
        get_or_create_user(user_id),
        user_id,
    )


@app.before_request
def before_request():

    g.user, g.user_id = current_user()


# ============================================================
# CHAT DATABASE
# ============================================================

def ensure_chat(
    user_id: str,
    chat_id: str = None,
    title: str = "New chat",
):

    if not chat_id:
        chat_id = str(uuid.uuid4())

    with DB_LOCK:

        conn = get_db()

        row = conn.execute(
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

        if row is None:

            conn.execute(
                """
                INSERT INTO chats (
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
                    title[:120],
                    utc_now(),
                    utc_now(),
                ),
            )

            conn.commit()

        conn.close()

    return chat_id


def add_message(
    chat_id: str,
    role: str,
    content: str,
    meta: Dict[str, Any] = None,
):

    with DB_LOCK:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO messages (
                chat_id,
                role,
                content,
                meta_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                role,
                content,
                json.dumps(
                    meta or {},
                    ensure_ascii=False,
                ),
                utc_now(),
            ),
        )

        conn.execute(
            """
            UPDATE chats
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                chat_id,
            ),
        )

        conn.commit()
        conn.close()


def get_history(
    chat_id: str,
    limit: int = MAX_HISTORY_MESSAGES,
):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT role, content
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

    conn.close()

    return [
        dict(row)
        for row in reversed(rows)
    ]


# ============================================================
# AGENT ROLES
# ============================================================

AGENT_ROLES = {

    "general":
        "general reasoning and planning",

    "reasoning":
        "hard reasoning and verification",

    "coding":
        "software engineering and debugging",

    "research":
        "research and evidence synthesis",

    "math":
        "mathematics and quantitative reasoning",

    "science":
        "science explanation",

    "data":
        "data analysis and statistics",

    "business":
        "business strategy and product analysis",

    "creative":
        "writing and ideation",

    "multimodal":
        "image and document understanding",

    "security":
        "defensive cybersecurity and secure coding",

    "planner":
        "task decomposition",

    "critic":
        "find errors and weaknesses",

    "judge":
        "compare candidate answers",

    "enterprise":
        "enterprise architecture and workflows",

    "automation":
        "tool and workflow orchestration",

    "robotics":
        "robotics and IoT concepts",

    "education":
        "teaching and tutoring",
}


# ============================================================
# ROUTING KEYWORDS
# ============================================================

KEYWORDS = {

    "coding": [
        "code",
        "python",
        "javascript",
        "typescript",
        "api",
        "flask",
        "react",
        "docker",
        "debug",
        "programming",
        "software",
    ],

    "math": [
        "math",
        "equation",
        "algebra",
        "geometry",
        "calculus",
        "probability",
        "statistics",
        "matrix",
    ],

    "research": [
        "research",
        "latest",
        "today",
        "current",
        "paper",
        "study",
        "source",
        "citation",
        "evidence",
        "compare",
        "news",
    ],

    "business": [
        "business",
        "startup",
        "company",
        "market",
        "product",
        "strategy",
        "sales",
        "marketing",
    ],

    "data": [
        "dataset",
        "csv",
        "pandas",
        "numpy",
        "dataframe",
        "regression",
        "data analysis",
    ],

    "security": [
        "cybersecurity",
        "cyber security",
        "security",
        "vulnerability",
        "hardening",
        "secure coding",
        "phishing",
        "malware",
    ],

    "science": [
        "physics",
        "chemistry",
        "biology",
        "genetics",
        "quantum",
        "molecule",
        "gravity",
    ],

    "creative": [
        "write",
        "story",
        "poem",
        "creative",
        "caption",
        "script",
        "design",
        "brainstorm",
    ],

    "education": [
        "explain",
        "teach",
        "learn",
        "homework",
        "lesson",
        "school",
    ],

    "robotics": [
        "robot",
        "robotics",
        "iot",
        "sensor",
        "arduino",
        "raspberry",
        "control system",
    ],
}


def route_domain(text: str):

    text = text.lower()

    scores = {
        domain: sum(
            text.count(keyword)
            for keyword in keywords
        )
        for domain, keywords in KEYWORDS.items()
    }

    if not scores:
        return "general"

    best = max(
        scores,
        key=scores.get,
    )

    if scores[best] <= 0:
        return "general"

    return best


# ============================================================
# 100+ HIGH-LEVEL SPECIALIST AGENTS
# ============================================================

MONSTER_AGENT_ROLES = [

    "General Reasoning",
    "Deep Reasoning",
    "Long-Horizon Planner",
    "Critical Thinker",
    "Judge",
    "Verifier",
    "Fact Checker",
    "Research Synthesizer",
    "Web Researcher",
    "Source Analyst",
    "Literature Analyst",
    "Math Solver",
    "Proof Checker",
    "Statistics Expert",
    "Physics Expert",
    "Chemistry Expert",
    "Biology Expert",
    "Computer Science Expert",
    "Algorithm Engineer",
    "Software Architect",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Engineer",
    "DevOps Engineer",
    "Cloud Architect",
    "Database Engineer",
    "API Engineer",
    "Testing Engineer",
    "Debugging Expert",
    "Data Analyst",
    "Data Scientist",
    "ML Engineer",
    "AI Engineer",
    "Prompt Engineer",
    "RAG Engineer",
    "Agent Engineer",
    "MCP Tool Engineer",
    "A2A Orchestrator",
    "Automation Planner",
    "Workflow Designer",
    "Business Strategist",
    "Startup Strategist",
    "Product Manager",
    "Product Strategist",
    "Market Analyst",
    "Growth Strategist",
    "Operations Analyst",
    "Financial Analyst",
    "Marketing Strategist",
    "Sales Strategist",
    "UX Strategist",
    "Creative Director",
    "Technical Writer",
    "Content Strategist",
    "Teacher",
    "Tutor",
    "Study Planner",
    "Science Communicator",
    "Robotics Engineer",
    "IoT Engineer",
    "Embedded Systems Expert",
    "Electronics Designer",
    "CAD Planning Agent",
    "Simulation Planner",
    "Security Architect",
    "Defensive Security Analyst",
    "Privacy Engineer",
    "Compliance Analyst",
    "Risk Analyst",
    "Enterprise Architect",
    "Solutions Architect",
    "Systems Engineer",
    "Distributed Systems Expert",
    "Knowledge Engineer",
    "Document Analyst",
    "Multimodal Planner",
    "Presentation Planner",
    "Data Visualization Analyst",
    "Experiment Designer",
    "Decision Analyst",
    "Scenario Planner",
    "Debate Analyst",
    "Counterargument Analyst",
    "Quality Assurance Agent",
    "Red-Team Critic",
    "Blue-Team Reviewer",
    "Code Review Agent",
    "Architecture Reviewer",
    "Release Planner",
    "Performance Engineer",
    "Cost Optimizer",
    "Latency Optimizer",
    "Reliability Engineer",
    "Observability Engineer",
    "Incident Analyst",
    "Product Researcher",
    "Competitor Analyst",
    "Customer Researcher",
    "Roadmap Planner",
    "SEO Strategist",
    "Localization Planner",
    "Accessibility Reviewer",
    "Policy Research Assistant",
    "Knowledge Tutor",
    "Generalist Researcher",
    "Answer Editor",
    "Final Response Editor",
]


def build_virtual_agents():

    providers = [
        model.provider
        for model in MODEL_CATALOG
    ]

    domains = list(
        AGENT_ROLES.keys()
    )

    agents = []

    for i in range(
        VIRTUAL_AGENT_COUNT
    ):

        role = MONSTER_AGENT_ROLES[
            i % len(MONSTER_AGENT_ROLES)
        ]

        domain = domains[
            i % len(domains)
        ]

        provider = (
            providers[
                i % len(providers)
            ]
            if providers
            else "unassigned"
        )

        agents.append(
            {
                "id":
                    f"veya-agent-{i + 1:04d}",

                "role":
                    role,

                "domain":
                    domain,

                "provider_preference":
                    provider,

                "active":
                    True,
            }
        )

    return agents


# This creates thousands of specialist configurations.
#
# IMPORTANT:
# These are orchestration configurations, NOT 5000 separate
# proprietary models running in memory.
#
# Real inference is still performed by configured provider APIs.
VIRTUAL_AGENTS = build_virtual_agents()


# ============================================================
# SAFE CALCULATOR
# ============================================================

MATH_FUNCTIONS = {

    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,

}

MATH_CONSTANTS = {

    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,

}


def calculator(expression: str):

    if len(expression) > 500:
        raise ValueError(
            "Expression is too long."
        )

    tree = ast.parse(
        expression,
        mode="eval",
    )

    def evaluate(node):

        if isinstance(
            node,
            ast.Expression,
        ):
            return evaluate(node.body)

        if (
            isinstance(node, ast.Constant)
            and isinstance(
                node.value,
                (int, float),
            )
        ):
            return node.value

        if (
            isinstance(node, ast.Name)
            and node.id in MATH_CONSTANTS
        ):
            return MATH_CONSTANTS[
                node.id
            ]

        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(
                node.op,
                (
                    ast.UAdd,
                    ast.USub,
                ),
            )
        ):

            value = evaluate(
                node.operand
            )

            if isinstance(
                node.op,
                ast.UAdd,
            ):
                return value

            return -value

        if (
            isinstance(node, ast.BinOp)
            and isinstance(
                node.op,
                (
                    ast.Add,
                    ast.Sub,
                    ast.Mult,
                    ast.Div,
                    ast.Pow,
                    ast.Mod,
                ),
            )
        ):

            left = evaluate(
                node.left
            )

            right = evaluate(
                node.right
            )

            if isinstance(
                node.op,
                ast.Add,
            ):
                return left + right

            if isinstance(
                node.op,
                ast.Sub,
            ):
                return left - right

            if isinstance(
                node.op,
                ast.Mult,
            ):
                return left * right

            if isinstance(
                node.op,
                ast.Div,
            ):
                return left / right

            if isinstance(
                node.op,
                ast.Pow,
            ):

                if abs(right) > 1000:
                    raise ValueError(
                        "Exponent is too large."
                    )

                return left ** right

            return left % right

        if (
            isinstance(node, ast.Call)
            and isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id
            in MATH_FUNCTIONS
        ):

            if node.keywords:
                raise ValueError(
                    "Keyword arguments are not allowed."
                )

            return MATH_FUNCTIONS[
                node.func.id
            ](
                *[
                    evaluate(arg)
                    for arg in node.args
                ]
            )

        raise ValueError(
            "Unsupported mathematical expression."
        )

    result = evaluate(tree)

    if not math.isfinite(
        float(result)
    ):
        raise ValueError(
            "Result is not finite."
        )

    return str(result)


# ============================================================
# URL SAFETY
# ============================================================

def safe_public_url(url: str):

    parsed = urlparse(url)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return False

    if not parsed.hostname:
        return False

    host = parsed.hostname.lower()

    if host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        return False

    try:

        ip = ip_address(host)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False

    except ValueError:
        pass

    return True


# ============================================================
# WEB SEARCH
# ============================================================
#
# Search priority:
#
# 1. Google Custom Search API
# 2. Tavily
# 3. No search
#
# This avoids pretending that a normal HTTP request is Google Search.
# ============================================================

def web_search(
    query: str,
    max_results: int = WEB_MAX_RESULTS,
):

    google_key = os.getenv(
        "GOOGLE_CSE_KEY",
        "",
    )

    google_cx = os.getenv(
        "GOOGLE_CSE_CX",
        "",
    )

    if google_key and google_cx:

        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": google_key,
                "cx": google_cx,
                "q": query,
                "num": min(
                    max_results,
                    10,
                ),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()

        return [
            {
                "title":
                    item.get(
                        "title",
                        "",
                    ),

                "url":
                    item.get(
                        "link",
                        "",
                    ),

                "snippet":
                    item.get(
                        "snippet",
                        "",
                    ),
            }
            for item in data.get(
                "items",
                [],
            )
        ]

    tavily_key = os.getenv(
        "TAVILY_API_KEY",
        "",
    )

    if tavily_key:

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key":
                    tavily_key,

                "query":
                    query,

                "max_results":
                    max_results,

                "search_depth":
                    "advanced",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()

        return [
            {
                "title":
                    item.get(
                        "title",
                        "",
                    ),

                "url":
                    item.get(
                        "url",
                        "",
                    ),

                "snippet":
                    item.get(
                        "content",
                        "",
                    ),
            }
            for item in data.get(
                "results",
                []
            )
        ]

    return []


# ============================================================
# WEB CRAWLER
# ============================================================

def crawl_url(url: str):

    if not safe_public_url(url):
        raise ValueError(
            "URL rejected for safety."
        )

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent":
                "VeyaBot/10.0"
        },
    )

    response.raise_for_status()

    html = response.text

    html = re.sub(
        r"<script[\s\S]*?</script>",
        " ",
        html,
        flags=re.I,
    )

    html = re.sub(
        r"<style[\s\S]*?</style>",
        " ",
        html,
        flags=re.I,
    )

    html = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )

    html = re.sub(
        r"\s+",
        " ",
        html,
    ).strip()

    return {
        "url":
            url,

        "status":
            response.status_code,

        "text":
            html[
                :CRAWL_MAX_CHARS
            ],
    }


# ============================================================
# OPENAI-COMPATIBLE PROVIDER
# ============================================================

def chat_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int = 7000,
):

    url = (
        base_url.rstrip("/")
        + "/chat/completions"
    )

    payload = {
        "model":
            model,

        "messages":
            messages,

        "max_tokens":
            max_tokens,

        "temperature":
            0.2,
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization":
                f"Bearer {api_key}",

            "Content-Type":
                "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data["choices"][0]["message"]
        .get("content", "")
    )

    if isinstance(
        content,
        list,
    ):

        content = "".join(
            str(
                item.get(
                    "text",
                    "",
                )
            )
            for item in content
            if isinstance(
                item,
                dict,
            )
        )

    return {
        "text":
            content,

        "usage":
            data.get(
                "usage",
                {},
            ),
    }


# ============================================================
# OPENAI
# ============================================================

def call_openai(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
):

    from openai import OpenAI

    client = OpenAI(
        api_key=API_KEYS["openai"],
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    instructions = "\n".join(
        message["content"]
        for message in messages
        if message["role"] == "system"
    )

    inputs = [
        message
        for message in messages
        if message["role"] != "system"
    ]

    kwargs = {
        "model":
            model,

        "input":
            inputs,

        "max_output_tokens":
            max_tokens,
    }

    if instructions:
        kwargs["instructions"] = (
            instructions
        )

    response = (
        client.responses.create(
            **kwargs
        )
    )

    return {
        "text":
            response.output_text,

        "usage":
            getattr(
                response,
                "usage",
                {},
            ),
    }


# ============================================================
# ANTHROPIC
# ============================================================

def call_anthropic(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
):

    system_text = "\n".join(
        message["content"]
        for message in messages
        if message["role"] == "system"
    )

    chat_messages = [
        message
        for message in messages
        if message["role"] != "system"
    ]

    response = requests.post(
        "https://api.anthropic.com/v1/messages",

        json={
            "model":
                model,

            "max_tokens":
                max_tokens,

            "system":
                system_text,

            "messages":
                chat_messages,
        },

        headers={
            "x-api-key":
                API_KEYS["anthropic"],

            "anthropic-version":
                "2023-06-01",

            "content-type":
                "application/json",
        },

        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    data = response.json()

    text = "".join(
        block.get(
            "text",
            "",
        )
        for block in data.get(
            "content",
            [],
        )
        if block.get("type")
        == "text"
    )

    return {
        "text":
            text,

        "usage":
            data.get(
                "usage",
                {},
            ),
    }


# ============================================================
# GOOGLE GEMINI
# ============================================================

def call_google(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
):

    contents = []

    system_text = ""

    for message in messages:

        role = message["role"]

        if role == "system":

            system_text += (
                message["content"]
                + "\n"
            )

            continue

        contents.append(
            {
                "role":
                    (
                        "model"
                        if role
                        == "assistant"
                        else "user"
                    ),

                "parts": [
                    {
                        "text":
                            message[
                                "content"
                            ]
                    }
                ],
            }
        )

    body = {
        "contents":
            contents,

        "generationConfig": {
            "maxOutputTokens":
                max_tokens,

            "temperature":
                0.2,
        },
    }

    if system_text:

        body[
            "systemInstruction"
        ] = {
            "parts": [
                {
                    "text":
                        system_text
                }
            ]
        }

    endpoint = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + quote(
            model,
            safe="",
        )
        + ":generateContent"
    )

    response = requests.post(
        endpoint,

        params={
            "key":
                API_KEYS["google"]
        },

        json=body,

        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    data = response.json()

    candidates = data.get(
        "candidates",
        [],
    )

    if not candidates:
        return {
            "text":
                "",
            "usage":
                data.get(
                    "usageMetadata",
                    {},
                ),
        }

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    text = "".join(
        part.get(
            "text",
            "",
        )
        for part in parts
    )

    return {
        "text":
            text,

        "usage":
            data.get(
                "usageMetadata",
                {},
            ),
    }


# ============================================================
# PROVIDER DISPATCH
# ============================================================

def call_provider(
    spec: ModelSpec,
    messages: List[Dict[str, Any]],
    max_tokens: int,
):

    provider = spec.provider

    if not API_KEYS.get(
        provider
    ):

        raise RuntimeError(
            f"{provider} API key is not configured."
        )

    if provider == "openai":

        return call_openai(
            spec.id,
            messages,
            max_tokens,
        )

    if provider == "anthropic":

        return call_anthropic(
            spec.id,
            messages,
            max_tokens,
        )

    if provider == "google":

        return call_google(
            spec.id,
            messages,
            max_tokens,
        )

    if provider == "microsoft":

        if not spec.base_url:

            raise RuntimeError(
                "FOUNDRY_BASE_URL is not configured."
            )

        return chat_openai_compatible(
            spec.base_url,
            API_KEYS["microsoft"],
            spec.id,
            messages,
            max_tokens,
        )

    return chat_openai_compatible(
        BASE_URLS[provider],
        API_KEYS[provider],
        spec.id,
        messages,
        max_tokens,
    )


# ============================================================
# CONFIGURED MODELS
# ============================================================

def configured_models(
    plan: str,
):

    result = []

    for model in MODEL_CATALOG:

        if not model.enabled:
            continue

        if not API_KEYS.get(
            model.provider
        ):
            continue

        if plan == "premium":

            result.append(model)

        elif model.tier == "free":

            result.append(model)

    return result


# ============================================================
# INTELLIGENT MODEL ROUTER
# ============================================================

def pick_models(
    domain: str,
    plan: str,
):

    pool = configured_models(
        plan
    )

    if not pool:
        return []

    def score(model):

        score_value = 0

        if domain in model.tags:
            score_value += 10

        if "reasoning" in model.tags:
            score_value += 5

        if "general" in model.tags:
            score_value += 2

        if "agents" in model.tags:
            score_value += 3

        if domain == "coding" and (
            "coding" in model.tags
        ):
            score_value += 8

        if domain == "research" and (
            "research" in model.tags
        ):
            score_value += 8

        if domain == "math" and (
            "math" in model.tags
        ):
            score_value += 8

        return score_value

    ranked = sorted(
        pool,
        key=score,
        reverse=True,
    )

    return ranked[
        :MAX_PARALLEL_MODELS
    ]


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Veya, a high-performance multi-model,
multi-agent AI platform.

Architecture:

User
 -> Router
 -> Specialist Agents
 -> Multiple Provider Models
 -> Tools / Web
 -> Cross-checking
 -> Judge
 -> Final Answer

Core rules:

1. Solve the user's actual task.

2. Never invent a source.

3. Never claim that a provider model was used
   unless the API call actually succeeded.

4. Prefer correctness over impressive wording.

5. When web sources are provided, use them
   as evidence and cite them as [1], [2], etc.

6. For current information, use web search
   whenever it is available and relevant.

7. For mathematical tasks, verify calculations.

8. For programming tasks, prioritize correct,
   runnable architecture.

9. For cybersecurity, stay defensive,
   authorized and educational.

10. Do not reveal private chain-of-thought.

11. Give concise reasoning summaries instead.

12. Never expose API keys, passwords,
    cookies or secrets.

13. If a provider is unavailable, do not pretend
    that provider answered.

14. If multiple candidate answers disagree,
    evaluate them and choose the most reliable answer.
"""


# ============================================================
# BUILD MODEL PROMPT
# ============================================================

def build_prompt(
    user_text: str,
    history: List[Dict[str, Any]],
    domain: str,
    web_context: str = "",
):

    system = (
        SYSTEM_PROMPT
        + "\n\n"
        + "ACTIVE SPECIALIST:\n"
        + domain
        + "\n\n"
        + "SPECIALIST ROLE:\n"
        + AGENT_ROLES.get(
            domain,
            AGENT_ROLES["general"],
        )
        + "\n\n"
        + "WEB CONTEXT:\n"
        + web_context
    )

    messages = [
        {
            "role":
                "system",

            "content":
                system,
        }
    ]

    messages.extend(
        history
    )

    messages.append(
        {
            "role":
                "user",

            "content":
                user_text,
        }
    )

    return messages


# ============================================================
# JUDGE / VERIFIER
# ============================================================

def judge_candidates(
    user_text: str,
    candidates: List[Dict[str, Any]],
    plan: str,
):

    if len(candidates) == 1:

        return (
            candidates[0]["text"],
            candidates,
        )

    judge_pool = [
        model
        for model in configured_models(
            plan
        )
        if (
            "reasoning"
            in model.tags
            or "general"
            in model.tags
        )
    ]

    if not judge_pool:

        return (
            candidates[0]["text"],
            candidates,
        )

    judge_model = judge_pool[0]

    candidate_text = "\n\n".join(
        (
            f"CANDIDATE {index + 1} "
            f"({candidate['provider']}/"
            f"{candidate['model']}):\n"
            f"{candidate['text']}"
        )
        for index, candidate
        in enumerate(candidates)
    )

    judge_messages = [

        {
            "role":
                "system",

            "content":
                SYSTEM_PROMPT
                + """

You are the Veya Judge.

Compare candidate answers.

Evaluate:

- correctness
- completeness
- evidence
- reasoning quality
- relevance
- instruction following

Return ONLY the best final answer.

Do not mention the internal model panel.
""",
        },

        {
            "role":
                "user",

            "content":
                user_text
                + "\n\n"
                + candidate_text,
        },
    ]

    try:

        result = call_provider(
            judge_model,
            judge_messages,
            7000,
        )

        return (
            result["text"],
            candidates,
        )

    except Exception as exc:

        app.logger.warning(
            "Judge failed: %s",
            exc,
        )

        return (
            candidates[0]["text"],
            candidates,
        )


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def run_chat(
    user_text: str,
    plan: str,
    history: List[Dict[str, Any]],
):

    domain = route_domain(
        user_text
    )

    lower = user_text.lower()

    should_search = any(
        keyword in lower
        for keyword in [
            "latest",
            "today",
            "current",
            "news",
            "research",
            "source",
            "citation",
            "compare",
            "2026",
        ]
    )

    web_results = []

    web_context = ""

    if should_search:

        try:

            web_results = web_search(
                user_text
            )

            web_context = "\n".join(
                (
                    f"[{index + 1}] "
                    f"{item.get('title', '')} "
                    f"— {item.get('url', '')}\n"
                    f"{item.get('snippet', '')}"
                )
                for index, item
                in enumerate(web_results)
            )

        except Exception as exc:

            app.logger.warning(
                "Web search failed: %s",
                exc,
            )

    messages = build_prompt(
        user_text,
        history,
        domain,
        web_context,
    )

    model_specs = pick_models(
        domain,
        plan,
    )

    if not model_specs:

        raise RuntimeError(
            "No configured model is available "
            "for this plan."
        )

    candidates = []

    with ThreadPoolExecutor(
        max_workers=len(model_specs)
    ) as executor:

        futures = {
            executor.submit(
                call_provider,
                model,
                messages,
                7000,
            ): model
            for model in model_specs
        }

        for future in as_completed(
            futures
        ):

            model = futures[
                future
            ]

            try:

                result = future.result()

                candidates.append(
                    {
                        "provider":
                            model.provider,

                        "model":
                            model.id,

                        "text":
                            result["text"],
                    }
                )

            except Exception as exc:

                app.logger.warning(
                    "Provider failed: %s/%s: %s",
                    model.provider,
                    model.id,
                    exc,
                )

    if not candidates:

        raise RuntimeError(
            "All configured model calls failed."
        )

    answer, candidates = (
        judge_candidates(
            user_text,
            candidates,
            plan,
        )
    )

    return {

        "answer":
            answer,

        "domain":
            domain,

        "models":
            [
                (
                    f"{item['provider']}/"
                    f"{item['model']}"
                )
                for item in candidates
            ],

        "sources":
            web_results,
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    premium_models = (
        configured_models(
            "premium"
        )
    )

    return jsonify(
        {
            "status":
                "online",

            "name":
                APP_NAME,

            "version":
                VERSION,

            "premium_price_usd":
                PREMIUM_PRICE_USD,

            "configured_providers":
                sorted(
                    {
                        model.provider
                        for model
                        in premium_models
                    }
                ),

            "configured_models":
                len(
                    premium_models
                ),

            "virtual_agents":
                len(
                    VIRTUAL_AGENTS
                ),

            "monster_roles":
                len(
                    MONSTER_AGENT_ROLES
                ),
        }
    )


# ============================================================
# PROVIDERS
# ============================================================

@app.get("/api/providers")
def providers():

    provider_names = sorted(
        {
            model.provider
            for model
            in MODEL_CATALOG
        }
    )

    result = []

    for provider in provider_names:

        models = [
            model
            for model
            in MODEL_CATALOG
            if model.provider
            == provider
        ]

        result.append(
            {
                "provider":
                    provider,

                "configured":
                    bool(
                        API_KEYS.get(
                            provider
                        )
                    ),

                "models":
                    [
                        asdict(model)
                        for model
                        in models
                    ],
            }
        )

    return jsonify(
        result
    )


# ============================================================
# AGENTS
# ============================================================

@app.get("/api/agents")
def agents():

    return jsonify(
        {
            "count":
                len(VIRTUAL_AGENTS),

            "monster_roles":
                MONSTER_AGENT_ROLES,

            # Do not dump all 5000 records to every request.
            "agents":
                VIRTUAL_AGENTS[
                    :200
                ],
        }
    )


# ============================================================
# CHAT LIST
# ============================================================

@app.get("/api/chats")
def chats():

    conn = get_db()

    rows = conn.execute(
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
            g.user_id,
        ),
    ).fetchall()

    conn.close()

    return jsonify(
        [
            dict(row)
            for row in rows
        ]
    )


# ============================================================
# GET CHAT
# ============================================================

@app.get("/api/chats/<chat_id>")
def get_chat(chat_id):

    conn = get_db()

    exists = conn.execute(
        """
        SELECT id
        FROM chats
        WHERE id = ?
        AND user_id = ?
        """,
        (
            chat_id,
            g.user_id,
        ),
    ).fetchone()

    if exists is None:

        conn.close()

        return jsonify(
            {
                "error":
                    "Chat not found."
            }
        ), 404

    rows = conn.execute(
        """
        SELECT
            role,
            content,
            meta_json,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id
        """,
        (
            chat_id,
        ),
    ).fetchall()

    conn.close()

    result = []

    for row in rows:

        try:

            meta = json.loads(
                row["meta_json"]
                or "{}"
            )

        except Exception:

            meta = {}

        result.append(
            {
                "role":
                    row["role"],

                "content":
                    row["content"],

                "meta":
                    meta,

                "created_at":
                    row["created_at"],
            }
        )

    return jsonify(
        result
    )


# ============================================================
# MAIN CHAT
# ============================================================

@app.post("/api/chat")
def chat_api():

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    user_text = str(
        body.get(
            "message",
            "",
        )
    ).strip()

    if not user_text:

        return jsonify(
            {
                "error":
                    "Message is required."
            }
        ), 400

    if len(user_text) > (
        MAX_MESSAGE_CHARS
    ):

        return jsonify(
            {
                "error":
                    "Message is too long."
            }
        ), 413

    plan = g.user[
        "plan"
    ]

    chat_id = ensure_chat(
        g.user_id,
        body.get("chat_id"),
        user_text[:60],
    )

    # Save user message first.
    add_message(
        chat_id,
        "user",
        user_text,
    )

    # Previous messages only.
    history = get_history(
        chat_id
    )

    if history:
        history = history[:-1]

    try:

        result = run_chat(
            user_text,
            plan,
            history,
        )

        add_message(
            chat_id,
            "assistant",
            result["answer"],
            {
                "domain":
                    result["domain"],

                "models":
                    result["models"],

                "sources":
                    result["sources"],
            },
        )

        return jsonify(
            {
                "status":
                    "success",

                "chat_id":
                    chat_id,

                "assistant":
                    APP_NAME,

                "plan":
                    plan,

                **result,
            }
        )

    except Exception as exc:

        app.logger.exception(
            "Veya chat failed"
        )

        return jsonify(
            {
                "status":
                    "error",

                "error":
                    str(exc),
            }
        ), 500


# ============================================================
# RESET CHAT
# ============================================================

@app.post("/api/reset")
def reset_chat():

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    chat_id = body.get(
        "chat_id"
    )

    if not chat_id:

        return jsonify(
            {
                "error":
                    "chat_id required"
            }
        ), 400

    with DB_LOCK:

        conn = get_db()

        conn.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            """,
            (
                chat_id,
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
                g.user_id,
            ),
        )

        conn.commit()
        conn.close()

    return jsonify(
        {
            "ok":
                True
        }
    )


# ============================================================
# A2A-STYLE AGENT ENDPOINT
# ============================================================

@app.get(
    "/.well-known/agent-card.json"
)
def agent_card():

    return jsonify(
        {
            "name":
                APP_NAME,

            "version":
                VERSION,

            "description":
                (
                    "Multi-model and "
                    "multi-agent AI "
                    "orchestration service."
                ),

            "capabilities":
                [
                    "chat",
                    "research",
                    "web-search",
                    "web-crawling",
                    "multi-model-routing",
                    "parallel-agents",
                    "verification",
                    "judge-synthesis",
                    "business-strategy",
                    "coding",
                    "data-analysis",
                ],

            "endpoints":
                {
                    "chat":
                        "/api/chat",

                    "a2a":
                        "/a2a",
                },
        }
    )


@app.post("/a2a")
def a2a_task():

    body = (
        request.get_json(
            silent=True
        )
        or {}
    )

    task = str(
        body.get(
            "task"
        )
        or body.get(
            "message"
        )
        or ""
    ).strip()

    if not task:

        return jsonify(
            {
                "error":
                    "task is required."
            }
        ), 400

    try:

        result = run_chat(
            task,
            g.user["plan"],
            [],
        )

        return jsonify(
            {
                "status":
                    "completed",

                "task":
                    task,

                "agent":
                    APP_NAME,

                "answer":
                    result["answer"],

                "domain":
                    result["domain"],

                "models":
                    result["models"],
            }
        )

    except Exception:

        app.logger.exception(
            "A2A task failed"
        )

        return jsonify(
            {
                "status":
                    "failed",

                "error":
                    "A2A task failed.",
            }
        ), 500


# ============================================================
# OPTIONAL STRIPE PREMIUM
# ============================================================

def stripe_client():

    stripe_key = os.getenv(
        "STRIPE_SECRET_KEY",
        "",
    )

    if not stripe_key:
        return None

    import stripe

    stripe.api_key = stripe_key

    return stripe


@app.post(
    "/api/billing/create-checkout"
)
def create_checkout():

    stripe = stripe_client()

    if stripe is None:

        return jsonify(
            {
                "error":
                    "Stripe is not configured."
            }
        ), 503

    price_id = os.getenv(
        "STRIPE_PRICE_ID",
        "",
    )

    if not price_id:

        return jsonify(
            {
                "error":
                    "STRIPE_PRICE_ID is not configured."
            }
        ), 503

    try:

        session = (
            stripe.checkout.Session.create(
                mode="subscription",

                line_items=[
                    {
                        "price":
                            price_id,

                        "quantity":
                            1,
                    }
                ],

                success_url=
                    os.getenv(
                        "STRIPE_SUCCESS_URL",
                        "/",
                    ),

                cancel_url=
                    os.getenv(
                        "STRIPE_CANCEL_URL",
                        "/",
                    ),

                client_reference_id=
                    g.user_id,

                metadata={
                    "veya_user_id":
                        g.user_id
                },
            )
        )

        return jsonify(
            {
                "url":
                    session.url
            }
        )

    except Exception:

        app.logger.exception(
            "Stripe checkout failed"
        )

        return jsonify(
            {
                "error":
                    "Could not create checkout session."
            }
        ), 500


@app.post(
    "/api/billing/webhook"
)
def stripe_webhook():

    stripe = stripe_client()

    if stripe is None:

        return jsonify(
            {
                "error":
                    "Stripe is not configured."
            }
        ), 503

    payload = request.get_data()

    signature = request.headers.get(
        "Stripe-Signature",
        "",
    )

    webhook_secret = os.getenv(
        "STRIPE_WEBHOOK_SECRET",
        "",
    )

    try:

        event = (
            stripe.Webhook.construct_event(
                payload,
                signature,
                webhook_secret,
            )
        )

    except Exception:

        return jsonify(
            {
                "error":
                    "Invalid webhook."
            }
        ), 400

    object_data = (
        event["data"]["object"]
    )

    if event["type"] in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
    }:

        metadata = (
            object_data.get(
                "metadata"
            )
            or {}
        )

        user_id = (
            metadata.get(
                "veya_user_id"
            )
            or object_data.get(
                "client_reference_id"
            )
        )

        if user_id:

            with DB_LOCK:

                conn = get_db()

                conn.execute(
                    """
                    UPDATE users
                    SET
                        plan = 'premium',
                        stripe_customer_id = ?
                    WHERE id = ?
                    """,
                    (
                        object_data.get(
                            "customer"
                        ),
                        user_id,
                    ),
                )

                conn.commit()
                conn.close()

    if (
        event["type"]
        == "customer.subscription.deleted"
    ):

        metadata = (
            object_data.get(
                "metadata"
            )
            or {}
        )

        user_id = metadata.get(
            "veya_user_id"
        )

        if user_id:

            with DB_LOCK:

                conn = get_db()

                conn.execute(
                    """
                    UPDATE users
                    SET plan = 'free'
                    WHERE id = ?
                    """,
                    (
                        user_id,
                    ),
                )

                conn.commit()
                conn.close()

    return jsonify(
        {
            "received":
                True
        }
    )


# ============================================================
# FRONTEND
# ============================================================

HTML = r"""
<!doctype html>

<html lang="en">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>Veya AI</title>

<style>

*{
    box-sizing:border-box;
}

body{
    margin:0;
    background:#080b12;
    color:#f4f7fb;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    height:100vh;
}

.app{
    display:grid;
    grid-template-columns:270px 1fr;
    height:100vh;
}

.sidebar{
    border-right:
        1px solid #202938;

    background:#0b0f17;

    padding:14px;

    display:flex;
    flex-direction:column;

    gap:10px;
}

.logo{
    font-size:26px;
    font-weight:850;

    padding:
        5px 8px 10px;
}

.new-chat,
.upgrade,
.send{
    border:0;

    border-radius:12px;

    padding:12px;

    font-weight:750;

    cursor:pointer;
}

.new-chat{
    background:#1a2230;
    color:#ffffff;
}

.upgrade{
    background:#72e6ae;
    color:#06120c;
}

.chat-list{
    overflow:auto;

    flex:1;
}

.chat-item{
    padding:10px;

    border-radius:10px;

    color:#b9c3d0;

    cursor:pointer;

    white-space:nowrap;

    overflow:hidden;

    text-overflow:ellipsis;
}

.chat-item:hover{
    background:#141b27;
}

.main{
    display:flex;

    flex-direction:column;

    min-width:0;
}

.topbar{
    height:62px;

    border-bottom:
        1px solid #202938;

    display:flex;

    align-items:center;

    justify-content:space-between;

    padding:
        0 18px;
}

.plan{
    font-size:12px;

    color:#72e6ae;
}

.messages{
    flex:1;

    overflow:auto;

    padding:
        28px 16px;
}

.message{
    max-width:850px;

    margin:
        0 auto 16px;

    padding:
        16px 18px;

    border-radius:16px;

    white-space:pre-wrap;

    line-height:1.65;
}

.message.user{
    background:#1d355b;
}

.message.assistant{
    background:#0f151f;

    border:
        1px solid #202938;
}

.meta{
    font-size:11px;

    color:#8995a6;

    margin-bottom:7px;
}

.composer{
    display:flex;

    gap:10px;

    padding:14px;

    border-top:
        1px solid #202938;
}

.composer textarea{
    flex:1;

    resize:none;

    min-height:52px;

    max-height:160px;

    background:#101722;

    color:#ffffff;

    border:
        1px solid #303b4c;

    border-radius:14px;

    padding:14px;

    font:inherit;

    outline:none;
}

.send{
    background:#ffffff;

    color:#0b0f17;

    padding:
        0 22px;
}

.send:disabled{
    opacity:.45;

    cursor:not-allowed;
}

@media(max-width:760px){

    .app{
        grid-template-columns:1fr;
    }

    .sidebar{
        display:none;
    }

    .topbar{
        height:56px;
    }

    .messages{
        padding:
            16px 8px;
    }

    .message{
        padding:
            13px;
    }

}

</style>

</head>

<body>

<div class="app">

<aside class="sidebar">

<div class="logo">
Veya
</div>

<button
    class="new-chat"
    onclick="newChat()"
>
＋ New chat
</button>

<button
    class="upgrade"
    onclick="upgrade()"
>
Upgrade • $20
</button>

<div
    id="chatList"
    class="chat-list"
></div>

</aside>


<section class="main">

<div class="topbar">

<b id="title">
Veya AI
</b>

<span
    id="plan"
    class="plan"
>
FREE
</span>

</div>


<div
    id="messages"
    class="messages"
></div>


<div class="composer">

<textarea
    id="input"
    placeholder="Message Veya..."
></textarea>

<button
    id="send"
    class="send"
    onclick="sendMessage()"
>
Send
</button>

</div>

</section>

</div>


<script>

let chatId = null;

const messages =
    document.getElementById(
        "messages"
    );

const input =
    document.getElementById(
        "input"
    );

const sendButton =
    document.getElementById(
        "send"
    );

const planBadge =
    document.getElementById(
        "plan"
    );


function addMessage(
    role,
    text,
    meta=""
){

    const box =
        document.createElement(
            "div"
        );

    box.className =
        "message " + role;


    if(meta){

        const metaBox =
            document.createElement(
                "div"
            );

        metaBox.className =
            "meta";

        metaBox.textContent =
            meta;

        box.appendChild(
            metaBox
        );
    }


    const content =
        document.createElement(
            "div"
        );

    content.textContent =
        text;

    box.appendChild(
        content
    );


    messages.appendChild(
        box
    );

    messages.scrollTop =
        messages.scrollHeight;
}


async function loadChats(){

    try{

        const response =
            await fetch(
                "/api/chats"
            );

        const chats =
            await response.json();

        const list =
            document.getElementById(
                "chatList"
            );

        list.innerHTML = "";


        chats.forEach(
            chat => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "chat-item";

                item.textContent =
                    chat.title;

                item.onclick =
                    () =>
                        loadChat(
                            chat.id
                        );

                list.appendChild(
                    item
                );

            }
        );

    }catch(error){

        console.error(
            error
        );

    }

}


async function loadChat(id){

    chatId = id;

    messages.innerHTML = "";


    const response =
        await fetch(
            "/api/chats/" + id
        );

    const data =
        await response.json();


    data.forEach(
        item => {

            addMessage(
                item.role === "user"
                    ? "user"
                    : "assistant",

                item.content,

                item.role === "user"
                    ? "You"
                    : "Veya"
            );

        }
    );

}


function newChat(){

    chatId = null;

    messages.innerHTML = "";


    addMessage(
        "assistant",

        "Hello! I’m Veya. Ask me anything and I’ll route the task to the appropriate specialist models.",

        "Veya"
    );

}


async function sendMessage(){

    const text =
        input.value.trim();


    if(!text){
        return;
    }


    addMessage(
        "user",
        text,
        "You"
    );


    input.value = "";

    sendButton.disabled = true;


    try{

        const response =
            await fetch(
                "/api/chat",
                {
                    method:
                        "POST",

                    headers:{
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                message:
                                    text,

                                chat_id:
                                    chatId
                            }
                        )
                }
            );


        const data =
            await response.json();


        if(!response.ok){

            throw new Error(
                data.error
                || "Request failed."
            );

        }


        chatId =
            data.chat_id;


        planBadge.textContent =
            (
                data.plan
                || "free"
            ).toUpperCase();


        const modelInfo =
            (
                data.models
                || []
            ).join(
                ", "
            );


        addMessage(
            "assistant",

            data.answer
            || "No answer returned.",

            "Veya • "
            + (
                data.domain
                || "general"
            )
            + (
                modelInfo
                    ? " • "
                    + modelInfo
                    : ""
            )
        );


        await loadChats();


    }catch(error){

        addMessage(
            "assistant",

            "Error: "
            + error.message,

            "System"
        );

    }finally{

        sendButton.disabled =
            false;

        input.focus();

    }

}


async function upgrade(){

    try{

        const response =
            await fetch(
                "/api/billing/create-checkout",
                {
                    method:
                        "POST"
                }
            );

        const data =
            await response.json();


        if(data.url){

            window.location.href =
                data.url;

            return;
        }


        alert(
            data.error
            || "Billing is not configured yet."
        );

    }catch(error){

        alert(
            "Billing is not available right now."
        );

    }

}


input.addEventListener(
    "keydown",
    event => {

        if(
            event.key === "Enter"
            && !event.shiftKey
        ){

            event.preventDefault();

            sendMessage();

        }

    }
);


newChat();

loadChats();

</script>

</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    response = render_template_string(
        HTML
    )

    # Persist anonymous browser user.
    response = app.make_response(
        response
    )

    response.set_cookie(
        "veya_user",
        g.user_id,
        max_age=60 * 60 * 24 * 365,
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