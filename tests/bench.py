"""Rough timing for the read path: python3 tests/bench.py [rows]"""

import gzip
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["PIPELINE_DB"] = os.path.join(tempfile.mkdtemp(), "bench.db")

import db  # noqa: E402
import matcher  # noqa: E402

rows = int(sys.argv[1]) if len(sys.argv) > 1 else 500
db.init_db()
analysis = matcher.analyze("prospecting demos quota fintech Salesforce enterprise saas 8+ years")
with db.connect() as conn:
    for i in range(rows):
        db.insert_opportunity(conn, {
            "id": f"b{i}", "title": "Account Executive", "company": f"Co{i}", "location": "NYC", "stage_id": "wishlist",
            "value": 150000, "contact_name": "", "contact_email": "", "contact_role": "", "hiring_manager_name": "",
            "hiring_manager_email": "", "job_url": "", "order_index": i, "match_score": analysis["score"],
            "match_analysis_json": analysis, "proof_of_work_json": {}, "job_details_json": {"requirements": "x" * 1500}})
        for n in range(3):
            db.insert_note(conn, f"n{i}-{n}", f"b{i}", "prep", "t", "c" * 300, "now")
            db.insert_task(conn, f"t{i}-{n}", f"b{i}", "task", "outreach")

t = time.perf_counter()
for _ in range(10):
    with db.connect() as conn:
        payload = json.dumps(db.list_opportunities(conn)).encode()
query_ms = (time.perf_counter() - t) * 100
t = time.perf_counter()
packed = gzip.compress(payload, 5)
gzip_ms = (time.perf_counter() - t) * 1000
print(f"{rows} opportunities: list+serialize {query_ms:.1f} ms, payload {len(payload)/1024:.0f} KB, gzip {len(packed)/1024:.0f} KB in {gzip_ms:.1f} ms")
