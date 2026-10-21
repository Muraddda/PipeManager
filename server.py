import gzip
import http.server
import json
import os
import re
import sqlite3
import urllib.parse

import candidate
import db
import drafts
import gemini_service
import linter
import matcher

PORT = int(os.environ.get("PORT", "8000"))
BIND = os.environ.get("PIPELINE_BIND", "127.0.0.1")
EXTRA_HOSTS = {h.strip().lower() for h in os.environ.get("PIPELINE_ALLOWED_HOSTS", "").split(",") if h.strip()}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FILES = {"/": "index.html", "/index.html": "index.html"}
MAX_BODY = 1_000_000
GZIP_MIN_BYTES = 1024


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _random_id(prefix, num_bytes):
    return prefix + os.urandom(num_bytes).hex()


def _require(body, field, kinds=str):
    value = body.get(field)
    if not isinstance(value, kinds):
        raise ApiError(f"'{field}' is required")
    return value


def _stage(value):
    if value not in db.STAGE_IDS:
        raise ApiError(f"stage must be one of {', '.join(db.STAGE_IDS)}")
    return value


def _found(ok, what="Opportunity"):
    if not ok:
        raise ApiError(f"{what} not found", 404)


# ---------------------------------------------------------------------------
# Route handlers: each takes (conn, match, body) and returns (payload, status)
# ---------------------------------------------------------------------------

def list_opportunities(conn, match, body):
    return db.list_opportunities(conn), 200


def get_profile(conn, match, body):
    return db.get_profile_dict(conn), 200


def update_profile(conn, match, body):
    updated = db.update_profile_dict(conn, body)
    return updated, 200


def test_gemini_key(conn, match, body):
    key = body.get("apiKey")
    if not key:
        prof = db.get_profile_dict(conn)
        key = prof.get("geminiApiKey") or os.environ.get("GEMINI_API_KEY", "")
    ok, msg = gemini_service.test_api_key(key)
    return {"valid": ok, "message": msg}, 200 if ok else 400


def anti_slop_linter(conn, match, body):
    text = body.get("text", "")
    prof = db.get_profile_dict(conn)
    if gemini_service.is_available(prof):
        ai_lint = gemini_service.lint_text(text, prof)
        if ai_lint:
            return ai_lint, 200
    return linter.lint(text), 200


def draft_email(conn, match, body):
    opp = db.get_opportunity(conn, _require(body, "opportunityId"))
    _found(opp)
    template = body.get("template")
    if template not in drafts.TEMPLATES:
        raise ApiError(f"template must be one of {', '.join(drafts.TEMPLATES)}")
    prof = db.get_profile_dict(conn)
    return drafts.build(opp, template, body.get("target", "hm"), profile=prof), 200


def analyze_opportunity(conn, match, body):
    """Score the posting against the candidate profile and store result."""
    opp_id = match.group(1)
    opp = db.get_opportunity(conn, opp_id)
    _found(opp)
    details = dict(opp["jobDetails"])
    text = body.get("text")
    if isinstance(text, str) and text.strip():
        details["requirements"] = text.strip()
        details["isTemplate"] = False
    prof = db.get_profile_dict(conn)
    result = matcher.analyze(
        details.get("requirements", ""),
        basis="template" if details.get("isTemplate") else "posting",
        profile=prof
    )
    analysis = {k: result[k] for k in ("basis", "strengths", "gaps", "matched", "stories")}
    db.update_opportunity(conn, opp_id, {"matchScore": result["score"], "matchDetails": analysis, "jobDetails": details})
    return {"matchScore": result["score"], "matchDetails": analysis, "jobDetails": details}, 200


def create_opportunity(conn, match, body):
    opp_id = body.get("id") or _random_id("job-", 4)
    prof = db.get_profile_dict(conn)
    default_ote = prof.get("targetOte") or 150000

    record = {
        "id": opp_id,
        "title": body.get("title") or (prof.get("targetRole") or "New Application"),
        "company": body.get("company") or "Target Company",
        "location": body.get("location", ""),
        "stage_id": _stage(body.get("stageId", "wishlist")),
        "value": body.get("value", default_ote),
        "contact_name": body.get("contactName", ""),
        "contact_email": body.get("contactEmail", ""),
        "contact_role": body.get("contactRole", "Recruiter"),
        "hiring_manager_name": body.get("hiringManagerName", ""),
        "hiring_manager_email": body.get("hiringManagerEmail", ""),
        "job_url": body.get("jobUrl", ""),
        "order_index": body.get("orderIndex", 1000),
        "match_score": body.get("matchScore", 0),
        "match_analysis_json": body.get("matchDetails", {}),
        "proof_of_work_json": body.get("proofOfWork", {}),
        "job_details_json": body.get("jobDetails", {}),
    }
    try:
        db.insert_opportunity(conn, record)
    except sqlite3.IntegrityError:
        raise ApiError("Opportunity id already exists", 409)
    return {"success": True, "id": opp_id}, 201


def reorder_opportunity(conn, match, body):
    stage = _stage(body.get("newStageId"))
    _found(db.move_opportunity(conn, _require(body, "opportunityId"), stage, body.get("newOrderIndex")))
    return {"success": True}, 200


def update_opportunity(conn, match, body):
    if "stageId" in body:
        _stage(body["stageId"])
    _found(db.update_opportunity(conn, match.group(1), body))
    return {"success": True}, 200


def delete_opportunity(conn, match, body):
    _found(db.delete_opportunity(conn, match.group(1)))
    return {"success": True}, 200


def _child_insert(insert, prefix, fields):
    def handler(conn, match, body):
        item_id = body.get("id") or _random_id(prefix, 3)
        values = {name: body.get(name, default) for name, default in fields}
        try:
            insert(conn, item_id, match.group(1), *values.values())
        except sqlite3.IntegrityError:
            raise ApiError("Opportunity not found, or id already exists", 404)
        return {"success": True, "id": item_id, **values}, 201
    return handler


add_note = _child_insert(
    lambda conn, i, o, t, title, content, time: db.insert_note(conn, i, o, t, title, content, time),
    "n-", [("type", "prep"), ("title", "Prep Note"), ("content", ""), ("time", "Just now")])
add_task = _child_insert(
    lambda conn, i, o, title, cat: db.insert_task(conn, i, o, title, cat),
    "t-", [("title", ""), ("category", "outreach")])
add_comm = _child_insert(
    lambda conn, i, o, t, recipient, title, content, time: db.insert_comm(conn, i, o, t, recipient, title, content, time),
    "c-", [("type", "email"), ("recipient", ""), ("title", ""), ("content", ""), ("time", "Just now")])


def update_task(conn, match, body):
    if not isinstance(body.get("isCompleted"), bool):
        raise ApiError("'isCompleted' must be true or false")
    _found(db.set_task_completed(conn, match.group(1), body["isCompleted"]), "Task")
    return {"success": True}, 200


def delete_task(conn, match, body):
    _found(db.delete_task(conn, match.group(1)), "Task")
    return {"success": True}, 200


ROUTES = [
    ("GET", r"/api/opportunities", list_opportunities),
    ("GET", r"/api/profile", get_profile),
    ("PATCH", r"/api/profile", update_profile),
    ("POST", r"/api/profile", update_profile),
    ("POST", r"/api/ai/test-key", test_gemini_key),
    ("POST", r"/api/ai/anti-slop-linter", anti_slop_linter),
    ("POST", r"/api/ai/draft", draft_email),
    ("POST", r"/api/opportunities", create_opportunity),
    ("POST", r"/api/opportunities/reorder", reorder_opportunity),
    ("POST", r"/api/opportunities/([^/]+)/analyze", analyze_opportunity),
    ("POST", r"/api/opportunities/([^/]+)/notes", add_note),
    ("POST", r"/api/opportunities/([^/]+)/tasks", add_task),
    ("POST", r"/api/opportunities/([^/]+)/comms", add_comm),
    ("PATCH", r"/api/tasks/([^/]+)", update_task),
    ("PATCH", r"/api/opportunities/([^/]+)", update_opportunity),
    ("DELETE", r"/api/opportunities/([^/]+)", delete_opportunity),
    ("DELETE", r"/api/tasks/([^/]+)", delete_task),
]
_COMPILED_ROUTES = [(method, re.compile(pattern + r"\Z"), handler) for method, pattern, handler in ROUTES]


def resolve(method, path):
    for route_method, pattern, handler in _COMPILED_ROUTES:
        if route_method == method:
            match = pattern.match(path)
            if match:
                return handler, match
    return None, None


class PipelineHandler(http.server.BaseHTTPRequestHandler):
    server_version = "JobPipeline/2.5"
    protocol_version = "HTTP/1.1"

    def _send(self, body, status, content_type, extra=None):
        if status >= 400:
            self.close_connection = True
            extra = {**(extra or {}), "Connection": "close"}
        headers = dict(extra or {})
        if len(body) >= GZIP_MIN_BYTES and "gzip" in self.headers.get("Accept-Encoding", "").lower():
            body = gzip.compress(body, 5)
            headers["Content-Encoding"] = "gzip"
        headers["Vary"] = "Accept-Encoding"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data, status=200):
        self._send(json.dumps(data).encode("utf-8"), status, "application/json", {"Cache-Control": "no-store"})

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ApiError("Body too large", 413)
        if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            raise ApiError("Content-Type must be application/json", 415)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(f"Invalid JSON body: {exc}")
        if not isinstance(body, dict):
            raise ApiError("JSON body must be an object")
        return body

    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        return host in ("localhost", "127.0.0.1", "::1") or host in EXTRA_HOSTS

    def _serve_static(self, name):
        with open(os.path.join(BASE_DIR, name), "rb") as fh:
            self._send(fh.read(), 200, "text/html; charset=utf-8", {"Cache-Control": "no-cache"})

    def _dispatch(self, method):
        if not self._host_ok():
            return self._send_json({"error": "Forbidden host"}, 403)
        path = urllib.parse.urlparse(self.path).path
        if method == "GET" and path in STATIC_FILES:
            return self._serve_static(STATIC_FILES[path])
        handler, match = resolve(method, path)
        if handler is None:
            return self._send_json({"error": "Not found"}, 404)
        try:
            body = self._read_json_body() if method in ("POST", "PATCH") else {}
            with db.connect() as conn:
                payload, status = handler(conn, match, body)
        except ApiError as exc:
            return self._send_json({"error": str(exc)}, exc.status)
        return self._send_json(payload, status)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def log_message(self, fmt, *args):
        if os.environ.get("PIPELINE_QUIET") != "1":
            super().log_message(fmt, *args)


def main():
    db.init_db(seed=False)
    server = http.server.ThreadingHTTPServer((BIND, PORT), PipelineHandler)
    print(f"Database ready. Serving on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
