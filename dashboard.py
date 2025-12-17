from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# Your auth router is mounted at /auth, so /me becomes /auth/me
ME_ENDPOINT = "/auth/me"

BASE_STYLE = """
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html, body { height: 100%; }

  body{
    margin:0;
    font-family:system-ui;
    background:#1A1A1A;
    color:#f5f5f5;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:flex-start;
    padding:48px 16px 40px;
    overflow:hidden;
  }
  @media (max-height: 740px), (max-width: 900px){
    body{ overflow:auto; }
  }

  .shell{
    width:100%;
    max-width:1100px;
    background:#121212;
    border-radius:16px;
    padding:28px;
    box-shadow:
      0 0 45px rgba(255,255,255,0.22),
      0 0 0 1px rgba(255,255,255,0.05);
  }

  .topbar{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:16px;
    margin-bottom:18px;
  }
  @media (max-width: 900px){
    .topbar{ flex-direction:column; }
  }

  .kicker{
    text-transform:uppercase;
    letter-spacing:.14em;
    font-size:11px;
    color:#7a7a7a;
    margin-bottom:6px;
  }
  h1{
    font-size:28px;
    margin:0 0 4px;
  }
  .sub{
    font-size:13px;
    color:#a0a0a0;
    margin:0;
    line-height:1.4;
  }

  .badge{
    margin-top:10px;
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:6px 12px;
    border-radius:999px;
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.05);
    font-size:11px;
    color:#7a7a7a;
    width:fit-content;
  }
  .dot{
    width:8px;height:8px;border-radius:50%;
    background:#4ade80;
    box-shadow:0 0 0 4px rgba(74,222,128,0.10);
  }

  .actions{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    justify-content:flex-end;
  }
  @media (max-width: 900px){
    .actions{ justify-content:flex-start; }
  }

  .btn, button{
    padding:11px 14px;
    border-radius:999px;
    border:0;
    background:linear-gradient(135deg,#fff,#ccc);
    color:#000;
    font-weight:600;
    cursor:pointer;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap:8px;
  }
  .ghost{
    padding:10px 14px;
    border-radius:999px;
    background:#1A1A1A;
    border:1px solid rgba(255,255,255,0.18);
    color:white;
    cursor:pointer;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap:8px;
  }

  .panel{
    margin-top:16px;
    border-radius:16px;
    padding:16px;
    background:linear-gradient(145deg,#121212 0,#181818 50%,#111 100%);
    border:1px solid rgba(255,255,255,0.05);
  }

  .grid{
    display:grid;
    grid-template-columns:repeat(3, 1fr);
    gap:12px;
  }
  @media (max-width: 1000px){
    .grid{ grid-template-columns:repeat(2, 1fr); }
  }
  @media (max-width: 640px){
    .grid{ grid-template-columns:1fr; }
  }

  .tile{
    position:relative;
    border-radius:14px;
    padding:14px;
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.05);
    text-decoration:none;
    color:#f5f5f5;
    transition: transform .08s ease, border-color .12s ease, background .12s ease;
    user-select:none;
    display:block;
    min-height:110px;
  }
  .tile:hover{
    transform: translateY(-1px);
    border-color: rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.03);
  }

  .tile-title{
    font-size:12px;
    text-transform:uppercase;
    letter-spacing:.12em;
    color:#7a7a7a;
    margin:0 0 8px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:10px;
  }
  .tile-body{
    font-size:13px;
    color:#eaeaea;
    margin:0;
    line-height:1.35;
  }

  .pill{
    font-size:11px;
    color:#a0a0a0;
    border:1px solid rgba(255,255,255,0.12);
    padding:3px 8px;
    border-radius:999px;
    background:rgba(0,0,0,0.25);
    white-space:nowrap;
  }

  .locked{
    opacity:.55;
    pointer-events:none;
  }
  .locked::after{
    content:"";
    position:absolute;
    inset:0;
    border-radius:14px;
    background: linear-gradient(135deg, rgba(0,0,0,0.40), rgba(0,0,0,0.65));
  }
  .locknote{
    margin-top:8px;
    font-size:12px;
    color:#8a8a8a;
  }

  .tiny{
    font-size:12px;
    color:#8a8a8a;
    line-height:1.35;
    margin:10px 0 0;
  }

  .split{
    display:grid;
    grid-template-columns: 1.2fr .8fr;
    gap:12px;
    margin-top:12px;
  }
  @media (max-width: 900px){
    .split{ grid-template-columns:1fr; }
  }

  .card{
    border-radius:14px;
    padding:14px;
    background:rgba(255,255,255,0.02);
    border:1px solid rgba(255,255,255,0.05);
  }
  .card h3{
    margin:0 0 8px;
    font-size:12px;
    text-transform:uppercase;
    letter-spacing:.12em;
    color:#7a7a7a;
  }
  .card p{
    margin:0;
    font-size:13px;
    color:#eaeaea;
    line-height:1.4;
  }
</style>
"""

CLIENT_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dreambox • Client Dashboard</title>
  __BASE_STYLE__
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="kicker">Client portal • Dashboard</div>
        <h1>Welcome back</h1>
        <p class="sub" id="subtext">Loading your access…</p>

        <div class="badge">
          <span class="dot" id="dot"></span>
          <span id="badgeText">Signed in</span>
        </div>
      </div>

      <!-- Top actions (we will hide some for PartnerAccount in JS) -->
      <div class="actions" id="topActions">
        <a class="btn" id="topChatBtn" href="/chat">Chat with us</a>
        <a class="ghost" id="topSurveyBtn" href="/survey">Onboarding survey</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="grid" id="tiles"></div>
      <div class="locknote" id="locknote"></div>
      <p class="tiny" id="emailLine"></p>
      <p class="tiny" id="errLine" style="color:#a0a0a0;"></p>
    </div>

    <div class="split">
      <div class="card">
        <h3>Next step</h3>
        <p id="nextStep">—</p>
      </div>
      <div class="card">
        <h3>Account type</h3>
        <p id="acctType">—</p>
      </div>
    </div>
  </div>

  <script>
    function logout(){
      localStorage.removeItem("dreambox_token");
      window.location.href = "/portal";
    }

    const token = localStorage.getItem("dreambox_token");
    if(!token){
      window.location.href = "/portal";
    }

    function setStatus(status){
      const dot = document.getElementById("dot");
      const badgeText = document.getElementById("badgeText");
      const subtext = document.getElementById("subtext");

      if(status === "AccountPending"){
        dot.style.background = "#fbbf24";
        dot.style.boxShadow = "0 0 0 4px rgba(251,191,36,0.10)";
        badgeText.textContent = "Pending";
        subtext.textContent = "You can chat with us, and update onboarding. Other areas are locked until approval.";
      }else{
        dot.style.background = "#4ade80";
        dot.style.boxShadow = "0 0 0 4px rgba(74,222,128,0.10)";
        badgeText.textContent = "Active";
        subtext.textContent = "Your dashboard is ready. Access depends on your account permissions.";
      }
    }

    function tile(title, desc, href, allowed){
      const pill = allowed ? '<span class="pill">Open</span>' : '<span class="pill">Locked</span>';
      const cls = allowed ? 'tile' : 'tile locked';
      return `
        <a class="${cls}" href="${allowed ? href : '#'}" aria-disabled="${allowed ? 'false' : 'true'}">
          <div class="tile-title"><span>${title}</span>${pill}</div>
          <p class="tile-body">${desc}</p>
        </a>
      `;
    }

async function loadMe(){
  const errLine = document.getElementById("errLine");
  errLine.textContent = "";

  let res;
  try{
    res = await fetch("__ME_ENDPOINT__", {
      headers: { "Authorization": "Bearer " + token }
    });
  }catch(e){
    errLine.textContent = "Network error loading your account. Please refresh.";
    return;
  }

  if(!res.ok){
    errLine.textContent = "Could not load permissions (" + res.status + ").";
    return;
  }

  const me = await res.json();
  const perms = me.permissions || {};
  const acctType = me.account_type || perms.account_type || "AccountPending";

  document.getElementById("emailLine").textContent = "Signed in as: " + (me.email || "—");
  document.getElementById("acctType").textContent = acctType;
  setStatus(acctType);

  const acctLower = (acctType || "").toLowerCase();
  const isPartner = acctLower === "partneraccount";

  // ✅ Admin should be permission-based (more reliable than string matching)
  const isAdmin = perms.can_admin === true;

  // ✅ Partner hides top Chat/Onboarding
  if(isPartner){
    const chatBtn = document.getElementById("topChatBtn");
    const surveyBtn = document.getElementById("topSurveyBtn");
    if(chatBtn) chatBtn.style.display = "none";
    if(surveyBtn) surveyBtn.style.display = "none";
  }

  const tiles = [];

  // ✅ Admin shortcut
  if(isAdmin){
    tiles.push(tile("Admin dashboard", "Management tools, approvals, and configuration.", "/admin", true));
  }

  // ✅ Only NON-partners get Chat + Onboarding tiles
  if(!isPartner){
    tiles.push(tile("Chat with us", "Message the Dreambox team for support and approval.", "/chat", true));
    tiles.push(tile("Onboarding", "Update your onboarding survey details.", "/survey", true));
  }

  // ✅ Games ONLY for Partner + Admin
  if(isPartner || isAdmin){
    tiles.push(tile("Games", "Add and view your connected games.", "/games", true));
  }

  // ✅ Partners must NOT see Projects/Team
  if(!isPartner){
    tiles.push(tile("Projects", "View your active projects and milestones.", "/projects", !!perms.can_view_projects));
    tiles.push(tile("Team", "Manage users linked to your account.", "/team", !!perms.can_team));
  }

  // ✅ Files + Invoices only if allowed
  if(perms.can_files === true){
    tiles.push(tile("Files", "Upload and download project files.", "/files", true));
  }
  if(perms.can_invoices === true){
    tiles.push(tile("Invoices", "View invoices and payment history.", "/invoices", true));
  }

  document.getElementById("tiles").innerHTML = tiles.join("");

  // Next step
  if(isPartner && acctType !== "AccountPending"){
    document.getElementById("nextStep").textContent = "Add your game(s) to start tracking performance.";
  }else{
    document.getElementById("nextStep").textContent =
      acctType === "AccountPending"
        ? "Use “Chat with us” to confirm your details — we’ll approve your account and unlock the dashboard."
        : "Choose a tile to continue.";
  }

  document.getElementById("locknote").textContent =
    acctType === "AccountPending"
      ? "Locked areas will unlock automatically once your account is approved or upgraded."
      : "";
}


loadMe();
  </script>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dreambox • Admin Dashboard</title>
  __BASE_STYLE__
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Management</div>
        <h1>Admin Dashboard</h1>
        <p class="sub">Manage accounts, approvals, roles, and system tools.</p>

        <div class="badge">
          <span class="dot" style="background:#60a5fa;box-shadow:0 0 0 4px rgba(96,165,250,0.10);"></span>
          Admin access
        </div>
      </div>

      <div class="actions">
        <!-- ✅ Back means dashboard home -->
        <a class="ghost" href="/portal-home">Back</a>
        <a class="ghost" href="/portal-home">Client view</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="grid" id="adminTiles"></div>
      <p class="tiny" id="adminEmailLine"></p>
      <p class="tiny" id="adminErr" style="color:#a0a0a0;"></p>
    </div>
  </div>

  <script>
    function logout(){
      localStorage.removeItem("dreambox_token");
      window.location.href = "/portal";
    }

    const token = localStorage.getItem("dreambox_token");
    if(!token){
      window.location.href = "/portal";
    }

    function tile(title, desc, href){
      return `
        <a class="tile" href="${href}">
          <div class="tile-title"><span>${title}</span><span class="pill">Open</span></div>
          <p class="tile-body">${desc}</p>
        </a>
      `;
    }

    async function loadMe(){
      const adminErr = document.getElementById("adminErr");
      adminErr.textContent = "";

      let res;
      try{
        res = await fetch("__ME_ENDPOINT__", {
          headers: { "Authorization": "Bearer " + token }
        });
      }catch(e){
        adminErr.textContent = "Network error. Please refresh.";
        return;
      }

      if(!res.ok){
        adminErr.textContent = "Could not load account (" + res.status + ").";
        return;
      }

      const me = await res.json();

      const acct = (me.account_type || "").toLowerCase();
      if(!acct.includes("administrator")){
        window.location.href = "/portal-home";
        return;
      }

      document.getElementById("adminEmailLine").textContent = "Signed in as: " + (me.email || "—");

      const tiles = [];
      tiles.push(tile("Pending approvals", "Review and approve pending accounts.", "/admin/approvals"));
      tiles.push(tile("User management", "Search users, change account types, reset access.", "/admin/users"));
      tiles.push(tile("Roles config", "View current role permissions.", "/admin/roles"));
      tiles.push(tile("Audit logs", "Review recent security and access events.", "/admin/logs"));
      tiles.push(tile("Support inbox", "View chats and support requests.", "/admin/support"));
      tiles.push(tile("System", "Health checks and internal tools.", "/admin/system"));

      document.getElementById("adminTiles").innerHTML = tiles.join("");
    }

    loadMe();
  </script>
</body>
</html>
"""

CLIENT_DASHBOARD_HTML = (
    CLIENT_DASHBOARD_TEMPLATE
    .replace("__BASE_STYLE__", BASE_STYLE)
    .replace("__ME_ENDPOINT__", ME_ENDPOINT)
)

ADMIN_DASHBOARD_HTML = (
    ADMIN_DASHBOARD_TEMPLATE
    .replace("__BASE_STYLE__", BASE_STYLE)
    .replace("__ME_ENDPOINT__", ME_ENDPOINT)
)

@router.get("/portal-home", response_class=HTMLResponse)
def client_dashboard():
    return HTMLResponse(CLIENT_DASHBOARD_HTML)

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return HTMLResponse(ADMIN_DASHBOARD_HTML)
