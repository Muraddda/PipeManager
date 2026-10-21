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
    type TEXT NOT NULL, -- 'email', 'draft', 'call', 'linkedin', 'referral'
    recipient TEXT,
    title TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL,
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

STAGE_IDS = ("wishlist", "applied", "screening", "interview", "offer")

OPPORTUNITY_COLUMNS = (
    "id", "title", "company", "location", "stage_id", "value", "contact_name",
    "contact_email", "contact_role", "hiring_manager_name", "hiring_manager_email",
    "job_url", "order_index", "match_score", "match_analysis_json",
    "proof_of_work_json", "job_details_json",
)
JSON_COLUMNS = ("match_analysis_json", "proof_of_work_json", "job_details_json")

OPPORTUNITY_API_FIELDS = {
    "stage_id": "stageId",
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
}

PATCHABLE_FIELDS = {
    "stageId": "stage_id",
    "value": "value",
    "company": "company",
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
        json.dumps(record[col]) if col in JSON_COLUMNS else record[col]
        for col in OPPORTUNITY_COLUMNS
    ]
    conn.execute(_INSERT_OPPORTUNITY_SQL, values)


def seed_data(conn):
    for record in SEED_OPPORTUNITIES:
        insert_opportunity(conn, record)
    conn.executemany("INSERT INTO notes (id, opportunity_id, type, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?)", SEED_NOTES)
    conn.executemany("INSERT INTO tasks (id, opportunity_id, title, category, is_completed, due_date) VALUES (?, ?, ?, ?, ?, ?)", SEED_TASKS)
    conn.executemany("INSERT INTO comms (id, opportunity_id, type, recipient, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", SEED_COMMS)
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


def _opportunity_to_api(row):
    opp = {}
    for col, value in dict(row).items():
        if col in JSON_API_FIELDS:
            opp[JSON_API_FIELDS[col]] = _load_json(value)
        else:
            opp[OPPORTUNITY_API_FIELDS.get(col, col)] = value
    return opp


def list_opportunities(conn):
    notes = _group_by_opportunity(conn, "SELECT opportunity_id, id, type, title, content, created_at AS time FROM notes ORDER BY rowid DESC")
    tasks = _group_by_opportunity(conn, "SELECT opportunity_id, id, title, category, is_completed, due_date FROM tasks ORDER BY rowid DESC", _task_to_api)
    comms = _group_by_opportunity(conn, "SELECT opportunity_id, id, type, recipient, title, content, created_at AS time FROM comms ORDER BY rowid DESC")
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
# Writes. Each returns True when a row was affected so handlers can answer 404.
# ---------------------------------------------------------------------------

def update_opportunity(conn, opp_id, changes):
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


def insert_comm(conn, comm_id, opp_id, comm_type, recipient, title, content, created_at):
    conn.execute("INSERT INTO comms (id, opportunity_id, type, recipient, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (comm_id, opp_id, comm_type, recipient, title, content, created_at))


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
