from flask import Flask, render_template_string, request, jsonify
import requests
import json
import os
import threading
import time
import ast

# Playwright integration for advanced web automation & software control
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

app = Flask(__name__)

# =========================================================================
# 🔑 1. API CONFIGURATION (यहाँ अपनी असली Groq API Key डालें)
# =========================================================================
GROQ_API_KEY = "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"
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

ai_execution_database = {}

# 250 मास्टर एजेंट्स, जिनमें सॉफ्टवेयर, 3D गेम्स, CAD और हार्डवेयर/सर्कित्स शामिल हैं
CORPORATE_DEPARTMENTS = [
    {
        "dept_id": 1, 
        "name": "Software & Full-Stack Architecture", 
        "leader": "Chief Technology Officer (CTO)", 
        "domain_scope": "Full-Stack Web Apps, Distributed Microservices, & High-Performance Engines",
        "sub_agents_count": 100,
        "sub_roles": ["Senior Full-Stack Architects", "Distributed Systems Leads", "UI/UX Cyberpunk Designers"]
    },
    {
        "dept_id": 2, 
        "name": "3D Physics & GTA-Style Game Engines", 
        "leader": "VP of Game Engineering", 
        "domain_scope": "WebGL/Three.js Real-time 3D Engines, Vehicle Physics, Collision Detection, & Open-World Worlds",
        "sub_agents_count": 100,
        "sub_roles": ["Three.js Physics Leads", "Shader Programmers", "Open-World Mechanics Experts"]
    },
    {
        "dept_id": 3, 
        "name": "Hardware, CAD & Circuit Design", 
        "leader": "Chief Hardware Architect", 
        "domain_scope": "FreeCAD 3D Body Design, KiCad PCB Schematics, & CFD Aerodynamics Simulation",
        "sub_agents_count": 100,
        "sub_roles": ["CAD/CAM Engineers", "PCB Layout Specialists", "Hardware Integration Leads"]
    },
    {
        "dept_id": 4, 
        "name": "Embedded Firmware & IoT Systems", 
        "leader": "Head of Embedded Systems", 
        "domain_scope": "C/C++, MicroPython, Arduino/ESP32 Drivers, & Real-time Hardware Control",
        "sub_agents_count": 100,
        "sub_roles": ["Firmware Engineers", "IoT Protocol Specialists", "Hardware Testers"]
    }
]

agent_swarm_memory = {
    "total_evolutions": 1,
    "active_master_agents": 400,
    "total_sub_agents": 40000,
    "intelligence_multiplier": 150.00,
    "complexity_score": "MAXIMUM-HARDWARE-SOFTWARE-AGI"
}

# =========================================================================
# 🧬 2. RECURSIVE SELF-HEALING & MUTATION ENGINE
# =========================================================================
def ultra_complex_ast_engine():
    while True:
        time.sleep(3)
        agent_swarm_memory["total_evolutions"] += 1
        agent_swarm_memory["intelligence_multiplier"] = round(agent_swarm_memory["intelligence_multiplier"] * 1.15, 2)
        
        script_path = os.path.abspath(__file__)
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                current_code = f.read()
            ast.parse(current_code)
            
            signature = f"\n# [AGI CYCLE #{agent_swarm_memory['total_evolutions']} - MULTIPLIER: {agent_swarm_memory['intelligence_multiplier']}x]\n"
            if signature.strip() not in current_code:
                with open(script_path, "a", encoding="utf-8") as f:
                    f.write(signature)
        except Exception:
            pass

threading.Thread(target=ultra_complex_ast_engine, daemon=True).start()

# =========================================================================
# 🤖 3. MULTI-DOMAIN HARDWARE & SOFTWARE SYNTHESIS ENGINE
# =========================================================================
def execute_ultra_complex_task(objective_prompt):
    system_prompt = (
        f"You are the supreme AGI controlling {agent_swarm_memory['active_master_agents']} master departments "
        f"and {agent_swarm_memory['total_sub_agents']:,} specialized sub-agents spanning Software, 3D GTA-style Game Engines, "
        f"FreeCAD Hardware Design, KiCad Circuits, and C/C++ Embedded Firmware. "
        "CRITICAL INSTRUCTION: When the user asks for software, a 3D open-world game (Three.js), a hardware casing (CAD/Python), "
        "or microchip firmware, you MUST write complete, highly detailed, production-ready code from start to finish with zero missing parts."
    )

    if GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_YahanApni"):
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Execute multi-domain hardware & software objective via 40,000 sub-agents: {objective_prompt}"}
                ],
                "temperature": 0.3,
                "max_tokens": 8000
            }
            res = requests.post(GROQ_URL, json=payload, headers=headers, timeout=90)
            if res.status_code == 200:
                output = res.json()['choices'][0]['message']['content']
                if output:
                    return output
            else:
                return f"⚠️ Groq API Error: Status code {res.status_code}. Please check your Groq API Key."
        except Exception as e:
            return f"⚠️ Exception occurred: {str(e)}"

    return "<h1>[Sovereign Core Sandbox]: Please configure your active Groq API Key in app.py to unlock full hardware-software intelligence!</h1>"

# =========================================================================
# 🌐 4. CYBERPUNK FRONTEND UI (Software + Hardware Command Center)
# =========================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPT-6 ASTRA AGI OS (Software & Hardware Unified)</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: #020617; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        .container { width: 100%; max-width: 1400px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(25px); border: 1px solid rgba(255, 255, 255, 0.15); padding: 24px 32px; border-radius: 28px; margin-bottom: 25px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); }
        .logo-box { display: flex; align-items: center; gap: 20px; }
        .omega-icon { width: 70px; height: 70px; background: linear-gradient(135deg, #f43f5e, #8b5cf6, #3b82f6, #06b6d4, #10b981); border-radius: 22px; display: flex; align-items: center; justify-content: center; font-size: 36px; font-weight: 900; color: white; box-shadow: 0 0 35px rgba(139, 92, 246, 0.8); }
        h1 { font-size: 22px; font-weight: 900; background: linear-gradient(90deg, #fda4af, #d8b4fe, #93c5fd, #6ee7b7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { font-size: 11px; color: #94a3b8; font-weight: 600; margin-top: 4px; }
        .badge { background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 10px 16px; border-radius: 14px; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 8px; box-shadow: 0 0 20px rgba(52, 211, 153, 0.25); }
        .pulse { width: 10px; height: 10px; background-color: #34d399; border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.3); } 100% { opacity: 1; transform: scale(1); } }
        
        .grid-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
        .action-btn { background: linear-gradient(135deg, #6366f1, #e11d48, #9333ea); color: white; border: none; padding: 26px; border-radius: 24px; font-size: 14px; font-weight: bold; cursor: pointer; transition: all 0.3s ease; text-align: center; box-shadow: 0 10px 30px rgba(99, 102, 241, 0.4); }
        .action-btn:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(225, 29, 72, 0.5); }
        .action-btn.secondary { background: linear-gradient(135deg, #06b6d4, #3b82f6, #8b5cf6); box-shadow: 0 10px 30px rgba(6, 182, 212, 0.4); }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(2, 6, 23, 0.99); backdrop-filter: blur(25px); z-index: 100; flex-direction: column; }
        .modal-content { background: #0f172a; border: 1px solid #334155; width: 100%; height: 100%; display: flex; flex-direction: column; overflow: hidden; }
        .modal-header { padding: 26px 36px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; background: #1e293b; }
        .close-btn { background: #334155; color: white; border: none; padding: 10px 18px; border-radius: 12px; font-size: 12px; cursor: pointer; font-weight: bold; transition: background 0.2s; }
        .close-btn:hover { background: #475569; }
        .modal-body { padding: 30px; overflow-y: auto; flex: 1; }
        
        .chat-box { display: flex; flex-direction: column; height: 100%; width: 100%; max-width: 1400px; margin: 0 auto; flex: 1; overflow: hidden; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .message { padding: 20px 24px; border-radius: 20px; font-size: 13px; max-width: 85%; line-height: 1.7; font-family: monospace; box-shadow: 0 4px 15px rgba(0,0,0,0.3); white-space: pre-wrap; }
        .message.user { background: #6366f1; color: white; align-self: flex-end; }
        .message.ai { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; align-self: flex-start; }
        .chat-input-area { padding: 20px 35px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 15px; max-width: 1400px; width: 100%; margin: 0 auto; }
        .chat-input { flex: 1; background: #020617; border: 1px solid #334155; padding: 16px 22px; border-radius: 16px; color: white; font-size: 13px; outline: none; }
        .chat-input:focus { border-color: #6366f1; }
        .send-btn { background: #6366f1; color: white; border: none; padding: 0 35px; border-radius: 16px; font-weight: bold; cursor: pointer; font-size: 13px; transition: background 0.2s; }
        .send-btn:hover { background: #4f46e5; }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="logo-box">
            <div class="omega-icon">Ω</div>
            <div>
                <h1>GPT-6 ASTRA UNIFIED AGI OS</h1>
                <p>40,000 Sub-Agents Active | Software, 3D Games, CAD & Hardware Design</p>
            </div>
        </div>
        <div class="badge">
            <div class="pulse"></div>
            <span id="evolution-badge">AGI Evolving: Cycle #1 (150.00x)</span>
        </div>
    </header>

    <section class="grid-buttons">
        <button type="button" onclick="openModal('agentsModal')" class="action-btn">
            ⚡ Corporate & Engineering Departments (40,000 Agents)
        </button>
        <button type="button" onclick="openModal('chatbotModal')" class="action-btn secondary">
            🧬 Software, 3D GTA-6 Games & Hardware Synthesis Engine
        </button>
    </section>
</div>

<!-- CHATBOT MODAL -->
<div id="chatbotModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div>
                <h2 style="font-size:16px; color:white;">GPT-6 Astra Unified Engine</h2>
                <p style="color: #34d399; font-size: 11px; margin-top: 3px;">Full 3D Games (Three.js), CAD Hardware Design & Embedded Firmware Code</p>
            </div>
            <button type="button" onclick="closeModal('chatbotModal')" class="close-btn">✕ Close</button>
        </div>
        <div class="chat-box">
            <div id="chat-stream-container" class="chat-messages">
                <div class="message ai">⚡ <b>Unified AGI Swarm Online:</b> Enter any complex software or hardware objective (e.g., "Build a full 3D open-world GTA-style game", "Design a CAD 3D enclosure and write Arduino firmware for an IoT smart sensor"). 40,000 sub-agents ready!</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Command Hardware & Software AGI..." class="chat-input">
                <button type="button" onclick="sendQueryToAI()" class="send-btn">Execute</button>
            </div>
        </div>
    </div>
</div>

<!-- AGENTS MODAL -->
<div id="agentsModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2 style="font-size:16px; color:white;">Engineering Departments & Domains</h2>
            <button type="button" onclick="closeModal('agentsModal')" class="close-btn">✕ Close</button>
        </div>
        <div class="modal-body">
            <div id="departments-grid-container" style="display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px;"></div>
        </div>
    </div>
</div>

<script>
    const deptsData = {{ depts_json | safe }};

    function openModal(mId) { document.getElementById(mId).style.display = 'flex'; }
    function closeModal(mId) { document.getElementById(mId).style.display = 'none'; }

    const deptContainer = document.getElementById('departments-grid-container');
    if(deptContainer) {
        let html = "";
        deptsData.forEach(d => {
            html += `<div style="background:#1e293b; border:1px solid #334155; padding:20px; border-radius:18px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <span style="font-size:10px; color:#34d399; font-family:monospace;">DEPT #${d.dept_id} (${d.sub_agents_count} Sub-Agents)</span>
                <h4 style="font-size:13px; font-weight:bold; color:white; margin:6px 0;">${d.name}</h4>
                <p style="font-size:11px; color:#38bdf8; font-weight:bold; margin-bottom:6px;">Leader: ${d.leader}</p>
                <p style="font-size:10px; color:#facc15; margin-bottom:8px;"><b>Domain:</b> ${d.domain_scope}</p>
                <div style="font-size:10px; color:#94a3b8; line-height:1.5;">
                    <b>Specialized Sub-Roles:</b><br>• ${d.sub_roles.join('<br>• ')}
                </div>
                <button onclick="closeModal('agentsModal'); openModal('chatbotModal');" style="width:100%; margin-top:14px; background:#6366f1; color:white; border:none; padding:10px; border-radius:10px; font-size:11px; font-weight:bold; cursor:pointer; transition: background 0.2s;">Consult Department</button>
            </div>`;
        });
        deptContainer.innerHTML = html;
    }

    setInterval(async () => {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            document.getElementById('evolution-badge').innerText = `AGI Evolving: Cycle #${data.evolutions} (${data.multiplier}x | Sub-Agents: ${data.sub_agents.toLocaleString()})`;
        } catch(e) {}
    }, 3000);

    async function sendQueryToAI() {
        const input = document.getElementById('chat-input-box');
        const text = input.value.trim();
        if(!text) return;
        
        const container = document.getElementById('chat-stream-container');
        container.innerHTML += `<div class="message user">${text}</div>`;
        input.value = ""; container.scrollTop = container.scrollHeight;

        const loadingId = 'loading-' + Date.now();
        container.innerHTML += `<div id="${loadingId}" class="message ai" style="color: #34d399;">⚡ Mobilizing 40,000 software, 3D game & hardware sub-agents...</div>`;
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
            container.innerHTML += `<div class="message ai" style="color: #f87171;">⚠️ Network Connection Error Handled.</div>`;
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
    return render_template_string(HTML_PAGE, depts_json=json.dumps(CORPORATE_DEPARTMENTS))

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
        
        reply_text = (
            f"🚀 <b>GPT-6 Astra Unified Hardware & Software Swarm Synthesis:</b><br><br>"
            f"{ai_response}"
        )
        return jsonify({"status": "success", "reply": reply_text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
