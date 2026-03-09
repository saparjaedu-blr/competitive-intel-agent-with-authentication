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
    """
    Safely check login state across different Streamlit versions.
    Streamlit >= 1.42 uses st.user.is_logged_in
    Older versions use st.experimental_user or session_state fallback.
    """
    # Try native st.user.is_logged_in (Streamlit >= 1.42)
    try:
        return bool(st.user.is_logged_in)
    except AttributeError:
        pass

    # Fallback: check if email exists in st.experimental_user
    try:
        return bool(st.experimental_user.get("email"))
    except Exception:
        pass

    # Fallback: session_state flag set after manual login
    return st.session_state.get("is_logged_in", False)


def _get_user_info() -> dict:
    """Get user info dict from whichever API is available."""
    try:
        u = st.user
        return {
            "email":       getattr(u, "email", ""),
            "given_name":  getattr(u, "given_name", "") or getattr(u, "name", "").split()[0] if getattr(u, "name", "") else "",
            "family_name": getattr(u, "family_name", "") or " ".join(getattr(u, "name", "").split()[1:]),
            "picture":     getattr(u, "picture", ""),
        }
    except Exception:
        try:
            u = st.experimental_user
            name = u.get("name", "")
            parts = name.split() if name else []
            return {
                "email":       u.get("email", ""),
                "given_name":  parts[0] if parts else "",
                "family_name": " ".join(parts[1:]) if len(parts) > 1 else "",
                "picture":     u.get("picture", ""),
            }
        except Exception:
            return {}


def _render_login_card():
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
    Returns True when signed in, False when showing login UI.
    """
    if not _is_logged_in():
        _render_login_card()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                # Streamlit native login button (>= 1.42)
                st.login()
            except AttributeError:
                st.error(
                    "This Streamlit version does not support native login. "
                    "Please upgrade to Streamlit >= 1.42.0"
                )
        st.markdown(
            "<p style='text-align:center;font-size:11px;color:#94a3b8;margin-top:16px'>"
            "Your data is private and not shared with other users.</p>",
            unsafe_allow_html=True,
        )
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
