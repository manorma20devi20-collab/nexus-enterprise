import os
import ast
import json
import math
import re
import uuid
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from ipaddress import ip_address

from flask import Flask, jsonify, request, render_template_string
from groq import Groq

# Optional local tools
try:
    import sympy as sp
except Exception:
    sp = None

try:
    import pandas as pd
except Exception:
    pd = None

# Optional browser automation.
# This controls a browser running on the SERVER, not the user's phone/PC.
try:
    from playwright.sync_api import sync_playwright, Browser, Page
except Exception:
    sync_playwright = None
    Browser = None
    Page = None


# ============================================================
# VEYA 3.0
# ============================================================
# IMPORTANT:
# Put your Groq key here.
# Keep this repository PRIVATE. A public repository would expose
# this secret to anyone who can read the source.
GROQ_API_KEY = "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"

APP_NAME = "Veya"
VERSION = "3.0"

# Current Groq GPT-OSS model.
MODEL = "openai/gpt-oss-120b"

# Keep these controls in code so Render does not need API-key
# environment variables or a web form.
ENABLE_SERVER_BROWSER = True
ENABLE_SERVER_DESKTOP_CONTROL = False

MAX_TOOL_ROUNDS = 8
MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_CHARS = 12000
MAX_OUTPUT_TOKENS = 12000

# Browser safety limits.
MAX_BROWSER_TEXT = 18000
BROWSER_TIMEOUT_MS = 15000
ALLOWED_BROWSER_SCHEMES = {"http", "https"}

if not GROQ_API_KEY or GROQ_API_KEY == "PASTE_YOUR_GROQ_API_KEY_HERE":
    raise RuntimeError(
        "Put your Groq API key into GROQ_API_KEY at the top of app.py."
    )

client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024


# ============================================================
# SESSION MEMORY
# ============================================================

SESSIONS: Dict[str, List[Dict[str, Any]]] = {}
SESSION_LOCK = threading.Lock()


def get_history(session_id: str) -> List[Dict[str, Any]]:
    with SESSION_LOCK:
        return list(SESSIONS.get(session_id, []))


def append_history(session_id: str, message: Dict[str, Any]) -> None:
    with SESSION_LOCK:
        history = SESSIONS.setdefault(session_id, [])
        history.append(message)
        # Keep only recent conversation messages.
        SESSIONS[session_id] = history[-MAX_HISTORY_MESSAGES:]


# ============================================================
# SPECIALIST AGENTS
# ============================================================

SPECIALISTS = {
    "general": {
        "name": "General Intelligence",
        "description": "General reasoning, planning, explanation and problem solving.",
    },
    "mathematics": {
        "name": "Mathematics Agent",
        "description": "Algebra, geometry, calculus, probability, statistics, number theory and linear algebra.",
    },
    "physics": {
        "name": "Physics Agent",
        "description": "Mechanics, electromagnetism, thermodynamics, optics, relativity and quantum concepts.",
    },
    "chemistry": {
        "name": "Chemistry Agent",
        "description": "Organic, inorganic, physical and analytical chemistry.",
    },
    "biology": {
        "name": "Biology Agent",
        "description": "Cell biology, genetics, molecular biology, ecology and evolution.",
    },
    "computer_science": {
        "name": "Computer Science Agent",
        "description": "Algorithms, data structures, operating systems, databases, AI/ML and distributed systems.",
    },
    "software_engineering": {
        "name": "Software Engineering Agent",
        "description": "Programming, architecture, debugging, testing, APIs, backend, frontend, DevOps and security.",
    },
    "data_science": {
        "name": "Data Science Agent",
        "description": "Data analysis, statistics, visualization and machine learning.",
    },
    "research": {
        "name": "Research Agent",
        "description": "Evidence-aware research, source comparison and current-information tasks.",
    },
    "business": {
        "name": "Business Agent",
        "description": "Business analysis, product strategy, operations, marketing and analytics.",
    },
    "creative": {
        "name": "Creative Agent",
        "description": "Writing, ideation, design concepts, storytelling and creative problem solving.",
    },
    "productivity": {
        "name": "Productivity Agent",
        "description": "Planning, summarization, organization, workflows and workspace tasks.",
    },
    "cybersecurity": {
        "name": "Cybersecurity Agent",
        "description": "Defensive security, secure coding, threat awareness and system hardening.",
    },
    "health_science": {
        "name": "Health & Biology Science Agent",
        "description": "General educational health, biology and life-science information; not diagnosis.",
    },
    "robotics": {
        "name": "Robotics & IoT Agent",
        "description": "Robotics concepts, sensors, control systems, IoT architecture and simulation.",
    },
}


ROUTING_RULES = {
    "mathematics": [
        "math", "mathematics", "equation", "algebra", "geometry", "calculus",
        "integral", "derivative", "probability", "statistics", "matrix",
    ],
    "physics": [
        "physics", "force", "velocity", "acceleration", "momentum",
        "energy", "gravity", "electric field", "magnetic",
    ],
    "chemistry": [
        "chemistry", "molecule", "reaction", "atom", "chemical",
        "organic chemistry", "inorganic",
    ],
    "biology": [
        "biology", "cell", "gene", "dna", "protein", "genetics",
        "organism", "ecology", "evolution",
    ],
    "software_engineering": [
        "python", "javascript", "typescript", "flask", "react", "api",
        "backend", "frontend", "software", "debug", "code", "programming",
        "docker", "database", "github",
    ],
    "data_science": [
        "dataset", "pandas", "numpy", "machine learning", "regression",
        "data analysis", "csv", "dataframe",
    ],
    "research": [
        "research", "latest", "paper", "study", "source", "evidence",
        "literature", "citation", "compare",
    ],
    "business": [
        "business", "startup", "company", "market", "product", "strategy",
        "sales", "marketing", "analytics", "finance",
    ],
    "productivity": [
        "plan", "schedule", "organize", "todo", "summarize", "notes",
        "productivity", "workflow",
    ],
    "cybersecurity": [
        "cybersecurity", "cyber security", "security", "vulnerability",
        "secure", "malware", "phishing", "hardening",
    ],
    "health_science": [
        "health", "biology", "medical", "medicine", "disease", "nutrition",
        "anatomy", "physiology",
    ],
    "robotics": [
        "robot", "robotics", "iot", "sensor", "arduino", "raspberry pi",
        "autonomous", "control system",
    ],
    "creative": [
        "write", "story", "poem", "design", "creative", "logo", "script",
        "caption", "idea", "brainstorm",
    ],
}


def classify_domain(user_message: str) -> str:
    text = user_message.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in ROUTING_RULES.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


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
    "fabs": math.fabs,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
}

MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def safe_calculator(expression: str) -> str:
    if len(expression) > 500:
        return "Calculator rejected the expression: too long."

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return "Calculator rejected the expression: invalid syntax."

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.Name) and node.id in MATH_CONSTANTS:
            return MATH_CONSTANTS[node.id]

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return +value if isinstance(node.op, ast.UAdd) else -value

        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
        ):
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                if abs(right) > 1000:
                    raise ValueError("Exponent is too large.")
                return left ** right
            return left % right

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = MATH_FUNCTIONS.get(node.func.id)
            if function is None or node.keywords:
                raise ValueError("Function is not allowed.")
            return function(*(evaluate(arg) for arg in node.args))

        raise ValueError("Expression contains an unsupported operation.")

    try:
        result = evaluate(tree)
        if not math.isfinite(float(result)):
            return "Calculator result is not finite."
        return str(result)
    except Exception as exc:
        return f"Calculator error: {exc}"


# ============================================================
# SYMBOLIC + DATA TOOLS
# ============================================================

def symbolic_math(expression: str) -> str:
    if sp is None:
        return "SymPy is not installed."
    if len(expression) > 1200:
        return "Expression is too long."

    try:
        result = sp.simplify(sp.sympify(expression))
        return str(result)
    except Exception as exc:
        return f"Symbolic math error: {exc}"


def analyze_json_data(data: str) -> str:
    if pd is None:
        return "Pandas is not installed."
    if len(data) > 100_000:
        return "Dataset is too large for this prototype."

    try:
        rows = json.loads(data)
        if not isinstance(rows, list):
            return "Expected a JSON array of records."

        frame = pd.DataFrame(rows)

        result = {
            "rows": int(len(frame)),
            "columns": [str(column) for column in frame.columns],
            "missing_values": {
                str(key): int(value)
                for key, value in frame.isna().sum().items()
            },
        }

        numeric = frame.select_dtypes(include="number")
        if not numeric.empty:
            result["numeric_summary"] = json.loads(numeric.describe().to_json())

        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        return f"Data analysis error: {exc}"


# ============================================================
# SERVER-SIDE BROWSER
# ============================================================
# This can automate a browser inside the Render container.
# It cannot control the user's Android/Windows browser.

_BROWSER = None
_BROWSER_PAGE: Optional[Any] = None
_BROWSER_LOCK = threading.Lock()


def valid_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_BROWSER_SCHEMES or not parsed.hostname:
            return False

        host = parsed.hostname.lower()

        # Prevent obvious localhost/private-network targets.
        if host in {"localhost", "127.0.0.1", "::1"}:
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
    except Exception:
        return False


def browser_open(url: str) -> str:
    global _BROWSER, _BROWSER_PAGE

    if not ENABLE_SERVER_BROWSER:
        return "Server browser control is disabled."

    if sync_playwright is None:
        return "Playwright is not installed."

    if not valid_public_url(url):
        return "Browser rejected this URL. Only public http/https URLs are allowed."

    with _BROWSER_LOCK:
        try:
            if _BROWSER is None:
                playwright = sync_playwright().start()
                _BROWSER = playwright.chromium.launch(headless=True)

            if _BROWSER_PAGE is None or _BROWSER_PAGE.is_closed():
                _BROWSER_PAGE = _BROWSER.new_page()

            _BROWSER_PAGE.goto(
                url,
                wait_until="domcontentloaded",
                timeout=BROWSER_TIMEOUT_MS,
            )

            title = _BROWSER_PAGE.title()
            text = _BROWSER_PAGE.locator("body").inner_text(
                timeout=BROWSER_TIMEOUT_MS
            )

            return (
                f"TITLE: {title}\n"
                f"URL: {_BROWSER_PAGE.url}\n\n"
                f"PAGE TEXT:\n{text[:MAX_BROWSER_TEXT]}"
            )
        except Exception as exc:
            return f"Browser error: {exc}"


def browser_click(selector: str) -> str:
    global _BROWSER_PAGE

    if not ENABLE_SERVER_BROWSER:
        return "Server browser control is disabled."

    if not selector or len(selector) > 500:
        return "Invalid selector."

    with _BROWSER_LOCK:
        try:
            if _BROWSER_PAGE is None or _BROWSER_PAGE.is_closed():
                return "No browser page is open. Open a public URL first."

            _BROWSER_PAGE.locator(selector).first.click(
                timeout=BROWSER_TIMEOUT_MS
            )
            return f"Clicked: {selector}"
        except Exception as exc:
            return f"Browser click error: {exc}"


def browser_fill(selector: str, value: str) -> str:
    global _BROWSER_PAGE

    if not ENABLE_SERVER_BROWSER:
        return "Server browser control is disabled."

    if len(selector) > 500 or len(value) > 5000:
        return "Selector or value is too long."

    with _BROWSER_LOCK:
        try:
            if _BROWSER_PAGE is None or _BROWSER_PAGE.is_closed():
                return "No browser page is open."

            _BROWSER_PAGE.locator(selector).first.fill(
                value,
                timeout=BROWSER_TIMEOUT_MS
            )
            return f"Filled: {selector}"
        except Exception as exc:
            return f"Browser fill error: {exc}"


def browser_press(key: str) -> str:
    global _BROWSER_PAGE

    if not ENABLE_SERVER_BROWSER:
        return "Server browser control is disabled."

    allowed_keys = {
        "Enter", "Tab", "Escape", "ArrowUp", "ArrowDown",
        "ArrowLeft", "ArrowRight", "Backspace"
    }

    if key not in allowed_keys:
        return "This key is not allowed."

    with _BROWSER_LOCK:
        try:
            if _BROWSER_PAGE is None or _BROWSER_PAGE.is_closed():
                return "No browser page is open."

            _BROWSER_PAGE.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as exc:
            return f"Browser key error: {exc}"


def browser_screenshot() -> str:
    global _BROWSER_PAGE

    if not ENABLE_SERVER_BROWSER:
        return "Server browser control is disabled."

    with _BROWSER_LOCK:
        try:
            if _BROWSER_PAGE is None or _BROWSER_PAGE.is_closed():
                return "No browser page is open."

            path = "/tmp/veya_browser.png"
            _BROWSER_PAGE.screenshot(path=path, full_page=True)
            return f"Screenshot saved on server: {path}"
        except Exception as exc:
            return f"Screenshot error: {exc}"


# ============================================================
# OPTIONAL DESKTOP CONTROL
# ============================================================
# IMPORTANT:
# Render is a cloud server, so pyautogui would control a desktop
# attached to that server, not the user's phone/PC.
# It stays disabled by default.
try:
    import pyautogui
except Exception:
    pyautogui = None


def desktop_control(action: str, x: int = 0, y: int = 0, text: str = "") -> str:
    if not ENABLE_SERVER_DESKTOP_CONTROL:
        return (
            "Desktop control is disabled. "
            "Enable it manually in the code only on a trusted local machine."
        )

    if pyautogui is None:
        return "PyAutoGUI is not installed."

    # Deliberately small, explicit action set.
    try:
        if action == "move":
            pyautogui.moveTo(x, y, duration=0.2)
            return "Mouse moved."

        if action == "click":
            pyautogui.click(x=x, y=y)
            return "Mouse clicked."

        if action == "write":
            if len(text) > 1000:
                return "Text is too long."
            pyautogui.write(text, interval=0.01)
            return "Text entered."

        return "Unsupported desktop action."
    except Exception as exc:
        return f"Desktop control error: {exc}"


# ============================================================
# GROQ TOOL DEFINITIONS
# ============================================================

LOCAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Safely calculate a mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "symbolic_math",
            "description": "Simplify or verify a symbolic mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_json_data",
            "description": "Analyze a JSON array of records using Pandas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string"}
                },
                "required": ["data"],
            },
        },
    },
]

if ENABLE_SERVER_BROWSER:
    LOCAL_TOOLS.extend([
        {
            "type": "function",
            "function": {
                "name": "browser_open",
                "description": "Open a public http/https URL in Veya's server-side browser and extract page text.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Click a CSS selector on the currently open server-side browser page.",
                "parameters": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser_fill",
                "description": "Fill a CSS selector on the currently open server-side browser page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["selector", "value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser_press",
                "description": "Press a safe keyboard key on the current browser page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": [
                                "Enter", "Tab", "Escape",
                                "ArrowUp", "ArrowDown",
                                "ArrowLeft", "ArrowRight",
                                "Backspace"
                            ],
                        }
                    },
                    "required": ["key"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current server-side browser page.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
    ])


def execute_local_tool(name: str, args: Dict[str, Any]) -> str:
    if name == "calculator":
        return safe_calculator(str(args.get("expression", "")))
    if name == "symbolic_math":
        return symbolic_math(str(args.get("expression", "")))
    if name == "analyze_json_data":
        return analyze_json_data(str(args.get("data", "")))
    if name == "browser_open":
        return browser_open(str(args.get("url", "")))
    if name == "browser_click":
        return browser_click(str(args.get("selector", "")))
    if name == "browser_fill":
        return browser_fill(
            str(args.get("selector", "")),
            str(args.get("value", "")),
        )
    if name == "browser_press":
        return browser_press(str(args.get("key", "")))
    if name == "browser_screenshot":
        return browser_screenshot()
    return f"Unknown local tool: {name}"


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt(domain: str) -> str:
    specialist = SPECIALISTS.get(domain, SPECIALISTS["general"])

    return f"""
You are {APP_NAME}, a high-performance multi-specialist AI system.

ACTIVE SPECIALIST:
{specialist["name"]}

SPECIALIST CAPABILITY:
{specialist["description"]}

ARCHITECTURE:
Router -> Specialist -> Tools -> Verification -> Final response.

RULES:
1. Solve the user's actual task.
2. Use tools when they improve accuracy.
3. For mathematics, verify important calculations with calculator or symbolic math.
4. For research/current information, use browser_search when available.
5. For websites, browser_open/click/fill can operate the server-side browser when appropriate.
6. Never claim you controlled the user's personal phone or computer. The Playwright browser runs on the server.
7. Never invent sources, results, calculations, experiments or tool actions.
8. Never expose API keys, secrets, cookies, passwords or private tokens.
9. Do not reveal private chain-of-thought. Give concise useful explanations instead.
10. For health topics, provide general educational information and do not claim to diagnose.
11. For cybersecurity, focus on defensive, authorized and educational work.
12. If a tool is unavailable, say so instead of pretending.
13. Prefer correctness over impressive language.
14. If the user asks for an action that could have an irreversible external effect, explain what will happen before taking that action when possible.
"""


# ============================================================
# MAIN AGENT LOOP
# ============================================================

def run_agent(session_id: str, user_message: str) -> Dict[str, Any]:
    domain = classify_domain(user_message)

    append_history(
        session_id,
        {"role": "user", "content": user_message}
    )

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": build_system_prompt(domain),
        }
    ]

    messages.extend(get_history(session_id))

    # Groq server-side tools for GPT-OSS:
    # browser_search + code_interpreter.
    # They run on Groq's infrastructure.
    groq_builtin_tools = [
        {"type": "browser_search"},
        {"type": "code_interpreter"},
    ]

    all_tools = groq_builtin_tools + LOCAL_TOOLS

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=all_tools,
            tool_choice="auto",
            reasoning_effort="high",
            include_reasoning=False,
            max_tokens=MAX_OUTPUT_TOKENS,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        # Groq built-in tools are handled by Groq itself.
        # Local function calls are returned here for our app to execute.
        if not tool_calls:
            answer = (message.content or "").strip()

            append_history(
                session_id,
                {"role": "assistant", "content": answer}
            )

            return {
                "answer": answer,
                "domain": domain,
                "agent": SPECIALISTS[domain]["name"],
                "rounds": round_number,
            }

        messages.append(message)

        for call in tool_calls:
            name = call.function.name

            try:
                arguments = json.loads(call.function.arguments or "{}")
            except Exception:
                arguments = {}

            if name in {
                "calculator",
                "symbolic_math",
                "analyze_json_data",
                "browser_open",
                "browser_click",
                "browser_fill",
                "browser_press",
                "browser_screenshot",
            }:
                result = execute_local_tool(name, arguments)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })
            else:
                # Built-in Groq tools should normally be completed by Groq.
                # If a provider-side tool call reaches this branch in an
                # incompatible SDK response, return a safe message.
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": (
                        f"{name} is a provider-managed tool. "
                        "Continue using its returned result."
                    ),
                })

    return {
        "answer": (
            "I reached the maximum tool rounds. "
            "Please try the task again with a more specific objective."
        ),
        "domain": domain,
        "agent": SPECIALISTS[domain]["name"],
        "rounds": MAX_TOOL_ROUNDS,
    }


# ============================================================
# API
# ============================================================

@app.get("/api/health")
def health():
    return jsonify({
        "status": "online",
        "name": APP_NAME,
        "version": VERSION,
        "model": MODEL,
        "browser_control": ENABLE_SERVER_BROWSER,
        "desktop_control": ENABLE_SERVER_DESKTOP_CONTROL,
        "specialists": list(SPECIALISTS.keys()),
        "local_tools": [
            "calculator",
            "symbolic_math",
            "analyze_json_data",
            "browser_open",
            "browser_click",
            "browser_fill",
            "browser_press",
            "browser_screenshot",
        ],
    })


@app.post("/api/chat")
def chat():
    try:
        body = request.get_json(silent=True) or {}
        user_message = str(body.get("message", "")).strip()

        if not user_message:
            return jsonify({"error": "Message is required."}), 400

        if len(user_message) > MAX_MESSAGE_CHARS:
            return jsonify({"error": "Message is too long."}), 413

        session_id = str(body.get("session_id") or uuid.uuid4())

        result = run_agent(session_id, user_message)

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "assistant": APP_NAME,
            **result,
        })

    except Exception:
        app.logger.exception("Veya request failed")
        return jsonify({
            "status": "error",
            "error": "Veya could not complete this request.",
        }), 500


# ============================================================
# FRONTEND
# ============================================================

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veya AI</title>
<style>
:root{
  --bg:#070a10;--panel:#0e131c;--line:#202938;
  --text:#f4f7fb;--muted:#8d99aa;--accent:#72e6ae;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,sans-serif;
}
header{
  height:68px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;padding:0 22px;
  background:#080c13;
}
.logo{font-size:25px;font-weight:800}
.status{margin-left:12px;font-size:12px;color:var(--accent)}
main{
  max-width:1050px;margin:auto;height:calc(100vh - 68px);
  display:flex;flex-direction:column;
}
#messages{flex:1;overflow:auto;padding:25px 18px}
.message{
  max-width:850px;margin:14px auto;padding:17px 18px;
  border-radius:16px;line-height:1.65;white-space:pre-wrap;
}
.ai{background:var(--panel);border:1px solid var(--line)}
.user{background:#21385f}
.meta{font-size:11px;color:var(--muted);margin-bottom:7px}
.composer{
  display:flex;gap:10px;padding:16px;
  border-top:1px solid var(--line);background:#080c13;
}
input{
  flex:1;background:#111721;color:white;border:1px solid #303b4c;
  padding:15px;border-radius:13px;outline:none;font-size:15px;
}
button{
  border:0;border-radius:13px;padding:0 23px;
  font-weight:750;cursor:pointer;
}
button:disabled{opacity:.45}
</style>
</head>
<body>
<header>
  <div class="logo">Veya</div>
  <div class="status">● AI Online</div>
</header>

<main>
  <div id="messages">
    <div class="message ai">
      <div class="meta">Veya</div>
      Hello. I'm Veya.
      Ask me about mathematics, science, programming,
      data, research, business, productivity and more.
    </div>
  </div>

  <div class="composer">
    <input id="input" autocomplete="off"
           placeholder="Ask Veya anything...">
    <button id="send">Send</button>
  </div>
</main>

<script>
const input=document.getElementById("input");
const send=document.getElementById("send");
const messages=document.getElementById("messages");

let sessionId=localStorage.getItem("veya_session")||null;

function addMessage(text,type,meta){
  const box=document.createElement("div");
  box.className="message "+type;

  if(meta){
    const m=document.createElement("div");
    m.className="meta";
    m.textContent=meta;
    box.appendChild(m);
  }

  const content=document.createElement("div");
  content.textContent=text;
  box.appendChild(content);

  messages.appendChild(box);
  messages.scrollTop=messages.scrollHeight;
}

async function sendMessage(){
  const text=input.value.trim();
  if(!text||send.disabled)return;

  addMessage(text,"user","You");
  input.value="";
  send.disabled=true;

  try{
    const res=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        message:text,
        session_id:sessionId
      })
    });

    const data=await res.json();

    if(!res.ok) throw new Error(data.error||"Request failed");

    sessionId=data.session_id;
    localStorage.setItem("veya_session",sessionId);

    addMessage(
      data.answer||"No answer returned.",
      "ai",
      "Veya • "+(data.agent||data.domain||"General")
    );
  }catch(err){
    addMessage("Error: "+err.message,"ai","System");
  }finally{
    send.disabled=false;
    input.focus();
  }
}

send.addEventListener("click",sendMessage);
input.addEventListener("keydown",e=>{
  if(e.key==="Enter")sendMessage();
});
</script>
</body>
</html>
"""


@app.get("/")
def home():
    return render_template_string(HTML)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
