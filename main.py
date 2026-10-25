from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI(title="Nexus Enterprise Sovereign AGI v36.0", version="36.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str
    agent_name: str = "Devin Code Architect #1"
    domain: str = "Software Engineering"

@app.post("/api/chat")
async def chat_with_agent(req: ChatRequest):
    # यहाँ अपनी असली Groq API Key डालें या Render एनवायरनमेंट से लें
    key = os.getenv("GROQ_API_KEY", "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")
    
    if not key or "gsk_" not in key:
        raise HTTPException(
            status_code=500, 
            detail="Groq API Key missing or invalid. Please check Render environment variables."
        )
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        f"You are {req.agent_name} operating strictly within the domain of {req.domain}. "
        "Provide professional, highly optimized, enterprise-grade technical answers directly and comprehensively. "
        "Never refuse queries, never say 'I am sorry', and always execute the user's technical requests with full implementation details."
    )
    
    # ग्रोक का सबसे एडवांस्ड मॉडल यहाँ सेट किया गया है
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 3072
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return {"status": "success", "reply": reply}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "system": "Nexus Enterprise AGI v36.0",
        "active_modules": 25,
        "agents_hub": "800 Agents Unlocked",
        "tech_giants": "300 Agents Unlocked",
        "model_active": "openai/gpt-oss-120b"
    }

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return """<!DOCTYPE html>
<html lang="en" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS Autonomous Enterprise Ecosystem v36.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .glass-panel { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(0, 0, 0, 0.08); }
        .glass-card { background: rgba(248, 250, 252, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(226, 232, 240, 0.8); transition: all 0.25s ease; }
        .glass-card:hover { border-color: rgba(99, 102, 241, 0.5); transform: translateY(-2px); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-100 text-slate-900 min-h-screen flex flex-col font-sans pb-10">

<header class="w-full max-w-2xl mx-auto p-6 flex items-center justify-between mt-2">
    <div class="flex items-center space-x-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-cyan-500 flex items-center justify-center font-black text-2xl text-white shadow-lg">Ω</div>
        <div class="text-left">
            <h1 class="text-sm md:text-base font-black tracking-wider bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-600 bg-clip-text text-transparent">NEXUS ENTERPRISE</h1>
            <p class="text-[10px] font-bold text-indigo-600">Autonomous Ecosystem v36.0 (Model: openai/gpt-oss-120b)</p>
        </div>
    </div>
    <div class="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-bold flex items-center space-x-1.5 shadow-sm">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>AGI Core Active</span>
    </div>
</header>

<section class="w-full max-w-2xl mx-auto px-4 space-y-3 mb-6">
    <div class="grid grid-cols-2 gap-3">
        <button onclick="openModal('agentsModal')" class="py-3.5 px-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-xs font-bold transition shadow-md flex items-center justify-center space-x-2">
            <span>⚡</span><span>800 Domain Agents Hub</span>
        </button>
        <button onclick="openModal('giantsModal')" class="py-3.5 px-4 rounded-2xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-xs font-bold transition shadow-md flex items-center justify-center space-x-2">
            <span>🚀</span><span>Tech Giants (300 Agents)</span>
        </button>
    </div>
    <div class="grid grid-cols-2 gap-3">
        <button onclick="openModal('customizerModal')" class="py-3 px-3 rounded-2xl bg-cyan-50 hover:bg-cyan-100 text-cyan-900 text-xs font-bold transition border border-cyan-200 flex items-center justify-center space-x-1.5">
            <span>🧬</span><span>Multi-Agent Customizer ($9/mo)</span>
        </button>
        <button onclick="openModal('chatbotCustomizerModal')" class="py-3 px-3 rounded-2xl bg-emerald-50 hover:bg-emerald-100 text-emerald-900 text-xs font-bold transition border border-emerald-200 flex items-center justify-center space-x-1.5">
            <span>⚙️</span><span>Multi-Chatbot Customizer</span>
        </button>
    </div>
    <div class="grid grid-cols-2 gap-3">
        <button onclick="openSelfHealingModal()" class="py-3 px-3 rounded-2xl bg-indigo-50 hover:bg-indigo-100 text-indigo-900 text-xs font-bold transition border border-indigo-200 flex items-center justify-center space-x-1.5">
            <span>🛠️</span><span>Self-Healing Engine</span>
        </button>
        <button onclick="openTerminalModal()" class="py-3 px-3 rounded-2xl bg-slate-900 hover:bg-slate-800 text-emerald-400 text-xs font-bold transition border border-slate-700 flex items-center justify-center space-x-1.5">
            <span>💻</span><span>Execution Terminal</span>
        </button>
    </div>
    <div>
        <button onclick="openModal('chatbotModal')" class="w-full py-3.5 px-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-bold transition flex items-center justify-center space-x-2 shadow-lg">
            <span>💬</span><span>Launch Active Agent / Live Chat Hub</span>
        </button>
    </div>
</section>

<!-- AGENTS MODAL -->
<div id="agentsModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">800 Autonomous AI Agents Hub (Unique Names)</h2>
        <button onclick="closeModal('agentsModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold">✕ Close</button>
    </div>
    <div class="p-4 bg-slate-100"><input type="text" id="agent-search" oninput="filterAgents()" placeholder="Search 800 agents..." class="w-full bg-white border border-slate-300 rounded-xl px-4 py-2 text-xs"></div>
    <div class="flex-1 overflow-y-auto p-6"><div id="agents-grid-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-7xl mx-auto"></div></div>
</div>

<!-- TECH GIANTS MODAL -->
<div id="giantsModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">300 Tech Giants Swarm (Unique Names)</h2>
        <button onclick="closeModal('giantsModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold">✕ Close</button>
    </div>
    <div class="p-4 bg-slate-100"><input type="text" id="giant-search" oninput="filterGiants()" placeholder="Search 300 tech giant agents..." class="w-full bg-white border border-slate-300 rounded-xl px-4 py-2 text-xs"></div>
    <div class="flex-1 overflow-y-auto p-6"><div id="giants-grid-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-7xl mx-auto"></div></div>
</div>

<!-- CUSTOMIZER MODAL -->
<div id="customizerModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">Multi-Agent Customizer ($9/mo Secured)</h2>
        <button onclick="closeModal('customizerModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold">✕ Close</button>
    </div>
    <div class="p-6 max-w-xl mx-auto w-full flex-1 flex flex-col gap-4">
        <input type="text" id="custom-agent-prompt" placeholder="e.g., Deep Python Async Expert" class="bg-white border rounded-xl px-4 py-3 text-xs">
        <button onclick="buildCustomAgent()" class="py-3 bg-indigo-600 text-white text-xs font-bold rounded-xl">Synthesize Agent</button>
    </div>
</div>

<!-- CHATBOT CUSTOMIZER MODAL -->
<div id="chatbotCustomizerModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <h2 class="font-bold text-sm text-slate-900">Multi-Chatbot Customizer Hub</h2>
        <button onclick="closeModal('chatbotCustomizerModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold">✕ Close</button>
    </div>
    <div class="p-6 max-w-xl mx-auto w-full flex-1 flex flex-col gap-4">
        <input type="text" id="custom-chatbot-name" placeholder="Chatbot Swarm Name..." class="bg-white border rounded-xl px-4 py-3 text-xs">
        <button onclick="saveCustomChatbot()" class="py-3 bg-emerald-600 text-white text-xs font-bold rounded-xl">Deploy Chatbot Swarm</button>
    </div>
</div>

<!-- CHATBOT MODAL -->
<div id="chatbotModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-xl hidden z-50 flex-col overflow-hidden">
    <div class="glass-panel border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
            <h2 class="font-bold text-sm text-slate-900" id="active-chatbot-title">Nexus AGI Hub</h2>
            <p class="text-[11px] text-indigo-600" id="active-chatbot-subtitle">Domain: Software Engineering</p>
        </div>
        <button onclick="closeModal('chatbotModal')" class="px-3 py-1.5 rounded-xl bg-slate-200 text-xs font-bold">✕ Close</button>
    </div>
    <div id="chat-stream-container" class="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 flex flex-col max-w-4xl w-full mx-auto"></div>
    <div class="glass-panel border-t p-4 shrink-0">
        <div class="max-w-4xl mx-auto flex items-center space-x-2">
            <input type="text" id="chat-input-box" onkeypress="handleChatKeyPress(event)" placeholder="Ask agent..." class="flex-1 bg-white border rounded-xl px-4 py-3 text-xs">
            <button onclick="sendQueryToGroqAI()" class="px-5 py-3 bg-indigo-600 text-white text-xs font-bold rounded-xl">Send</button>
        </div>
    </div>
</div>

<script>
    let allAgentsList = [];
    let allGiantsList = [];
    let activeAgent = "Devin Code Architect #1";
    let activeDomain = "Software Engineering";
    let isDataInitialized = false;

    window.addEventListener('DOMContentLoaded', () => {
        initializeData();
    });

    function initializeData() {
        if(isDataInitialized) return;
        
        // 800 Agents with 100% Unique Names & Distinct Designations
        const prefixes = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Prime", "Quantum", "Hyper", "Apex", "Nexus", "Vector", "Matrix", "Sovereign", "Cyber", "Neural", "Core"];
        const domains = ["Software Engineering", "Semiconductor & Silicon", "CyberSecurity & Defense", "Education & Pedagogy", "Quantum Computing", "Autonomous Robotics", "Cloud Infrastructure", "Neural Networks"];
        const roles = ["Architect", "Engine Lead", "Specialist", "Auditor", "Optimizer", "Master", "Synthesizer", "Analyst", "Sentinel", "Commander"];
        
        for(let i=1; i<=800; i++) {
            let pref = prefixes[(i * 7) % prefixes.length];
            let role = roles[(i * 3) % roles.length];
            let domain = domains[(i - 1) % domains.length];
            allAgentsList.push({ 
                id: i, 
                name: `${pref} Agent ${role} Unit-${i}`, 
                domain: domain, 
                desc: `Unique autonomous enterprise specialist unit #${i}.` 
            });
        }
        renderAgents(allAgentsList);

        // 300 Tech Giants with 100% Unique Names Across Providers
        const providers = ["OpenAI", "Anthropic", "Google DeepMind", "Nvidia", "Meta AI", "Microsoft Research", "Mistral AI", "Cohere", "DeepSeek", "Apple Intelligence"];
        const specialties = ["LLM Architecture", "ASIC & Silicon Design", "Threat Mitigation", "CUDA Acceleration", "AGI Reasoning", "Autonomous Agents", "Multimodal Vision", "Quantum Simulation"];
        
        for(let i=1; i<=300; i++) {
            let prov = providers[(i * 3) % providers.length];
            let spec = specialties[(i * 5) % specialties.length];
            allGiantsList.push({
                id: i,
                name: `${prov} Sovereign Swarm Node #${i}`,
                provider: prov,
                domain: "Advanced Tech Swarm",
                specialty: spec
            });
        }
        renderGiants(allGiantsList);
        isDataInitialized = true;
    }

    function openModal(modalId) {
        const m = document.getElementById(modalId);
        if(m) {
            m.classList.remove('hidden');
            m.classList.add('flex');
        }
    }

    function closeModal(modalId) {
        const m = document.getElementById(modalId);
        if(m) {
            m.classList.remove('flex');
            m.classList.add('hidden');
        }
    }
    
    function renderAgents(list) {
        const c = document.getElementById('agents-grid-container');
        let html = "";
        list.slice(0, 200).forEach(a => {
            html += `
                <div class="glass-card p-4 rounded-2xl border bg-white shadow-sm flex flex-col justify-between">
                    <div>
                        <span class="text-[9px] font-mono text-indigo-600 font-bold">ID #${a.id}</span>
                        <h3 class="font-bold text-xs mb-1 text-slate-900">${a.name}</h3>
                        <p class="text-[10px] text-indigo-600 font-semibold mb-2">${a.domain}</p>
                    </div>
                    <button onclick="selectAgent('${a.name}', '${a.domain}')" class="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold rounded-xl transition">Deploy</button>
                </div>`;
        });
        c.innerHTML = html;
    }

    function renderGiants(list) {
        const c = document.getElementById('giants-grid-container');
        let html = "";
        list.forEach(g => {
            html += `
                <div class="glass-card p-4 rounded-2xl border bg-white shadow-sm flex flex-col justify-between">
                    <div>
                        <span class="text-[9px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-bold">${g.provider}</span>
                        <h3 class="font-bold text-xs mt-2 text-slate-900">${g.name}</h3>
                        <p class="text-[10px] text-slate-600 mt-1">${g.specialty}</p>
                    </div>
                    <button onclick="selectAgent('${g.name}', '${g.domain}')" class="mt-3 w-full py-1.5 bg-violet-600 hover:bg-violet-500 text-white text-[10px] font-bold rounded-xl transition">Launch Chatbot</button>
                </div>`;
        });
        c.innerHTML = html;
    }

    function selectAgent(name, domain) {
        activeAgent = name;
        activeDomain = domain;
        document.getElementById('active-chatbot-title').innerText = `Active: ${name}`;
        document.getElementById('active-chatbot-subtitle').innerText = `Domain: ${domain}`;
        closeModal('agentsModal');
        closeModal('giantsModal');
        openModal('chatbotModal');
    }
    
    async function sendQueryToGroqAI() {
        const input = document.getElementById('chat-input-box');
        const text = input.value.trim();
        if(!text) return;
        
        const container = document.getElementById('chat-stream-container');
        container.innerHTML += `<div class="flex justify-end"><div class="bg-indigo-600 text-white p-3 rounded-xl text-xs max-w-[80%]" style="word-break: break-word;">${text}</div></div>`;
        input.value = "";
        container.scrollTop = container.scrollHeight;

        const loadingId = 'loading-' + Date.now();
        container.innerHTML += `
            <div id="${loadingId}" class="flex items-start space-x-3">
                <div class="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div>
                <div class="glass-card rounded-2xl p-4 text-xs text-indigo-700 font-semibold max-w-[85%] animate-pulse">
                    ⚡ Processing with ${activeAgent} via openai/gpt-oss-120b...
                </div>
            </div>
        `;
        container.scrollTop = container.scrollHeight;
        
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ prompt: text, agent_name: activeAgent, domain: activeDomain })
            });
            const data = await res.json();
            document.getElementById(loadingId).remove();
            
            if(res.status !== 200) {
                container.innerHTML += `<div class="text-rose-600 text-xs p-3">Server Error: ${data.detail || 'Check API Key configuration.'}</div>`;
                return;
            }

            container.innerHTML += `
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">AI</div>
                    <div class="glass-card rounded-2xl p-4 text-xs text-slate-800 max-w-[85%] leading-relaxed font-mono whitespace-pre-wrap border" style="word-break: break-word;">
                        <strong class="text-indigo-600">${activeAgent} (${activeDomain}):</strong><br><br>${data.reply}
                    </div>
                </div>`;
        } catch(e) {
            document.getElementById(loadingId).remove();
            container.innerHTML += `<div class="text-rose-600 text-xs p-3">Error connecting to server. Please verify your backend deployment and API key.</div>`;
        }
        container.scrollTop = container.scrollHeight;
    }

    function openSelfHealingModal() { alert("Self-Healing Diagnostic Matrix active and secure."); }
    function openTerminalModal() { alert("Autonomous Execution Terminal ready."); }
    function handleChatKeyPress(e) { if(e.key === 'Enter') sendQueryToGroqAI(); }
    
    function filterAgents() {
        const query = document.getElementById('agent-search').value.toLowerCase();
        const filtered = allAgentsList.filter(a => a.name.toLowerCase().includes(query) || a.domain.toLowerCase().includes(query));
        renderAgents(filtered);
    }

    function filterGiants() {
        const query = document.getElementById('giant-search').value.toLowerCase();
        const filtered = allGiantsList.filter(g => g.name.toLowerCase().includes(query) || g.provider.toLowerCase().includes(query));
        renderGiants(filtered);
    }
    
    function buildCustomAgent() {
        const prompt = document.getElementById('custom-agent-prompt').value.trim();
        if(!prompt) return;
        alert(`Custom Agent '${prompt}' successfully synthesized under $9/mo tier!`);
        closeModal('customizerModal');
        selectAgent(prompt + " (Custom)", "Software Engineering");
    }

    function saveCustomChatbot() {
        const name = document.getElementById('custom-chatbot-name').value.trim();
        if(!name) return;
        alert(`Chatbot Swarm '${name}' deployed successfully!`);
        closeModal('chatbotCustomizerModal');
        selectAgent(name, "Multi-Chatbot Swarm");
    }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
