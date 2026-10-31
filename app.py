from flask import Flask, render_template_string, request, jsonify
import requests
import json
import uuid
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# =========================================================================
# 🔑 1. SECURE CONFIGURATION: API KEYS
# =========================================================================
GROQ_API_KEY ="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"  # अपनी असली Groq API Key यहाँ डालें
GROQ_MODEL = "openai/gpt-oss-120b"                        # अनुरोधित मॉडल

# =========================================================================
# 🤖 2. GPT-6 ASTRA FULLY DYNAMIC AI WEBSITE GENERATOR ENGINE
# =========================================================================
def generate_dynamic_website_via_ai(spec_prompt):
    """
    यह इंजन Groq API की मदद से यूजर के किसी भी प्रॉम्प्ट के लिए पूरी तरह 
    कस्टमाइज्ड और कॉम्प्लेक्स HTML/CSS/JS कोड खुद जेनरेट करता है।
    """
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("gsk_YahanApni"):
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>API Key Required</title><script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-6">
            <div class="max-w-md w-full bg-slate-900 p-8 rounded-3xl border border-rose-800 text-center space-y-4">
                <h1 class="text-xl font-black text-rose-400">Groq API Key Missing</h1>
                <p class="text-xs text-slate-300">कृपया app.py में अपनी असली Groq API Key दर्ज करें ताकि एआई किसी भी प्रकार की कॉम्प्लेक्स वेबसाइट खुद कोड कर सके।</p>
                <a href="/" class="inline-block px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl">Back to Home</a>
            </div>
        </body>
        </html>
        """
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are an elite GPT-6 Astra Full-Stack AI Engineer. Your job is to write a complete, stunning, "
        "production-ready, and fully functional single-file HTML website (including internal Tailwind CSS and JavaScript) "
        "based strictly on the user's requested application or website objective. "
        "Return ONLY valid raw HTML code starting with <!DOCTYPE html> and ending with </html>. Do not include markdown code blocks like ```html."
    )
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Build a fully functional, stunning website for this objective: {spec_prompt}"}
        ],
        "temperature": 0.3,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", json=payload, headers=headers, timeout=45)
        res_data = response.json()
        if response.status_code == 200:
            html_content = res_data['choices'][0]['message']['content']
            # यदि एआई गलती से markdown block दे दे तो उसे साफ करना
            html_content = re.sub(r'^```html\s*', '', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'\s*```$', '', html_content)
            return html_content
        else:
            return f"<h1>AI Generation Error: {str(res_data)}</h1>"
    except Exception as e:
        return f"<h1>Deployment Exception: {str(e)}</h1>"

# =========================================================================
# 🧬 3. 100 FREE DANGEROUS & POWERFUL SOVEREIGN AGENTS
# =========================================================================
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
# 🌐 4. PROFESSIONAL FRONTEND UI
# =========================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS GPT-6 Astra Sovereign Operating System</title>
    <script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script>
    <style>
        .glass-panel { background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(20px); border: 1px solid rgba(0, 0, 0, 0.08); }
        .glass-card { background: rgba(248, 250, 252, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(226, 232, 240, 0.8); transition: all 0.25s ease; }
        .glass-card:hover { border-color: rgba(99, 102, 241, 0.5); transform: translateY(-2px); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col font-sans pb-10">

<header class="w-full max-w-4xl mx-auto p-6 flex items-center justify-between mt-2">
    <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-rose-600 via-purple-600 to-indigo-600 flex items-center justify-center font-black text-2xl text-white shadow-lg shadow-rose-900/50">Ω</div>
        <div class="text-left">
            <h1 class="text-sm md:text-base font-black tracking-wider bg-gradient-to-r from-rose-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent">NEXUS GPT-6 ASTRA OS</h1>
            <p class="text-[10px] font-bold text-emerald-400">100 Free Sovereign Agents | Fully Dynamic AI Website Builder</p>
        </div>
    </div>
    <div class="px-3 py-1.5 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-[10px] font-bold flex items-center space-x-1.5 shadow-sm">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>All Features Unlocked</span>
    </div>
</header>

<section class="w-full max-w-4xl mx-auto px-4 space-y-3 mb-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <button type="button" onclick="openModal('agentsModal')" class="py-4 px-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-rose-600 text-white text-xs font-bold transition shadow-lg flex items-center justify-center space-x-2 cursor-pointer">
            <span>⚡</span><span>Explore 100 Free Dangerous Agents</span>
        </button>
        <button type="button" onclick="openModal('customizerModal')" class="py-4 px-4 rounded-2xl bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs font-bold transition shadow-lg flex items-center justify-center space-x-2 cursor-pointer">
            <span>🧬</span><span>Multi-Agent Customizer (100% Free & Unlocked)</span>
        </button>
    </div>
</section>

<!-- 100 AGENTS MODAL -->
<div id="agentsModal" class="fixed inset-0 bg-slate-950/90 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-white">100 Free Sovereign Agents</h2>
        <button type="button" onclick="closeModal('agentsModal')" class="px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div class="p-4 bg-slate-950"><input type="text" id="agent-search" oninput="filterAgents()" placeholder="Search agents by codename or domain..." class="w-full bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-2.5 text-xs"></div>
    <div class="flex-1 overflow-y-auto p-6"><div id="agents-grid-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl mx-auto"></div></div>
</div>

<!-- MULTI-AGENT CUSTOMIZER MODAL (FREE) -->
<div id="customizerModal" class="fixed inset-0 bg-slate-950/90 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-white">Multi-Agent Customizer (Free & Unlocked)</h2>
        <button type="button" onclick="closeModal('customizerModal')" class="px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div class="p-6 max-w-xl mx-auto w-full flex-1 flex flex-col gap-4 overflow-y-auto">
        <div class="p-4 bg-emerald-950/40 border border-emerald-800 rounded-xl text-xs text-emerald-200">
            <p class="font-bold mb-1">✨ Fully Unlocked: Create any custom agent instantly without payment!</p>
        </div>
        <input type="text" id="custom-agent-prompt" placeholder="Custom Agent Objective (e.g., Build e-commerce store or complex calculator)" class="bg-slate-900 border border-slate-700 text-white rounded-xl px-4 py-3 text-xs">
        <button type="button" onclick="launchCustomAgent()" class="py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl cursor-pointer shadow-md">Launch Custom Agent</button>
    </div>
</div>

<!-- LIVE CHAT & OS AUTOMATION MODAL -->
<div id="chatbotModal" class="fixed inset-0 bg-slate-950/90 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
            <h2 class="font-bold text-sm text-white" id="active-chatbot-title">Nexus Astra OS</h2>
            <p class="text-[11px] text-rose-400" id="active-chatbot-subtitle">GPT-6 Astra Autonomous Operator Active</p>
        </div>
        <button type="button" onclick="closeModal('chatbotModal')" class="px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div id="chat-stream-container" class="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 flex flex-col max-w-4xl w-full mx-auto"></div>
    <div class="bg-slate-900 border-t border-slate-800 p-4 shrink-0">
        <div class="max-w-4xl mx-auto flex items-center space-x-2">
            <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Command agent (e.g., Build e-commerce store, form, or solve math)..." class="flex-1 bg-slate-950 border border-slate-700 text-white rounded-xl px-4 py-3 text-xs">
            <button type="button" onclick="sendQueryToGroqAI()" class="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl cursor-pointer">Execute</button>
        </div>
    </div>
</div>

<script>
    const agentsData = {{ agents_json | safe }};
    let activeAgent = "CyberNet Sovereign Prime-1";
    let activeDomain = "Autonomous Full-Stack Engineering";

    function openModal(mId) { const m = document.getElementById(mId); if(m) { m.style.display = 'flex'; m.classList.remove('hidden'); } }
    function closeModal(mId) { const m = document.getElementById(mId); if(m) { m.style.display = 'none'; m.classList.add('hidden'); } }

    const agentContainer = document.getElementById('agents-grid-container');
    function renderAgentsList(list) {
        if(!agentContainer) return;
        let html = "";
        list.forEach(a => {
            html += `<div class="glass-card p-4 rounded-2xl border border-slate-800 bg-slate-900 shadow-sm flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-[9px] font-mono text-emerald-400 font-bold">AGID #${a.id}</span>
                        <span class="text-[9px] px-2 py-0.5 rounded-full font-bold border bg-emerald-950 text-emerald-300 border-emerald-800">FREE</span>
                    </div>
                    <h3 class="font-bold text-xs mb-1 text-white">${a.name}</h3>
                    <p class="text-[10px] text-slate-400 font-semibold mb-2">${a.domain}</p>
                </div>
                <button type="button" onclick="deployAgentCheck(${a.id}, '${a.name}', '${a.domain}')" class="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold rounded-xl transition cursor-pointer">Deploy Agent</button>
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
        container.innerHTML += `<div class="flex justify-end"><div class="bg-indigo-600 text-white p-3 rounded-xl text-xs max-w-[80%]">${text}</div></div>`;
        input.value = ""; container.scrollTop = container.scrollHeight;

        const loadingId = 'loading-' + Date.now();
        container.innerHTML += `<div id="${loadingId}" class="flex items-start space-x-3"><div class="w-8 h-8 rounded-xl bg-rose-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div><div class="glass-card rounded-2xl p-4 text-xs text-rose-300 font-semibold max-w-[85%] animate-pulse bg-slate-900 border-slate-800">⚡ GPT-6 Astra OS & AI Engine compiling custom website & app...</div></div>`;
        container.scrollTop = container.scrollHeight;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, agent: activeAgent, domain: activeDomain }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            const data = await response.json();
            document.getElementById(loadingId).remove();

            if(response.status !== 200) {
                container.innerHTML += `<div class="text-rose-400 text-xs p-3 font-bold bg-rose-950/50 rounded-xl border border-rose-800">⚠️ Error: ${data.message}</div>`;
                return;
            }

            container.innerHTML += `<div class="flex items-start space-x-3"><div class="w-8 h-8 rounded-xl bg-rose-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div><div class="glass-card rounded-2xl p-4 text-xs text-slate-200 max-w-[85%] leading-relaxed font-mono whitespace-pre-wrap border border-slate-800 bg-slate-900"><strong class="text-rose-400">${activeAgent}:</strong><br><br>${data.reply}</div></div>`;
        } catch(e) {
            document.getElementById(loadingId).remove();
            let errMsg = e.name === 'AbortError' ? "Server timeout (> 90s)." : "Network Connection Error Handled.";
            container.innerHTML += `<div class="text-rose-400 text-xs p-3">⚠️ ${errMsg}</div>`;
        }
        container.scrollTop = container.scrollHeight;
    }

    function handleChatKeyPress(e) { if(e.key === 'Enter') sendQueryToGroqAI(); }

    function launchCustomAgent() {
        const promptText = document.getElementById('custom-agent-prompt').value.trim();
        if(!promptText) { alert("❌ कृपया कस्टम एजेंट का उद्देश्य (Objective) दर्ज करें!"); return; }
        closeModal('customizerModal'); 
        deployAgentCheck(999, promptText + " (Custom Free)", "Advanced Swarm");
    }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(
        HTML_PAGE, 
        agents_json=json.dumps(AGENTS_LIST)
    )

@app.route('/live-app/<app_id>')
def live_deployed_app(app_id):
    spec = request.args.get('spec', 'Custom Web Application')
    # अब यह फिक्स नहीं है! यह सीधे AI को कॉल करके आपके हर प्रॉम्प्ट के हिसाब से असली वेबसाइट कोड रेंडर करेगा।
    return generate_dynamic_website_via_ai(spec)

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
        
        # 1. वेबसाइट, ऐप या कोडिंग डिप्लॉयमेंट ट्रिगर
        deployment_triggers = ["deploy", "app", "code", "build", "website", "create site", "live link", "form", "store", "shop", "button", "calculator", "game"]
        if any(w in user_msg.lower() for w in deployment_triggers):
            app_id = str(uuid.uuid4())[:8]
            live_deployment_link = f"{base_url}/live-app/{app_id}?spec={requests.utils.quote(user_msg)}"
            
            reply_text = (
                f"🚀 **GPT-6 Astra Autonomous Deployment Success:**\n"
                f"- **Live Deployed App Link:** <a href='{live_deployment_link}' target='_blank' style='color: #38bdf8; text-decoration: underline; font-weight: bold;'>{live_deployment_link}</a>\n"
                f"- **Details:** Successfully architected and deployed custom web application for: '{user_msg}'"
            )
            return jsonify({"status": "success", "reply": reply_text})

        # 2. Groq AI चैट रिस्पॉन्स (हार्ड कोडिंग और मैथ्स सॉल्विंग)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            f"You are {active_agent}, expert in {active_domain}, powered by 50 enterprise backend AGI features and GPT-6 Astra OS control. "
            f"You excel at hard coding, building complex websites, and solving advanced mathematical problems with step-by-step logic."
        )
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        response = requests.post("[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)", json=payload, headers=headers, timeout=30)
        res_data = response.json()
        
        if response.status_code != 200:
            return jsonify({"status": "error", "message": str(res_data)}), 400
        
        return jsonify({"status": "success", "reply": res_data['choices'][0]['message']['content']})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
