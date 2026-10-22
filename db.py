"""SQLite schema, connection handling and data access for the pipeline."""

import json
import os
import sqlite3
import sys
from collections import defaultdict
from contextlib import contextmanager

from seed import SEED_COMMS, SEED_FILES, SEED_NOTES, SEED_OPPORTUNITIES, SEED_TASKS

DB_PATH = os.environ.get("PIPELINE_DB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    company_description TEXT DEFAULT '',
    contacts_json TEXT DEFAULT '[]',
    location TEXT,
    stage_id TEXT NOT NULL,
    value REAL DEFAULT 0,
    contact_name TEXT,
    contact_email TEXT,
    contact_role TEXT DEFAULT 'Recruiter',
    hiring_manager_name TEXT,
    hiring_manager_email TEXT,
    job_url TEXT,
    order_index REAL DEFAULT 1000,
    match_score INTEGER DEFAULT 0,
    match_analysis_json TEXT,
    proof_of_work_json TEXT,
    job_details_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    type TEXT DEFAULT 'prep', -- 'prep', 'star_story', 'gap_talking_point'
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'outreach', -- 'outreach', 'prep', 'artifact', 'referral'
    is_completed INTEGER DEFAULT 0,
    due_date TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comms (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    type TEXT NOT NULL, -- 'audio', 'video', 'email', 'other'
    recipient TEXT,
    title TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL,
    date TEXT DEFAULT '',
    contact_name TEXT DEFAULT '',
    method TEXT DEFAULT 'email',
    summary TEXT DEFAULT '',
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'resume',
    size TEXT NOT NULL,
    url TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    name TEXT NOT NULL,
    email TEXT,
    headline TEXT,
    location TEXT,
    target_role TEXT,
    target_ote REAL DEFAULT 150000,
    years_experience INTEGER DEFAULT 5,
    background_summary TEXT,
    skills_json TEXT,
    stories_json TEXT,
    gaps_json TEXT,
    gemini_api_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Child lookups and board ordering run on every page load.
CREATE INDEX IF NOT EXISTS idx_notes_opp ON notes (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_tasks_opp ON tasks (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_comms_opp ON comms (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_files_opp ON files (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_opps_order ON opportunities (order_index);
"""

# The three simplified opportunity stages
STAGE_IDS = ("targeted", "applied", "interview_loop")

OPPORTUNITY_COLUMNS = (
    "id", "title", "company", "company_description", "contacts_json", "location", "stage_id", "value", "contact_name",
    "contact_email", "contact_role", "hiring_manager_name", "hiring_manager_email",
    "job_url", "order_index", "match_score", "match_analysis_json",
    "proof_of_work_json", "job_details_json",
)
JSON_COLUMNS = ("match_analysis_json", "proof_of_work_json", "job_details_json", "contacts_json")

OPPORTUNITY_API_FIELDS = {
    "stage_id": "stageId",
    "company_description": "companyDescription",
    "contact_name": "contactName",
    "contact_email": "contactEmail",
    "contact_role": "contactRole",
    "hiring_manager_name": "hiringManagerName",
    "hiring_manager_email": "hiringManagerEmail",
    "job_url": "jobUrl",
    "order_index": "orderIndex",
    "match_score": "matchScore",
}
JSON_API_FIELDS = {
    "match_analysis_json": "matchDetails",
    "proof_of_work_json": "proofOfWork",
    "job_details_json": "jobDetails",
    "contacts_json": "contacts",
}

PATCHABLE_FIELDS = {
    "stageId": "stage_id",
    "value": "value",
    "company": "company",
    "companyDescription": "company_description",
    "contacts": "contacts_json",
    "contactName": "contact_name",
    "contactEmail": "contact_email",
    "contactRole": "contact_role",
    "hiringManagerName": "hiring_manager_name",
    "hiringManagerEmail": "hiring_manager_email",
    "title": "title",
    "location": "location",
    "jobUrl": "job_url",
    "matchScore": "match_score",
    "matchDetails": "match_analysis_json",
    "proofOfWork": "proof_of_work_json",
    "jobDetails": "job_details_json",
}
_JSON_PATCH_COLUMNS = set(JSON_API_FIELDS)

_INSERT_OPPORTUNITY_SQL = "INSERT INTO opportunities ({}) VALUES ({})".format(
    ", ".join(OPPORTUNITY_COLUMNS), ", ".join("?" * len(OPPORTUNITY_COLUMNS))
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_columns(conn):
    """Safely add new columns to existing SQLite databases."""
    opp_cols = [r[1] for r in conn.execute("PRAGMA table_info(opportunities)").fetchall()]
    if "company_description" not in opp_cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN company_description TEXT DEFAULT ''")
    if "contacts_json" not in opp_cols:
        conn.execute("ALTER TABLE opportunities ADD COLUMN contacts_json TEXT DEFAULT '[]'")

    comm_cols = [r[1] for r in conn.execute("PRAGMA table_info(comms)").fetchall()]
    if "date" not in comm_cols:
        conn.execute("ALTER TABLE comms ADD COLUMN date TEXT DEFAULT ''")
    if "contact_name" not in comm_cols:
        conn.execute("ALTER TABLE comms ADD COLUMN contact_name TEXT DEFAULT ''")
    if "method" not in comm_cols:
        conn.execute("ALTER TABLE comms ADD COLUMN method TEXT DEFAULT 'email'")
    if "summary" not in comm_cols:
        conn.execute("ALTER TABLE comms ADD COLUMN summary TEXT DEFAULT ''")

    prof_cols = [r[1] for r in conn.execute("PRAGMA table_info(profile)").fetchall()]
    if "gmail_app_password" not in prof_cols:
        conn.execute("ALTER TABLE profile ADD COLUMN gmail_app_password TEXT DEFAULT ''")

    # Migrate legacy stage IDs to the 3 simplified stages
    conn.execute("UPDATE opportunities SET stage_id = 'targeted' WHERE stage_id IN ('wishlist')")
    conn.execute("UPDATE opportunities SET stage_id = 'interview_loop' WHERE stage_id IN ('screening', 'interview', 'offer')")


def init_default_profile(conn):
    """Seed a clean, customizable starter profile if none exists."""
    row = conn.execute("SELECT id FROM profile WHERE id = 'default'").fetchone()
    if row:
        return

    skills = [
        {"key": "sales", "label": "Pipeline & Prospecting", "evidence": "Demonstrated track record of outbound prospecting, discovery, and business acquisition."},
        {"key": "closing", "label": "Discovery, Demos & Closing", "evidence": "Ran consultative discovery meetings, structured product demos, and closed new business against targets."},
        {"key": "accounts", "label": "Client Relationship Management", "evidence": "Managed client accounts with high satisfaction, retention, and account expansion."},
        {"key": "tools", "label": "CRM & Modern Tools", "evidence": "Proficient in CRM tools, pipeline forecasting, and structured follow-up routines."},
    ]
    stories = [
        {
            "id": "story-1",
            "title": "Exceeded Revenue Quota",
            "company": "Prior Role",
            "role": "Top Performer",
            "pitch": "Consistently outperformed quota through disciplined outbound prospecting and consultative discovery.",
            "situation": "Target required ramping revenue and signing new clients in a competitive market.",
            "task": "Build outbound momentum and secure high-value client commitments.",
            "action": "Implemented structured discovery, mapped stakeholder needs, and tailored value propositions.",
            "result": "Surpassed quarterly targets and expanded book of business.",
            "prompts": ["What specific objection did you overcome?", "What was the measurable revenue impact?"]
        }
    ]

    conn.execute(
        """
        INSERT INTO profile (
            id, name, email, headline, location, target_role, target_ote,
            years_experience, background_summary, skills_json, stories_json,
            gaps_json, gemini_api_key
        ) VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Candidate",
            "",
            "Sales & Fintech Professional",
            "New York, NY / Remote",
            "Account Executive",
            150000,
            6,
            "Experienced sales and fintech professional with proven track record in client acquisition, consultative advisory, and revenue growth.",
            json.dumps(skills),
            json.dumps(stories),
            json.dumps([]),
            "",
        )
    )


def init_db(seed=False):
    """Initialize SQLite database with WAL and schema. Does not auto-seed fake opportunities."""
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        _ensure_columns(conn)
        init_default_profile(conn)
        # Clear legacy seeded demo records
        conn.execute("DELETE FROM opportunities WHERE id IN ('job-1', 'job-2', 'job-3', 'job-4', 'job-5') OR company IN ('Toast', 'Block (Square)', 'Ramp', 'Brex', 'Stripe', 'Company', 'Target Company')")
        conn.execute("DELETE FROM notes WHERE opportunity_id NOT IN (SELECT id FROM opportunities)")
        conn.execute("DELETE FROM tasks WHERE opportunity_id NOT IN (SELECT id FROM opportunities)")
        conn.execute("DELETE FROM comms WHERE opportunity_id NOT IN (SELECT id FROM opportunities)")
        conn.execute("DELETE FROM files WHERE opportunity_id NOT IN (SELECT id FROM opportunities)")
        if seed and conn.execute("SELECT count(*) FROM opportunities").fetchone()[0] == 0:
            seed_data(conn)


def insert_opportunity(conn, record):
    values = [
        json.dumps(record[col]) if col in JSON_COLUMNS else record.get(col, "" if col.endswith("_json") or col == "company_description" else None)
        for col in OPPORTUNITY_COLUMNS
    ]
    conn.execute(_INSERT_OPPORTUNITY_SQL, values)


def seed_data(conn):
    for record in SEED_OPPORTUNITIES:
        # Remap legacy seed stage IDs
        stage = record.get("stage_id", "targeted")
        if stage == "wishlist":
            record["stage_id"] = "targeted"
        elif stage in ("screening", "interview", "offer"):
            record["stage_id"] = "interview_loop"
        record["company_description"] = record.get("company_description", "")
        record["contacts_json"] = []
        insert_opportunity(conn, record)
    conn.executemany("INSERT INTO notes (id, opportunity_id, type, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?)", SEED_NOTES)
    conn.executemany("INSERT INTO tasks (id, opportunity_id, title, category, is_completed, due_date) VALUES (?, ?, ?, ?, ?, ?)", SEED_TASKS)
    conn.executemany("INSERT INTO comms (id, opportunity_id, type, recipient, title, content, created_at, date, contact_name, method, summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [(c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[6][:10] if len(c[6]) >= 10 else "", c[3], "email" if c[2] == "email" else "other", c[5] or c[4]) for c in SEED_COMMS])
    conn.executemany("INSERT INTO files (id, opportunity_id, name, type, size, url) VALUES (?, ?, ?, ?, ?, ?)", SEED_FILES)


def _load_json(raw):
    return json.loads(raw) if raw else {}


def _group_by_opportunity(conn, sql, transform=dict):
    grouped = defaultdict(list)
    for row in conn.execute(sql):
        item = transform(row)
        grouped[item.pop("opportunity_id")].append(item)
    return grouped


def _task_to_api(row):
    return {
        "opportunity_id": row["opportunity_id"],
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "isCompleted": bool(row["is_completed"]),
        "dueDate": row["due_date"],
    }


def _comm_to_api(row):
    r = dict(row)
    method = (r.get("method") or r.get("type") or "email").lower()
    if method not in ("audio", "video", "email", "other"):
        if "call" in method or "phone" in method:
            method = "audio"
        elif "zoom" in method or "meet" in method or "video" in method:
            method = "video"
        elif "email" in method or "mail" in method:
            method = "email"
        else:
            method = "other"

    contact_name = r.get("contact_name") or r.get("recipient") or ""
    date_val = r.get("date") or r.get("created_at") or ""
    summary_val = r.get("summary") or r.get("content") or r.get("title") or ""

    return {
        "opportunity_id": r["opportunity_id"],
        "id": r["id"],
        "date": date_val,
        "contactName": contact_name,
        "method": method,
        "summary": summary_val,
        # Backward compatibility fields
        "type": method,
        "recipient": contact_name,
        "title": summary_val,
        "content": summary_val,
        "time": date_val,
    }


def _opportunity_to_api(row):
    opp = {}
    r = dict(row)
    for col, value in r.items():
        if col in JSON_API_FIELDS:
            opp[JSON_API_FIELDS[col]] = _load_json(value)
        else:
            opp[OPPORTUNITY_API_FIELDS.get(col, col)] = value

    # Ensure companyDescription is a string
    opp["companyDescription"] = opp.get("companyDescription") or ""

    # Ensure contacts is a list. If empty, synthesize from contactName / hiringManagerName
    contacts = opp.get("contacts")
    if not isinstance(contacts, list) or len(contacts) == 0:
        syn = []
        if r.get("hiring_manager_name"):
            syn.append({"id": "c-hm", "name": r["hiring_manager_name"], "role": "Hiring Manager", "email": r.get("hiring_manager_email") or ""})
        if r.get("contact_name"):
            syn.append({"id": "c-rec", "name": r["contact_name"], "role": r.get("contact_role") or "Recruiter", "email": r.get("contact_email") or ""})
        opp["contacts"] = syn

    return opp


def list_opportunities(conn):
    _ensure_columns(conn)
    notes = _group_by_opportunity(conn, "SELECT opportunity_id, id, type, title, content, created_at AS time FROM notes ORDER BY rowid DESC")
    tasks = _group_by_opportunity(conn, "SELECT opportunity_id, id, title, category, is_completed, due_date FROM tasks ORDER BY rowid DESC", _task_to_api)
    comms = _group_by_opportunity(conn, "SELECT opportunity_id, id, type, recipient, title, content, created_at, date, contact_name, method, summary FROM comms ORDER BY rowid DESC", _comm_to_api)
    files = _group_by_opportunity(conn, "SELECT opportunity_id, id, name, type, size, url FROM files ORDER BY rowid ASC")

    result = []
    for row in conn.execute("SELECT * FROM opportunities ORDER BY order_index ASC"):
        opp = _opportunity_to_api(row)
        opp_id = opp["id"]
        opp["notes"] = notes.get(opp_id, [])
        opp["tasks"] = tasks.get(opp_id, [])
        opp["comms"] = comms.get(opp_id, [])
        opp["files"] = files.get(opp_id, [])
        result.append(opp)
    return result


def get_opportunity_row(conn, opp_id):
    _ensure_columns(conn)
    return conn.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,)).fetchone()


def get_opportunity(conn, opp_id):
    row = get_opportunity_row(conn, opp_id)
    return _opportunity_to_api(row) if row else None


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------

def _mask_key(key):
    if not key:
        return ""
    if len(key) <= 8:
        return "••••••••"
    return key[:4] + "••••" + key[-4:]


def get_profile_dict(conn):
    init_default_profile(conn)
    row = conn.execute("SELECT * FROM profile WHERE id = 'default'").fetchone()
    if not row:
        return {}

    raw_skills = _load_json(row["skills_json"])
    raw_stories = _load_json(row["stories_json"])
    raw_gaps = _load_json(row["gaps_json"])

    env_key = os.environ.get("GEMINI_API_KEY", "")
    key = row["gemini_api_key"] or env_key

    return {
        "name": row["name"],
        "email": row["email"] or "",
        "headline": row["headline"] or "",
        "location": row["location"] or "",
        "targetRole": row["target_role"] or "",
        "targetOte": row["target_ote"] or 150000,
        "yearsExperience": row["years_experience"] or 5,
        "backgroundSummary": row["background_summary"] or "",
        "skills": raw_skills if isinstance(raw_skills, list) else [],
        "stories": raw_stories if isinstance(raw_stories, list) else [],
        "gaps": raw_gaps if isinstance(raw_gaps, list) else [],
        "hasGeminiKey": bool(key),
        "geminiApiKeyMasked": _mask_key(key),
        "geminiApiKey": row["gemini_api_key"] or "",
        "gmailAppPassword": (row["gmail_app_password"] or "") if "gmail_app_password" in row.keys() else "",
        "hasGmailAppPassword": bool(((row["gmail_app_password"] or "") if "gmail_app_password" in row.keys() else "") or os.environ.get("GMAIL_APP_PASSWORD", "")),
    }


def update_profile_dict(conn, updates):
    init_default_profile(conn)
    col_map = {
        "name": "name",
        "email": "email",
        "headline": "headline",
        "location": "location",
        "targetRole": "target_role",
        "targetOte": "target_ote",
        "yearsExperience": "years_experience",
        "backgroundSummary": "background_summary",
        "geminiApiKey": "gemini_api_key",
        "gmailAppPassword": "gmail_app_password",
    }
    json_map = {
        "skills": "skills_json",
        "stories": "stories_json",
        "gaps": "gaps_json",
    }

    cols = []
    vals = []
    for field, col in col_map.items():
        if field in updates:
            cols.append(f"{col} = ?")
            vals.append(updates[field])

    for field, col in json_map.items():
        if field in updates:
            cols.append(f"{col} = ?")
            vals.append(json.dumps(updates[field]))

    if not cols:
        return get_profile_dict(conn)

    cols.append("updated_at = CURRENT_TIMESTAMP")
    sql = f"UPDATE profile SET {', '.join(cols)} WHERE id = 'default'"
    conn.execute(sql, vals)
    return get_profile_dict(conn)


# ---------------------------------------------------------------------------
# Writes.
# ---------------------------------------------------------------------------

def update_opportunity(conn, opp_id, changes):
    _ensure_columns(conn)
    columns = []
    for field, col in PATCHABLE_FIELDS.items():
        if field in changes:
            value = changes[field]
            columns.append((col, json.dumps(value) if col in _JSON_PATCH_COLUMNS else value))
    if not columns:
        return get_opportunity_row(conn, opp_id) is not None
    assignments = ", ".join(f"{col} = ?" for col, _ in columns)
    cur = conn.execute(
        f"UPDATE opportunities SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [value for _, value in columns] + [opp_id],
    )
    return cur.rowcount > 0


def move_opportunity(conn, opp_id, stage_id, order_index):
    _ensure_columns(conn)
    cur = conn.execute("UPDATE opportunities SET stage_id = ?, order_index = ? WHERE id = ?", (stage_id, order_index, opp_id))
    return cur.rowcount > 0


def delete_opportunity(conn, opp_id):
    return conn.execute("DELETE FROM opportunities WHERE id = ?", (opp_id,)).rowcount > 0


def insert_note(conn, note_id, opp_id, note_type, title, content, created_at):
    conn.execute("INSERT INTO notes (id, opportunity_id, type, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (note_id, opp_id, note_type, title, content, created_at))


def insert_task(conn, task_id, opp_id, title, category):
    conn.execute("INSERT INTO tasks (id, opportunity_id, title, category, is_completed) VALUES (?, ?, ?, ?, 0)",
                 (task_id, opp_id, title, category))


def set_task_completed(conn, task_id, is_completed):
    return conn.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if is_completed else 0, task_id)).rowcount > 0


def delete_task(conn, task_id):
    return conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0


def insert_comm(conn, comm_id, opp_id, date, contact_name, method, summary, created_at=None):
    _ensure_columns(conn)
    if not created_at:
        created_at = date or "Just now"
    method_val = (method or "email").lower()
    if method_val not in ("audio", "video", "email", "other"):
        method_val = "other"
    conn.execute(
        """
        INSERT INTO comms (id, opportunity_id, type, recipient, title, content, created_at, date, contact_name, method, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (comm_id, opp_id, method_val, contact_name, summary, summary, created_at, date, contact_name, method_val, summary)
    )


def delete_comm(conn, comm_id):
    return conn.execute("DELETE FROM comms WHERE id = ?", (comm_id,)).rowcount > 0


def reset_db(seed=False):
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(DB_PATH + suffix):
            os.remove(DB_PATH + suffix)
    init_db(seed=seed)


if __name__ == "__main__":
    if "--reset" in sys.argv or "--seed" in sys.argv:
        reset_db(seed="--seed" in sys.argv)
        print("Database initialized at:", DB_PATH)
    else:
        init_db(seed=False)
        print("Database ready at:", DB_PATH)
