import os
import ast
import json
import math
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, request, jsonify, render_template_string
from groq import Groq

# Optional scientific libraries
try:
    import sympy as sp
except Exception:
    sp = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import scipy
except Exception:
    scipy = None

# Optional browser automation
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


# ============================================================
# VEYA
# ============================================================

APP_NAME = "Veya"
VERSION = "4.0"

# ============================================================
# API KEY
# ============================================================
#
# Put your API key here.
#
# IMPORTANT:
# Never publish this file in a public GitHub repository.
#

GROQ_API_KEY = "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"

if not GROQ_API_KEY or GROQ_API_KEY.startswith("PASTE_"):
    raise RuntimeError(
        "Put your Groq API key in GROQ_API_KEY at the top of app.py."
    )

MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ============================================================
# LIMITS
# ============================================================

MAX_TOOL_ROUNDS = 8
MAX_HISTORY = 20
MAX_MESSAGE_LENGTH = 30000

# Number of expert reports activated for one task.
DEFAULT_ACTIVE_AGENTS = 8
MAX_ACTIVE_AGENTS = 16

# 100 Master Agents.
MASTER_AGENT_COUNT = 100

# 50 virtual worker slots per master.
WORKER_SLOTS_PER_MASTER = 50

# ============================================================
# SESSION MEMORY
# ============================================================

SESSIONS: Dict[str, List[Dict[str, str]]] = {}

SESSION_LOCK = threading.Lock()


# ============================================================
# 100 MASTER AGENTS
# ============================================================

DOMAIN_DEFINITIONS = {

    "mathematics": [
        "algebra",
        "calculus",
        "geometry",
        "number theory",
        "probability",
        "statistics",
        "linear algebra",
        "discrete mathematics",
        "optimization",
        "mathematical proof",
    ],

    "physics": [
        "mechanics",
        "electromagnetism",
        "thermodynamics",
        "optics",
        "relativity",
        "quantum physics",
        "fluid mechanics",
        "astrophysics",
        "particle physics",
        "physics problem solving",
    ],

    "chemistry": [
        "organic chemistry",
        "inorganic chemistry",
        "physical chemistry",
        "analytical chemistry",
        "biochemistry",
        "chemical equations",
        "molecular chemistry",
        "thermochemistry",
        "electrochemistry",
        "chemistry reasoning",
    ],

    "biology": [
        "cell biology",
        "genetics",
        "molecular biology",
        "microbiology",
        "ecology",
        "evolution",
        "neuroscience",
        "bioinformatics",
        "biochemistry",
        "biology reasoning",
    ],

    "computer_science": [
        "algorithms",
        "data structures",
        "operating systems",
        "databases",
        "computer networks",
        "distributed systems",
        "AI",
        "machine learning",
        "security engineering",
        "computer science theory",
    ],

    "software_engineering": [
        "Python engineering",
        "JavaScript engineering",
        "backend engineering",
        "frontend engineering",
        "API engineering",
        "testing",
        "debugging",
        "DevOps",
        "system architecture",
        "code review",
    ],

    "data_science": [
        "data analysis",
        "statistics",
        "data cleaning",
        "visualization",
        "machine learning",
        "feature engineering",
        "model evaluation",
        "experimentation",
        "forecasting",
        "data engineering",
    ],

    "research": [
        "literature analysis",
        "evidence evaluation",
        "source comparison",
        "scientific reasoning",
        "research design",
        "hypothesis analysis",
        "fact checking",
        "technical research",
        "research synthesis",
        "uncertainty analysis",
    ],

    "business": [
        "business strategy",
        "product strategy",
        "startup analysis",
        "market analysis",
        "operations",
        "business analytics",
        "pricing",
        "growth",
        "competitive analysis",
        "product management",
    ],

    "creative": [
        "writing",
        "storytelling",
        "design",
        "branding",
        "marketing",
        "content strategy",
        "creative ideation",
        "game concepts",
        "UX concepts",
        "creative problem solving",
    ],
}


def build_master_agents() -> Dict[str, Dict[str, Any]]:
    agents = {}

    counter = 1

    for domain, specialties in DOMAIN_DEFINITIONS.items():

        for specialty in specialties:

            agent_id = f"M{counter:03d}"

            agents[agent_id] = {
                "id": agent_id,
                "name": f"{specialty.title()} Master",
                "domain": domain,
                "specialty": specialty,
                "worker_slots": WORKER_SLOTS_PER_MASTER,
                "role": (
                    f"Act as an expert in {specialty}. "
                    f"Analyze the user's task independently, "
                    f"identify errors and produce evidence-based conclusions."
                ),
            }

            counter += 1

    return agents


MASTER_AGENTS = build_master_agents()


# ============================================================
# VERIFY 100 AGENTS EXIST
# ============================================================

assert len(MASTER_AGENTS) == MASTER_AGENT_COUNT


# ============================================================
# KEYWORD ROUTER
# ============================================================

DOMAIN_KEYWORDS = {

    "mathematics": [
        "math",
        "mathematics",
        "equation",
        "integral",
        "derivative",
        "algebra",
        "geometry",
        "probability",
        "statistics",
        "matrix",
        "proof",
    ],

    "physics": [
        "physics",
        "force",
        "velocity",
        "acceleration",
        "energy",
        "momentum",
        "gravity",
        "electric",
        "magnetic",
        "quantum",
    ],

    "chemistry": [
        "chemistry",
        "chemical",
        "molecule",
        "atom",
        "reaction",
        "organic",
        "compound",
        "acid",
        "base",
    ],

    "biology": [
        "biology",
        "cell",
        "dna",
        "gene",
        "protein",
        "genetics",
        "organism",
        "evolution",
        "bacteria",
    ],

    "computer_science": [
        "algorithm",
        "data structure",
        "operating system",
        "database",
        "network",
        "machine learning",
        "artificial intelligence",
        "distributed system",
    ],

    "software_engineering": [
        "python",
        "javascript",
        "typescript",
        "flask",
        "react",
        "api",
        "backend",
        "frontend",
        "docker",
        "debug",
        "code",
        "programming",
    ],

    "data_science": [
        "dataset",
        "pandas",
        "numpy",
        "scipy",
        "data analysis",
        "regression",
        "classification",
        "statistics",
        "visualization",
    ],

    "research": [
        "research",
        "paper",
        "study",
        "evidence",
        "source",
        "latest",
        "compare",
        "literature",
    ],

    "business": [
        "business",
        "startup",
        "company",
        "market",
        "product",
        "strategy",
        "pricing",
        "growth",
        "customer",
    ],

    "creative": [
        "write",
        "story",
        "design",
        "brand",
        "marketing",
        "creative",
        "game",
        "content",
        "logo",
    ],
}


def route_domains(text: str) -> List[str]:

    text = text.lower()

    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        scores[domain] = score

    ranked = sorted(
        scores,
        key=scores.get,
        reverse=True
    )

    selected = [
        domain
        for domain in ranked
        if scores[domain] > 0
    ]

    if not selected:
        return ["computer_science", "research", "mathematics"]

    return selected[:4]


# ============================================================
# SELECT MASTER AGENTS
# ============================================================

def select_agents(
    user_message: str,
    count: int = DEFAULT_ACTIVE_AGENTS
) -> List[Dict[str, Any]]:

    count = max(
        1,
        min(count, MAX_ACTIVE_AGENTS)
    )

    domains = route_domains(user_message)

    candidates = []

    for agent in MASTER_AGENTS.values():

        if agent["domain"] in domains:
            candidates.append(agent)

    # Add independent verification agents.
    verification_domains = [
        "research",
        "mathematics",
        "computer_science",
    ]

    for agent in MASTER_AGENTS.values():

        if (
            agent["domain"] in verification_domains
            and agent not in candidates
        ):
            candidates.append(agent)

    return candidates[:count]


# ============================================================
# SAFE CALCULATOR
# ============================================================

MATH_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
}


ALLOWED_AST = (
    ast.Expression,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.Name,
)


def safe_calculator(expression: str) -> str:

    if len(expression) > 1000:
        return "Expression too long."

    try:

        tree = ast.parse(
            expression,
            mode="eval"
        )

        for node in ast.walk(tree):

            if not isinstance(node, ALLOWED_AST):
                return "Calculator rejected this expression."

            if isinstance(node, ast.Call):

                if not isinstance(
                    node.func,
                    ast.Name
                ):
                    return "Calculator rejected this function."

                if node.func.id not in MATH_FUNCTIONS:
                    return "Function not allowed."

            if isinstance(node, ast.Name):

                if node.id not in MATH_FUNCTIONS:
                    return "Name not allowed."

        return str(
            eval(
                compile(
                    tree,
                    "<calculator>",
                    "eval"
                ),
                {
                    "__builtins__": {}
                },
                MATH_FUNCTIONS
            )
        )

    except Exception as exc:

        return f"Calculator error: {exc}"


# ============================================================
# SYMBOLIC MATH
# ============================================================

def symbolic_math(expression: str) -> str:

    if sp is None:
        return "SymPy is unavailable."

    if len(expression) > 5000:
        return "Expression too large."

    try:

        result = sp.sympify(expression)

        return str(
            sp.simplify(result)
        )

    except Exception as exc:

        return f"SymPy error: {exc}"


# ============================================================
# DATA ANALYSIS
# ============================================================

def analyze_json_data(data: str) -> str:

    if pd is None:
        return "Pandas is unavailable."

    try:

        rows = json.loads(data)

        frame = pd.DataFrame(rows)

        result = {
            "rows": len(frame),
            "columns": list(frame.columns),
            "missing_values": {
                str(k): int(v)
                for k, v in frame.isna().sum().items()
            },
        }

        if len(frame.select_dtypes(include="number").columns):

            result["numeric_summary"] = (
                frame
                .describe(
                    include="number"
                )
                .to_dict()
            )

        return json.dumps(
            result,
            indent=2,
            default=str
        )

    except Exception as exc:

        return f"Data analysis error: {exc}"


# ============================================================
# SAFE TOOL REGISTRY
# ============================================================

TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Safely calculate a mathematical expression."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string"
                    }
                },
                "required": [
                    "expression"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "symbolic_math",
            "description": (
                "Perform symbolic mathematics using SymPy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string"
                    }
                },
                "required": [
                    "expression"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "analyze_json_data",
            "description": (
                "Analyze a JSON array using Pandas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string"
                    }
                },
                "required": [
                    "data"
                ]
            }
        }
    },
]


def execute_tool(
    name: str,
    arguments: Dict[str, Any]
) -> str:

    if name == "calculator":

        return safe_calculator(
            str(
                arguments.get(
                    "expression",
                    ""
                )
            )
        )

    if name == "symbolic_math":

        return symbolic_math(
            str(
                arguments.get(
                    "expression",
                    ""
                )
            )
        )

    if name == "analyze_json_data":

        return analyze_json_data(
            str(
                arguments.get(
                    "data",
                    "[]"
                )
            )
        )

    return "Unknown tool."


# ============================================================
# AGENT PROMPT
# ============================================================

def build_agent_prompt(
    agent: Dict[str, Any],
    user_message: str
) -> str:

    return f"""
You are Master Agent {agent["id"]}.

Name:
{agent["name"]}

Domain:
{agent["domain"]}

Specialty:
{agent["specialty"]}

You have {agent["worker_slots"]} virtual worker slots.

Your role:
{agent["role"]}

USER TASK:
{user_message}

Work independently.

Do not blindly agree with another agent.

Check assumptions.

For numerical problems, verify calculations.

For programming, identify bugs and edge cases.

For scientific questions, distinguish facts from uncertainty.

For research questions, never invent sources.

Do not claim that you performed an external action unless a real tool performed it.

Return a concise expert report containing:

1. Your interpretation.
2. Your proposed solution.
3. Important calculations or evidence.
4. Potential mistakes or uncertainty.
5. A final recommendation.

Do not reveal private chain-of-thought.
Provide useful conclusions and concise reasoning instead.
"""


# ============================================================
# SINGLE MASTER AGENT CALL
# ============================================================

def ask_master_agent(
    agent: Dict[str, Any],
    user_message: str
) -> str:

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": build_agent_prompt(
                        agent,
                        user_message
                    )
                }
            ],
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort="high",
            temperature=0.15,
            max_tokens=5000,
        )

        message = response.choices[0].message

        tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if not tool_calls:

            return message.content or ""

        tool_messages = [
            message
        ]

        for call in tool_calls:

            try:

                arguments = json.loads(
                    call.function.arguments
                )

            except Exception:

                arguments = {}

            result = execute_tool(
                call.function.name,
                arguments
            )

            tool_messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result
            })

        second = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": build_agent_prompt(
                        agent,
                        user_message
                    )
                }
            ] + tool_messages,
            reasoning_effort="high",
            temperature=0.1,
            max_tokens=5000,
        )

        return (
            second
            .choices[0]
            .message
            .content
            or ""
        )

    except Exception as exc:

        logging.exception(
            "Agent %s failed",
            agent["id"]
        )

        return (
            f"Agent {agent['id']} could not complete "
            f"its report."
        )


# ============================================================
# SWARM JUDGE
# ============================================================

def judge_reports(
    user_message: str,
    agents: List[Dict[str, Any]],
    reports: List[str]
) -> str:

    packet = []

    for agent, report in zip(
        agents,
        reports
    ):

        packet.append(
            f"""
AGENT {agent["id"]}
NAME: {agent["name"]}
DOMAIN: {agent["domain"]}
SPECIALTY: {agent["specialty"]}

REPORT:
{report}
"""
        )

    evidence = "\n".join(packet)

    judge_prompt = f"""
You are the Veya Swarm Judge.

A group of independent specialist agents analyzed the same user task.

USER TASK:
{user_message}

SPECIALIST REPORTS:
{evidence}

Your job is NOT to vote blindly.

You must:

1. Compare the reports.
2. Detect contradictions.
3. Check calculations where possible.
4. Reject unsupported claims.
5. Prefer internally consistent conclusions.
6. Combine useful insights.
7. Clearly identify uncertainty.
8. Produce one final answer to the user.

If agents disagree, explain the important disagreement briefly
and choose the conclusion best supported by the available evidence.

Never invent information merely to make the agents agree.

Do not reveal private chain-of-thought.

Return only the final user-facing answer.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": judge_prompt
            }
        ],
        reasoning_effort="high",
        temperature=0.1,
        max_tokens=10000,
    )

    return (
        response
        .choices[0]
        .message
        .content
        or "No final answer was produced."
    )


# ============================================================
# MEMORY
# ============================================================

def get_history(
    session_id: str
) -> List[Dict[str, str]]:

    with SESSION_LOCK:

        return list(
            SESSIONS.get(
                session_id,
                []
            )
        )


def save_message(
    session_id: str,
    role: str,
    content: str
):

    with SESSION_LOCK:

        history = SESSIONS.setdefault(
            session_id,
            []
        )

        history.append({
            "role": role,
            "content": content
        })

        del history[:-MAX_HISTORY]


# ============================================================
# FULL SWARM
# ============================================================

def run_swarm(
    session_id: str,
    user_message: str,
    agent_count: int = DEFAULT_ACTIVE_AGENTS
) -> Dict[str, Any]:

    agents = select_agents(
        user_message,
        agent_count
    )

    save_message(
        session_id,
        "user",
        user_message
    )

    reports = []

    for agent in agents:

        report = ask_master_agent(
            agent,
            user_message
        )

        reports.append(report)

    final_answer = judge_reports(
        user_message,
        agents,
        reports
    )

    save_message(
        session_id,
        "assistant",
        final_answer
    )

    return {
        "answer": final_answer,

        "active_agents": [
            {
                "id": agent["id"],
                "name": agent["name"],
                "domain": agent["domain"],
                "specialty": agent["specialty"],
                "worker_slots": agent["worker_slots"],
            }
            for agent in agents
        ],

        "master_agents_available": len(
            MASTER_AGENTS
        ),

        "virtual_worker_slots": (
            len(MASTER_AGENTS)
            * WORKER_SLOTS_PER_MASTER
        ),

        "judge": "Swarm Judge",
    }


# ============================================================
# JSON ERROR HANDLER
# ============================================================

@app.errorhandler(Exception)
def handle_exception(error):

    logging.exception(
        "Unhandled server error"
    )

    return jsonify({
        "status": "error",
        "error": (
            "Veya encountered a server error. "
            "Check the server logs for details."
        )
    }), 500


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({
        "status": "online",
        "name": APP_NAME,
        "version": VERSION,
        "model": MODEL,
        "master_agents": len(MASTER_AGENTS),
        "worker_slots": (
            len(MASTER_AGENTS)
            * WORKER_SLOTS_PER_MASTER
        ),
        "tools": [
            tool["function"]["name"]
            for tool in TOOLS
        ],
        "browser_available": (
            sync_playwright is not None
        ),
        "scientific_stack": {
            "sympy": sp is not None,
            "numpy": np is not None,
            "scipy": scipy is not None,
            "pandas": pd is not None,
        },
    })


# ============================================================
# AGENT REGISTRY
# ============================================================

@app.get("/api/agents")
def agents():

    return jsonify({
        "master_agents": list(
            MASTER_AGENTS.values()
        ),
        "master_count": len(
            MASTER_AGENTS
        ),
        "virtual_worker_slots": (
            len(MASTER_AGENTS)
            * WORKER_SLOTS_PER_MASTER
        ),
    })


# ============================================================
# CHAT
# ============================================================

@app.post("/api/chat")
def chat():

    body = request.get_json(
        silent=True
    )

    if not isinstance(body, dict):

        return jsonify({
            "status": "error",
            "error": "Request body must be JSON."
        }), 400

    message = str(
        body.get(
            "message",
            ""
        )
    ).strip()

    if not message:

        return jsonify({
            "status": "error",
            "error": "Message is required."
        }), 400

    if len(message) > MAX_MESSAGE_LENGTH:

        return jsonify({
            "status": "error",
            "error": "Message is too long."
        }), 413

    session_id = str(
        body.get(
            "session_id"
        )
        or uuid.uuid4()
    )

    try:

        requested_agents = int(
            body.get(
                "agents",
                DEFAULT_ACTIVE_AGENTS
            )
        )

    except Exception:

        requested_agents = DEFAULT_ACTIVE_AGENTS

    result = run_swarm(
        session_id,
        message,
        requested_agents
    )

    return jsonify({
        "status": "success",
        "session_id": session_id,
        "assistant": APP_NAME,
        **result
    })


# ============================================================
# SAFE BROWSER CONTROL
# ============================================================
#
# This controls a browser running on the SERVER/container.
# It does NOT control the user's Android Chrome.
#
# It does not bypass website authentication or permissions.
# ============================================================

def browser_open(url: str) -> str:

    if sync_playwright is None:
        return "Playwright is not installed."

    if not url.startswith(
        ("http://", "https://")
    ):
        return "Only HTTP/HTTPS URLs are supported."

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            title = page.title()

            current_url = page.url

            text = page.locator(
                "body"
            ).inner_text(
                timeout=10000
            )[:10000]

            browser.close()

            return json.dumps({
                "title": title,
                "url": current_url,
                "text": text
            }, indent=2)

    except Exception as exc:

        return f"Browser error: {exc}"


@app.post("/api/browser/open")
def browser_open_api():

    body = request.get_json(
        silent=True
    ) or {}

    url = str(
        body.get(
            "url",
            ""
        )
    ).strip()

    if not url:

        return jsonify({
            "status": "error",
            "error": "URL required."
        }), 400

    return jsonify({
        "status": "success",
        "result": browser_open(url)
    })


# ============================================================
# ANDROID BRIDGE
# ============================================================
#
# IMPORTANT:
#
# Python cannot magically obtain control of an Android phone.
#
# A real Android companion app must:
#
# 1. Be installed by the user.
# 2. Receive Android OS permissions through normal Android UI.
# 3. Authenticate requests from Veya.
# 4. Perform only operations allowed by those permissions.
#
# This backend therefore provides a SAFE command boundary.
#
# It deliberately does not bypass Android security.
# ============================================================

ANDROID_BRIDGE_ENABLED = False

ANDROID_BRIDGE_URL = os.environ.get(
    "ANDROID_BRIDGE_URL",
    ""
)

ANDROID_BRIDGE_TOKEN = os.environ.get(
    "ANDROID_BRIDGE_TOKEN",
    ""
)


@app.get("/api/android/status")
def android_status():

    return jsonify({
        "enabled": ANDROID_BRIDGE_ENABLED,
        "connected": bool(
            ANDROID_BRIDGE_URL
            and ANDROID_BRIDGE_TOKEN
        ),
        "message": (
            "Android control requires a user-installed "
            "companion app and Android OS permissions."
        )
    })


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

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background:
        radial-gradient(
            circle at top,
            #17203a,
            #070a10 55%
        );
    color: #f5f7fb;
    font-family:
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        sans-serif;
}

header {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 22px;
    border-bottom: 1px solid #242b3a;
    backdrop-filter: blur(15px);
}

.logo {
    font-size: 25px;
    font-weight: 850;
}

.status {
    color: #68e6a3;
    font-size: 12px;
}

.container {
    height: calc(100vh - 72px);
    display: flex;
    flex-direction: column;
    max-width: 1200px;
    margin: auto;
}

.stats {
    padding: 10px 18px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.stat {
    border: 1px solid #293247;
    background: #0d121c;
    padding: 7px 10px;
    border-radius: 9px;
    font-size: 11px;
    color: #aab4c7;
}

#messages {
    flex: 1;
    overflow-y: auto;
    padding: 22px;
}

.message {
    max-width: 900px;
    margin: 14px auto;
    padding: 17px;
    border-radius: 16px;
    line-height: 1.65;
    white-space: pre-wrap;
}

.user {
    background: #1c3e78;
}

.ai {
    background: #111722;
    border: 1px solid #273044;
}

.meta {
    color: #8591a6;
    font-size: 11px;
    margin-bottom: 8px;
}

.agents {
    margin-top: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.agent {
    background: #182132;
    border: 1px solid #303d55;
    padding: 5px 8px;
    border-radius: 7px;
    font-size: 10px;
    color: #b7c2d6;
}

.composer {
    padding: 16px;
    display: flex;
    gap: 9px;
    border-top: 1px solid #242b3a;
}

input {
    flex: 1;
    min-width: 0;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #303a4e;
    background: #0e131c;
    color: white;
    outline: none;
}

button {
    border: 0;
    border-radius: 12px;
    padding: 0 21px;
    background: white;
    color: #070a10;
    font-weight: 800;
    cursor: pointer;
}

button:disabled {
    opacity: .5;
}

</style>

</head>

<body>

<header>

<div class="logo">
Veya
</div>

<div class="status">
● ONLINE
</div>

</header>

<div class="container">

<div class="stats">

<div class="stat">
100 Master Agents
</div>

<div class="stat">
5,000 Virtual Worker Slots
</div>

<div class="stat">
Multi-Agent Verification
</div>

<div class="stat">
Tool Calling
</div>

</div>

<div id="messages">

<div class="message ai">

<div class="meta">
Veya • Swarm Intelligence
</div>

Hello. I'm Veya.

I can route difficult tasks to multiple
specialist agents and compare their reports
before producing a final answer.

</div>

</div>

<div class="composer">

<input
id="input"
placeholder="Ask Veya anything..."
autocomplete="off"
/>

<button
id="send"
>
Send
</button>

</div>

</div>

<script>

const input =
    document.getElementById("input");

const send =
    document.getElementById("send");

const messages =
    document.getElementById("messages");

let sessionId =
    localStorage.getItem("veya_session");

function addMessage(
    text,
    type,
    meta = ""
) {

    const box =
        document.createElement("div");

    box.className =
        "message " + type;

    if (meta) {

        const m =
            document.createElement("div");

        m.className = "meta";

        m.textContent = meta;

        box.appendChild(m);
    }

    const content =
        document.createElement("div");

    content.textContent = text;

    box.appendChild(content);

    messages.appendChild(box);

    messages.scrollTop =
        messages.scrollHeight;

    return box;
}

function addAgents(
    box,
    agents
) {

    if (!agents || !agents.length) {
        return;
    }

    const wrapper =
        document.createElement("div");

    wrapper.className = "agents";

    for (const agent of agents) {

        const tag =
            document.createElement("div");

        tag.className = "agent";

        tag.textContent =
            agent.id +
            " • " +
            agent.specialty;

        wrapper.appendChild(tag);
    }

    box.appendChild(wrapper);
}

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    addMessage(
        text,
        "user",
        "You"
    );

    input.value = "";

    send.disabled = true;

    const loading =
        addMessage(
            "Veya is consulting specialist agents...",
            "ai",
            "Swarm"
        );

    try {

        const response =
            await fetch(
                "/api/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: text,
                        session_id: sessionId,
                        agents: 8
                    })
                }
            );

        const raw =
            await response.text();

        let data;

        try {

            data =
                JSON.parse(raw);

        } catch {

            throw new Error(
                "Server returned an invalid response. HTTP " +
                response.status
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                "Server request failed."
            );
        }

        if (data.session_id) {

            sessionId =
                data.session_id;

            localStorage.setItem(
                "veya_session",
                sessionId
            );
        }

        loading.remove();

        const answerBox =
            addMessage(
                data.answer,
                "ai",
                "Veya • Swarm Judge"
            );

        addAgents(
            answerBox,
            data.active_agents
        );

    } catch (error) {

        loading.remove();

        addMessage(
            "Veya could not complete this request.\n\n" +
            error.message,
            "ai",
            "System"
        );

    } finally {

        send.disabled = false;

        input.focus();
    }
}

send.addEventListener(
    "click",
    sendMessage
);

input.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {
            sendMessage();
        }

    }
);

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
# START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )