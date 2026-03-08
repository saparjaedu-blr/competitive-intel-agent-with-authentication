"""
ui/pages/admin.py — Super Admin dashboard.

Visible only to users with Role_Super_Admin.
Shows: user list, role management, usage analytics, all reports.
"""

import json
import streamlit as st
from db.auth_db import (
    get_all_users, get_user_roles, assign_role_to_user,
    remove_role_from_user, get_usage_stats, get_all_reports_admin,
    ROLE_SUPER_ADMIN, ROLE_END_USER
)
from auth.google_auth import current_user_is_admin, get_current_user_id


def render():
    if not current_user_is_admin():
        st.error("Access denied. Super Admin role required.")
        return

    st.markdown("## Admin Dashboard")
    st.markdown(
        "<p style='color:#64748b;margin-top:-8px;font-size:14px'>"
        "Manage users, roles, and monitor platform usage.</p>",
        unsafe_allow_html=True
    )

    tab_users, tab_analytics, tab_reports = st.tabs([
        "👥  Users & Roles",
        "📊  Usage Analytics",
        "📋  All Reports",
    ])

    # ── Tab 1: Users & Roles ───────────────────────────────────────────────────
    with tab_users:
        _render_users_tab()

    # ── Tab 2: Usage Analytics ─────────────────────────────────────────────────
    with tab_analytics:
        _render_analytics_tab()

    # ── Tab 3: All Reports ─────────────────────────────────────────────────────
    with tab_reports:
        _render_reports_tab()


def _render_users_tab():
    users = get_all_users()
    current_uid = get_current_user_id()

    st.markdown(
        f"<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
        f"text-transform:uppercase;color:#94a3b8'>{len(users)} Registered User(s)</p>",
        unsafe_allow_html=True
    )

    for user in users:
        roles = get_user_roles(user["id"])
        is_admin_user = ROLE_SUPER_ADMIN in roles
        is_self = user["id"] == current_uid

        name = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or "—"
        role_badge = (
            f"<span style='background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;"
            f"border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700;"
            f"letter-spacing:0.04em;text-transform:uppercase'>Super Admin</span>"
            if is_admin_user else
            f"<span style='background:#f0fdf4;border:1px solid #86efac;color:#15803d;"
            f"border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700;"
            f"letter-spacing:0.04em;text-transform:uppercase'>End User</span>"
        )
        self_badge = " &nbsp;<span style='font-size:10px;color:#94a3b8'>(you)</span>" if is_self else ""

        with st.expander(f"{'⭐ ' if is_admin_user else '👤 '}{name}  ·  {user['email']}", expanded=False):
            col_info, col_roles = st.columns([3, 2])

            with col_info:
                st.markdown(f"""
                    <div style='font-size:13px;color:#475569;line-height:2'>
                        <b>Email:</b> {user['email']}<br>
                        <b>Joined:</b> {user.get('created_at','—')[:10]}<br>
                        <b>Last Active:</b> {(user.get('last_active') or '—')[:16]}<br>
                        <b>Role:</b> &nbsp;{role_badge}{self_badge}
                    </div>
                """, unsafe_allow_html=True)

            with col_roles:
                st.markdown(
                    "<p style='font-size:11px;font-weight:700;letter-spacing:0.06em;"
                    "text-transform:uppercase;color:#94a3b8;margin-bottom:8px'>Manage Roles</p>",
                    unsafe_allow_html=True
                )

                # Don't allow removing super admin from self
                if not is_self:
                    if is_admin_user:
                        if st.button(
                            "Remove Super Admin",
                            key=f"rm_admin_{user['id']}",
                            type="secondary",
                            use_container_width=True
                        ):
                            remove_role_from_user(user["id"], ROLE_SUPER_ADMIN)
                            st.success(f"Removed Super Admin from {name}")
                            st.rerun()
                    else:
                        if st.button(
                            "Grant Super Admin",
                            key=f"add_admin_{user['id']}",
                            type="primary",
                            use_container_width=True
                        ):
                            assign_role_to_user(user["id"], ROLE_SUPER_ADMIN)
                            st.success(f"Granted Super Admin to {name}")
                            st.rerun()
                else:
                    st.caption("Cannot modify your own role")


def _render_analytics_tab():
    stats = get_usage_stats()

    if not stats:
        st.info("No usage data yet.")
        return

    # Summary metrics
    total_users  = len(stats)
    total_evals  = sum(s.get("total_evaluations") or 0 for s in stats)
    active_users = sum(1 for s in stats if (s.get("total_evaluations") or 0) > 0)

    c1, c2, c3 = st.columns(3)
    for col, label, value, sub in [
        (c1, "TOTAL USERS",       total_users,  "Registered via Google"),
        (c2, "ACTIVE USERS",      active_users, "Have run ≥1 evaluation"),
        (c3, "TOTAL EVALUATIONS", total_evals,  "Across all users"),
    ]:
        with col:
            st.markdown(f"""
                <div style='background:#ffffff;border:1px solid #e8e4dd;border-radius:12px;
                    padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.04)'>
                    <div style='font-size:10px;font-weight:700;letter-spacing:0.08em;
                        text-transform:uppercase;color:#94a3b8;margin-bottom:6px'>{label}</div>
                    <div style='font-size:32px;font-weight:700;color:#1a56db;
                        font-family:monospace;line-height:1'>{value}</div>
                    <div style='font-size:11px;color:#94a3b8;margin-top:4px'>{sub}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
        "text-transform:uppercase;color:#94a3b8'>Per-User Breakdown</p>",
        unsafe_allow_html=True
    )

    # Per-user table
    table_data = [["User", "Email", "Evaluations", "Avg Duration", "Last Active"]]
    for s in stats:
        name = f"{s.get('first_name','') or ''} {s.get('last_name','') or ''}".strip() or "—"
        evals = s.get("total_evaluations") or 0
        avg   = f"{s.get('avg_duration_secs') or 0:.1f}s" if evals > 0 else "—"
        last  = (s.get("last_active") or "Never")[:16]
        table_data.append([name, s["email"], str(evals), avg, last])

    # Render as styled HTML table
    header = table_data[0]
    rows   = table_data[1:]

    header_html = "".join(
        f"<th style='padding:10px 14px;text-align:left;font-size:11px;font-weight:700;"
        f"letter-spacing:0.06em;text-transform:uppercase;color:#94a3b8;background:#f8f7f4;"
        f"border-bottom:1px solid #e8e4dd'>{h}</th>"
        for h in header
    )

    rows_html = ""
    for i, row in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#fafaf9"
        cells = "".join(
            f"<td style='padding:10px 14px;font-size:13px;color:#475569;"
            f"border-bottom:1px solid #f1f0ec'>{cell}</td>"
            for cell in row
        )
        rows_html += f"<tr style='background:{bg}'>{cells}</tr>"

    st.markdown(f"""
        <div style='background:#ffffff;border:1px solid #e8e4dd;border-radius:12px;
            overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04)'>
            <table style='width:100%;border-collapse:collapse'>
                <thead><tr>{header_html}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    """, unsafe_allow_html=True)


def _render_reports_tab():
    reports = get_all_reports_admin()

    if not reports:
        st.info("No reports have been generated yet.")
        return

    st.markdown(
        f"<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
        f"text-transform:uppercase;color:#94a3b8'>{len(reports)} Report(s) Across All Users</p>",
        unsafe_allow_html=True
    )

    for report in reports:
        vendors = json.loads(report.get("vendors_covered") or "[]")
        vendor_str = ", ".join(vendors) if vendors else "—"
        name = f"{report.get('first_name','')} {report.get('last_name','')}".strip()
        email = report.get("email", "—")
        gdrive_link = report.get("gdrive_link", "")
        has_drive = gdrive_link and gdrive_link.startswith("http")

        label = f"👤 {name or email}  ·  📅 {report['run_date']}  ·  {(report['research_query'] or '')[:50]}"

        with st.expander(label, expanded=False):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(
                    f"<p style='font-size:12px;color:#64748b;margin:0'>"
                    f"<b>User:</b> {email}<br>"
                    f"<b>Vendors:</b> {vendor_str}</p>",
                    unsafe_allow_html=True
                )
            with col2:
                if has_drive:
                    st.link_button("☁ Open in Drive", gdrive_link, use_container_width=True)
                if st.button("📄 View", key=f"admin_view_{report['id']}", use_container_width=True):
                    st.session_state["admin_viewing_report"] = report["id"]

    if "admin_viewing_report" in st.session_state:
        target_id = st.session_state["admin_viewing_report"]
        match = next((r for r in reports if r["id"] == target_id), None)
        if match:
            st.divider()
            st.markdown(f"**Report by {match.get('email')}** — {match['run_date']}")
            st.markdown(match["report_markdown"])
            if st.button("✕ Close", type="secondary"):
                del st.session_state["admin_viewing_report"]
                st.rerun()
