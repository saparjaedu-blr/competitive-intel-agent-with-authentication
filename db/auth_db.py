"""
auth_db.py — User, role, and per-user data management.

Tables:
  users           — registered users (from Google OAuth)
  roles           — role definitions (Role_Super_Admin, Role_End_User)
  user_roles      — many-to-many user ↔ role assignments
  competitors     — now has user_id column (per-user)
  reports         — now has user_id column, max 3 per user enforced here
"""

import sqlite3
import json
from datetime import datetime
from config.settings import DB_PATH

SUPER_ADMIN_EMAIL = "saparja.edu@gmail.com"

ROLE_SUPER_ADMIN = "Role_Super_Admin"
ROLE_END_USER    = "Role_End_User"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema init ────────────────────────────────────────────────────────────────

def init_auth_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- Users registered via Google OAuth
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT    NOT NULL UNIQUE,
            first_name    TEXT,
            last_name     TEXT,
            picture_url   TEXT,
            last_active   TIMESTAMP,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Role definitions
        CREATE TABLE IF NOT EXISTS roles (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT NOT NULL UNIQUE
        );

        -- User ↔ Role assignments
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id    INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, role_id)
        );

        -- Usage tracking
        CREATE TABLE IF NOT EXISTS usage_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            action        TEXT    NOT NULL,
            vendors       TEXT,
            research_query TEXT,
            duration_secs  REAL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Seed roles
    for role in [ROLE_SUPER_ADMIN, ROLE_END_USER]:
        try:
            conn.execute("INSERT INTO roles (role_name) VALUES (?)", (role,))
        except Exception:
            pass
    conn.commit()

    # Add user_id to competitors table if not present
    for col in [("user_id", "INTEGER")]:
        try:
            conn.execute(f"ALTER TABLE competitors ADD COLUMN {col[0]} {col[1]}")
            conn.commit()
        except Exception:
            pass

    # Add user_id to reports table if not present
    for col in [("user_id", "INTEGER")]:
        try:
            conn.execute(f"ALTER TABLE reports ADD COLUMN {col[0]} {col[1]}")
            conn.commit()
        except Exception:
            pass

    conn.close()


# ── User CRUD ──────────────────────────────────────────────────────────────────

def upsert_user(email: str, first_name: str, last_name: str, picture_url: str = "") -> dict:
    """
    Create user if not exists, update last_active timestamp.
    Assigns Role_End_User automatically on first login.
    saparja.edu@gmail.com gets both roles.
    Returns user dict.
    """
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE users SET last_active=?, first_name=?, last_name=?, picture_url=? WHERE email=?",
            (now, first_name, last_name, picture_url, email)
        )
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone())
    else:
        conn.execute(
            """INSERT INTO users (email, first_name, last_name, picture_url, last_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (email, first_name, last_name, picture_url, now, now)
        )
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone())

        # Assign default role
        _assign_role(conn, user["id"], ROLE_END_USER)
        if email == SUPER_ADMIN_EMAIL:
            _assign_role(conn, user["id"], ROLE_SUPER_ADMIN)

    conn.close()
    return user


def _assign_role(conn, user_id: int, role_name: str):
    role = conn.execute(
        "SELECT id FROM roles WHERE role_name=?", (role_name,)
    ).fetchone()
    if role:
        try:
            conn.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, role["id"])
            )
            conn.commit()
        except Exception:
            pass  # already assigned


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_roles(user_id: int) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.role_name FROM roles r
           JOIN user_roles ur ON ur.role_id = r.id
           WHERE ur.user_id = ?""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [r["role_name"] for r in rows]


def is_super_admin(user_id: int) -> bool:
    return ROLE_SUPER_ADMIN in get_user_roles(user_id)


# ── Admin: user management ─────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def assign_role_to_user(user_id: int, role_name: str):
    conn = get_connection()
    _assign_role(conn, user_id, role_name)
    conn.close()


def remove_role_from_user(user_id: int, role_name: str):
    conn = get_connection()
    role = conn.execute(
        "SELECT id FROM roles WHERE role_name=?", (role_name,)
    ).fetchone()
    if role:
        conn.execute(
            "DELETE FROM user_roles WHERE user_id=? AND role_id=?",
            (user_id, role["id"])
        )
        conn.commit()
    conn.close()


# ── Per-user competitors ───────────────────────────────────────────────────────

def get_competitors_for_user(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM competitors WHERE user_id=? ORDER BY vendor_name",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_competitor_for_user(user_id: int, vendor_name, website_url="",
                             blog_url="", docs_url="", changelog_url="",
                             youtube_channel="") -> bool:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO competitors
               (user_id, vendor_name, website_url, blog_url, docs_url, changelog_url, youtube_channel)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, vendor_name, website_url, blog_url,
             docs_url, changelog_url, youtube_channel)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_competitor_by_name_for_user(user_id: int, vendor_name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM competitors WHERE user_id=? AND vendor_name=?",
        (user_id, vendor_name)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Per-user reports (max 3) ───────────────────────────────────────────────────

def save_report_for_user(user_id: int, research_query: str,
                          vendors_covered: list, report_markdown: str,
                          gdrive_link: str = "") -> int:
    """Save report for user. Enforces max 3 reports — deletes oldest if exceeded."""
    conn = get_connection()
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor = conn.execute(
        """INSERT INTO reports (user_id, run_date, research_query, vendors_covered,
           report_markdown, gdrive_link)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, run_date, research_query,
         json.dumps(vendors_covered), report_markdown, gdrive_link)
    )
    report_id = cursor.lastrowid
    conn.commit()

    # Enforce max 3 — delete oldest beyond limit
    old_reports = conn.execute(
        """SELECT id FROM reports WHERE user_id=?
           ORDER BY created_at DESC""",
        (user_id,)
    ).fetchall()

    if len(old_reports) > 3:
        ids_to_delete = [r["id"] for r in old_reports[3:]]
        for rid in ids_to_delete:
            conn.execute("DELETE FROM diff_log WHERE report_id=?", (rid,))
            conn.execute("DELETE FROM reports WHERE id=?", (rid,))
        conn.commit()

    conn.close()
    return report_id


def get_reports_for_user(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM reports WHERE user_id=?
           ORDER BY created_at DESC LIMIT 3""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report_by_id_for_user(report_id: int, user_id: int) -> dict | None:
    """Only returns report if it belongs to this user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE id=? AND user_id=?",
        (report_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Usage logging ──────────────────────────────────────────────────────────────

def log_usage(user_id: int, action: str, vendors: list = None,
              research_query: str = "", duration_secs: float = 0.0):
    conn = get_connection()
    conn.execute(
        """INSERT INTO usage_log (user_id, action, vendors, research_query, duration_secs)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, action, json.dumps(vendors or []), research_query, duration_secs)
    )
    conn.commit()
    conn.close()


# ── Admin analytics ────────────────────────────────────────────────────────────

def get_usage_stats() -> list[dict]:
    """Per-user usage summary for admin dashboard."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               u.id, u.email, u.first_name, u.last_name,
               u.created_at, u.last_active,
               COUNT(ul.id) as total_evaluations,
               ROUND(AVG(ul.duration_secs), 1) as avg_duration_secs,
               COUNT(DISTINCT ul.vendors) as unique_queries
           FROM users u
           LEFT JOIN usage_log ul ON ul.user_id = u.id AND ul.action = 'evaluation'
           GROUP BY u.id
           ORDER BY total_evaluations DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_reports_admin() -> list[dict]:
    """All reports across all users — for Super Admin only."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, u.email, u.first_name, u.last_name
           FROM reports r
           JOIN users u ON u.id = r.user_id
           ORDER BY r.created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
