"""
auth/google_auth.py — Google OAuth using Streamlit native auth (st.login / st.user)

Requires in secrets.toml:
    [auth]
    redirect_uri        = "https://your-app.streamlit.app/oauth2callback"
    cookie_secret       = "random_hex_string"
    client_id           = "xxx.apps.googleusercontent.com"
    client_secret       = "xxx"
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

Requires in requirements.txt:
    streamlit>=1.42.0
    authlib>=1.3.2
"""

import streamlit as st
from db.auth_db import upsert_user, get_user_roles, ROLE_SUPER_ADMIN


# ── Session helpers ────────────────────────────────────────────────────────────

def init_session() -> dict:
    """Called once after login to populate session state from st.user."""
    u          = st.user
    name       = getattr(u, "name", "") or ""
    parts      = name.split()
    first      = getattr(u, "given_name",  "") or (parts[0]              if parts        else "")
    last       = getattr(u, "family_name", "") or (" ".join(parts[1:])   if len(parts)>1 else "")
    email      = getattr(u, "email",   "")
    picture    = getattr(u, "picture", "")

    user  = upsert_user(email, first, last, picture)
    roles = get_user_roles(user["id"])

    st.session_state["user"]       = user
    st.session_state["user_roles"] = roles
    st.session_state["is_admin"]   = ROLE_SUPER_ADMIN in roles
    return user


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def get_current_user_id() -> int | None:
    user = get_current_user()
    return user["id"] if user else None


def current_user_is_admin() -> bool:
    return st.session_state.get("is_admin", False)


# ── Landing page HTML ──────────────────────────────────────────────────────────

def _render_homepage():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }

    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.6; }
        50%       { transform: scale(1.15); opacity: 1; }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes ticker {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1a56db 100%);
        min-height: 90vh;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        text-align: center; padding: 60px 24px 40px;
        position: relative; overflow: hidden;
    }
    .hero::before {
        content:''; position:absolute; width:600px; height:600px;
        background:radial-gradient(circle,rgba(59,130,246,.15) 0%,transparent 70%);
        top:-100px; right:-100px; border-radius:50%;
        animation:pulse 4s ease-in-out infinite;
    }
    .hero::after {
        content:''; position:absolute; width:400px; height:400px;
        background:radial-gradient(circle,rgba(99,102,241,.12) 0%,transparent 70%);
        bottom:-80px; left:-80px; border-radius:50%;
        animation:pulse 4s ease-in-out infinite 2s;
    }
    .hero-badge {
        display:inline-flex; align-items:center; gap:8px;
        background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.2);
        border-radius:100px; padding:6px 16px; font-size:12px; font-weight:600;
        color:#93c5fd; letter-spacing:.06em; text-transform:uppercase;
        margin-bottom:28px; animation:fadeInUp .6s ease both; position:relative; z-index:1;
    }
    .hero-title {
        font-size:clamp(36px,6vw,72px); font-weight:800; color:#fff;
        line-height:1.1; letter-spacing:-.04em; margin-bottom:24px;
        animation:fadeInUp .6s ease .1s both; position:relative; z-index:1;
    }
    .hero-title span {
        background:linear-gradient(90deg,#60a5fa,#a78bfa);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
    }
    .hero-sub {
        font-size:clamp(16px,2vw,20px); color:#94a3b8; max-width:600px;
        line-height:1.7; margin-bottom:40px;
        animation:fadeInUp .6s ease .2s both; position:relative; z-index:1;
    }
    .stats-row {
        display:flex; gap:40px; justify-content:center; flex-wrap:wrap;
        margin-bottom:40px; animation:fadeInUp .6s ease .3s both;
        position:relative; z-index:1;
    }
    .stat { text-align:center; }
    .stat-value { font-size:36px; font-weight:800; color:#fff; letter-spacing:-.03em; line-height:1; }
    .stat-label { font-size:12px; color:#64748b; font-weight:500; margin-top:4px;
        letter-spacing:.04em; text-transform:uppercase; }

    .ticker-wrap {
        width:100%; overflow:hidden;
        background:rgba(255,255,255,.04);
        border-top:1px solid rgba(255,255,255,.08);
        border-bottom:1px solid rgba(255,255,255,.08);
        padding:14px 0; margin-top:40px;
        position:relative; z-index:1;
    }
    .ticker-track { display:flex; width:max-content; animation:ticker 30s linear infinite; }
    .ticker-item {
        display:inline-flex; align-items:center; gap:10px;
        font-size:13px; font-weight:500; color:#64748b;
        padding:0 32px; white-space:nowrap;
    }
    .ticker-item span { color:#3b82f6; font-size:16px; }

    .features-section { background:#f8f7f4; padding:96px 24px; }
    .section-label {
        text-align:center; font-size:11px; font-weight:700;
        letter-spacing:.1em; text-transform:uppercase; color:#1a56db; margin-bottom:16px;
    }
    .section-title {
        text-align:center; font-size:clamp(28px,4vw,44px); font-weight:800;
        color:#0f172a; letter-spacing:-.03em; line-height:1.2; margin-bottom:16px;
    }
    .section-sub {
        text-align:center; font-size:16px; color:#64748b;
        max-width:520px; margin:0 auto 64px; line-height:1.7;
    }
    .features-grid {
        display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
        gap:24px; max-width:1080px; margin:0 auto;
    }
    .feature-card {
        background:#fff; border:1px solid #e8e4dd; border-radius:16px;
        padding:32px; box-shadow:0 2px 8px rgba(0,0,0,.04);
        transition:transform .2s,box-shadow .2s;
    }
    .feature-card:hover { transform:translateY(-4px); box-shadow:0 12px 32px rgba(0,0,0,.08); }
    .feature-icon { width:48px; height:48px; border-radius:12px; font-size:22px; margin-bottom:20px;
        display:flex; align-items:center; justify-content:center; }
    .feature-title { font-size:16px; font-weight:700; color:#0f172a; margin-bottom:8px; letter-spacing:-.02em; }
    .feature-desc  { font-size:14px; color:#64748b; line-height:1.7; }

    .how-section { background:#fff; padding:96px 24px; }
    .steps-row {
        display:flex; gap:0; max-width:900px; margin:0 auto;
        flex-wrap:wrap; justify-content:center;
    }
    .step { flex:1; min-width:200px; text-align:center; padding:0 24px; position:relative; }
    .step:not(:last-child)::after {
        content:'→'; position:absolute; right:-12px; top:20px;
        font-size:20px; color:#cbd5e1;
    }
    .step-num {
        width:44px; height:44px; border-radius:50%;
        background:#eff6ff; border:2px solid #bfdbfe; color:#1a56db;
        font-size:16px; font-weight:800; display:flex;
        align-items:center; justify-content:center; margin:0 auto 16px;
    }
    .step-title { font-size:14px; font-weight:700; color:#0f172a; margin-bottom:8px; }
    .step-desc  { font-size:13px; color:#64748b; line-height:1.6; }

    .cta-section {
        background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%);
        padding:80px 24px 20px; text-align:center;
    }
    .cta-title {
        font-size:clamp(28px,4vw,48px); font-weight:800; color:#fff;
        letter-spacing:-.03em; margin-bottom:16px;
    }
    .cta-sub { font-size:18px; color:#94a3b8; margin-bottom:40px; }
    .cta-note {
        font-size:11px; color:#475569;
        background:#0f172a; padding:0 0 32px; margin:0; text-align:center;
    }
    .app-footer {
        background:#0f172a; border-top:1px solid rgba(255,255,255,.06);
        padding:28px 24px; text-align:center; color:#475569; font-size:13px;
    }

    /* Override Streamlit button inside dark CTA */
    .stButton > button {
        background:#fff !important; color:#1e293b !important;
        border:none !important; border-radius:12px !important;
        font-size:15px !important; font-weight:600 !important;
        padding:14px 32px !important;
        box-shadow:0 4px 16px rgba(0,0,0,.2) !important;
    }
    .stButton > button:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 24px rgba(0,0,0,.28) !important;
    }
    </style>

    <!-- HERO -->
    <div class="hero">
        <div class="hero-badge">⚡ AI-Powered Intelligence</div>
        <div class="hero-title">Know your competitors<br><span>before they move</span></div>
        <div class="hero-sub">
            CompIntel monitors competitor websites, docs, YouTube channels and your
            research notes — synthesizing everything into actionable intelligence
            reports in under 60 seconds.
        </div>
        <div class="stats-row">
            <div class="stat"><div class="stat-value">53s</div><div class="stat-label">Avg Analysis Time</div></div>
            <div class="stat"><div class="stat-value">8</div><div class="stat-label">Analysis Dimensions</div></div>
            <div class="stat"><div class="stat-value">5+</div><div class="stat-label">Data Sources</div></div>
            <div class="stat"><div class="stat-value">4hrs</div><div class="stat-label">Saved per Week</div></div>
        </div>
        <div class="ticker-wrap">
            <div class="ticker-track">
                <div class="ticker-item"><span>🚀</span> Feature Launches</div>
                <div class="ticker-item"><span>💰</span> Pricing Changes</div>
                <div class="ticker-item"><span>⚙️</span> Technical Architecture</div>
                <div class="ticker-item"><span>🎯</span> Use Cases &amp; Segments</div>
                <div class="ticker-item"><span>🖥️</span> UI/UX Patterns</div>
                <div class="ticker-item"><span>🧭</span> Strategic Direction</div>
                <div class="ticker-item"><span>⚔️</span> Competitive Gaps</div>
                <div class="ticker-item"><span>👁️</span> Watch Points</div>
                <div class="ticker-item"><span>📹</span> YouTube Analysis</div>
                <div class="ticker-item"><span>📄</span> Doc Scraping</div>
                <!-- duplicate for seamless loop -->
                <div class="ticker-item"><span>🚀</span> Feature Launches</div>
                <div class="ticker-item"><span>💰</span> Pricing Changes</div>
                <div class="ticker-item"><span>⚙️</span> Technical Architecture</div>
                <div class="ticker-item"><span>🎯</span> Use Cases &amp; Segments</div>
                <div class="ticker-item"><span>🖥️</span> UI/UX Patterns</div>
                <div class="ticker-item"><span>🧭</span> Strategic Direction</div>
                <div class="ticker-item"><span>⚔️</span> Competitive Gaps</div>
                <div class="ticker-item"><span>👁️</span> Watch Points</div>
                <div class="ticker-item"><span>📹</span> YouTube Analysis</div>
                <div class="ticker-item"><span>📄</span> Doc Scraping</div>
            </div>
        </div>
    </div>

    <!-- FEATURES -->
    <div class="features-section">
        <div class="section-label">What CompIntel does</div>
        <div class="section-title">Everything your team needs<br>to stay ahead</div>
        <div class="section-sub">Built for Product Managers who need deep competitive intelligence without the manual grind.</div>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon" style="background:#eff6ff">🌐</div>
                <div class="feature-title">Multi-Source Scraping</div>
                <div class="feature-desc">Monitors competitor websites, blogs, product docs, changelogs, and YouTube channels automatically.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="background:#fdf4ff">🧠</div>
                <div class="feature-title">GPT-4o Vision Analysis</div>
                <div class="feature-desc">Reads screenshots, pricing tables, and roadmap slides from your Google Doc scrapbook.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="background:#f0fdf4">🔄</div>
                <div class="feature-title">Semantic Diff Engine</div>
                <div class="feature-desc">Only surfaces what actually changed since last run — no noise, just signal.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="background:#fff7ed">⚡</div>
                <div class="feature-title">Real-Time Streaming</div>
                <div class="feature-desc">Watch the analysis happen live with streaming progress and synthesis preview.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="background:#fef2f2">🔒</div>
                <div class="feature-title">Private &amp; Isolated</div>
                <div class="feature-desc">Your configurations and reports are completely private — no other user can see your data.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon" style="background:#eff6ff">☁️</div>
                <div class="feature-title">Google Drive Archive</div>
                <div class="feature-desc">Publish and archive reports to Google Drive and share with your team via email.</div>
            </div>
        </div>
    </div>

    <!-- HOW IT WORKS -->
    <div class="how-section">
        <div class="section-label">How it works</div>
        <div class="section-title">From zero to insight in 4 steps</div>
        <div class="section-sub">No setup complexity. Just configure, run, and read.</div>
        <div class="steps-row">
            <div class="step">
                <div class="step-num">1</div>
                <div class="step-title">Add Competitors</div>
                <div class="step-desc">Enter URLs for website, blog, docs, changelog, and YouTube</div>
            </div>
            <div class="step">
                <div class="step-num">2</div>
                <div class="step-title">Ask a Question</div>
                <div class="step-desc">Type a research query like "What's new in their pricing?"</div>
            </div>
            <div class="step">
                <div class="step-num">3</div>
                <div class="step-title">Agent Runs</div>
                <div class="step-desc">LangGraph pipeline scrapes, reads, and synthesizes all sources</div>
            </div>
            <div class="step">
                <div class="step-num">4</div>
                <div class="step-title">Read the Report</div>
                <div class="step-desc">8-dimension analysis with delta highlights in under 60 seconds</div>
            </div>
        </div>
    </div>

    <!-- CTA -->
    <div class="cta-section">
        <div class="cta-title">Ready to stop guessing<br>what your competitors are doing?</div>
        <div class="cta-sub">Sign in with Google and run your first analysis in minutes.</div>
    </div>
    """, unsafe_allow_html=True)


# ── Auth gate ──────────────────────────────────────────────────────────────────

def require_auth() -> bool:
    """
    Call once at the top of app.py.
    Pattern from Streamlit docs: render page first, call st.login() inside button if-block.
    Returns True when signed in, False when showing landing page.
    """
    if not st.user.is_logged_in:
        _render_homepage()

        # Button inside CTA — st.login() called inside the if-block per official docs
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔑  Sign in with Google", type="primary", use_container_width=True):
                st.login()

        st.markdown(
            "<p class='cta-note'>Your data is private and never shared with other users.</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='app-footer'>Built with LangGraph · GPT-4o Vision · Streamlit &nbsp;|&nbsp; © 2026 CompIntel</div>",
            unsafe_allow_html=True,
        )
        return False

    # Signed in — populate session once per session
    if "user" not in st.session_state:
        init_session()
    return True


# ── Sidebar widgets ────────────────────────────────────────────────────────────

def render_user_pill():
    user = get_current_user()
    if not user:
        return
    roles      = st.session_state.get("user_roles", [])
    role_label = "Super Admin" if ROLE_SUPER_ADMIN in roles else "End User"
    role_color = "#1a56db"    if ROLE_SUPER_ADMIN in roles else "#15803d"
    name       = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user["email"]
    picture    = user.get("picture_url", "")
    if picture:
        avatar = f"<img src='{picture}' style='width:32px;height:32px;border-radius:50%;object-fit:cover'>"
    else:
        initials = (user.get("first_name","?")[0] + user.get("last_name","?")[0]).upper()
        avatar   = (f"<div style='width:32px;height:32px;border-radius:50%;background:#1a56db;"
                    f"color:white;display:flex;align-items:center;justify-content:center;"
                    f"font-size:12px;font-weight:700'>{initials}</div>")
    st.markdown(f"""
        <div style='display:flex;align-items:center;gap:10px;padding:12px 4px'>
            {avatar}
            <div>
                <div style='font-size:13px;font-weight:600;color:#0f172a;line-height:1.2'>{name}</div>
                <div style='font-size:10px;font-weight:700;color:{role_color};
                    letter-spacing:0.05em;text-transform:uppercase'>{role_label}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_logout():
    if st.button("Sign Out", use_container_width=True, type="secondary"):
        for k in ["user", "user_roles", "is_admin"]:
            st.session_state.pop(k, None)
        st.logout()
