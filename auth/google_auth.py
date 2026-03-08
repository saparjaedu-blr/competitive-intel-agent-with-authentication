"""
auth/google_auth.py

Handles Google OAuth sign-in flow using streamlit-google-auth.
Manages session state and role-based access control.

Setup required in .streamlit/secrets.toml:
    [google_oauth]
    client_id     = "YOUR_GOOGLE_CLIENT_ID"
    client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
    redirect_uri  = "http://localhost:8501"   # or your deployed URL
"""

import streamlit as st
from db.auth_db import (
    upsert_user, get_user_roles, is_super_admin,
    ROLE_SUPER_ADMIN, ROLE_END_USER
)


def render_login_page():
    """Full-page login screen shown to unauthenticated users."""
    st.markdown("""
    <style>
    .login-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
        text-align: center;
    }
    .login-card {
        background: #ffffff;
        border: 1px solid #e8e4dd;
        border-radius: 16px;
        padding: 48px 56px;
        max-width: 440px;
        width: 100%;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='display:flex;flex-direction:column;align-items:center;
        justify-content:center;min-height:70vh'>
        <div style='background:#ffffff;border:1px solid #e8e4dd;border-radius:16px;
            padding:48px 56px;max-width:440px;width:100%;
            box-shadow:0 4px 24px rgba(0,0,0,0.06);text-align:center'>
            <div style='background:#1a56db;color:white;border-radius:14px;
                width:56px;height:56px;display:flex;align-items:center;
                justify-content:center;font-size:28px;font-weight:700;
                margin:0 auto 20px auto;box-shadow:0 4px 14px rgba(26,86,219,0.3)'>⚡</div>
            <div style='font-size:24px;font-weight:700;color:#0f172a;
                letter-spacing:-0.03em;margin-bottom:8px'>CompIntel</div>
            <div style='font-size:14px;color:#64748b;margin-bottom:32px;line-height:1.6'>
                AI-Powered Competitive Intelligence Agent<br>
                Sign in to access your dashboard
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;margin-top:16px'>
        <p style='font-size:11px;color:#94a3b8'>
            By signing in you agree to use this tool responsibly.<br>
            Your data is private and not shared with other users.
        </p>
    </div>
    """, unsafe_allow_html=True)


def init_session(google_user: dict) -> dict:
    """
    Called after successful Google OAuth.
    Upserts user in DB, loads roles, stores in session_state.
    google_user keys: email, given_name, family_name, picture
    """
    email      = google_user.get("email", "")
    first_name = google_user.get("given_name", "")
    last_name  = google_user.get("family_name", "")
    picture    = google_user.get("picture", "")

    user = upsert_user(email, first_name, last_name, picture)
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


def require_auth():
    """
    Main auth gate. Call at top of app.py before rendering any page.
    Returns True if authenticated, False if login page is being shown.
    """
    try:
        from streamlit_google_auth import Authenticate

        client_id     = st.secrets["google_oauth"]["client_id"]
        client_secret = st.secrets["google_oauth"]["client_secret"]
        redirect_uri  = st.secrets["google_oauth"]["redirect_uri"]
        cookie_key    = st.secrets.get("cookie_key", "compintel_secret_key_2026")

        auth = Authenticate(
            secret_credentials_path=None,
            cookie_name="compintel_session",
            cookie_key=cookie_key,
            redirect_uri=redirect_uri,
        )
        auth.check_authentification()

        if not st.session_state.get("connected"):
            # Show login page UI + the single Google sign-in button
            render_login_page()
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                auth.login()
            return False

        # Authenticated — init session if not already done
        if "user" not in st.session_state:
            user_info = st.session_state.get("user_info", {})
            google_user = {
                "email":       user_info.get("email", ""),
                "given_name":  user_info.get("given_name", ""),
                "family_name": user_info.get("family_name", ""),
                "picture":     user_info.get("picture", ""),
            }
            init_session(google_user)

        return True

    except ImportError:
        # Dev mode — bypass auth if library not installed
        st.warning("⚠️ Running in dev mode without authentication.")
        if "user" not in st.session_state:
            st.session_state["user"] = {
                "id": 1, "email": "saparja.edu@gmail.com",
                "first_name": "Saparja", "last_name": "Edu",
                "picture_url": ""
            }
            st.session_state["user_roles"] = [ROLE_SUPER_ADMIN, ROLE_END_USER]
            st.session_state["is_admin"] = True
        return True

    except Exception as e:
        render_login_page()
        st.error(f"Auth configuration error: {e}")
        st.info("Check your .streamlit/secrets.toml configuration.")
        return False


def render_user_pill():
    """Renders the signed-in user avatar + name in the sidebar."""
    user = get_current_user()
    if not user:
        return

    roles = st.session_state.get("user_roles", [])
    role_label = "Super Admin" if ROLE_SUPER_ADMIN in roles else "End User"
    role_color = "#1a56db" if ROLE_SUPER_ADMIN in roles else "#15803d"

    name = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user["email"]
    picture = user.get("picture_url", "")

    if picture:
        avatar_html = f"<img src='{picture}' style='width:32px;height:32px;border-radius:50%;object-fit:cover'>"
    else:
        initials = (user.get("first_name","?")[0] + user.get("last_name","?")[0]).upper()
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
    """Logout button in sidebar."""
    if st.button("Sign Out", use_container_width=True, type="secondary"):
        for key in ["user", "user_roles", "is_admin", "connected", "user_info"]:
            st.session_state.pop(key, None)
        st.rerun()
