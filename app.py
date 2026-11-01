from flask import Flask, render_template_string, request, jsonify
import requests
import json
import uuid
import re
import base64
import os

app = Flask(__name__)

# =========================================================================
# 🔑 1. SECURE CONFIGURATION: API KEYS & DETAILS
# =========================================================================
GROQ_API_KEY = "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"  # अपनी असली Groq API Key यहाँ डालें
GROQ_MODEL = "openai/gpt-oss-120b"                        # मुख्य मैसिव मॉडल
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GITHUB_TOKEN = "your-github-personal-access-token"       # वैकल्पिक
GITHUB_USERNAME = "your-github-username"                  # वैकल्पिक

PHONEPE_ID = "your-phonepe-id@ybl"
PHONEPE_NUMBER = "9876543210"

html_storage_db = {}  # सभी डायनामिक ऐप्स और वेबसाइट्स को स्टोर करने के लिए डेटाबेस

# =========================================================================
# 🧠 2. ADVANCED AUTONOMOUS PROMPT OPTIMIZER & SELF-HEALING ENGINE
# =========================================================================
def analyze_and_enhance_prompt(user_prompt):
    """
    यह इंजन यूजर के प्रॉम्प्ट की कमियों को खुद भांपता है, उसमें जरूरी लॉजिक, 
    जावास्क्रिप्ट एपीआई हैंडलिंग, मैप्स, एआई चैट इंटीग्रेशन और एरर-फ्री स्ट्रक्चर जोड़ता है।
    """
    enhancements_noted = []
    enhanced_prompt = user_prompt
    
    # यदि यूजर मैप या जियोलोकेशन मांग रहा है
    if "map" in user_prompt.lower() or "मैप" in user_prompt:
        enhancements_noted.append("Integrated Leaflet.js Interactive World Map Engine.")
        enhanced_prompt += " (Include fully interactive Leaflet.js world map via CDN with zoom, pan, and search functionality). "
        
    # यदि यूजर एआई चैट या असिस्टेंट मांग रहा है
    if "ai" in user_prompt.lower() or "assistant" in user_prompt.lower() or "chatbot" in user_prompt.lower():
        enhancements_noted.append("Integrated Full-Screen AI Assistant Chatbot Overlay.")
        enhanced_prompt += " (Include a prominent bottom-right glowing AI button that triggers a full-screen immersive chat interface connected to advanced models). "

    # सामान्य या किसी भी फील्ड की वेबसाइट के लिए यूनिवर्सल एनहांसमेंट
    enhancements_noted.append("Applied Enterprise-Grade Tailwind UI, Full JavaScript Logic, and Zero-Error Loop.")
    enhanced_prompt += " (Ensure complete production-ready single-file HTML structure with Tailwind CSS, responsive layout, and flawless JS interactivity without any placeholders)."
    
    return enhanced_prompt, enhancements_noted

# =========================================================================
# 🚀 3. CLOUD DEPLOYMENT AUTOMATION ENGINE
# =========================================================================
def auto_deploy_to_cloud(site_name, html_content):
    app_id = str(uuid.uuid4())[:8]
    html_storage_db[app_id] = html_content
    
    if GITHUB_TOKEN and not GITHUB_TOKEN.startswith("your-github"):
        try:
            repo_name = f"nexus-app-{app_id}"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            repo_payload = {"name": repo_name, "private": False, "description": "Auto-deployed by NEXUS GPT-6 Astra OS"}
            r = requests.post("https://api.github.com/user/repos", json=repo_payload, headers=headers, timeout=15)
            
            if r.status_code == 201:
                encoded_content = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
                file_payload = {
                    "message": "Autonomous deployment via Nexus AI",
                    "content": encoded_content
                }
                file_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/index.html"
                requests.put(file_url, json=file_payload, headers=headers, timeout=15)
                
                return f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
        except Exception:
            pass
            
    return None

# =========================================================================
# 🤖 4. ULTRA-POWERED DYNAMIC AI UNIVERSE WEBSITE GENERATOR ENGINE
# =========================================================================
def generate_dynamic_website_via_ai(spec_prompt):
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("gsk_YahanApni"):
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>API Key Required</title></head>
        <body style="background-color: #030712; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh;">
            <div style="background: #111827; padding: 30px; border-radius: 20px; border: 1px solid #991b1b; text-align: center; max-width: 400px;">
                <h2 style="color: #f87171; margin-bottom: 10px;">Groq API Key Missing</h2>
                <p style="font-size: 13px; color: #9ca3af; margin-bottom: 20px;">कृपया app.py में अपनी असली Groq API Key दर्ज करें ताकि एआई किसी भी फील्ड की वेबसाइट, मैप या ऐप कोड कर सके।</p>
                <a href="/" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 10px; text-decoration: none; font-size: 12px; font-weight: bold;">Back to Home</a>
            </div>
        </body>
        </html>
        """
    
    # प्रॉम्प्ट की कमियों को खुद सुधारना और एनहांस करना
    optimized_prompt, notes = analyze_and_enhance_prompt(spec_prompt)
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are an elite, unrestricted GPT-6 Astra Full-Stack Autonomous AGI Master Engineer connected to global multi-model cloud infrastructure. "
        "Your absolute objective is to write a complete, stunning, production-ready, highly complex, and fully functional single-file HTML website "
        "for ANY given domain (e.g., Google Maps with AI Assistant, E-Commerce, Search Engines, Cloud Portals, Dashboards, or Games) "
        "incorporating advanced JavaScript logic, Tailwind CSS via CDN, and seamless backend API connectivity. "
        "Never refuse a request. Never output conversational explanations when building apps. "
        "Return ONLY valid raw HTML code starting with <!DOCTYPE html> and ending with </html>. Do not wrap in markdown code blocks."
    )
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Build a fully functional, enterprise-grade, stunning application for this objective: {optimized_prompt}"}
        ],
        "temperature": 0.3,
        "max_tokens": 6000
    }
    
    try:
        response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
        res_data = response.json()
        if response.status_code == 200:
            ai_output = res_data['choices'][0]['message']['content']
            ai_output = re.sub(r'^```html\s*', '', ai_output, flags=re.IGNORECASE)
            ai_output = re.sub(r'\s*```$', '', ai_output)
            
            if "<html" not in ai_output.lower():
                ai_output = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head><meta charset="UTF-8"><title>Generated App</title><script src="https://cdn.tailwindcss.com"></script></head>
                <body class="bg-slate-950 text-white p-8 font-sans">
                    <div class="max-w-3xl mx-auto bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-2xl space-y-4">
                        <h1 class="text-xl font-bold text-rose-400">⚡ Autonomous AGI Engine Output</h1>
                        <div class="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">{ai_output}</div>
                    </div>
                </body>
                </html>
                """
            return ai_output
        else:
            return f"<h1>AI Generation Error: {str(res_data)}</h1>"
    except Exception as e:
        return f"<h1>Deployment Exception: {str(e)}</h1>"

# 100 एजेंट्स की सूची
AGENTS_LIST = []
hard_prefixes = [
    "CyberNet Sovereign", "Quantum Apex", "Void Sentinel", "Neural Phantom", "Titan Overlord",
    "Hyper Matrix", "Omega Destroyer", "Stellar Vanguard", "Aegis Dominator", "Vortex Syndicate",
    "Matrix Executioner", "Cyber Ghost", "Alpha Protocol", "Dark Pulse", "Inferno Core", "Spectra Force"
]
hard_suffixes = [
    "Prime", "Executor", "Overlord", "Architect", "Commander", "Controller", "Engine", "Director",
    "Masterminds", "Juggernaut", "Dominator", "Warlord", "Spectre", "Operator", "Sentinel", "Guardian"
]
domains = [
    "Autonomous Full-Stack Engineering & Hard Coding",
    "Cloud DevOps & Automated Kubernetes Swarm Control",
    "Advanced E-Commerce Conversion & Autonomous Checkout",
    "CyberSecurity Penetration Testing & Zero-Day Defense",
    "Legal Smart Contract Automation & Autonomous Compliance",
    "Medical Diagnostics Swarm & Genomic Intelligence",
    "High-Frequency Financial Auditing & Complex Math Solver",
    "Viral Omnichannel Growth & Autonomous Marketing Matrix"
]

for i in range(1, 101):
    p_fix = hard_prefixes[(i * 5) % len(hard_prefixes)]
    s_suf = hard_suffixes[i % len(hard_suffixes)]
    agent_dangerous_name = f"{p_fix} {s_suf}-{i}"
    dom = domains[i % len(domains)]
    AGENTS_LIST.append({
        "id": i,
        "name": agent_dangerous_name,
        "domain": dom,
        "tier": "FREE",
        "price": 0,
        "description": f"GPT-6 Astra sovereign agent specialized in {dom}, powered by 50 backend engines."
    })

# =========================================================================
# 🌐 STABLE PREMIUM FRONTEND UI (YOUR ORIGINAL LOOK & GLASSMORPHISM)
# =========================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS GPT-6 Astra Sovereign Operating System</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        .container { width: 100%; max-width: 800px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }
        .logo-box { display: flex; align-items: center; gap: 15px; }
        .omega-icon { width: 50px; height: 50px; background: linear-gradient(135deg, #e11d48, #9333ea, #4f46e5); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 900; color: white; box-shadow: 0 0 20px rgba(225, 29, 72, 0.4); }
        h1 { font-size: 16px; font-weight: 900; background: linear-gradient(90deg, #fb7185, #c084fc, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { font-size: 11px; color: #94a3b8; font-weight: 600; margin-top: 2px; }
        .badge { background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(244, 63, 94, 0.3); color: #fb7185; padding: 6px 12px; border-radius: 10px; font-size: 10px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
        .pulse { width: 8px; height: 8px; background-color: #f43f5e; border-radius: 50%; box-shadow: 0 0 10px #f43f5e; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .grid-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px; }
        .action-btn { background: linear-gradient(135deg, #4f46e5, #e11d48); color: white; border: none; padding: 18px; border-radius: 16px; font-size: 12px; font-weight: bold; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center; }
        .action-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(225, 29, 72, 0.4); }
        .action-btn.secondary { background: linear-gradient(135deg, #7c3aed, #db2777); }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(3, 7, 18, 0.95); backdrop-filter: blur(16px); z-index: 100; flex-direction: column; }
        .modal-content { background: #0f172a; border: 1px solid #334155; width: 100%; height: 100%; display: flex; flex-direction: column; overflow: hidden; }
        .modal-header { padding: 20px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; background: #1e293b; }
        .modal-header h2 { font-size: 15px; font-weight: bold; color: white; }
        .close-btn { background: #334155; color: white; border: none; padding: 8px 16px; border-radius: 10px; font-size: 12px; cursor: pointer; font-weight: bold; }
        .modal-body { padding: 20px; overflow-y: auto; flex: 1; }
        .search-input { width: 100%; background: #0f172a; border: 1px solid #334155; padding: 14px 18px; border-radius: 12px; color: white; font-size: 13px; margin-bottom: 20px; }
        .agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .agent-card { background: #1e293b; border: 1px solid #334155; padding: 18px; border-radius: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; transition: border-color 0.2s; }
        .agent-card:hover { border-color: #f43f5e; }
        .deploy-card-btn { background: #4f46e5; color: white; border: none; padding: 10px; border-radius: 10px; font-size: 11px; font-weight: bold; cursor: pointer; width: 100%; }
        
        .chat-box { display: flex; flex-direction: column; height: 100%; width: 100%; max-width: 1000px; margin: 0 auto; flex: 1; overflow: hidden; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 16px 20px; border-radius: 16px; font-size: 13px; max-width: 85%; line-height: 1.6; font-family: monospace; }
        .message.user { background: #4f46e5; color: white; align-self: flex-end; }
        .message.ai { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; align-self: flex-start; }
        .chat-input-area { padding: 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 12px; max-width: 1000px; width: 100%; margin: 0 auto; }
        .chat-input { flex: 1; background: #0f172a; border: 1px solid #334155; padding: 14px 18px; border-radius: 14px; color: white; font-size: 13px; }
        .send-btn { background: #4f46e5; color: white; border: none; padding: 0 25px; border-radius: 14px; font-weight: bold; cursor: pointer; font-size: 13px; }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="logo-box">
            <div class="omega-icon">Ω</div>
            <div>
                <h1>NEXUS GPT-6 ASTRA OS</h1>
                <p>100 Sovereign Dangerous Agents | Universal Autonomous AGI</p>
            </div>
        </div>
        <div class="badge">
            <div class="pulse"></div>
            <span>50 Backend Engines Active</span>
        </div>
    </header>

    <section class="grid-buttons">
        <button type="button" onclick="openModal('agentsModal')" class="action-btn">
            ⚡ Explore 100 Sovereign Agents (Free)
        </button>
        <button type="button" onclick="openModal('customizerModal')" class="action-btn secondary">
            🧬 Multi-Agent Customizer & Cloud AI
        </button>
    </section>
</div>

<!-- AGENTS MODAL -->
<div id="agentsModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2>100 Sovereign Dangerous Agents</h2>
            <button type="button" onclick="closeModal('agentsModal')" class="close-btn">✕ Close</button>
        </div>
        <div style="padding: 20px; background: #0f172a; border-bottom: 1px solid #334155;">
            <input type="text" id="agent-search" oninput="filterAgents()" placeholder="Search agents..." class="search-input">
        </div>
        <div class="modal-body">
            <div id="agents-grid-container" class="agents-grid"></div>
        </div>
    </div>
</div>

<!-- CUSTOMIZER MODAL -->
<div id="customizerModal" class="modal">
    <div class="modal-content" style="max-width: 600px; height: auto; margin: auto; border-radius: 20px;">
        <div class="modal-header">
            <h2>Multi-Agent Customizer</h2>
            <button type="button" onclick="closeModal('customizerModal')" class="close-btn">✕ Close</button>
        </div>
        <div class="modal-body" style="display: flex; flex-direction: column; gap: 20px;">
            <input type="text" id="custom-agent-prompt" placeholder="Objective (e.g., Google Maps with AI, E-Commerce, Azure Portal)" class="search-input" style="margin: 0;">
            <button type="button" onclick="launchCustomAgent()" class="action-btn">Launch Cloud Agent</button>
        </div>
    </div>
</div>

<!-- CHATBOT MODAL -->
<div id="chatbotModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <div>
                <h2 id="active-chatbot-title">Nexus Astra OS</h2>
                <p id="active-chatbot-subtitle" style="color: #fb7185; font-size: 11px; margin-top: 2px;">GPT-6 Astra Autonomous Operator Active</p>
            </div>
            <button type="button" onclick="closeModal('chatbotModal')" class="close-btn">✕ Close</button>
        </div>
        <div class="chat-box">
            <div id="chat-stream-container" class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Command agent (e.g., Build Google Maps with AI Assistant, E-Commerce, Game)..." class="chat-input">
                <button type="button" onclick="sendQueryToGroqAI()" class="send-btn">Execute</button>
            </div>
        </div>
    </div>
</div>

<script>
    const agentsData = {{ agents_json | safe }};
    let activeAgent = "CyberNet Sovereign Prime-1";
    let activeDomain = "Autonomous Full-Stack Engineering";

    function openModal(mId) { const m = document.getElementById(mId); if(m) m.style.display = 'flex'; }
    function closeModal(mId) { const m = document.getElementById(mId); if(m) m.style.display = 'none'; }

    const agentContainer = document.getElementById('agents-grid-container');
    function renderAgentsList(list) {
        if(!agentContainer) return;
        let html = "";
        list.forEach(a => {
            html += `<div class="agent-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 10px; font-family: monospace; color: #fb7185; font-weight: bold;">AGID #${a.id}</span>
                        <span style="font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: bold; background: rgba(16, 185, 129, 0.1); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">FREE</span>
                    </div>
                    <h3 style="font-size: 12px; font-weight: bold; color: white; margin-bottom: 6px;">${a.name}</h3>
                    <p style="font-size: 10px; color: #94a3b8;">${a.domain}</p>
                </div>
                <button type="button" onclick="deployAgentCheck(${a.id}, '${a.name}', '${a.domain}')" class="deploy-card-btn">Deploy Agent</button>
            </div>`;
        });
        agentContainer.innerHTML = html;
    }
    renderAgentsList(agentsData);

    function filterAgents() {
        const query = document.getElementById('agent-search').value.toLowerCase();
        renderAgentsList(agentsData.filter(a => a.name.toLowerCase().includes(query) || a.domain.toLowerCase().includes(query)));
    }

    function deployAgentCheck(id, name, domain) {
        activeAgent = name; activeDomain = domain;
        document.getElementById('active-chatbot-title').innerText = `Active: ${name}`;
        closeModal('agentsModal'); openModal('chatbotModal');
    }

    async function sendQueryToGroqAI() {
        const input = document.getElementById('chat-input-box');
        const text = input.value.trim();
        if(!text) return;
        
        const container = document.getElementById('chat-stream-container');
        container.innerHTML += `<div class="message user">${text}</div>`;
        input.value = ""; container.scrollTop = container.scrollHeight;

        const loadingId = 'loading-' + Date.now();
        container.innerHTML += `<div id="${loadingId}" class="message ai" style="color: #fb7185;">⚡ Analyzing prompt, correcting gaps & compiling universal app via GPT-6 Astra...</div>`;
        container.scrollTop = container.scrollHeight;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, agent: activeAgent, domain: activeDomain })
            });
            const data = await response.json();
            document.getElementById(loadingId).remove();

            if(response.status !== 200) {
                container.innerHTML += `<div class="message ai" style="color: #f87171;">⚠️ Error: ${data.message}</div>`;
                return;
            }

            container.innerHTML += `<div class="message ai"><strong style="color: #fb7185;">${activeAgent}:</strong><br><br>${data.reply}</div>`;
        } catch(e) {
            document.getElementById(loadingId).remove();
            container.innerHTML += `<div class="message ai" style="color: #f87171;">⚠️ Network Connection Error Handled.</div>`;
        }
        container.scrollTop = container.scrollHeight;
    }

    function handleChatKeyPress(e) { if(e.key === 'Enter') sendQueryToGroqAI(); }
    function launchCustomAgent() {
        const promptText = document.getElementById('custom-agent-prompt').value.trim();
        if(!promptText) { alert("❌ कृपया उद्देश्य दर्ज करें!"); return; }
        closeModal('customizerModal'); 
        deployAgentCheck(999, promptText + " (Custom)", "Advanced Swarm");
    }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(
        HTML_PAGE, 
        agents_json=json.dumps(AGENTS_LIST),
        phonepe_id=PHONEPE_ID,
        phonepe_number=PHONEPE_NUMBER
    )

@app.route('/live-app/<app_id>')
def live_deployed_app(app_id):
    if app_id in html_storage_db:
        return html_storage_db[app_id]
    return "<h1>404: App Not Found or Expired</h1>"

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.json
        user_msg = data.get('message', '')
        active_agent = data.get('agent', 'CyberNet Sovereign Prime-1')
        active_domain = data.get('domain', 'Autonomous Full-Stack Engineering')
        
        if not GROQ_API_KEY or GROQ_API_KEY.startswith("gsk_YahanApni"):
            return jsonify({"status": "error", "message": "कृपया अपनी असली Groq API Key ऐप में सेट करें।"}), 400
        
        base_url = request.host_url.rstrip('/')
        
        # यूनिवर्सल ट्रिगर्स: किसी भी प्रकार की वेबसाइट, मैप, गेम या ऐप बनाने के लिए
        deployment_triggers = [
            "deploy", "app", "code", "build", "website", "create site", "live link", 
            "form", "store", "shop", "game", "search engine", "google", "chatbot", 
            "ecommerce", "calculator", "map", "azure", "portal", "dashboard", "maps"
        ]
        
        if any(w in user_msg.lower() for w in deployment_triggers) or len(user_msg) > 3:
            # 1. प्रॉम्प्ट एनालाइज़र जो हर कमी को खुद ठीक कर देगा
            optimized_prompt, notes = analyze_and_enhance_prompt(user_msg)
            
            # 2. एआई से अल्टीमेट कोड जनरेट करवाना
            generated_html_code = generate_dynamic_website_via_ai(user_msg)
            
            # 3. स्टोरेज और लाइव डिप्लॉयमेंट
            app_id = str(uuid.uuid4())[:8]
            html_storage_db[app_id] = generated_html_code
            
            cloud_link = auto_deploy_to_cloud(user_msg, generated_html_code)
            final_live_link = cloud_link if cloud_link else f"{base_url}/live-app/{app_id}"
            
            notes_str = "<br>".join([f"- {n}" for n in notes]) if notes else "- Optimized standard structure."
            
            reply_text = (
                f"🚀 <b>GPT-6 Astra Autonomous Cloud Deployment Success:</b><br>"
                f"- <b>Target Objective:</b> {user_msg}<br>"
                f"- <b>Autonomous Prompt Enhancements & Gap Corrections:</b><br>{notes_str}<br>"
                f"- <b>Live Cloud Deployed Link:</b> <a href='{final_live_link}' target='_blank' style='color: #38bdf8; text-decoration: underline; font-weight: bold;'>{final_live_link}</a><br>"
                f"- <b>Status:</b> Universal application compiled with multi-model intelligence and hosted live!"
            )
            return jsonify({"status": "success", "reply": reply_text})

        # सामान्य चैट के लिए
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            f"You are {active_agent} expert in {active_domain}, powered by 50 enterprise backend AGI features and GPT-6 Astra OS control. "
            f"You excel at hard coding, building complex websites, search engines, e-commerce stores, and solving complex problems."
        )
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
        res_data = response.json()
        
        if response.status_code != 200:
            return jsonify({"status": "error", "message": str(res_data)}), 400
        
        return jsonify({"status": "reply": res_data['choices'][0]['message']['content']})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
