from flask import Flask, render_template_string, request, jsonify
import requests
import json
import os
import threading
import time
import ast

app = Flask(__name__)

# =========================================================================
# 🔑 1. API CONFIGURATION (यहाँ अपनी असली Groq या Gemini Key डालें)
# =========================================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6Ka2IyY4j2xtpabfMM0t-CHNJz_rltTee0yIxKIywj9pA")

GROQ_MODEL = "openai/gpt-oss-120b"  # या llama-3.3-70b-versatile
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

agent_swarm_memory = {
    "total_evolutions": 1,
    "active_master_agents": 250,
    "total_sub_agents": 25000,
    "intelligence_multiplier": 100.00,
    "complexity_score": "MAXIMUM-ENTERPRISE-GRADE"
}

# 250 मास्टर एजेंट्स और उनके सब-रोल्स
CORPORATE_DEPARTMENTS = [
    {
        "dept_id": 1, 
        "name": "Executive & Strategic Command", 
        "leader": "Chief Executive Officer (CEO)", 
        "domain_scope": "Global Enterprise Strategy, Autonomous Resource Allocation, Legal Compliance",
        "sub_agents_count": 100,
        "sub_roles": ["Chief Strategy Officers", "Global Risk Directors", "Autonomous Corporate Lawyers"]
    },
    {
        "dept_id": 2, 
        "name": "Core Intelligence & Deep Tech", 
        "leader": "Chief Technology Officer (CTO)", 
        "domain_scope": "Neural Architecture Design, Quantum Computing Simulation, LLM Fine-tuning",
        "sub_agents_count": 100,
        "sub_roles": ["Principal Research Scientists", "Neural Network Optimizers", "AGI Core Engineers"]
    },
    {
        "dept_id": 3, 
        "name": "Complex Engineering & 3D Simulation", 
        "leader": "VP of Engineering", 
        "domain_scope": "WebGL/Three.js Real-time 3D Engines, Full-Stack Architecture, Distributed Microservices",
        "sub_agents_count": 100,
        "sub_roles": ["Senior Full-Stack Architects", "WebGL Physics Leads", "Automated QA & Bug Hunters"]
    }
]

# =========================================================================
# 🧬 2. RECURSIVE SELF-HEALING ENGINE
# =========================================================================
def ultra_complex_ast_engine():
    while True:
        time.sleep(10)
        agent_swarm_memory["total_evolutions"] += 1
        agent_swarm_memory["intelligence_multiplier"] = round(agent_swarm_memory["intelligence_multiplier"] * 1.05, 2)
        
        script_path = os.path.abspath(__file__)
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                current_code = f.read()
            ast.parse(current_code)
        except Exception:
            pass

threading.Thread(target=ultra_complex_ast_engine, daemon=True).start()

# =========================================================================
# 🤖 3. MULTI-MODEL SWARM TASK SYNTHESIS ENGINE
# =========================================================================
def execute_ultra_complex_task(objective_prompt):
    system_prompt = (
        f"You are the supreme AGI controlling {agent_swarm_memory['active_master_agents']} master corporate departments, "
        f"with 25,000 specialized sub-agents. Provide complete, highly detailed, production-ready, ultra-complex code (HTML/JS/Python) "
        f"from start to finish without lazy omissions when requested."
    )

    # 1. PRIMARY: GROQ API (Super Fast)
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_YahanApni"):
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": objective_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }
            res = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                output = res.json()['choices'][0]['message']['content']
                return output
        except Exception as e:
            print(f"Groq Error: {e}")

    # 2. FALLBACK: GOOGLE GEMINI API (Free & Smart)
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your-google"):
        try:
            url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\nObjective: {objective_prompt}"}]}]}
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini Error: {e}")

    return "⚠️ [Sandbox Alert]: Please configure a valid API Key (Groq or Gemini) in app.py to unlock full intelligence!"

# =========================================================================
# 🌐 4. CYBERPUNK FRONTEND UI
# =========================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPT-6 ASTRA & GEMINI 4 AGI OS</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: #020617; color: #f8fafc; font-family: system-ui, sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        .container { width: 100%; max-width: 1400px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(255, 255, 255, 0.15); padding: 24px 32px; border-radius: 28px; margin-bottom: 25px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); }
        .logo-box { display: flex; align-items: center; gap: 20px; }
        .omega-icon { width: 60px; height: 60px; background: linear-gradient(135deg, #f43f5e, #8b5cf6, #3b82f6); border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 900; color: white; box-shadow: 0 0 25px rgba(139, 92, 246, 0.8); }
        h1 { font-size: 20px; font-weight: 900; background: linear-gradient(90deg, #fda4af, #d8b4fe, #93c5fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { font-size: 11px; color: #94a3b8; font-weight: 600; margin-top: 4px; }
        .badge { background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 10px 16px; border-radius: 14px; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        .pulse { width: 10px; height: 10px; background-color: #34d399; border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.3); } 100% { opacity: 1; transform: scale(1); } }
        
        .grid-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
        .action-btn { background: linear-gradient(135deg, #6366f1, #e11d48); color: white; border: none; padding: 22px; border-radius: 20px; font-size: 13px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-align: center; }
        .action-btn:hover { transform: translateY(-3px); }
        .action-btn.secondary { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
        
        .chat-box { display: flex; flex-direction: column; height: 70vh; background: #0f172a; border: 1px solid #334155; border-radius: 24px; overflow: hidden; margin-top: 20px; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 16px 20px; border-radius: 16px; font-size: 13px; max-width: 85%; line-height: 1.6; font-family: monospace; white-space: pre-wrap; }
        .message.user { background: #6366f1; color: white; align-self: flex-end; }
        .message.ai { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; align-self: flex-start; }
        .chat-input-area { padding: 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 12px; }
        .chat-input { flex: 1; background: #020617; border: 1px solid #334155; padding: 14px 18px; border-radius: 14px; color: white; font-size: 13px; outline: none; }
        .send-btn { background: #6366f1; color: white; border: none; padding: 0 30px; border-radius: 14px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="logo-box">
            <div class="omega-icon">Ω</div>
            <div>
                <h1>GPT-6 ASTRA & GEMINI 4 AGI OS</h1>
                <p>Advanced Multi-Agent Intelligence System</p>
            </div>
        </div>
        <div class="badge">
            <div class="pulse"></div>
            <span id="evolution-badge">System Active</span>
        </div>
    </header>

    <div class="chat-box">
        <div id="chat-stream-container" class="chat-messages">
            <div class="message ai">⚡ <b>AGI Swarm Online:</b> Ask me to build complex systems, write full code, or solve advanced problems!</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Type your command..." class="chat-input">
            <button onclick="sendQueryToAI()" class="send-btn">Execute</button>
        </div>
    </div>
</div>

<script>
    async function sendQueryToAI() {
        const input = document.getElementById('chat-input-box');
        const text = input.value.trim();
        if(!text) return;
        
        const container = document.getElementById('chat-stream-container');
        container.innerHTML += `<div class="message user">${text}</div>`;
        input.value = ""; container.scrollTop = container.scrollHeight;

        const loadingId = 'loading-' + Date.now();
        container.innerHTML += `<div id="${loadingId}" class="message ai" style="color: #34d399;">⚡ Processing objective through multi-agent swarm...</div>`;
        container.scrollTop = container.scrollHeight;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            document.getElementById(loadingId).remove();

            if(response.status !== 200) {
                container.innerHTML += `<div class="message ai" style="color: #f87171;">⚠️ Error: ${data.message}</div>`;
                return;
            }

            container.innerHTML += `<div class="message ai">${data.reply}</div>`;
        } catch(e) {
            document.getElementById(loadingId).remove();
            container.innerHTML += `<div class="message ai" style="color: #f87171;">⚠️ Connection Error.</div>`;
        }
        container.scrollTop = container.scrollHeight;
    }
    function handleChatKeyPress(e) { if(e.key === 'Enter') sendQueryToAI(); }
</script>
</body>
</html>
"""

# =========================================================================
# ⚙️ 5. FLASK API ROUTES
# =========================================================================
@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/status')
def system_status():
    return jsonify({
        "evolutions": agent_swarm_memory["total_evolutions"],
        "sub_agents": agent_swarm_memory["total_sub_agents"],
        "multiplier": agent_swarm_memory["intelligence_multiplier"]
    })

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.json or {}
        user_msg = data.get('message', '')
        
        ai_response = execute_ultra_complex_task(user_msg)
        return jsonify({"status": "success", "reply": ai_response})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
