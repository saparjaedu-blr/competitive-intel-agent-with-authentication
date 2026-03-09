"""
auth/google_auth.py — Google OAuth using Streamlit's native built-in auth

secrets.toml format:
    [auth]
    redirect_uri        = "https://your-app.streamlit.app/oauth2callback"
    cookie_secret       = "your_random_secret"
    client_id           = "xxx.apps.googleusercontent.com"
    client_secret       = "xxx"
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
"""

import streamlit as st
from db.auth_db import (
    upsert_user, get_user_roles,
    ROLE_SUPER_ADMIN, ROLE_END_USER
)


def _is_logged_in() -> bool:
    try:
        return bool(st.user.is_logged_in)
    except AttributeError:
        pass
    try:
        return bool(st.experimental_user.get("email"))
    except Exception:
        pass
    return st.session_state.get("is_logged_in", False)


def _get_user_info() -> dict:
    try:
        u = st.user
        name = getattr(u, "name", "") or ""
        parts = name.split()
        return {
            "email":       getattr(u, "email", ""),
            "given_name":  getattr(u, "given_name", "") or (parts[0] if parts else ""),
            "family_name": getattr(u, "family_name", "") or (" ".join(parts[1:]) if len(parts) > 1 else ""),
            "picture":     getattr(u, "picture", ""),
        }
    except Exception:
        try:
            u = st.experimental_user
            name = u.get("name", "") or ""
            parts = name.split()
            return {
                "email":       u.get("email", ""),
                "given_name":  parts[0] if parts else "",
                "family_name": " ".join(parts[1:]) if len(parts) > 1 else "",
                "picture":     u.get("picture", ""),
            }
        except Exception:
            return {}


def _render_homepage():
    """Full modern landing page with animations, features, and sign-in CTA."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Hide Streamlit chrome on landing page */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    .block-container { padding: 0 !important; max-width: 100% !important; }

    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }

    /* ── Hero Section ── */
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1a56db 100%);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 60px 24px 80px;
        position: relative;
        overflow: hidden;
    }

    .hero::before {
        content: '';
        position: absolute;
        width: 600px; height: 600px;
        background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
        top: -100px; right: -100px;
        border-radius: 50%;
        animation: pulse 4s ease-in-out infinite;
    }
    .hero::after {
        content: '';
        position: absolute;
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
        bottom: -80px; left: -80px;
        border-radius: 50%;
        animation: pulse 4s ease-in-out infinite 2s;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.6; }
        50% { transform: scale(1.15); opacity: 1; }
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    @keyframes ticker {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 100px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 600;
        color: #93c5fd;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 28px;
        animation: fadeInUp 0.6s ease both;
        position: relative; z-index: 1;
    }

    .hero-title {
        font-size: clamp(36px, 6vw, 72px);
        font-weight: 800;
        color: #ffffff;
        line-height: 1.1;
        letter-spacing: -0.04em;
        margin-bottom: 24px;
        animation: fadeInUp 0.6s ease 0.1s both;
        position: relative; z-index: 1;
    }

    .hero-title span {
        background: linear-gradient(90deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-sub {
        font-size: clamp(16px, 2vw, 20px);
        color: #94a3b8;
        max-width: 600px;
        line-height: 1.7;
        margin-bottom: 48px;
        animation: fadeInUp 0.6s ease 0.2s both;
        position: relative; z-index: 1;
    }

    /* ── Ticker ── */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background: rgba(255,255,255,0.04);
        border-top: 1px solid rgba(255,255,255,0.08);
        border-bottom: 1px solid rgba(255,255,255,0.08);
        padding: 14px 0;
        margin: 48px 0;
        position: relative; z-index: 1;
    }
    .ticker-track {
        display: flex;
        gap: 0;
        width: max-content;
        animation: ticker 30s linear infinite;
    }
    .ticker-item {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        font-weight: 500;
        color: #64748b;
        padding: 0 32px;
        white-space: nowrap;
    }
    .ticker-item span { color: #3b82f6; font-size: 16px; }

    /* ── Stats row ── */
    .stats-row {
        display: flex;
        gap: 40px;
        justify-content: center;
        flex-wrap: wrap;
        margin-bottom: 56px;
        animation: fadeInUp 0.6s ease 0.3s both;
        position: relative; z-index: 1;
    }
    .stat {
        text-align: center;
    }
    .stat-value {
        font-size: 36px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        line-height: 1;
    }
    .stat-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
        margin-top: 4px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    /* ── Features Section ── */
    .features-section {
        background: #f8f7f4;
        padding: 96px 24px;
    }
    .section-label {
        text-align: center;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #1a56db;
        margin-bottom: 16px;
    }
    .section-title {
        text-align: center;
        font-size: clamp(28px, 4vw, 44px);
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 16px;
    }
    .section-sub {
        text-align: center;
        font-size: 16px;
        color: #64748b;
        max-width: 520px;
        margin: 0 auto 64px;
        line-height: 1.7;
    }
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 24px;
        max-width: 1080px;
        margin: 0 auto;
    }
    .feature-card {
        background: #ffffff;
        border: 1px solid #e8e4dd;
        border-radius: 16px;
        padding: 32px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        animation: fadeInUp 0.5s ease both;
    }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.08);
    }
    .feature-icon {
        width: 48px; height: 48px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
        margin-bottom: 20px;
    }
    .feature-title {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    .feature-desc {
        font-size: 14px;
        color: #64748b;
        line-height: 1.7;
    }

    /* ── How it works ── */
    .how-section {
        background: #ffffff;
        padding: 96px 24px;
    }
    .steps-row {
        display: flex;
        gap: 0;
        max-width: 900px;
        margin: 0 auto;
        position: relative;
        flex-wrap: wrap;
        justify-content: center;
    }
    .step {
        flex: 1;
        min-width: 200px;
        text-align: center;
        padding: 0 24px;
        position: relative;
    }
    .step:not(:last-child)::after {
        content: '→';
        position: absolute;
        right: -12px;
        top: 20px;
        font-size: 20px;
        color: #cbd5e1;
    }
    .step-num {
        width: 44px; height: 44px;
        border-radius: 50%;
        background: #eff6ff;
        border: 2px solid #bfdbfe;
        color: #1a56db;
        font-size: 16px;
        font-weight: 800;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 16px;
    }
    .step-title {
        font-size: 14px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 8px;
    }
    .step-desc {
        font-size: 13px;
        color: #64748b;
        line-height: 1.6;
    }

    /* ── CTA Section ── */
    .cta-section {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 100px 24px;
        text-align: center;
    }
    .cta-title {
        font-size: clamp(28px, 4vw, 48px);
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin-bottom: 16px;
        animation: fadeInUp 0.6s ease both;
    }
    .cta-sub {
        font-size: 18px;
        color: #94a3b8;
        margin-bottom: 48px;
        animation: fadeInUp 0.6s ease 0.1s both;
    }

    /* Google sign-in button override */
    .stButton > button {
        background: #ffffff !important;
        color: #1e293b !important;
        border: none !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        padding: 14px 32px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15) !important;
        letter-spacing: -0.01em !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
    }

    .footer {
        background: #0f172a;
        border-top: 1px solid rgba(255,255,255,0.06);
        padding: 32px 24px;
        text-align: center;
        color: #475569;
        font-size: 13px;
    }
    </style>

    <!-- ── HERO ── -->
    <div class="hero">
        <div class="hero-badge">⚡ AI-Powered Intelligence</div>
        <div class="hero-title">
            Know your competitors<br><span>before they move</span>
        </div>
        <div class="hero-sub">
            CompIntel monitors competitor websites, docs, YouTube channels, and your
            research notes — then synthesizes everything into actionable intelligence
            reports in under 60 seconds.
        </div>

        <div class="stats-row">
            <div class="stat">
                <div class="stat-value">53s</div>
                <div class="stat-label">Avg. Analysis Time</div>
            </div>
            <div class="stat">
                <div class="stat-value">8</div>
                <div class="stat-label">Analysis Dimensions</div>
            </div>
            <div class="stat">
                <div class="stat-value">5+</div>
                <div class="stat-label">Data Sources</div>
            </div>
            <div class="stat">
                <div class="stat-value">4hrs</div>
                <div class="stat-label">Saved per Week</div>
            </div>
        </div>

        <!-- Ticker -->
        <div class="ticker-wrap">
            <div class="ticker-track">
                <div class="ticker-item"><span>🚀</span> Feature Launches</div>
                <div class="ticker-item"><span>💰</span> Pricing Changes</div>
                <div class="ticker-item"><span>⚙️</span> Technical Architecture</div>
                <div class="ticker-item"><span>🎯</span> Use Cases & Segments</div>
                <div class="ticker-item"><span>🖥️</span> UI/UX Patterns</div>
                <div class="ticker-item"><span>🧭</span> Strategic Direction</div>
                <div class="ticker-item"><span>⚔️</span> Competitive Gaps</div>
                <div class="ticker-item"><span>👁️</span> Key Watch Points</div>
                <div class="ticker-item"><span>📹</span> YouTube Analysis</div>
                <div class="ticker-item"><span>📄</span> Doc Scraping</div>
                <!-- duplicate for seamless loop -->
                <div class="ticker-item"><span>🚀</span> Feature Launches</div>
                <div class="ticker-item"><span>💰</span> Pricing Changes</div>
                <div class="ticker-item"><span>⚙️</span> Technical Architecture</div>
                <div class="ticker-item"><span>🎯</span> Use Cases & Segments</div>
                <div class="ticker-item"><span>🖥️</span> UI/UX Patterns</div>
                <div class="ticker-item"><span>🧭</span> Strategic Direction</div>
                <div class="ticker-item"><span>⚔️</span> Competitive Gaps</div>
                <div class="ticker-item"><span>👁️</span> Key Watch Points</div>
                <div class="ticker-item"><span>📹</span> YouTube Analysis</div>
                <div class="ticker-item"><span>📄</span> Doc Scraping</div>
            </div>
        </div>
    </div>

    <!-- ── FEATURES ── -->
    <div class="features-section">
        <div class="section-label">What CompIntel does</div>
        <div class="section-title">Everything your team needs<br>to stay ahead</div>
        <div class="section-sub">
            Built for Product Managers who need deep competitive intelligence
            without the manual research grind.
        </div>
        <div class="features-grid">
            <div class="feature-card" style="animation-delay:0.0s">
                <div class="feature-icon" style="background:#eff6ff">🌐</div>
                <div class="feature-title">Multi-Source Scraping</div>
                <div class="feature-desc">
                    Automatically monitors competitor websites, blogs, product docs,
                    changelogs, and YouTube channels — all in one run.
                </div>
            </div>
            <div class="feature-card" style="animation-delay:0.1s">
                <div class="feature-icon" style="background:#fdf4ff">🧠</div>
                <div class="feature-title">GPT-4o Vision Analysis</div>
                <div class="feature-desc">
                    Reads screenshots, pricing tables, and roadmap slides from your
                    Google Doc scrapbook using GPT-4o Vision.
                </div>
            </div>
            <div class="feature-card" style="animation-delay:0.2s">
                <div class="feature-icon" style="background:#f0fdf4">🔄</div>
                <div class="feature-title">Semantic Diff Engine</div>
                <div class="feature-desc">
                    Only shows what actually changed since the last run —
                    not a wall of text. Focus on what's new, not what you already know.
                </div>
            </div>
            <div class="feature-card" style="animation-delay:0.3s">
                <div class="feature-icon" style="background:#fff7ed">⚡</div>
                <div class="feature-title">Real-Time Streaming</div>
                <div class="feature-desc">
                    Watch the analysis happen live with a streaming progress bar
                    and live synthesis preview as GPT-4o processes each vendor.
                </div>
            </div>
            <div class="feature-card" style="animation-delay:0.4s">
                <div class="feature-icon" style="background:#fef2f2">🔒</div>
                <div class="feature-title">Private & Isolated</div>
                <div class="feature-desc">
                    Your competitor configurations and reports are completely private.
                    No other user can see your data — ever.
                </div>
            </div>
            <div class="feature-card" style="animation-delay:0.5s">
                <div class="feature-icon" style="background:#eff6ff">☁️</div>
                <div class="feature-title">Google Drive Archive</div>
                <div class="feature-desc">
                    Optionally publish and archive reports to Google Drive
                    and share with your team via email.
                </div>
            </div>
        </div>
    </div>

    <!-- ── HOW IT WORKS ── -->
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

    <!-- ── CTA ── -->
    <div class="cta-section">
        <div class="cta-title">Ready to stop guessing<br>what your competitors are doing?</div>
        <div class="cta-sub">Sign in with Google and run your first analysis in minutes.</div>
    </div>
    """, unsafe_allow_html=True)


def init_session() -> dict:
    """Populate session state from Google user info after login."""
    info = _get_user_info()
    user  = upsert_user(
        info.get("email", ""),
        info.get("given_name", ""),
        info.get("family_name", ""),
        info.get("picture", ""),
    )
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


def require_auth() -> bool:
    """
    Auth gate — call once at the top of app.py.
    Returns True when signed in, False when showing landing page + login UI.
    """
    if not _is_logged_in():
        # Render full landing page
        _render_homepage()
        # Sign in button centred below CTA
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            try:
                st.login("google")
            except TypeError:
                st.login()
        st.markdown(
            "<p style='text-align:center;font-size:11px;color:#475569;"
            "background:#0f172a;padding:0 0 40px;margin:0'>"
            "Your data is private and never shared with other users.</p>",
            unsafe_allow_html=True,
        )
        # Footer
        st.markdown("""
            <div class="footer">
                Built with LangGraph · GPT-4o Vision · Streamlit &nbsp;|&nbsp;
                © 2026 CompIntel
            </div>
        """, unsafe_allow_html=True)
        return False

    # Signed in — populate session once per session
    if "user" not in st.session_state:
        init_session()
    return True


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
        avatar_html = (f"<img src='{picture}' style='width:32px;height:32px;"
                       f"border-radius:50%;object-fit:cover'>")
    else:
        initials    = (user.get("first_name","?")[0] + user.get("last_name","?")[0]).upper()
        avatar_html = (f"<div style='width:32px;height:32px;border-radius:50%;"
                       f"background:#1a56db;color:white;display:flex;align-items:center;"
                       f"justify-content:center;font-size:12px;font-weight:700'>{initials}</div>")

    st.markdown(f"""
        <div style='display:flex;align-items:center;gap:10px;padding:12px 4px'>
            {avatar_html}
            <div>
                <div style='font-size:13px;font-weight:600;color:#0f172a;line-height:1.2'>{name}</div>
                <div style='font-size:10px;font-weight:700;color:{role_color};
                    letter-spacing:0.05em;text-transform:uppercase'>{role_label}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_logout():
    if st.button("Sign Out", use_container_width=True, type="secondary"):
        for k in ["user", "user_roles", "is_admin", "is_logged_in"]:
            st.session_state.pop(k, None)
        try:
            st.logout()
        except AttributeError:
            st.rerun()
