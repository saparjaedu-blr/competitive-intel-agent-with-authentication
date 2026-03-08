import streamlit as st
import json
from db.auth_db import get_reports_for_user, get_report_by_id_for_user
from auth.google_auth import get_current_user_id


def _is_valid_drive_link(link: str) -> bool:
    if not link:
        return False
    if link.startswith("[") or link == "__local_only__":
        return False
    return link.startswith("http")


def render():
    user_id = get_current_user_id()
    if not user_id:
        st.error("Not authenticated.")
        return

    st.markdown("## Report History")
    st.markdown(
        "<p style='color:#64748b;margin-top:-8px;font-size:14px'>"
        "Your last 3 archived reports. Only you can see these.</p>",
        unsafe_allow_html=True
    )

    reports = get_reports_for_user(user_id)

    if not reports:
        st.info("No archived reports yet. Run an evaluation with **Publish & Archive Report** enabled.")
        return

    st.markdown(
        f"<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
        f"text-transform:uppercase;color:#94a3b8'>{len(reports)} / 3 Reports Stored</p>",
        unsafe_allow_html=True
    )

    for report in reports:
        vendors = json.loads(report.get("vendors_covered") or "[]")
        vendor_str = ", ".join(vendors) if vendors else "—"
        gdrive_link = report.get("gdrive_link", "")
        has_drive = _is_valid_drive_link(gdrive_link)

        label = f"📅  {report['run_date']}  ·  {(report['research_query'] or '')[:65]}"

        with st.expander(label, expanded=False):
            col_meta, col_actions = st.columns([3, 2])

            with col_meta:
                st.markdown(
                    f"<p style='font-size:12px;color:#64748b;margin:0'>"
                    f"<b style='color:#475569'>Vendors:</b> {vendor_str}</p>",
                    unsafe_allow_html=True
                )
                badge = (
                    "<span style='display:inline-flex;align-items:center;gap:4px;"
                    "background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;"
                    "padding:2px 10px;font-size:11px;font-weight:600;color:#1d4ed8;"
                    "margin-top:6px'>☁ Archived to Google Drive</span>"
                    if has_drive else
                    "<span style='display:inline-flex;align-items:center;gap:4px;"
                    "background:#f8f7f4;border:1px solid #e8e4dd;border-radius:12px;"
                    "padding:2px 10px;font-size:11px;font-weight:500;color:#94a3b8;"
                    "margin-top:6px'>Local only</span>"
                )
                st.markdown(badge, unsafe_allow_html=True)

            with col_actions:
                b1, b2 = st.columns(2)
                with b1:
                    if has_drive:
                        st.link_button("☁ Drive", gdrive_link, use_container_width=True)
                    else:
                        st.button("☁ Drive", disabled=True,
                                  key=f"drive_{report['id']}", use_container_width=True,
                                  help="Not published to Drive")
                with b2:
                    if st.button("📄 View", key=f"view_{report['id']}", use_container_width=True):
                        st.session_state["viewing_report_id"] = report["id"]

    # ── Inline viewer ──────────────────────────────────────────────────────────
    if "viewing_report_id" in st.session_state:
        report_id = st.session_state["viewing_report_id"]
        report = get_report_by_id_for_user(report_id, user_id)
        if report:
            st.divider()
            st.markdown(
                f"<p style='font-size:11px;font-weight:700;letter-spacing:0.07em;"
                f"text-transform:uppercase;color:#94a3b8'>Viewing Report</p>"
                f"<h3 style='margin-top:4px;color:#0f172a'>{report['run_date']}</h3>",
                unsafe_allow_html=True
            )
            st.markdown(report["report_markdown"])
            st.divider()
            if st.button("✕  Close Report", type="secondary"):
                del st.session_state["viewing_report_id"]
                st.rerun()
