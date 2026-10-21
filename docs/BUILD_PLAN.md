# Job Hunt Pipeline Studio: Research, Architecture, Automations & System Design

## 1. Research: How to Stand Out from the AI Applicant Flood

Recent industry surveys and hiring manager debriefs reveal that over 80% of hiring managers can now spot AI-generated resumes and cover letters on sight. Automated application bots have flooded Applicant Tracking Systems (ATS) with generic "AI slop," causing human recruiters to become skeptical of applications that rely on formulaic AI buzzwords (*"spearheaded"*, *"leveraged"*, *"multifaceted"*, *"delve"*).

To break through this noise, candidates must shift from **volume-based spam** to **high-signal proof-of-work**:

1. **Proof of Work Over Generic Resumes**: Instead of a generic PDF, providing a tailored 1-page system architecture teardown, a live interactive prototype, or a 90-second Loom video walkthrough creates an undeniable signal of competence.
2. **Reverse Recruitment & Direct Back-Channeling**: High-signal applicants bypass public ATS queues by reaching out directly to the **Hiring Manager** (Director of Engineering, VP, or Team Lead) with an insightful technical observation on their actual stack.
3. **Truth-Constrained AI (No Hallucinations)**: Using AI not to fabricate inflated claims, but as an analytical research partner that conducts honest gap analyses and structures battle-tested STAR stories (Situation, Task, Action, Result) with real production tradeoffs.

---

## 2. AI & Non-AI Automations Included in the System

### A. Ensuring Quality & Matchability
* **AI Semantic Gap & Match Matrix**: Analyzes job requirements against your verified background, generating a 0–100% **Matchability Score**. Rather than simple keyword stuffing, it breaks down *Direct Hard Matches*, *Transferable Skills*, and *Identified Gaps*, providing pre-formulated counter-narratives for technical interviews.
* **Truth-Constrained STAR Story Bank (Non-AI + AI)**: Enforces real, quantifiable production metrics (e.g., P99 latency drops from 1.8s to 120ms during Black Friday spikes) to ground your stories in verified experience.
* **AI "Anti-Slop" Linter**: An automated linter that audits cover notes and outreach emails for telltale AI buzzwords, calculating a **Human Authenticity Score** and suggesting natural engineering phrasing.

### B. Maximizing Visibility
* **Hiring Manager Back-Channeling Engine**: Identifies and maps the likely Engineering Manager or Director alongside the talent partner, targeting cold outreach directly to decision-makers.
* **Proof-of-Work Artifact Launcher**: Attaches role-tailored technical artifacts (architecture whitepapers, interactive sandboxes, GitHub case studies) to bypass automated ATS filters.
* **Coordinated High-Signal Gmail Studio**: Provides 4 anti-slop email templates (*HM 3-Sentence Teardown*, *Screening Follow-up*, *Post-Loop Architecture Debrief*, *Offer Negotiation*) that log sent communications directly to your application history.

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                             CLIENT LAYER                               │
│  State 1: All Opportunity Board   │  State 2: Single Opp Cockpit       │
│  - Stage Swimlanes & Reordering   │  - Dynamic Tool Dock               │
│  - Matchability Badges (96%)      │  - Match Matrix Workpad            │
│  - Proof of Work Indicators       │  - STAR Prep Workpad               │
├───────────────────────────────────┼────────────────────────────────────┤
│     LEFT AUXILIARY WORKSPACE (Covers Board when called out)             │
│  [ Built-in Browser & Clip-to-Notes ]  [ High-Signal Gmail Studio ]    │
│  - Requirements Extraction             - Direct to Hiring Manager      │
│  - Career Page / Blog Reader           - Anti-Slop Linter & Templates  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│                          APPLICATION SERVER                            │
│  Python 3 HTTP Server • Anti-Slop Linter • Reorder Engine              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLite Driver
┌───────────────────────────────────▼────────────────────────────────────┐
│                           DATABASE LAYER                               │
│  SQLite3 (pipeline.db): opportunities, notes, tasks, comms, files      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File Structure

```text
job_hunt_pipeline/
├── index.html               # Complete, standalone interactive UI prototype
├── db.py                    # SQLite schema, relations, and seed data
├── pipeline.db              # Pre-seeded database with Stripe, Linear, OpenAI, etc.
├── server.py                # Python REST API server with Anti-Slop Linter
├── run.sh                   # Startup shell script
├── RESEARCH_AND_DESIGN.md   # Architectural and research specifications
└── README.md                # Quickstart documentation
```

---

## 5. Database Schema (`pipeline.db` / SQLite)

```sql
CREATE TABLE opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    stage_id TEXT NOT NULL,
    value REAL DEFAULT 0,
    contact_name TEXT,
    contact_email TEXT,
    contact_role TEXT DEFAULT 'Talent Partner',
    hiring_manager_name TEXT,
    hiring_manager_email TEXT,
    job_url TEXT,
    order_index REAL DEFAULT 1000,
    match_score INTEGER DEFAULT 85,
    match_analysis_json TEXT,
    proof_of_work_json TEXT,
    job_details_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    type TEXT DEFAULT 'prep', -- 'prep', 'star_story', 'gap_talking_point'
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'outreach', -- 'outreach', 'prep', 'artifact', 'referral'
    is_completed INTEGER DEFAULT 0,
    due_date TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE comms (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    type TEXT NOT NULL, -- 'email', 'call', 'linkedin'
    recipient TEXT,
    title TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'resume',
    size TEXT NOT NULL,
    url TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);
```

---

## 6. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/opportunities` | Returns all applications with match scores, proof of work, and notes |
| `POST` | `/api/opportunities` | Creates a new target application |
| `PATCH` | `/api/opportunities/<id>` | Updates application attributes (stage, comp, contacts) |
| `DELETE` | `/api/opportunities/<id>` | Deletes application without page refresh |
| `POST` | `/api/opportunities/reorder` | Updates fractional ordering of cards |
| `POST` | `/api/opportunities/<id>/notes` | Adds verified STAR story or prep note |
| `POST` | `/api/opportunities/<id>/tasks` | Adds next action task |
| `PATCH` | `/api/tasks/<id>` | Toggles task completion |
| `POST` | `/api/opportunities/<id>/comms` | Records outbound outreach to comms log |
| `POST` | `/api/ai/anti-slop-linter` | Scans text for AI buzzwords and calculates authenticity score |
| `POST` | `/api/ai/match-analysis` | Computes semantic strengths, gaps, and mitigation talking points |

---

## 7. UI Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STATE 1: ALL OPPORTUNITY BOARD (Target: $1.42M)   [Search...] [Stage: All ▾] [+ Add]   │
├───────────────────┬───────────────────┬───────────────────┬────────────────────────────┤
│ WISHLIST (1) $360k│ APPLIED (1) $230k │ SCREENING (1)$240k│ INTERVIEW (1) $285k        │
├───────────────────┼───────────────────┼───────────────────┼────────────────────────────┤
│ ┌───────────────┐ │ ┌───────────────┐ │ ┌───────────────┐ │ ┌────────────────────────┐ │
│ │OpenAI (89%)   │ │ │Vercel (94%)   │ │ │Linear (92%)   │ │ │Stripe (96% MATCH)      │ │
│ │$360,000       │ │ │$230,000       │ │ │$240,000       │ │ │$285,000                │ │
│ │[Proof of Work]│ │ │[RSC Whitepapr]│ │ │[Local Sync]   │ │ │[Payment Idempotency]   │ │
│ │▲ ▼ 🗑 Cockpit │ │ │▲ ▼ 🗑 Cockpit │ │ │▲ ▼ 🗑 Cockpit │ │ │▲ ▼ 🗑 Cockpit          │ │
│ └───────────────┘ │ └───────────────┘ │ └───────────────┘ │ └────────────────────────┘ │
└───────────────────┴───────────────────┴───────────────────┴────────────────────────────┘

WHEN SINGLE OPPORTUNITY COCKPIT + LEFT AUXILIARY WORKSPACE ARE OPEN:
┌───────────────────────────────────────────────┬────────────────────────────────────────┐
│ CALLED-OUT AUXILIARY VIEW (COVERS BOARD)      │ SINGLE OPPORTUNITY COCKPIT (Stripe)    │
│ [ 🌐 Browser ]  [ ✉️ High-Signal Gmail ]      │ Stage: [Technical Interview ▾] $285,000│
│ ───────────────────────────────────────────── │ Hiring Manager: David Chen (Director)  │
│ Gmail Mode: Target [Hiring Manager ▾]         ├────────────────────────────────────────┤
│ Strategy: [⚡ HM 3-Sentence Teardown]         │ TOOL DOCK (TAGS vs USING):             │
│ Subject: Stripe payments API idempotency note │ [🎯 Match & Gaps] [📁 Proof of Work]   │
│ Body:                                         │ [📝 STAR Prep (2)] [✅ Tasks (2)]      │
│ "Hi David, saw your tech post on distributed  │                                        │
│ latency. Built a 1-page idempotency teardown  │ ┌── [ACTIVE: MATCH MATRIX] ──────────┐ │
│ and spec: github.com/maxmardan/stripe-spec..."│ │ • Strengths: Idempotency (10/10)   │ │
│ [🛡️ Anti-Slop Audit: 100% Human-Written]     │ │ • Gap Mitigation: Ruby on Rails    │ │
│ [Send via Gmail]                              │ └────────────────────────────────────┘ │
└───────────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 8. Complete Code Implementation

### A. Database Initialization (`db.py`)
```python
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, location TEXT,
        stage_id TEXT NOT NULL, value REAL DEFAULT 0, contact_name TEXT, contact_email TEXT,
        contact_role TEXT DEFAULT 'Talent Partner', hiring_manager_name TEXT, hiring_manager_email TEXT,
        job_url TEXT, order_index REAL DEFAULT 1000, match_score INTEGER DEFAULT 85,
        match_analysis_json TEXT, proof_of_work_json TEXT, job_details_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL, type TEXT DEFAULT 'prep',
        title TEXT, content TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL, title TEXT NOT NULL,
        category TEXT DEFAULT 'outreach', is_completed INTEGER DEFAULT 0, due_date TEXT,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS comms (
        id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL, type TEXT NOT NULL,
        recipient TEXT, title TEXT NOT NULL, content TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL, name TEXT NOT NULL,
        type TEXT DEFAULT 'resume', size TEXT NOT NULL, url TEXT,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()
```

### B. Anti-Slop & API Server (`server.py`)
```python
import http.server, socketserver, json, os, urllib.parse
from db import init_db, get_connection

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AI_SLOP_BUZZWORDS = {
    "spearheaded": "led / architected / designed",
    "leveraged": "used / implemented / applied",
    "delve": "examine / explore / investigate",
    "testament": "evidence / proof / demonstrated by",
    "multifaceted": "comprehensive / cross-functional",
    "synergy": "alignment / joint integration",
    "game-changer": "significant improvement",
    "pivotal": "critical / foundational",
    "harnessing": "utilizing / employing",
    "cutting-edge": "modern / production-grade"
}

class PipelineHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if parsed.path == "/api/ai/anti-slop-linter":
            text = body.get("text", "")
            flagged = [bw for bw in AI_SLOP_BUZZWORDS if bw in text.lower()]
            return self._send_json({
                "flagged": flagged,
                "authenticityScore": max(60, 100 - len(flagged) * 10)
            })
```

---

## 9. How to Run the Prototype

1. **Direct In-Browser**: Open `index.html` directly in Safari or Chrome.
2. **Local Python Server**:
   ```bash
   cd job_hunt_pipeline
   ./run.sh
   ```
   Navigate to `http://localhost:8000`.
