from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# Reuse the exact style used on /portal
PORTAL_STYLE = """
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

  input, textarea{
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
  textarea{ min-height:90px; resize:vertical; }

  input:focus, textarea:focus{
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
    text-align:center;
    text-decoration:none;
    display:inline-block;
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
    text-align:center;
    text-decoration:none;
    display:inline-block;
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

  .badge{
    margin-top:18px;
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:5px 10px;
    border-radius:999px;
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.04);
    font-size:11px;
    color:#7a7a7a;
  }
</style>
"""

LANDING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dreambox Interactive</title>
  """ + PORTAL_STYLE + """
</head>
<body>
  <div class="shell">
    <div>
      <div style="text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#7a7a7a;margin-bottom:6px;">
        Welcome • Start here
      </div>

      <h1 style="font-size:28px;margin:0 0 4px;">Dreambox Interactive</h1>
      <p style="font-size:13px;color:#a0a0a0;margin:0;">
        Welcome. Start onboarding below.
      </p>

      <div class="badge">
        <span style="width:8px;height:8px;background:#4ade80;border-radius:50%;box-shadow:0 0 0 4px rgba(74,222,128,0.1);"></span>
        Secure portal with 2FA
      </div>

      <div style="margin-top:20px;padding:14px;border-radius:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);font-size:12px;color:#7a7a7a;">
        New clients: complete the survey to create your account. Returning clients: sign in to the portal.
      </div>
    </div>

    <div class="panel">
      <div style="text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#7a7a7a;margin-bottom:10px;">
        Choose an option
      </div>

      <a class="btn" href="/survey">Start survey (Contact us / Sign up)</a>
      <a class="ghost-link" href="/portal">Client portal (Sign in)</a>

      <div class="secondary-row">
        <a href="/survey">New here?</a>
        <a href="/portal">Already have access?</a>
      </div>

      <div class="tiny">
        The survey takes about a minute. We’ll email you a link to set your password.
      </div>
    </div>
  </div>
</body>
</html>
"""

SURVEY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dreambox Survey</title>
  """ + PORTAL_STYLE + """
</head>
<body>
  <div class="shell">
    <div>
      <div style="text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#7a7a7a;margin-bottom:6px;">
        Step 0 • Onboarding
      </div>

      <h1 style="font-size:28px;margin:0 0 4px;">Contact us / Sign up</h1>
      <p style="font-size:13px;color:#a0a0a0;margin:0;">
        Enter your email — we’ll send you a link to set your password.
      </p>

      <div class="badge">
        <span style="width:8px;height:8px;background:#4ade80;border-radius:50%;box-shadow:0 0 0 4px rgba(74,222,128,0.1);"></span>
        Quick onboarding
      </div>

      <div id="infoBox" style="margin-top:20px;padding:14px;border-radius:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);font-size:12px;color:#7a7a7a;">
        Fill this out and we’ll follow up. If you already have an account, use the client portal.
      </div>
    </div>

    <div class="panel">
      <form id="surveyForm" onsubmit="submitSurvey(event)">
        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Your name</label>
        <input id="name" required placeholder="Your name">

        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Company / brand</label>
        <input id="company" placeholder="Company / brand">

        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Work email</label>
        <input id="email" type="email" required placeholder="you@company.com">

        <label style="font-size:12px;text-transform:uppercase;color:#7a7a7a;margin-top:12px;display:block;">Preferred Zoom time (optional)</label>
        <input id="preferredTime" placeholder="e.g. Tue 2pm GMT">

        <button id="submitBtn" type="submit">Submit</button>
        <a class="ghost-link" href="/portal">Client portal (Sign in)</a>

        <div class="secondary-row">
          <a href="/">Back to home</a>
          <a href="/portal">Already have access?</a>
        </div>

        <div id="status" class="tiny"></div>
      </form>

      <script>
        async function submitSurvey(event) {
          event.preventDefault();
          const btn = document.getElementById("submitBtn");
          const status = document.getElementById("status");
          btn.disabled = true;
          status.textContent = "Submitting…";

          const payload = {
            name: document.getElementById("name").value,
            company: document.getElementById("company").value,
            email: document.getElementById("email").value,
            preferred_time: document.getElementById("preferredTime").value || "",
            role: "",
            goals: "",
            budget_range: "",
            timeline: "",
            extra_notes: ""
          };

          try {
            const res = await fetch("/survey/submit", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) {
              status.textContent = data.detail || "Something went wrong.";
              btn.disabled = false;
              return;
            }

            status.textContent = data.detail || "Submitted. Check your email to set your password.";
          } catch (e) {
            status.textContent = "Network error. Please try again.";
            btn.disabled = false;
          }
        }
      </script>
    </div>
  </div>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
def landing_root():
    return HTMLResponse(LANDING_HTML)

@router.get("/landing", response_class=HTMLResponse)
def landing_alias():
    return HTMLResponse(LANDING_HTML)

@router.get("/survey", response_class=HTMLResponse)
def survey_page():
    return HTMLResponse(SURVEY_HTML)
