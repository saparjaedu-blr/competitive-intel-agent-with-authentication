from agent.state import AgentState
from agent.tools.scraper_tool import scrape_multiple
from db.auth_db import get_competitor_by_name_for_user
from db.database import get_competitor_by_name


def web_scraper_node(state: AgentState) -> AgentState:
    """
    Fetch and scrape website, blog, docs, and changelog content for each vendor.
    Uses user-scoped competitor lookup when user_id is present in state.
    """
    vendors = state["vendors"]
    user_id = state.get("user_id")
    raw_data = state.get("raw_data", [])
    errors = state.get("errors", [])

    existing = {d["vendor_name"]: d for d in raw_data}

    for vendor_name in vendors:
        # User-scoped lookup first, fallback to global
        if user_id:
            competitor = get_competitor_by_name_for_user(user_id, vendor_name)
        else:
            competitor = get_competitor_by_name(vendor_name)

        if not competitor:
            errors.append(f"Vendor '{vendor_name}' not found.")
            continue

        # ── Marketing content (website + blog) ────────────────────────────────
        marketing_urls = [u for u in [
            competitor.get("website_url", ""),
            competitor.get("blog_url", ""),
        ] if u]
        web_content = scrape_multiple(marketing_urls) if marketing_urls else ""

        # ── Technical content (docs + changelog) ──────────────────────────────
        technical_urls = [u for u in [
            competitor.get("docs_url", ""),
            competitor.get("changelog_url", ""),
        ] if u]
        docs_content = scrape_multiple(technical_urls) if technical_urls else ""

        if vendor_name in existing:
            existing[vendor_name]["web_content"]  = web_content
            existing[vendor_name]["docs_content"] = docs_content
        else:
            existing[vendor_name] = {
                "vendor_name":      vendor_name,
                "web_content":      web_content,
                "docs_content":     docs_content,
                "youtube_content":  "",
                "scrapbook_content": "",
                "scrapbook_images": [],
            }

    return {
        **state,
        "raw_data":     list(existing.values()),
        "errors":       errors,
        "current_step": "web_scraping_complete",
    }
