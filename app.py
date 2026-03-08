import streamlit as st
from db.database import init_db
from db.auth_db import init_auth_db
from auth.google_auth import require_auth, render_user_pill, render_logout, current_user_is_admin
from ui.pages import configure, evaluate, history
from ui.pages import admin

st.set_page_config(
    page_title="CompIntel — Competitive Intelligence Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise both DB schemas
init_db()
init_auth_db()

# ── Auth gate — stop here if not signed in ─────────────────────────────────────
if not require_auth():
    st.stop()

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #f8f7f4; }

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1080px;
}

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8e4dd;
    box-shadow: 1px 0 8px rgba(0,0,0,0.04);
}
[data-testid="stSidebar"] .stRadio > div { gap: 2px; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 13.5px; font-weight: 500; color: #64748b;
    padding: 8px 12px; border-radius: 8px; letter-spacing: -0.01em;
    transition: all 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover { background: #f1f0ec; color: #1e293b; }

hr { border-color: #e8e4dd !important; margin: 12px 0 !important; }

.stExpander {
    background: #ffffff !important; border: 1px solid #e8e4dd !important;
    border-radius: 12px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
.streamlit-expanderHeader {
    background: #ffffff !important; border-radius: 12px !important;
    font-weight: 600 !important; font-size: 14px !important; color: #1e293b !important;
    padding: 14px 16px !important;
}
.streamlit-expanderContent { border-top: 1px solid #f1f0ec !important; }

.stTextInput input, .stTextArea textarea {
    background: #ffffff !important; border: 1.5px solid #e2ddd6 !important;
    border-radius: 8px !important; color: #1e293b !important;
    font-family: 'Inter', sans-serif !important; font-size: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #1a56db !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,0.1) !important;
}

.stTextInput label, .stTextArea label, .stMultiSelect label {
    font-size: 13px !important; font-weight: 600 !important;
    color: #475569 !important; letter-spacing: 0.01em !important;
}

.stMultiSelect [data-baseweb="select"] > div {
    background: #ffffff !important; border: 1.5px solid #e2ddd6 !important;
    border-radius: 8px !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: #eff6ff !important; border: 1px solid #bfdbfe !important;
    border-radius: 6px !important; color: #1d4ed8 !important;
    font-size: 12px !important; font-weight: 500 !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: #f1f0ec; border-radius: 10px; padding: 4px;
    gap: 2px; border: 1px solid #e8e4dd;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px; font-size: 12px; font-weight: 500; color: #64748b; padding: 6px 14px;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important; color: #1a56db !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important; font-weight: 600 !important;
}

.stButton > button[kind="primary"] {
    background: #1a56db !important; border: none !important;
    border-radius: 9px !important; font-weight: 600 !important; font-size: 14px !important;
    padding: 11px 24px !important;
    box-shadow: 0 1px 3px rgba(26,86,219,0.3), 0 4px 12px rgba(26,86,219,0.15) !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1e40af !important; transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #ffffff !important; border: 1.5px solid #e2ddd6 !important;
    border-radius: 9px !important; font-weight: 500 !important;
    font-size: 13px !important; color: #475569 !important;
}
.stButton > button[kind="secondary"]:hover { border-color: #1a56db !important; color: #1a56db !important; }

.stProgress > div > div {
    background: linear-gradient(90deg, #1a56db, #3b82f6) !important; border-radius: 4px !important;
}

.stAlert { border-radius: 10px !important; border-left-width: 3px !important; font-size: 13.5px !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f8f7f4; }
::-webkit-scrollbar-thumb { background: #d1cec9; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #1a56db; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='padding:12px 4px 16px 4px'>
            <div style='display:flex;align-items:center;gap:8px'>
                <div style='background:#1a56db;color:white;border-radius:8px;
                    width:32px;height:32px;display:flex;align-items:center;
                    justify-content:center;font-size:16px;font-weight:700;
                    box-shadow:0 2px 8px rgba(26,86,219,0.3)'>⚡</div>
                <div>
                    <div style='font-size:16px;font-weight:700;color:#0f172a;
                        letter-spacing:-0.03em'>CompIntel</div>
                    <div style='font-size:10px;color:#94a3b8;letter-spacing:0.06em;
                        text-transform:uppercase;margin-top:1px'>Intelligence Agent</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Signed-in user pill
    render_user_pill()
    st.divider()

    # Nav — show Admin tab only for super admins
    nav_options = ["Evaluate Competitors", "Configure Competitors", "Report History"]
    if current_user_is_admin():
        nav_options.append("⭐ Admin Dashboard")

    page = st.radio(
        "Navigation",
        options=nav_options,
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    render_logout()

    st.divider()

    st.markdown("""
        <div style='padding:4px'>
            <div style='font-size:11px;color:#cbd5e1;font-weight:600;
                letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px'>Powered by</div>
            <div style='display:flex;flex-direction:column;gap:5px'>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#1a56db'></div>
                    <span style='font-size:12px;color:#64748b'>LangGraph</span>
                </div>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#10b981'></div>
                    <span style='font-size:12px;color:#64748b'>GPT-4o Vision</span>
                </div>
                <div style='display:flex;align-items:center;gap:7px'>
                    <div style='width:5px;height:5px;border-radius:50%;background:#f59e0b'></div>
                    <span style='font-size:12px;color:#64748b'>Streamlit</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ── Page Routing ───────────────────────────────────────────────────────────────
if page == "Configure Competitors":
    configure.render()
elif page == "Evaluate Competitors":
    evaluate.render()
elif page == "Report History":
    history.render()
elif page == "⭐ Admin Dashboard":
    admin.render()
