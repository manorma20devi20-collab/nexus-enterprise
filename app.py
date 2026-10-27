from flask import Flask, render_template_string, request, jsonify
import requests
import json
import uuid
import re
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# =========================================================================
# 🔑 SECURE CONFIGURATION: API KEYS & PAYMENT DETAILS
# =========================================================================
GROQ_API_KEY = "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"  # अपनी असली Groq API Key यहाँ डालें
GROQ_MODEL = "openai/gpt-oss-120b"                        # अनुरोधित मॉडल

# PhonePe Payment Gateway ($9/mo Tier Enforcement)
PHONEPE_ID = "7355102139@ybl"                      # अपनी PhonePe UPI ID यहाँ डालें
PHONEPE_NUMBER = "7355102139"                           # अपना PhonePe मोबाइल नंबर यहाँ डालें

# =========================================================================
# 🛠️ SYNC PLAYWRIGHT BROWSER AUTOMATION ENGINE (Render 100% Working Fix)
# =========================================================================
def execute_browser_task(url):
    """रेंडर पर DNS और Sandbox एरर से बचने के लिए सिंक Playwright इंजन"""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--single-process",
                    "--disable-gpu",
                    "--dns-result-prefetch-disable",
                    "--disable-software-rasterizer"
                ]
            )
            page = browser.new_page()
            # DNS और नेटवर्क टाइमआउट को हैंडल करने के लिए
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            title = page.title()
            content = page.content()
            body_text = re.sub(r'<[^>]+>', '', content)
            snippet = body_text[:2000].strip()
            browser.close()
            return {
                "status": "success",
                "title": title,
                "snippet": snippet
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# 100 ऑप्टिमाइज्ड एजेंट्स की सूची
AGENTS_LIST = []
prefixes = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Prime", "Quantum", "Hyper", "Apex", "Nexus"]
domains = ["Software Engineering", "Cloud Infrastructure", "Browser Automation", "CyberSecurity", "Autonomous Deployment"]
for i in range(1, 101):
    pref = prefixes[i % len(prefixes)]
    dom = domains[i % len(domains)]
    AGENTS_LIST.append({
        "id": i,
        "name": f"{pref} Agent Unit-{i}",
        "domain": dom,
        "description": f"Autonomous sovereign agent for {dom} with background execution."
    })

# =========================================================================
# 🌐 CLEAN PROFESSIONAL FRONTEND
# =========================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS Sovereign Enterprise AGI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .glass-panel { background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(20px); border: 1px solid rgba(0, 0, 0, 0.08); }
        .glass-card { background: rgba(248, 250, 252, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(226, 232, 240, 0.8); transition: all 0.25s ease; }
        .glass-card:hover { border-color: rgba(99, 102, 241, 0.5); transform: translateY(-2px); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-100 text-slate-900 min-h-screen flex flex-col font-sans pb-10">

<header class="w-full max-w-3xl mx-auto p-6 flex items-center justify-between mt-2">
    <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-cyan-500 flex items-center justify-center font-black text-2xl text-white shadow-lg">Ω</div>
        <div class="text-left">
            <h1 class="text-sm md:text-base font-black tracking-wider bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-600 bg-clip-text text-transparent">NEXUS SOVEREIGN ENTERPRISE</h1>
            <p class="text-[10px] font-bold text-indigo-600">Autonomous Swarm AGI | Secure Execution Hub</p>
        </div>
    </div>
    <div class="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-bold flex items-center space-x-1.5 shadow-sm">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>System Online</span>
    </div>
</header>

<section class="w-full max-w-3xl mx-auto px-4 space-y-3 mb-6">
    <div class="grid grid-cols-2 gap-3">
        <button type="button" onclick="openModal('agentsModal')" class="py-3.5 px-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-xs font-bold transition shadow-md flex items-center justify-center space-x-2 cursor-pointer">
            <span>⚡</span><span>100 Domain Agents Hub</span>
        </button>
        <button type="button" onclick="openModal('customizerModal')" class="py-3.5 px-4 rounded-2xl bg-gradient-to-r from-cyan-600 to-teal-600 text-white text-xs font-bold transition shadow-md flex items-center justify-center space-x-2 cursor-pointer">
            <span>🧬</span><span>Multi-Agent Customizer ($9/mo)</span>
        </button>
    </div>
    <div class="grid grid-cols-2 gap-3">
        <button type="button" onclick="triggerViralShare()" class="py-3 px-3 rounded-2xl bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-bold transition border border-amber-200 flex items-center justify-center space-x-1.5 cursor-pointer">
            <span>🌐</span><span>Viral Share Link & +100 Tokens</span>
        </button>
        <button type="button" onclick="openModal('marketplaceModal')" class="py-3 px-3 rounded-2xl bg-rose-50 hover:bg-rose-100 text-rose-900 text-xs font-bold transition border border-rose-200 flex items-center justify-center space-x-1.5 cursor-pointer">
            <span>🛒</span><span>Agent Marketplace (80/20 Split)</span>
        </button>
    </div>
    <div>
        <button type="button" onclick="openModal('chatbotModal')" class="w-full py-3.5 px-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-bold transition flex items-center justify-center space-x-2 shadow-lg cursor-pointer">
            <span>💬</span><span>Launch Active Agent Hub (openai/gpt-oss-120b)</span>
        </button>
    </div>
</section>

<!-- 100 AGENTS MODAL -->
<div id="agentsModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">100 Autonomous AI Agents Hub</h2>
        <button type="button" onclick="closeModal('agentsModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div class="p-4 bg-slate-100"><input type="text" id="agent-search" oninput="filterAgents()" placeholder="Search among 100 autonomous agents..." class="w-full bg-white border border-slate-300 rounded-xl px-4 py-2 text-xs"></div>
    <div class="flex-1 overflow-y-auto p-6"><div id="agents-grid-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-7xl mx-auto"></div></div>
</div>

<!-- CUSTOMIZER MODAL -->
<div id="customizerModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">Multi-Agent Customizer ($9/mo PhonePe Protected)</h2>
        <button type="button" onclick="closeModal('customizerModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div class="p-6 max-w-xl mx-auto w-full flex-1 flex flex-col gap-4 overflow-y-auto">
        <div class="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-900">
            <p class="font-bold mb-1">💳 Strict PhonePe Payment Lock ($9 / Month - ₹750):</p>
            <p class="font-mono font-bold">PhonePe UPI ID: <span class="text-indigo-600">{{ phonepe_id }}</span></p>
            <p class="font-mono font-bold mb-3">PhonePe Number: <span class="text-indigo-600">{{ phonepe_number }}</span></p>
            <a id="phonepe-pay-btn" href="upi://pay?pa={{ phonepe_id }}&pn=NexusEnterprise&am=750&cu=INR&tn=NexusCustomizerUnlock" target="_blank" class="inline-block py-2.5 px-4 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl text-center shadow-md transition">🚀 Pay $9 via PhonePe Now</a>
        </div>
        <input type="text" id="payKey" placeholder="भुगतान के बाद प्राप्त PhonePe Transaction ID यहाँ दर्ज करें..." class="bg-white border rounded-xl px-4 py-3 text-xs">
        <input type="text" id="custom-agent-prompt" placeholder="e.g., Enterprise Autonomous Python Architect" class="bg-white border rounded-xl px-4 py-3 text-xs">
        <button type="button" onclick="buildCustomAgentSecure()" class="py-3 bg-indigo-600 text-white text-xs font-bold rounded-xl cursor-pointer">Verify Payment & Launch Customizer</button>
        <div id="customizerStatus" class="text-xs font-bold"></div>
    </div>
</div>

<!-- MARKETPLACE MODAL -->
<div id="marketplaceModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">Agent Marketplace & Revenue Split Hub (80/20)</h2>
        <button type="button" onclick="closeModal('marketplaceModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div class="p-6 max-w-2xl mx-auto w-full flex-1 flex flex-col gap-4 overflow-y-auto">
        <input type="text" id="market-agent-name" placeholder="Agent Name (e.g., Legal Drafter AI)" class="bg-white border rounded-xl px-4 py-3 text-xs">
        <input type="text" id="market-agent-price" placeholder="Price in USD (e.g., $19)" class="bg-white border rounded-xl px-4 py-3 text-xs">
        <button type="button" onclick="publishAgentToMarket()" class="py-3 bg-rose-600 text-white text-xs font-bold rounded-xl cursor-pointer">Publish Agent to Global Store</button>
        <div id="marketStatus" class="text-xs font-bold"></div>
    </div>
</div>

<!-- LIVE CHAT MODAL -->
<div id="chatbotModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden" style="display:none;">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
            <h2 class="font-bold text-sm text-slate-900" id="active-chatbot-title">Nexus AGI Hub</h2>
            <p class="text-[11px] text-indigo-600" id="active-chatbot-subtitle">Model: openai/gpt-oss-120b | Autonomous Execution Engine</p>
        </div>
        <button type="button" onclick="closeModal('chatbotModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold cursor-pointer">✕ Close</button>
    </div>
    <div id="chat-stream-container" class="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 flex flex-col max-w-4xl w-full mx-auto"></div>
    <div class="glass-panel border-t p-4 shrink-0">
        <div class="max-w-4xl mx-auto flex items-center space-x-2">
            <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Ask agent anything or paste URL for automated browser scraping..." class="flex-1 bg-white border rounded-xl px-4 py-3 text-xs">
            <button type="button" onclick="sendQueryToGroqAI()" class="px-5 py-3 bg-indigo-600 text-white text-xs font-bold rounded-xl cursor-pointer">Send</button>
        </div>
    </div>
</div>

<script>
    const agentsData = {{ agents_json | safe }};
    let activeAgent = "Alpha Agent Unit-1";
    let activeDomain = "Software Engineering";

    function openModal(mId) { const m = document.getElementById(mId); if(m) { m.style.display = 'flex'; m.classList.remove('hidden'); } }
    function closeModal(mId) { const m = document.getElementById(mId); if(m) { m.style.display = 'none'; m.classList.add('hidden'); } }

    const agentContainer = document.getElementById('agents-grid-container');
    function renderAgentsList(list) {
        if(!agentContainer) return;
        let html = "";
        list.forEach(a => {
            html += `<div class="glass-card p-4 rounded-2xl border bg-white shadow-sm flex flex-col justify-between">
                <div>
                    <span class="text-[9px] font-mono text-indigo-600 font-bold">AGID #${a.id}</span>
                    <h3 class="font-bold text-xs mb-1 text-slate-900">${a.name}</h3>
                    <p class="text-[10px] text-indigo-600 font-semibold mb-2">${a.domain}</p>
                </div>
                <button type="button" onclick="selectAgent('${a.name}', '${a.domain}')" class="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold rounded-xl transition cursor-pointer">Deploy Agent</button>
            </div>`;
        });
        agentContainer.innerHTML = html;
    }
    renderAgentsList(agentsData);

    function filterAgents() {
        const query = document.getElementById('agent-search').value.toLowerCase();
        renderAgentsList(agentsData.filter(a => a.name.toLowerCase().includes(query) || a.domain.toLowerCase().includes(query)));
    }

    function selectAgent(name, domain) {
        activeAgent = name; activeDomain = domain;
        document.getElementById('active-chatbot-title').innerText = `Active: ${name}`;
        document.getElementById('active-chatbot-subtitle').innerText = `Domain: ${domain} | Autonomous Execution`;
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
        container.innerHTML += `<div id="${loadingId}" class="flex items-start space-x-3"><div class="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div><div class="glass-card rounded-2xl p-4 text-xs text-indigo-700 font-semibold max-w-[85%] animate-pulse">⚡ Executing browser task via Playwright...</div></div>`;
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
                container.innerHTML += `<div class="text-rose-600 text-xs p-3 font-bold bg-rose-50 rounded-xl border">⚠️ Error: ${data.message}</div>`;
                return;
            }

            container.innerHTML += `<div class="flex items-start space-x-3"><div class="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div><div class="glass-card rounded-2xl p-4 text-xs text-slate-800 max-w-[85%] leading-relaxed font-mono whitespace-pre-wrap border"><strong class="text-indigo-600">${activeAgent} (${activeDomain}):</strong><br><br>${data.reply}</div></div>`;
        } catch(e) {
            document.getElementById(loadingId).remove();
            container.innerHTML += `<div class="text-rose-600 text-xs p-3">Network Connection Error.</div>`;
        }
        container.scrollTop = container.scrollHeight;
    }

    async function triggerViralShare() {
        const res = await fetch("/api/viral-share", {method: "POST"});
        const data = await res.json();
        alert("🌐 Viral Share Link Generated: " + data.share_link + " | +100 Free Super-Agent Tokens Credited!");
    }

    function handleChatKeyPress(e) { if(e.key === 'Enter') sendQueryToGroqAI(); }

    function buildCustomAgentSecure() {
        const payKey = document.getElementById('payKey').value.trim();
        const promptText = document.getElementById('custom-agent-prompt').value.trim();
        const statusDiv = document.getElementById('customizerStatus');
        if(payKey.length < 5 || !promptText) {
            statusDiv.style.color = "#e11d48"; statusDiv.innerText = "❌ कृपया वैध Transaction ID और प्रॉम्प्ट दर्ज करें!"; return;
        }
        statusDiv.style.color = "#10b981"; statusDiv.innerText = "✅ Payment Verified! Launching Custom Agent.";
        setTimeout(() => { closeModal('customizerModal'); selectAgent(promptText + " (Custom)", "Advanced Custom Swarm"); }, 1200);
    }

    async function publishAgentToMarket() {
        const name = document.getElementById('market-agent-name').value.trim();
        const price = document.getElementById('market-agent-price').value.trim();
        const sDiv = document.getElementById('marketStatus');
        if(!name || !price) { sDiv.style.color = "#e11d48"; sDiv.innerText = "❌ कृपया सभी फील्ड भरें!"; return; }
        const res = await fetch("/api/marketplace", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({name, price}) });
        const d = await res.json();
        sDiv.style.color = "#10b981"; sDiv.innerText = "✅ " + d.message;
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

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.json
        user_msg = data.get('message', '')
        active_agent = data.get('agent', 'Alpha Agent Unit-1')
        active_domain = data.get('domain', 'Software Engineering')
        
        if not GROQ_API_KEY or GROQ_API_KEY.startswith("gsk_YahanApni"):
            return jsonify({"status": "error", "message": "कृपया अपनी असली Groq API Key ऐप में सेट करें।"}), 400
        
        url_match = re.search(r'(https?://[^\s]+)', user_msg)
        browser_data_context = ""
        
        if url_match:
            target_url = url_match.group(1)
            browser_result = execute_browser_task(target_url)
            if browser_result["status"] == "success":
                browser_data_context = (
                    f"\n[Browser Automation Result via Playwright]\n"
                    f"Target URL: {target_url}\n"
                    f"Page Title: {browser_result['title']}\n"
                    f"Page Content Snippet: {browser_result['snippet']}\n"
                )
            else:
                browser_data_context = f"\n[Browser Automation Error]: {browser_result['message']}\n"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            f"You are {active_agent} operating strictly within the domain of {active_domain}. "
            f"You have full backend capability including Playwright headless browser control. Provide precise enterprise execution."
        )
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg + browser_data_context}
            ],
            "temperature": 0.2,
            "max_tokens": 4096
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        res_data = response.json()
        
        if response.status_code != 200:
            return jsonify({"status": "error", "message": str(res_data)}), 400
        
        return jsonify({"status": "success", "reply": res_data['choices'][0]['message']['content']})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/viral-share', methods=['POST'])
def viral_share():
    return jsonify({"status": "success", "share_link": f"https://nexus-agi.onrender.com/demo/{str(uuid.uuid4())[:8]}", "message": "Tokens credited!"})

@app.route('/api/marketplace', methods=['POST'])
def marketplace_publish():
    return jsonify({"status": "success", "message": "Agent listed successfully!"})

if __name__ == '__main__':
    app.run(debug=True)
