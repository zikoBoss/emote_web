import os
import time
import json
import requests
from collections import defaultdict
from flask import Flask, request, jsonify, render_template_string, session
from upstash_redis import Redis

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key-change-this")

API_BASE = os.environ.get("API_BASE")
API_KEY = os.environ.get("API_KEY")
IMAGE_BASE = os.environ.get("IMAGE_BASE")
DATA_URL = os.environ.get("DATA_URL")
ADMIN_CODE = os.environ.get("ADMIN_CODE", "ZikoB0SS2006")

if not API_BASE or not API_KEY or not IMAGE_BASE or not DATA_URL:
    raise ValueError("Missing required environment variables: API_BASE, API_KEY, IMAGE_BASE, DATA_URL")

# إعداد Redis
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is required for Vercel deployment")
redis = Redis.from_url(REDIS_URL)

def get_maintenance():
    data = redis.get("maintenance")
    if data:
        return json.loads(data)
    return {"enabled": False, "message": "Site is under maintenance. Please come back later."}

def set_maintenance(data):
    redis.set("maintenance", json.dumps(data))

maintenance = get_maintenance()

request_history = defaultdict(list)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XcTxTeaM EeMoT</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:radial-gradient(circle at 20% 30%,#0a0a0a,#000);font-family:'Segoe UI',system-ui;color:#f0f0f0;padding:20px;overflow-x:hidden}
        .container{max-width:1400px;margin:0 auto;transition:transform 0.3s ease}
        .header{text-align:center;margin-bottom:30px;position:relative}
        .header h1{font-size:2.6rem;background:linear-gradient(135deg,#fff,#aa2e2e);-webkit-background-clip:text;background-clip:text;color:transparent}
        .header p{color:#bbb;margin-top:8px}
        .sidebar{position:fixed;top:0;left:-320px;width:300px;height:100%;background:#0f0f0f;border-right:1px solid #3a2a2a;z-index:1000;transition:left 0.3s ease;padding:20px;box-shadow:5px 0 15px rgba(0,0,0,0.5)}
        .sidebar.open{left:0}
        .sidebar h3{color:#cc5555;margin-bottom:20px;border-bottom:1px solid #3a2a2a;padding-bottom:10px}
        .sidebar .field{margin-bottom:20px}
        .sidebar label{display:block;font-size:0.8rem;color:#dd8888;margin-bottom:5px}
        .sidebar input,.sidebar select{width:100%;background:#1a1a1a;border:1px solid #3a2a2a;border-radius:20px;padding:10px 15px;color:#fff}
        .sidebar button{background:linear-gradient(135deg,#a22,#600);border:none;color:#fff;padding:10px;border-radius:40px;cursor:pointer;width:100%;font-weight:bold}
        .sidebar button:disabled{opacity:0.5;cursor:not-allowed}
        .overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:999;display:none}
        .overlay.active{display:block}
        .menu-icon,.admin-icon{position:fixed;background:#1f1f1f;border-radius:50%;width:45px;height:45px;display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:1001;border:1px solid #a22;box-shadow:0 2px 10px rgba(0,0,0,0.5)}
        .menu-icon{top:20px;left:20px}
        .admin-icon{bottom:20px;left:20px}
        .menu-icon svg,.admin-icon svg{width:24px;height:24px;fill:#cc5555}
        .admin-modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#111;border-radius:28px;padding:25px;z-index:1100;width:90%;max-width:400px;border:1px solid #a22;display:none;flex-direction:column;gap:15px}
        .admin-modal input,.admin-modal textarea{background:#1a1a1a;border:1px solid #3a2a2a;border-radius:20px;padding:10px;color:#fff}
        .admin-modal button{background:#a22;border:none;padding:10px;border-radius:40px;color:#fff;cursor:pointer}
        .admin-modal .close{background:#333;margin-top:5px}
        .maintenance-message{background:#2a1a1a;border-left:6px solid #a22;padding:12px;margin-bottom:20px;border-radius:12px;text-align:center}
        .input-card{background:rgba(15,15,15,0.8);backdrop-filter:blur(12px);border-radius:32px;padding:24px;margin-bottom:30px;border:1px solid rgba(200,50,50,0.3)}
        .field-group{display:flex;flex-wrap:wrap;gap:20px;margin-bottom:20px}
        .field{flex:1;min-width:180px}
        .field label{display:block;font-size:0.8rem;font-weight:600;text-transform:uppercase;color:#cc5555;margin-bottom:8px}
        .field input,.uid-input{width:100%;background:#1a1a1a;border:1px solid #3a2a2a;border-radius:20px;padding:12px 18px;color:#fff;font-size:1rem}
        .uids-area{background:rgba(0,0,0,0.4);border-radius:24px;padding:16px;margin-top:10px}
        .uids-header{display:flex;justify-content:space-between;margin-bottom:12px}
        .add-uid-btn{background:linear-gradient(135deg,#a22,#600);border:none;color:#fff;padding:6px 16px;border-radius:40px;cursor:pointer}
        .uids-container{display:flex;flex-wrap:wrap;gap:12px}
        .uid-input{flex:1;min-width:110px;background:#151515}
        .search-bar{text-align:center;margin-bottom:30px}
        .search-bar input{width:100%;max-width:500px;background:#111;border:1px solid #3a2a2a;border-radius:50px;padding:14px 24px;color:#fff}
        .ob-filters{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:30px}
        .ob-btn{background:#1f1f1f;border:none;padding:8px 18px;border-radius:40px;color:#ccc;cursor:pointer}
        .ob-btn.active{background:linear-gradient(135deg,#b33,#800);color:#fff}
        .emote-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:20px;max-height:60vh;overflow-y:auto;padding:8px 4px 20px}
        .emote-card{background:linear-gradient(145deg,#111,#0a0a0a);border-radius:28px;padding:16px 8px;text-align:center;cursor:pointer;border:1px solid #2a1a1a;transition:0.2s}
        .emote-card:hover{transform:translateY(-6px);border-color:#aa4444;box-shadow:0 12px 24px rgba(170,0,0,0.3)}
        .emote-card img{width:80px;height:80px;object-fit:contain}
        .emote-id{font-size:11px;color:#aa7777;margin-top:10px}
        .emote-name{font-size:13px;font-weight:500;margin-top:4px}
        .pagination{display:flex;justify-content:center;gap:10px;margin:30px 0}
        .pagination button{background:#1e1e1e;border:none;color:#fff;padding:8px 16px;border-radius:30px;cursor:pointer}
        .pagination button.active-page{background:#b33}
        .toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#1f1f1f;backdrop-filter:blur(12px);border-radius:50px;padding:12px 28px;color:#fff;z-index:2000;opacity:0;transition:opacity 0.3s;pointer-events:none;border-left:6px solid #b33}
        .toast.success{border-left-color:#2e7d32;background:#1e2a1e}
        .toast.error{border-left-color:#c62828;background:#2a1a1a}
        footer{text-align:center;margin-top:40px;padding:20px;border-top:1px solid #2a1a1a;color:#aa8888}
        footer a{color:#dd5555;text-decoration:none;cursor:pointer}
        ::-webkit-scrollbar{width:6px}
        ::-webkit-scrollbar-track{background:#1a1a1a}
        ::-webkit-scrollbar-thumb{background:#b33;border-radius:10px}
    </style>
</head>
<body>
<div class="menu-icon" id="menuIcon">
    <svg viewBox="0 0 24 24"><path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z"/></svg>
</div>
<div class="admin-icon" id="adminIcon">
    <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/></svg>
</div>
<div class="sidebar" id="sidebar">
    <h3>Invite to Squad</h3>
    <div class="field">
        <label>Your UID</label>
        <input type="text" id="inviteUid" placeholder="Enter your UID">
    </div>
    <div class="field">
        <label>Squad Size</label>
        <select id="squadSize">
            <option value="3">3 Players</option>
            <option value="5">5 Players</option>
            <option value="6">6 Players</option>
        </select>
    </div>
    <button id="inviteBtn">Send Invite</button>
</div>
<div class="overlay" id="overlay"></div>

<div class="admin-modal" id="adminModal">
    <h3>Admin Panel</h3>
    <input type="password" id="adminCode" placeholder="Enter admin code">
    <button id="verifyAdminBtn">Verify</button>
    <div id="adminControls" style="display:none; margin-top:15px">
        <label style="display:flex; align-items:center; gap:10px; margin-bottom:10px">
            <input type="checkbox" id="maintenanceToggle"> Maintenance Mode
        </label>
        <textarea id="maintenanceMsg" rows="3" placeholder="Maintenance message..."></textarea>
        <button id="saveMaintenanceBtn">Save Changes</button>
    </div>
    <button class="close" id="closeAdminModal">Close</button>
</div>

<div class="container" id="mainContent">
    <div class="header"><h1>𝕏𝕔𝕋𝕩𝕋𝕖𝕒𝕄 𝔼𝕖𝕄𝕠𝕋</h1><p>Click any emote to send instantly</p></div>
    <div id="maintenanceBanner" style="display:none" class="maintenance-message"></div>
    <div class="input-card">
        <div class="field-group"><div class="field"><label>🏷️ Team Code</label><input type="text" id="teamCode" placeholder="Example: ABC123"></div></div>
        <div class="uids-area">
            <div class="uids-header"><span>👥 Player UIDs (max 5)</span><button class="add-uid-btn" id="addUidBtn">+ Add UID</button></div>
            <div id="uidsContainer" class="uids-container"><input type="text" class="uid-input" placeholder="UID 1"></div>
            <div style="font-size:12px;color:#a55;margin-top:8px">※ Max 5 players</div>
        </div>
    </div>
    <div class="search-bar"><input type="text" id="searchBox" placeholder="🔍 Search by name or ID"></div>
    <div id="obFilterContainer" class="ob-filters"></div>
    <div id="itemsGrid" class="emote-grid">Loading...</div>
    <div class="pagination" id="pagination"></div>
    <footer>dev by <a id="devLink">Zakaria</a></footer>
</div>

<script>
    const API_DANCE = "/api/dance";
    const API_DATA = "/api/data";
    const API_IMAGE_BASE = "/api/image/";
    const API_INVITE = "/api/invite";
    const API_SQUAD = "/api/squad";
    const API_ADMIN_VERIFY = "/api/admin/verify";
    const API_ADMIN_STATUS = "/api/admin/status";
    const API_ADMIN_SET = "/api/admin/set";
    const FALLBACK_IMG = "https://via.placeholder.com/80/222222/FF5555?text=Emote";

    let allItems = [], filteredItems = [], currentPage = 1, itemsPerPage = 30, activeOB = null;
    let isThrottled = false;
    let inviteThrottled = false;
    const THROTTLE_MS = 2000;
    const INVITE_THROTTLE_MS = 10000;

    const menuIcon = document.getElementById('menuIcon');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const adminIcon = document.getElementById('adminIcon');
    const adminModal = document.getElementById('adminModal');
    const closeAdminModal = document.getElementById('closeAdminModal');
    const verifyAdminBtn = document.getElementById('verifyAdminBtn');
    const adminControls = document.getElementById('adminControls');
    const maintenanceToggle = document.getElementById('maintenanceToggle');
    const maintenanceMsg = document.getElementById('maintenanceMsg');
    const saveMaintenanceBtn = document.getElementById('saveMaintenanceBtn');
    const maintenanceBanner = document.getElementById('maintenanceBanner');
    const inviteBtn = document.getElementById('inviteBtn');
    const inviteUid = document.getElementById('inviteUid');
    const squadSize = document.getElementById('squadSize');

    function toggleSidebar(show) {
        if(show === undefined) show = !sidebar.classList.contains('open');
        if(show) {
            sidebar.classList.add('open');
            overlay.classList.add('active');
        } else {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
    }
    menuIcon.onclick = () => toggleSidebar();
    overlay.onclick = () => toggleSidebar(false);

    adminIcon.onclick = () => {
        adminModal.style.display = 'flex';
    };
    closeAdminModal.onclick = () => {
        adminModal.style.display = 'none';
    };

    async function checkAdminStatus() {
        try {
            const res = await fetch('/api/admin/check');
            const data = await res.json();
            if(data.isAdmin) {
                adminControls.style.display = 'block';
                const statusRes = await fetch(API_ADMIN_STATUS);
                const status = await statusRes.json();
                maintenanceToggle.checked = status.enabled;
                maintenanceMsg.value = status.message;
            } else {
                adminControls.style.display = 'none';
            }
        } catch(e) {}
    }

    verifyAdminBtn.onclick = async () => {
        const code = document.getElementById('adminCode').value;
        const res = await fetch(API_ADMIN_VERIFY, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code})
        });
        const data = await res.json();
        if(data.success) {
            alert('Admin verified');
            checkAdminStatus();
        } else {
            alert('Invalid code');
        }
    };

    saveMaintenanceBtn.onclick = async () => {
        const enabled = maintenanceToggle.checked;
        const message = maintenanceMsg.value;
        const res = await fetch(API_ADMIN_SET, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled, message})
        });
        const data = await res.json();
        if(data.success) {
            alert('Maintenance settings saved');
            location.reload();
        } else {
            alert('Failed to save');
        }
    };

    async function fetchData() {
        try {
            const res = await fetch(API_DATA);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            allItems = await res.json();
            filteredItems = [...allItems];
            renderItems();
            buildOBFilters();
            showToast(`✅ Loaded ${allItems.length} emotes`);
        } catch(err) {
            document.getElementById('itemsGrid').innerHTML = `<div style="text-align:center;padding:40px;">❌ Failed to load data<br>${err.message}</div>`;
        }
    }

    function buildOBFilters() {
        const versions = new Set();
        allItems.forEach(item => {
            let idStr = item.Id.toString();
            if (idStr.length >= 6) versions.add("OB" + idStr.substring(4,6));
        });
        const sorted = [...versions].sort((a,b)=>parseInt(b.slice(2))-parseInt(a.slice(2)));
        const container = document.getElementById('obFilterContainer');
        container.innerHTML = '<button class="ob-btn" data-ob="all">All</button>';
        sorted.forEach(ob => {
            const btn = document.createElement('button');
            btn.className = 'ob-btn';
            btn.innerText = ob;
            btn.onclick = () => filterByOB(ob);
            container.appendChild(btn);
        });
        highlightActiveOB();
    }

    function filterByOB(ob) {
        activeOB = ob === 'all' ? null : ob;
        if (activeOB) {
            const code = activeOB.slice(2);
            filteredItems = allItems.filter(item => item.Id.toString().startsWith("9090"+code));
        } else {
            filteredItems = [...allItems];
        }
        currentPage = 1;
        renderItems();
        highlightActiveOB();
    }

    function highlightActiveOB() {
        document.querySelectorAll('.ob-btn').forEach(btn => {
            if ((activeOB === null && btn.dataset.ob === 'all') || btn.dataset.ob === activeOB)
                btn.classList.add('active');
            else btn.classList.remove('active');
        });
    }

    function renderItems() {
        const searchTerm = document.getElementById('searchBox').value.toLowerCase();
        let data = filteredItems.filter(item => item.name.toLowerCase().includes(searchTerm) || item.Id.toString().includes(searchTerm));
        const grid = document.getElementById('itemsGrid');
        if (!data.length) { grid.innerHTML = '<div style="text-align:center;padding:50px;">No results</div>'; updatePagination(0); return; }
        const start = (currentPage-1)*itemsPerPage;
        const pageItems = data.slice(start, start+itemsPerPage);
        grid.innerHTML = '';
        pageItems.forEach(item => {
            const card = document.createElement('div');
            card.className = 'emote-card';
            const imgSrc = `${API_IMAGE_BASE}${item.Id}`;
            card.innerHTML = `<img src="${imgSrc}" onerror="this.src='${FALLBACK_IMG}'" alt="${item.name}"><div class="emote-id">${item.Id}</div><div class="emote-name">${item.name}</div>`;
            card.onclick = () => sendEmote(item);
            grid.appendChild(card);
        });
        updatePagination(data.length);
    }

    function updatePagination(total) {
        const totalPages = Math.ceil(total/itemsPerPage);
        const pagDiv = document.getElementById('pagination');
        if (totalPages <= 1) { pagDiv.innerHTML = ''; return; }
        pagDiv.innerHTML = '';
        for (let i=1; i<=Math.min(totalPages,6); i++) {
            const btn = document.createElement('button');
            btn.innerText = i;
            if (i === currentPage) btn.classList.add('active-page');
            btn.onclick = () => { currentPage=i; renderItems(); window.scrollTo({top:0,behavior:'smooth'}); };
            pagDiv.appendChild(btn);
        }
    }

    function showToast(msg, isError=false) {
        const toast = document.createElement('div');
        toast.className = `toast ${isError ? 'error' : 'success'}`;
        toast.innerText = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.style.opacity = '1', 10);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 400); }, 3000);
    }

    function getUIDs() {
        const inputs = document.querySelectorAll('.uid-input');
        const uids = Array.from(inputs).map(i=>i.value.trim()).filter(v=>v && /^\d+$/.test(v));
        if (uids.length > 5) { showToast('⚠️ Max 5 players', true); return null; }
        if (!uids.length) { showToast('❌ Add at least one UID', true); return null; }
        return uids;
    }

    async function sendEmote(item) {
        if (isThrottled) { showToast('⏳ Please wait 2 seconds', true); return; }
        const teamCode = document.getElementById('teamCode').value.trim();
        if (!teamCode) { showToast('❌ Enter team code', true); return; }
        const uids = getUIDs();
        if (!uids) return;
        const uidsParam = uids.join(',');
        const url = `${API_DANCE}?emote_id=${item.Id}&team_code=${encodeURIComponent(teamCode)}&uids=${encodeURIComponent(uidsParam)}`;
        isThrottled = true;
        setTimeout(() => { isThrottled = false; }, THROTTLE_MS);
        showToast(`⏳ Sending ${item.name}...`);
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.success) showToast(`✅ ${data.message}`);
            else showToast(`❌ Failed: ${data.message || 'Error'}`, true);
        } catch(err) {
            showToast(`❌ Connection error: ${err.message}`, true);
        }
    }

    async function sendInvite() {
        if (inviteThrottled) { showToast('⏳ Please wait 10 seconds before sending another invite', true); return; }
        const uid = inviteUid.value.trim();
        if (!uid || !/^\d+$/.test(uid)) { showToast('❌ Enter a valid UID', true); return; }
        const size = squadSize.value;
        let endpoint = '';
        if (size === '3') endpoint = '/3';
        else if (size === '5') endpoint = '/5';
        else if (size === '6') endpoint = '/6';
        const url = `${API_SQUAD}${endpoint}?uid=${uid}`;
        inviteThrottled = true;
        setTimeout(() => { inviteThrottled = false; }, INVITE_THROTTLE_MS);
        showToast(`⏳ Sending invite for ${size}-player squad...`);
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.success) showToast(`✅ Invite sent for ${size}-player squad`);
            else showToast(`❌ Failed: ${data.message || 'Error'}`, true);
        } catch(err) {
            showToast(`❌ Connection error: ${err.message}`, true);
        }
    }

    inviteBtn.onclick = sendInvite;

    document.getElementById('addUidBtn').onclick = () => {
        const container = document.getElementById('uidsContainer');
        if (document.querySelectorAll('.uid-input').length >= 5) { showToast('⚠️ Max 5 players', true); return; }
        const newInput = document.createElement('input');
        newInput.type = 'text';
        newInput.className = 'uid-input';
        newInput.placeholder = `UID ${document.querySelectorAll('.uid-input').length+1}`;
        container.appendChild(newInput);
    };
    let searchTimeout;
    document.getElementById('searchBox').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => { currentPage=1; renderItems(); }, 300);
    });
    document.getElementById('devLink').onclick = () => window.open('https://t.me/ZikoB0SS', '_blank');

    async function checkMaintenance() {
        try {
            const res = await fetch(API_ADMIN_STATUS);
            const data = await res.json();
            if(data.enabled) {
                const banner = document.getElementById('maintenanceBanner');
                banner.style.display = 'block';
                banner.innerText = data.message;
                document.querySelectorAll('.emote-card, .add-uid-btn, #inviteBtn, .uid-input, #teamCode, .ob-btn, .search-bar input').forEach(el => {
                    el.disabled = true;
                });
                showToast('Site is in maintenance mode', true);
            }
        } catch(e) {}
    }

    fetchData();
    checkAdminStatus();
    checkMaintenance();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def is_admin():
    return session.get('admin', False)

@app.route('/api/admin/verify', methods=['POST'])
def verify_admin():
    data = request.json
    if data and data.get('code') == ADMIN_CODE:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 403

@app.route('/api/admin/check')
def admin_check():
    return jsonify({"isAdmin": is_admin()})

@app.route('/api/admin/status')
def admin_status():
    return jsonify(get_maintenance())

@app.route('/api/admin/set', methods=['POST'])
def admin_set():
    if not is_admin():
        return jsonify({"success": False}), 403
    data = request.json
    new_maintenance = {"enabled": data.get('enabled', False), "message": data.get('message', 'Maintenance mode active')}
    set_maintenance(new_maintenance)
    return jsonify({"success": True})

def maintenance_check():
    maint = get_maintenance()
    if maint['enabled'] and not is_admin():
        return jsonify({"success": False, "message": maint['message']}), 503
    return None

def rate_limit(ip):
    # Vercel will not persist across instances, but we can keep it per request
    # In serverless we might skip or use Redis, but for simplicity we'll use a limited dictionary
    # This is not perfect but better than nothing.
    now = time.time()
    # We'll store in memory; it will reset per instance, which is fine for rate limiting
    # We'll use a global dict, but be aware it's not shared across instances
    # For simplicity, leave as is.
    if ip not in request_history:
        request_history[ip] = []
    request_history[ip] = [t for t in request_history[ip] if now - t < 30]
    if len(request_history[ip]) >= 15:
        return True
    request_history[ip].append(now)
    return False

@app.route('/api/dance')
def proxy_dance():
    maint = maintenance_check()
    if maint:
        return maint
    ip = request.remote_addr
    if rate_limit(ip):
        return jsonify({"success": False, "message": "Too many requests"}), 429
    emote_id = request.args.get('emote_id')
    team_code = request.args.get('team_code')
    uids = request.args.get('uids')
    if not emote_id or not team_code or not uids:
        return jsonify({"success": False, "message": "Missing parameters"}), 400
    target = f"{API_BASE}/dance?emote_id={emote_id}&team_code={team_code}&uids={uids}&api_key={API_KEY}"
    try:
        resp = requests.get(target, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/squad/<path:endpoint>')
def proxy_squad(endpoint):
    if endpoint not in ('3', '5', '6'):
        return jsonify({"success": False, "message": "Invalid squad size"}), 400
    maint = maintenance_check()
    if maint:
        return maint
    ip = request.remote_addr
    if rate_limit(ip):
        return jsonify({"success": False, "message": "Too many requests"}), 429
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"success": False, "message": "Missing UID"}), 400
    target = f"{API_BASE}/{endpoint}?uid={uid}&api_key={API_KEY}"
    try:
        resp = requests.get(target, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/invite')
def proxy_invite():
    maint = maintenance_check()
    if maint:
        return maint
    ip = request.remote_addr
    if rate_limit(ip):
        return jsonify({"success": False, "message": "Too many requests"}), 429
    team_code = request.args.get('team_code')
    uid = request.args.get('uid')
    if not team_code or not uid:
        return jsonify({"success": False, "message": "Missing team_code or uid"}), 400
    target = f"{API_BASE}/inv?team_code={team_code}&uid={uid}&api_key={API_KEY}"
    try:
        resp = requests.get(target, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/data')
def proxy_data():
    try:
        resp = requests.get(DATA_URL, timeout=10)
        if resp.status_code != 200:
            return jsonify([]), 500
        return jsonify(resp.json())
    except Exception:
        return jsonify([]), 500

@app.route('/api/image/<image_id>')
def proxy_image(image_id):
    url = f"{IMAGE_BASE}/{image_id}.png"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return "", 404
        return resp.content, 200, {'Content-Type': 'image/png'}
    except Exception:
        return "", 404

# Vercel requires the app object to be named 'app'
app = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)