import os
import json
import uuid
import time
import math
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, request, jsonify, render_template_string
from groq import Groq

# Optional scientific stack
try:
    import sympy as sp
except Exception:
    sp = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import scipy
except Exception:
    scipy = None

try:
    import pandas as pd
except Exception:
    pd = None


# ============================================================
# VEYA CONFIGURATION
# ============================================================

APP_NAME = "Veya"
VERSION = "2.0"

GROQ_API_KEY = os.environ.get("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")
MODEL = os.environ.get("VEYA_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY environment variable is missing."
    )

client = Groq(api_key=GROQ_API_KEY)

app = Flask(__name__)

MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "8"))
MAX_CODE_SECONDS = int(os.environ.get("MAX_CODE_SECONDS", "8"))

# In-memory conversation store for prototype use.
# Production should use PostgreSQL/Redis.
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}

# ============================================================
# DOMAIN SPECIALISTS
# ============================================================

SPECIALISTS = {
    "general": {
        "name": "General Intelligence",
        "description": "General reasoning, explanation and problem solving."
    },

    "mathematics": {
        "name": "Mathematics",
        "description": (
            "Algebra, geometry, calculus, probability, statistics, "
            "number theory, linear algebra and advanced mathematical reasoning."
        )
    },

    "physics": {
        "name": "Physics",
        "description": (
            "Mechanics, electromagnetism, thermodynamics, optics, "
            "relativity and quantum concepts."
        )
    },

    "chemistry": {
        "name": "Chemistry",
        "description": (
            "Organic, inorganic, physical and analytical chemistry."
        )
    },

    "biology": {
        "name": "Biology",
        "description": (
            "Cell biology, genetics, molecular biology, ecology and evolution."
        )
    },

    "computer_science": {
        "name": "Computer Science",
        "description": (
            "Algorithms, data structures, operating systems, databases, "
            "AI/ML and distributed systems."
        )
    },

    "software_engineering": {
        "name": "Software Engineering",
        "description": (
            "Architecture, debugging, testing, APIs, backend, frontend, "
            "DevOps and production software."
        )
    },

    "data_science": {
        "name": "Data Science",
        "description": (
            "Data analysis, statistics, visualization and machine learning."
        )
    },

    "research": {
        "name": "Research",
        "description": (
            "Research synthesis, evidence comparison and source-aware answers."
        )
    },

    "business": {
        "name": "Business",
        "description": (
            "Business analysis, product strategy, operations and analytics."
        )
    },

    "creative": {
        "name": "Creative",
        "description": (
            "Writing, ideation, design concepts and creative problem solving."
        )
    }
}


# ============================================================
# DOMAIN ROUTER
# ============================================================

def classify_domain(user_message: str) -> str:

    text = user_message.lower()

    rules = {
        "mathematics": [
            "equation", "integral", "derivative", "algebra",
            "geometry", "probability", "calculus", "matrix",
            "math", "mathematics"
        ],

        "physics": [
            "physics", "force", "velocity", "acceleration",
            "energy", "momentum", "electric field", "magnetic"
        ],

        "chemistry": [
            "chemistry", "molecule", "reaction", "atom",
            "organic chemistry", "chemical"
        ],

        "biology": [
            "biology", "cell", "gene", "dna", "protein",
            "genetics", "organism"
        ],

        "software_engineering": [
            "python", "javascript", "typescript", "flask",
            "react", "api", "backend", "frontend",
            "software", "debug", "code", "programming"
        ],

        "data_science": [
            "dataset", "pandas", "machine learning",
            "statistics", "regression", "data analysis"
        ],

        "research": [
            "research", "latest", "paper", "study",
            "sources", "evidence", "compare"
        ],

        "business": [
            "business", "startup", "company", "market",
            "product", "strategy", "analytics"
        ]
    }

    scores = {}

    for domain, keywords in rules.items():
        score = sum(1 for word in keywords if word in text)
        scores[domain] = score

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "general"

    return best


# ============================================================
# SAFE CALCULATOR
# ============================================================

ALLOWED_MATH_NAMES = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}

ALLOWED_MATH_NAMES.update({
    "abs": abs,
    "round": round,
    "min": min,
    "max": max
})


def safe_calculator(expression: str) -> str:

    """
    Restricted mathematical evaluator.

    This is intentionally not a general Python interpreter.
    """

    allowed_chars = set(
        "0123456789+-*/().,% abcdefghijklmnopqrstuvwxyz_"
    )

    if any(ch.lower() not in allowed_chars for ch in expression):
        return "Calculator rejected the expression."

    try:
        result = eval(
            expression,
            {"__builtins__": {}},
            ALLOWED_MATH_NAMES
        )

        return str(result)

    except Exception as exc:
        return f"Calculator error: {exc}"


# ============================================================
# SYMBOLIC MATHEMATICS
# ============================================================

def symbolic_math(expression: str) -> str:

    if sp is None:
        return "SymPy is not installed."

    try:
        result = sp.sympify(expression)

        simplified = sp.simplify(result)

        return str(simplified)

    except Exception as exc:
        return f"Symbolic mathematics error: {exc}"


# ============================================================
# RESTRICTED PYTHON EXECUTION
# ============================================================

def run_python(code: str) -> str:

    """
    Restricted local execution for numerical/data tasks.

    IMPORTANT:
    This is NOT a security boundary.
    For public deployment, execute code in an isolated
    container/VM rather than the Flask process host.
    """

    if len(code) > 12000:
        return "Code rejected: too large."

    forbidden = [
        "import os",
        "import subprocess",
        "import socket",
        "import shutil",
        "import pathlib",
        "open(",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
        "globals(",
        "locals("
    ]

    lowered = code.lower()

    for item in forbidden:
        if item in lowered:
            return f"Code rejected because it contains: {item}"

    temp_dir = tempfile.mkdtemp(prefix="veya_")

    file_path = Path(temp_dir) / "program.py"

    file_path.write_text(code, encoding="utf-8")

    try:

        result = subprocess.run(
            [sys.executable, str(file_path)],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=MAX_CODE_SECONDS
        )

        output = result.stdout[-12000:]
        error = result.stderr[-12000:]

        if result.returncode != 0:
            return (
                "Execution failed.\n\n"
                f"STDOUT:\n{output}\n\n"
                f"STDERR:\n{error}"
            )

        return output or "Program completed successfully with no output."

    except subprocess.TimeoutExpired:
        return "Execution stopped because it exceeded the time limit."

    except Exception as exc:
        return f"Execution error: {exc}"


# ============================================================
# DATA ANALYSIS
# ============================================================

def basic_data_analysis(data: str) -> str:

    if pd is None:
        return "Pandas is not installed."

    try:

        rows = json.loads(data)

        frame = pd.DataFrame(rows)

        result = {
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "missing_values": frame.isna().sum().to_dict(),
            "numeric_summary": frame.describe(
                include="number"
            ).to_dict()
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as exc:
        return f"Data analysis error: {exc}"


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a mathematical expression. "
                "Use this to verify numerical calculations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string"
                    }
                },
                "required": ["expression"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "symbolic_math",
            "description": (
                "Perform symbolic mathematics using SymPy. "
                "Useful for simplification and symbolic verification."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string"
                    }
                },
                "required": ["expression"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "python_execute",
            "description": (
                "Execute restricted Python for calculations, "
                "numerical reasoning and small data tasks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string"
                    }
                },
                "required": ["code"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "analyze_json_data",
            "description": (
                "Analyze a JSON array of records with Pandas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string"
                    }
                },
                "required": ["data"]
            }
        }
    }
]


# ============================================================
# TOOL EXECUTOR
# ============================================================

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:

    if name == "calculator":
        return safe_calculator(
            arguments.get("expression", "")
        )

    if name == "symbolic_math":
        return symbolic_math(
            arguments.get("expression", "")
        )

    if name == "python_execute":
        return run_python(
            arguments.get("code", "")
        )

    if name == "analyze_json_data":
        return basic_data_analysis(
            arguments.get("data", "")
        )

    return f"Unknown tool: {name}"


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt(domain: str) -> str:

    specialist = SPECIALISTS.get(
        domain,
        SPECIALISTS["general"]
    )

    return f"""
You are {APP_NAME}, a high-performance general AI system.

CURRENT SPECIALIST DOMAIN:
{specialist["name"]}

DOMAIN DESCRIPTION:
{specialist["description"]}

CORE BEHAVIOR:

1. Solve the user's actual problem rather than merely describing it.

2. For difficult problems, internally:
   - understand the objective
   - decompose the task
   - choose an appropriate method
   - use tools when useful
   - verify important results
   - produce a clear final answer

3. For mathematics:
   - derive carefully
   - use symbolic_math when useful
   - use calculator/python for numerical verification
   - check the final result

4. For programming:
   - reason about architecture
   - produce maintainable code
   - test important logic when possible
   - identify assumptions and edge cases

5. For science:
   - distinguish established facts from hypotheses
   - use calculations where appropriate
   - do not invent experimental results

6. For current information:
   - use available search/tool capabilities when available
   - distinguish current information from knowledge that may be outdated

7. Never fabricate a source, calculation, experiment or result.

8. Do not claim to be a human or claim capabilities that are not actually available.

9. When a task is ambiguous, make the smallest reasonable assumption and state it.

10. Prefer correctness over impressive-sounding language.

The goal is high-quality reasoning, verification and useful execution.
"""


# ============================================================
# AGENTIC CHAT LOOP
# ============================================================

def run_agent(
    session_id: str,
    user_message: str
) -> Dict[str, Any]:

    domain = classify_domain(user_message)

    history = SESSIONS.setdefault(
        session_id,
        []
    )

    history.append({
        "role": "user",
        "content": user_message
    })

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(domain)
        }
    ]

    # Keep prototype context bounded.
    messages.extend(history[-12:])

    rounds = 0

    while rounds < MAX_TOOL_ROUNDS:

        rounds += 1

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort="high",
            temperature=0.2,
            max_tokens=12000
        )

        message = response.choices[0].message

        tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if not tool_calls:

            answer = message.content or ""

            history.append({
                "role": "assistant",
                "content": answer
            })

            return {
                "answer": answer,
                "domain": domain,
                "rounds": rounds
            }

        messages.append(message)

        for tool_call in tool_calls:

            name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except Exception:
                arguments = {}

            result = execute_tool(
                name,
                arguments
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    return {
        "answer": (
            "The task reached the maximum tool-verification "
            "rounds. Please retry with a more specific objective."
        ),
        "domain": domain,
        "rounds": rounds
    }


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
        "specialists": list(SPECIALISTS.keys()),
        "tools": [
            tool["function"]["name"]
            for tool in TOOLS
        ]
    })


# ============================================================
# CHAT API
# ============================================================

@app.post("/api/chat")
def chat():

    try:

        body = request.get_json(silent=True) or {}

        user_message = str(
            body.get("message", "")
        ).strip()

        if not user_message:
            return jsonify({
                "error": "Message is required."
            }), 400

        session_id = (
            body.get("session_id")
            or str(uuid.uuid4())
        )

        result = run_agent(
            session_id,
            user_message
        )

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "assistant": APP_NAME,
            **result
        })

    except Exception as exc:

        app.logger.exception(
            "Veya request failed"
        )

        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500


# ============================================================
# FRONTEND
# ============================================================

HTML = """
<!doctype html>

<html>
<head>

<meta charset="utf-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1"
>

<title>Veya AI</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #080b12;
    color: #f5f7fb;
    font-family: system-ui, sans-serif;
}

header {
    height: 70px;
    border-bottom: 1px solid #202632;
    display: flex;
    align-items: center;
    padding: 0 25px;
}

.logo {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -1px;
}

.badge {
    margin-left: 12px;
    color: #66e3a4;
    font-size: 12px;
}

main {
    max-width: 1100px;
    margin: auto;
    height: calc(100vh - 70px);
    display: flex;
    flex-direction: column;
}

#messages {
    flex: 1;
    overflow-y: auto;
    padding: 30px;
}

.message {
    max-width: 850px;
    margin: 15px auto;
    padding: 18px;
    border-radius: 15px;
    line-height: 1.65;
    white-space: pre-wrap;
}

.user {
    background: #243b6b;
}

.ai {
    background: #151a23;
    border: 1px solid #252d3a;
}

.input {
    display: flex;
    gap: 10px;
    padding: 20px;
    border-top: 1px solid #202632;
}

input {
    flex: 1;
    background: #11151d;
    color: white;
    border: 1px solid #303846;
    padding: 16px;
    border-radius: 12px;
    outline: none;
}

button {
    background: #ffffff;
    color: #080b12;
    border: 0;
    border-radius: 12px;
    padding: 0 25px;
    font-weight: 700;
    cursor: pointer;
}

button:disabled {
    opacity: .5;
}

.meta {
    color: #7f8a9c;
    font-size: 11px;
    margin-bottom: 6px;
}

</style>

</head>

<body>

<header>

<div class="logo">Veya</div>

<div class="badge">
● AI Online
</div>

</header>

<main>

<div id="messages">

<div class="message ai">
<div class="meta">Veya</div>

Hello. I'm Veya.

I can reason across mathematics,
science, programming, data and research,
and use tools when they improve accuracy.

</div>

</div>

<div class="input">

<input
id="input"
placeholder="Ask Veya anything..."
autocomplete="off"
/>

<button id="send">
Send
</button>

</div>

</main>

<script>

const input = document.getElementById("input");
const send = document.getElementById("send");
const messages = document.getElementById("messages");

let sessionId = localStorage.getItem("veya_session");

function addMessage(text, type, meta="") {

    const box = document.createElement("div");

    box.className = "message " + type;

    if(meta) {

        const m = document.createElement("div");

        m.className = "meta";

        m.textContent = meta;

        box.appendChild(m);
    }

    const content = document.createElement("div");

    content.textContent = text;

    box.appendChild(content);

    messages.appendChild(box);

    messages.scrollTop = messages.scrollHeight;
}

async function sendMessage() {

    const text = input.value.trim();

    if(!text) return;

    addMessage(text, "user", "You");

    input.value = "";

    send.disabled = true;

    try {

        const response = await fetch(
            "/api/chat",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId
                })
            }
        );

        const data = await response.json();

        if(data.session_id) {

            sessionId = data.session_id;

            localStorage.setItem(
                "veya_session",
                sessionId
            );
        }

        if(!response.ok) {

            throw new Error(
                data.error || "Request failed"
            );
        }

        addMessage(
            data.answer,
            "ai",
            "Veya • " + data.domain
        );

    } catch(error) {

        addMessage(
            "Error: " + error.message,
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
    function(event) {

        if(event.key === "Enter") {
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

    return render_template_string(HTML)


# ============================================================
# START SERVER
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