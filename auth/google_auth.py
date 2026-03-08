"""
auth/google_auth.py — Google OAuth via streamlit-google-auth
"""

import json
import tempfile
import streamlit as st
from db.auth_db import (
    upsert_user, get_user_roles,
    ROLE_SUPER_ADMIN, ROLE_END_USER
)


def _make_credentials_file() -> str:
    """
    streamlit-google-auth needs a credentials JSON file path.
    We build it on-the-fly from secrets.toml so no file needs to be committed.
    """
    client_id     = st.secrets["google_oauth"]["client_id"]
    client_secret = st.secrets["google_oauth"]["client_secret"]
    redirect_uri  = st.secrets["google_oauth"]["redirect_uri"]

    creds = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(creds, tmp)
    tmp.flush()
    return tmp.name


def _get_auth():
    """Return a single Authenticate instance cached in session_state."""
    if "auth_instance" not in st.session_state:
        from streamlit_google_auth import Authenticate
        creds_path   = _make_credentials_file()
        redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
        cookie_key   = st.secrets.get("cookie_key", "compintel_secret_key_2026")

        st.session_state["auth_instance"] = Authenticate(
            secret_credentials_path=creds_path,
            cookie_name="compintel_session",
            cookie_key=cookie_key,
            redirect_uri=redirect_uri,
        )
    return st.session_state["auth_instance"]


def _render_login_card():
    """Renders the branding card above the Google button."""
    st.markdown("""
        <div style='display:flex;justify-content:center;margin-top:80px;margin-bottom:32px'>
            <div style='background:#ffffff;border:1px solid #e8e4dd;border-radius:16px;
                padding:40px 52px;max-width:420px;width:100%;
                box-shadow:0 4px 24px rgba(0,0,0,0.06);text-align:center'>
                <div style='background:#1a56db;color:white;border-radius:14px;
                    width:52px;height:52px;line-height:52px;font-size:26px;font-weight:700;
                    margin:0 auto 18px auto;
                    box-shadow:0 4px 14px rgba(26,86,219,0.3)'>⚡</div>
                <div style='font-size:22px;font-weight:700;color:#0f172a;
                    letter-spacing:-0.03em;margin-bottom:6px'>CompIntel</div>
                <div style='font-size:13px;color:#64748b;line-height:1.6'>
                    AI-Powered Competitive Intelligence Agent<br>
                    Sign in with Google to access your dashboard
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def init_session(google_user: dict) -> dict:
    email      = google_user.get("email", "")
    first_name = google_user.get("given_name", "")
    last_name  = google_user.get("family_name", "")
    picture    = google_user.get("picture", "")

    user  = upsert_user(email, first_name, last_name, picture)
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
    Returns True when signed in, False when showing login UI.
    """
    try:
        auth = _get_auth()
        auth.check_authentification()

        if not st.session_state.get("connected"):
            _render_login_card()
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                auth.login()
            st.markdown(
                "<p style='text-align:center;font-size:11px;color:#94a3b8;margin-top:16px'>"
                "Your data is private and not shared with other users.</p>",
                unsafe_allow_html=True
            )
            return False

        # Signed in — populate session once
        if "user" not in st.session_state:
            user_info = st.session_state.get("user_info", {})
            init_session({
                "email":       user_info.get("email", ""),
                "given_name":  user_info.get("given_name", ""),
                "family_name": user_info.get("family_name", ""),
                "picture":     user_info.get("picture", ""),
            })

        return True

    except ImportError:
        st.warning("⚠️  Dev mode — auth bypassed.")
        if "user" not in st.session_state:
            st.session_state["user"]       = {
                "id": 1, "email": "saparja.edu@gmail.com",
                "first_name": "Saparja", "last_name": "Edu", "picture_url": ""
            }
            st.session_state["user_roles"] = [ROLE_SUPER_ADMIN, ROLE_END_USER]
            st.session_state["is_admin"]   = True
        return True

    except Exception as e:
        _render_login_card()
        st.error(f"Auth error: {e}")
        st.info("Check your Streamlit secrets (google_oauth section).")
        return False


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
        for k in ["user", "user_roles", "is_admin", "connected", "user_info", "auth_instance"]:
            st.session_state.pop(k, None)
        st.rerun()
