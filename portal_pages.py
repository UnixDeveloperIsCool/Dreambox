from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PORTAL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dreambox Portal</title>
  <style>
    /* ✅ IMPORTANT: padding won't add extra height beyond 100vh */
    *, *::before, *::after { box-sizing: border-box; }

    html, body { height: 100%; }

    body{
      margin:0;
      font-family:system-ui;
      background:#1A1A1A;
      color:#f5f5f5;

      /* ✅ fixed viewport height */
      height:100vh;

      display:flex;
      justify-content:center;
      align-items:flex-start;

      /* ✅ can keep bottom padding now because of border-box sizing */
      padding:48px 16px 40px;

      /* ✅ prevent tiny 1px overflow from shadows/rounding */
      overflow:hidden;
    }

    /* ✅ allow scrolling ONLY on small screens where content truly doesn't fit */
    @media (max-height: 740px), (max-width: 800px){
      body{ overflow:auto; }
    }

    .shell{
      width:100%;
      max-width:900px;
      background:#121212;
      border-radius:16px;
      padding:28px;

      display:grid;
      grid-template-columns:1.1fr .9fr;
      gap:32px;

      /* ✅ never stretch */
      height:auto;
      align-content:start;

      box-shadow:
        0 0 45px rgba(255,255,255,0.22),
        0 0 0 1px rgba(255,255,255,0.05);
    }

    @media (max-width:800px){
      .shell{grid-template-columns:1fr;}
    }

    input{
      width:100%;
      padding:9px 10px;
      margin-top:4px;
      border-radius:10px;
      background:#0d0d0d;
      border:1px solid #2a2a2a;
      color:#fff;
      font-size:13px;
      outline:none;
    }
    input:focus{
      border-color: rgba(255,255,255,0.22);
      box-shadow: 0 0 0 3px rgba(255,255,255,0.06);
    }

    button, .btn{
      margin-top:14px;
      width:100%;
      padding:11px;
      border-radius:999px;
      border:0;
      background:linear-gradient(135deg,#fff,#ccc);
      color:#000;
      font-weight:600;
      cursor:pointer;
      text-decoration:none;
      display:inline-block;
      text-align:center;
    }

    .ghost-btn, .ghost-link{
      margin-top:8px;
      width:100%;
      padding:10px;
      border-radius:999px;
      background:#1A1A1A;
      border:1px solid rgba(255,255,255,0.18);
      color:white;
      cursor:pointer;
      text-decoration:none;
      display:inline-block;
      text-align:center;
    }

    .secondary-row{
      margin-top:10px;
      font-size:12px;
      color:#7a7a7a;
      display:flex;
      justify-content:space-between;
      align-items:center;
    }
    .secondary-row a{
      color:#a0a0a0;
      text-decoration:underline;
      text-underline-offset:3px;
    }

    .panel{
      background:linear-gradient(145deg,#121212 0,#181818 50%,#111 100%);
      border-radius:16px;
      padding:18px;
      height:fit-content;
      align-self:start;
    }

    .step{ display:none; }
    .step.active{ display:block; }

    .code{
      letter-spacing:.22em;
      text-align:center;
      font-size:16px;
    }

    .tiny{
      font-size:12px;
      color:#8a8a8a;
      margin-top:10px;
      line-height:1.35;
    }
  </style>
</head>
<body>
  <iframe id="fullpage-iframe"
          style="display:none;position:fixed;inset:0;width:100vw;height:100vh;border:none;background:#000;z-index:9999;"></iframe>

  <div class="shell" id="login-shell">
    <div>
      <div style="text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#7a7a7a;margin-bottom:6px;">
        Step <span id="stepNum">1</span> • Secure login
      </div>

      <h1 id="title" style="font-size:28px;margin:0 0 4px;">Sign in to Dreambox</h1>
      <p id="subtitle" style="font-size:13px;color:#a0a0a0;">
        Enter your email & password, then check your email for the 2FA code.
      </p>

      <div style="margin-top:18px;display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);font-size:11px;color:#7a7a7a;">
        <span style="width:8px;height:8px;background:#4ade80;border-radius:50%;box-shadow:0 0 0 4px rgba(74,222,128,0.1);"></span>
        2FA required for every login
      </div>

      <div id="infoBox" style="margin-top:20px;padding:14px;border-radius:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);font-size:12px;color:#7a7a7a;">
        No account yet? Click sign up to begin onboarding.
      </div>
    </div>

    <div class="panel">
      <div class="step active" id="step-login">
        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Email</label>
        <input id="email" type="email" placeholder="you@company.com">

        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Password</label>
        <input id="password" type="password" placeholder="••••••••">

        <button id="loginBtn" onclick="sendLogin()">Continue</button>
        <button class="ghost-btn" onclick="openSignup()">New to Dreambox? Sign Up</button>

        <div class="secondary-row">
          <span></span>
          <a href="/forgot-password">Forgot your password?</a>
        </div>

        <div id="msg" style="margin-top:10px;color:#a0a0a0;font-size:12px;"></div>
      </div>

      <div class="step" id="step-2fa">
        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">2FA Code</label>
        <input id="twofa" class="code" inputmode="numeric" maxlength="6" placeholder="••••••">

        <button id="verifyBtn" onclick="verify2FA()">Continue</button>

        <div class="tiny">
          We emailed a 6-digit code. If it expires, refresh this page and sign in again to resend.
        </div>

        <div id="msg2" style="margin-top:10px;color:#a0a0a0;font-size:12px;"></div>
      </div>
    </div>
  </div>

  <script>
    function setStep(n){
      document.getElementById("step-login").classList.remove("active");
      document.getElementById("step-2fa").classList.remove("active");
      document.getElementById("stepNum").textContent = n;

      if(n === 1){
        document.getElementById("step-login").classList.add("active");
        document.getElementById("title").textContent = "Sign in to Dreambox";
        document.getElementById("subtitle").textContent =
          "Enter your email & password, then check your email for the 2FA code.";
        document.getElementById("infoBox").textContent =
          "No account yet? Click sign up to begin onboarding.";
      } else {
        document.getElementById("step-2fa").classList.add("active");
        document.getElementById("title").textContent = "Verify 2FA";
        document.getElementById("subtitle").textContent =
          "Enter the 6-digit code we sent to your email.";
        document.getElementById("infoBox").textContent =
          "2FA is required for every login to keep your account secure.";
      }
    }

    async function sendLogin() {
      const msg = document.getElementById("msg");
      msg.textContent = "Checking credentials…";

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      if(!email || !password){
        msg.textContent = "Please enter email and password.";
        return;
      }

      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const res = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body
      });

      if (!res.ok) {
          msg.textContent = "Invalid email or password.";
          return;
      }

      msg.textContent = "";
      document.getElementById("twofa").value = "";
      setStep(2);
      document.getElementById("twofa").focus();
    }

    async function verify2FA(){
      const msg2 = document.getElementById("msg2");
      msg2.textContent = "Verifying code…";

      const email = document.getElementById("email").value.trim();
      const code = document.getElementById("twofa").value.trim();

      if(!code || code.length !== 6){
        msg2.textContent = "Please enter the 6-digit code.";
        return;
      }

      const res = await fetch("/auth/verify-2fa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code })
      });

      if(!res.ok){
        msg2.textContent = "Invalid or expired code. Refresh and sign in again to resend.";
        return;
      }

      const data = await res.json();
      localStorage.setItem("dreambox_token", data.access_token);

      msg2.textContent = "Success. Redirecting…";
      window.location.href = "/portal-home"; // change this
    }

    function openSignup() {
      document.getElementById("login-shell").style.display = "none";
      const iframe = document.getElementById("fullpage-iframe");
      iframe.src = "/survey";
      iframe.style.display = "block";

      document.body.style.padding = "0";
      document.body.style.alignItems = "stretch";
      document.body.style.height = "100vh";
      document.body.style.overflow = "hidden";
    }

    setStep(1);
  </script>
</body>
</html>
"""

FORGOT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Forgot Password • Dreambox</title>
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

    @media (max-height: 740px), (max-width: 800px){
      body{ overflow:auto; }
    }

    .shell{
      width:100%;
      max-width:900px;
      background:#121212;
      border-radius:16px;
      padding:28px;
      display:grid;
      grid-template-columns:1.1fr .9fr;
      gap:32px;
      height:auto;
      align-content:start;
      box-shadow:
        0 0 45px rgba(255,255,255,0.22),
        0 0 0 1px rgba(255,255,255,0.05);
    }
    @media (max-width:800px){
      .shell{grid-template-columns:1fr;}
    }

    input{
      width:100%;
      padding:9px 10px;
      margin-top:4px;
      border-radius:10px;
      background:#0d0d0d;
      border:1px solid #2a2a2a;
      color:#fff;
      font-size:13px;
      outline:none;
    }
    input:focus{
      border-color: rgba(255,255,255,0.22);
      box-shadow: 0 0 0 3px rgba(255,255,255,0.06);
    }

    button, .btn{
      margin-top:14px;
      width:100%;
      padding:11px;
      border-radius:999px;
      border:0;
      background:linear-gradient(135deg,#fff,#ccc);
      color:#000;
      font-weight:600;
      cursor:pointer;
      text-decoration:none;
      display:inline-block;
      text-align:center;
    }

    .ghost-link{
      margin-top:8px;
      width:100%;
      padding:10px;
      border-radius:999px;
      background:#1A1A1A;
      border:1px solid rgba(255,255,255,0.18);
      color:white;
      cursor:pointer;
      text-decoration:none;
      display:inline-block;
      text-align:center;
    }

    .secondary-row{
      margin-top:10px;
      font-size:12px;
      color:#7a7a7a;
      display:flex;
      justify-content:space-between;
      align-items:center;
    }
    .secondary-row a{
      color:#a0a0a0;
      text-decoration:underline;
      text-underline-offset:3px;
    }

    .panel{
      background:linear-gradient(145deg,#121212 0,#181818 50%,#111 100%);
      border-radius:16px;
      padding:18px;
      height:fit-content;
      align-self:start;
    }

    .tiny{
      font-size:12px;
      color:#8a8a8a;
      margin-top:10px;
      line-height:1.35;
    }
  </style>
</head>
<body>
  <div class="shell">
    <div>
      <div style="text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#7a7a7a;margin-bottom:6px;">
        Password reset
      </div>

      <h1 style="font-size:28px;margin:0 0 4px;">Forgot your password?</h1>
      <p style="font-size:13px;color:#a0a0a0;margin:0;">
        Enter your email and we’ll send a reset link.
      </p>

      <div style="margin-top:20px;padding:14px;border-radius:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);font-size:12px;color:#7a7a7a;">
        If you don’t see the email within a few minutes, check spam/junk.
      </div>
    </div>

    <div class="panel">
      <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Email</label>
      <input id="email" type="email" placeholder="you@company.com">

      <button id="sendBtn" onclick="sendReset()">Send reset link</button>
      <a class="ghost-link" href="/portal">Back to sign in</a>

      <div class="secondary-row">
        <span></span>
        <a href="/survey">Need an account?</a>
      </div>

      <div id="status" class="tiny"></div>
    </div>
  </div>

  <script>
    async function sendReset(){
      const status = document.getElementById("status");
      const btn = document.getElementById("sendBtn");
      const email = document.getElementById("email").value.trim();

      if(!email){
        status.textContent = "Please enter your email.";
        return;
      }

      btn.disabled = true;
      status.textContent = "Sending reset link…";

      try{
        // Adjust endpoint to whatever you implement server-side
        const res = await fetch("/auth/forgot-password", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ email })
        });

        const data = await res.json().catch(() => ({}));

        if(!res.ok){
          status.textContent = data.detail || "Could not send reset email. Try again.";
          btn.disabled = false;
          return;
        }

        status.textContent = data.detail || "If an account exists, a reset link has been sent.";
      }catch(e){
        status.textContent = "Network error. Please try again.";
        btn.disabled = false;
      }
    }
  </script>
</body>
</html>
"""

@router.get("/portal", response_class=HTMLResponse)
def portal_page():
  return HTMLResponse(content=PORTAL_HTML)

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
  return HTMLResponse(content=FORGOT_HTML)
