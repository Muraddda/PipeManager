"""Run with: python3 -m unittest discover -s tests -v   (no dependencies)."""

import http.client
import json
import os
import re
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["PIPELINE_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PIPELINE_QUIET"] = "1"

import candidate  # noqa: E402
import db  # noqa: E402
import drafts  # noqa: E402
import http.server  # noqa: E402
import linter  # noqa: E402
import matcher  # noqa: E402
import server  # noqa: E402


PROFILE = {
    "skills": [
        {"key": "sales", "label": "Prospecting", "weight": 2, "keywords": ["prospecting", "outbound"],
         "evidence": "Ran outbound prospecting that added 108 new clients."},
        {"key": "tools", "label": "CRM", "weight": 1, "keywords": ["salesforce"], "evidence": "Daily Salesforce user."},
    ],
    "gaps": [
        {"key": "saas", "label": "Enterprise SaaS quota", "weight": 1, "keywords": ["enterprise saas", "meddpicc"],
         "mitigation": "No enterprise SaaS quota yet."},
    ],
    "stories": [{"id": "story-1", "skills": ["sales"], "pitch": "I added 108 new clients."}],
    "yearsExperience": 5,
}


class MatcherTests(unittest.TestCase):
    def test_empty_text_has_no_score(self):
        self.assertEqual(matcher.analyze("")["score"], 0)
        self.assertEqual(matcher.analyze("We make quantum widgets.")["score"], 0)

    def test_matches_come_with_resume_evidence(self):
        result = matcher.analyze("Outbound prospecting and demos, Salesforce", profile=PROFILE)
        self.assertTrue(any("108 new clients" in s for s in result["strengths"]))

    def test_gaps_are_reported_not_hidden(self):
        result = matcher.analyze("Enterprise SaaS account executive with MEDDPICC, prospecting", profile=PROFILE)
        self.assertTrue(any(g.startswith("Enterprise SaaS quota") for g in result["gaps"]))
        self.assertLess(result["score"], 98)

    def test_years_gap_only_when_exceeded(self):
        self.assertFalse(any("years required" in g for g in matcher.analyze("5+ years of prospecting", profile=PROFILE)["gaps"]))
        self.assertTrue(any("10+ years required" in g for g in matcher.analyze("10+ years of prospecting", profile=PROFILE)["gaps"]))

    def test_score_never_perfect(self):
        text = " ".join(kw.rstrip("*") for s in candidate.SKILLS for kw in s["keywords"])
        self.assertLessEqual(matcher.analyze(text, profile=PROFILE)["score"], 98)
        self.assertLessEqual(matcher.analyze("prospecting outbound salesforce", profile=PROFILE)["score"], 98)

    def test_word_boundaries(self):
        # "arr" must not match inside "carry"; "sas" not inside "sasquatch".
        self.assertNotIn("Enterprise SaaS quota", " ".join(matcher.analyze("carry the sasquatch", profile=PROFILE)["gaps"]))

    def test_story_picks_exist(self):
        for story_id in matcher.analyze("prospecting quota fintech leadership")["stories"]:
            self.assertIsNotNone(candidate.story_by_id(story_id))
        self.assertEqual(matcher.analyze("prospecting", profile=PROFILE)["stories"], ["story-1"])


class LinterTests(unittest.TestCase):
    def test_flags_and_cleans(self):
        result = linter.lint("I spearheaded and leveraged synergy.")
        self.assertEqual(result["flaggedCount"], 3)
        self.assertNotIn("spearheaded", result["cleaned"])

    def test_clean_text_scores_100(self):
        self.assertEqual(linter.lint("I led a team of 7.")["humanAuthenticityScore"], 100)

    def test_whole_words_only(self):
        self.assertEqual(linter.lint("The leveraged buyout")["flaggedCount"], 1)
        self.assertEqual(linter.lint("Our delvers")["flaggedCount"], 0)


class DraftTests(unittest.TestCase):
    def setUp(self):
        db.reset_db(seed=True)

    def _make_opp(self):
        with db.connect() as conn:
            db.insert_opportunity(conn, {
                "id": "opp-d", "title": "Account Executive", "company": "Acme", "company_description": "",
                "contacts_json": [], "location": "", "stage_id": "targeted", "value": 150000,
                "contact_name": "", "contact_email": "", "contact_role": "", "hiring_manager_name": "",
                "hiring_manager_email": "", "job_url": "", "order_index": 1, "match_score": 0,
                "match_analysis_json": {}, "proof_of_work_json": {}, "job_details_json": {},
            })
            return db.list_opportunities(conn)[0]

    def test_drafts_use_only_verified_facts_and_never_guess_emails(self):
        opp = self._make_opp()
        for name in drafts.TEMPLATES:
            draft = drafts.build(opp, name, "hm")
            self.assertEqual(draft["to"], "")
            self.assertNotIn("Staff", draft["body"])
            self.assertEqual(linter.lint(draft["body"])["flaggedCount"], 0, name)

    def test_fresh_db_has_no_demo_people_or_history(self):
        with db.connect() as conn:
            self.assertEqual(db.list_opportunities(conn), [])
        self.assertEqual(db.STAGE_IDS, ("targeted", "applied", "interview_loop"))
        opp = self._make_opp()
        self.assertEqual(opp["contactName"] + opp["contactEmail"] + opp["hiringManagerName"], "")
        self.assertEqual(opp["comms"], [])
        self.assertEqual(opp["stageId"], "targeted")
        self.assertEqual(opp["matchScore"], 0)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.reset_db()
        # init_db purges the legacy demo ids (opp-1..5), so fixtures use their own ids.
        with db.connect() as conn:
            for i, company in enumerate(("Acme", "Globex", "Initech", "Umbrella", "Hooli"), 1):
                db.insert_opportunity(conn, {
                    "id": f"opp-{i}", "title": "Account Executive", "company": company, "company_description": "",
                    "contacts_json": [], "location": "", "stage_id": "targeted", "value": 150000,
                    "contact_name": "", "contact_email": "", "contact_role": "", "hiring_manager_name": "",
                    "hiring_manager_email": "", "job_url": "", "order_index": i, "match_score": 0,
                    "match_analysis_json": {}, "proof_of_work_json": {}, "job_details_json": {},
                })
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.PipelineHandler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def call(self, method, path, body=None, headers=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        hdrs = {"Host": host or f"localhost:{self.port}"}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        hdrs.update(headers or {})
        conn.request(method, path, body=data, headers=hdrs)
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        try:
            return res.status, json.loads(raw)
        except ValueError:
            return res.status, raw

    def test_static_page_served(self):
        status, body = self.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Opportunity Pipeline</title>", body)

    def test_unknown_paths_and_files_are_404(self):
        self.assertEqual(self.call("GET", "/db.py")[0], 404)
        self.assertEqual(self.call("GET", "/../server.py")[0], 404)

    def test_rebinding_host_rejected(self):
        self.assertEqual(self.call("GET", "/api/opportunities", host="evil.example.com")[0], 403)

    def test_text_plain_post_rejected(self):
        status, _ = self.call("POST", "/api/opportunities/opp-1/tasks", b'{"title":"x"}', {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_no_cors_headers(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", "/api/opportunities", headers={"Host": f"localhost:{self.port}", "Origin": "https://evil.example"})
        res = conn.getresponse()
        res.read()
        self.assertIsNone(res.getheader("Access-Control-Allow-Origin"))

    def test_large_responses_are_gzipped_only_when_asked(self):
        import gzip
        host = {"Host": f"localhost:{self.port}"}
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", "/", headers={**host, "Accept-Encoding": "gzip"})
        res = conn.getresponse()
        packed = res.read()
        self.assertEqual(res.getheader("Content-Encoding"), "gzip")
        self.assertIn(b"<title>Opportunity Pipeline</title>", gzip.decompress(packed))
        conn.request("GET", "/", headers=host)
        res = conn.getresponse()
        res.read()
        self.assertIsNone(res.getheader("Content-Encoding"))

    def test_connection_is_reused_and_error_closes_it(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        host = {"Host": f"localhost:{self.port}"}
        for _ in range(3):
            conn.request("GET", "/api/profile", headers=host)
            res = conn.getresponse()
            res.read()
            self.assertEqual(res.status, 200)
        conn.request("POST", "/api/opportunities/opp-1/tasks", body=b'{"title":"x"}',
                     headers={**host, "Content-Type": "text/plain"})
        res = conn.getresponse()
        res.read()
        self.assertEqual(res.status, 415)
        self.assertEqual(res.getheader("Connection"), "close")

    def test_bad_json_is_400_not_500(self):
        self.assertEqual(self.call("POST", "/api/ai/anti-slop-linter", b"{nope")[0], 400)

    def test_notes_tasks_comms_attach_to_right_opportunity(self):
        # V1 bug B2: these were saved against the literal string "opportunities".
        for kind, body in (("notes", {"content": "hi"}), ("tasks", {"title": "t"}), ("comms", {"title": "c"})):
            status, res = self.call("POST", f"/api/opportunities/opp-2/{kind}", body)
            self.assertEqual(status, 201, kind)
        _, opps = self.call("GET", "/api/opportunities")
        job2 = next(o for o in opps if o["id"] == "opp-2")
        self.assertTrue(any(n["content"] == "hi" for n in job2["notes"]))
        self.assertTrue(any(t["title"] == "t" for t in job2["tasks"]))
        self.assertEqual(len(job2["comms"]), 1)

    def test_child_of_missing_opportunity_is_404(self):
        self.assertEqual(self.call("POST", "/api/opportunities/nope/notes", {"content": "x"})[0], 404)

    def test_client_supplied_ids_are_honored(self):
        status, res = self.call("POST", "/api/opportunities/opp-1/tasks", {"id": "t-client", "title": "x"})
        self.assertEqual(res["id"], "t-client")
        self.assertEqual(self.call("PATCH", "/api/tasks/t-client", {"isCompleted": True})[0], 200)
        self.assertEqual(self.call("DELETE", "/api/tasks/t-client")[0], 200)
        self.assertEqual(self.call("DELETE", "/api/tasks/t-client")[0], 404)

    def test_task_completed_must_be_bool(self):
        self.assertEqual(self.call("PATCH", "/api/tasks/t-missing", {"isCompleted": "yes"})[0], 400)

    def test_stage_validated(self):
        self.assertEqual(self.call("PATCH", "/api/opportunities/opp-1", {"stageId": "bogus"})[0], 400)
        self.assertEqual(self.call("POST", "/api/opportunities/reorder", {"opportunityId": "opp-1", "newStageId": "bogus", "newOrderIndex": 1})[0], 400)
        self.assertEqual(self.call("PATCH", "/api/opportunities/opp-1", {"stageId": "applied"})[0], 200)
        self.assertEqual(self.call("PATCH", "/api/opportunities/missing", {"stageId": "applied"})[0], 404)

    def test_patch_persists_json_fields(self):
        self.call("PATCH", "/api/opportunities/opp-4", {"proofOfWork": {"status": "ready", "artifactName": "plan"}, "hiringManagerName": "Sam"})
        _, opps = self.call("GET", "/api/opportunities")
        job4 = next(o for o in opps if o["id"] == "opp-4")
        self.assertEqual(job4["proofOfWork"]["status"], "ready")
        self.assertEqual(job4["hiringManagerName"], "Sam")

    def test_delete_cascades(self):
        # V1 bug B3: foreign keys were never enabled, so children were orphaned.
        self.call("POST", "/api/opportunities", {"id": "tmp-1", "title": "T", "company": "C"})
        self.call("POST", "/api/opportunities/tmp-1/notes", {"id": "n-tmp", "content": "x"})
        self.assertEqual(self.call("DELETE", "/api/opportunities/tmp-1")[0], 200)
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM notes WHERE opportunity_id='tmp-1'").fetchone()[0], 0)

    def test_duplicate_opportunity_id_is_409(self):
        self.assertEqual(self.call("POST", "/api/opportunities", {"id": "opp-1"})[0], 409)

    def test_analyze_scores_and_stores(self):
        self.call("POST", "/api/profile", {"skills": PROFILE["skills"], "gaps": PROFILE["gaps"], "stories": PROFILE["stories"]})
        status, res = self.call("POST", "/api/opportunities/opp-5/analyze", {"text": "Outbound prospecting, demos, quota, Salesforce"})
        self.assertEqual(status, 200)
        self.assertGreater(res["matchScore"], 0)
        self.assertFalse(res["jobDetails"]["isTemplate"])
        _, opps = self.call("GET", "/api/opportunities")
        self.assertEqual(next(o for o in opps if o["id"] == "opp-5")["matchScore"], res["matchScore"])
        self.assertEqual(self.call("POST", "/api/opportunities/missing/analyze", {})[0], 404)

    def test_draft_endpoint(self):
        status, res = self.call("POST", "/api/ai/draft", {"opportunityId": "opp-1", "template": "counter", "target": "recruiter"})
        self.assertEqual(status, 200)
        self.assertIn("Candidate", res["body"])
        self.assertEqual(self.call("POST", "/api/ai/draft", {"opportunityId": "opp-1", "template": "nope"})[0], 400)

    def test_profile_endpoint_has_no_phone_number(self):
        _, profile = self.call("GET", "/api/profile")
        blob = json.dumps(profile)
        self.assertIsNone(re.search(r"\d{3}[-. ]\d{3}[-. ]\d{4}", blob))
        self.assertNotIn("legal name", blob.lower())
        self.assertEqual(len(profile["stories"]), len(candidate.STORIES))

    def test_data_survives_restart(self):
        # V1: run.sh wiped the DB on every start. init_db must keep existing rows.
        self.call("PATCH", "/api/opportunities/opp-1", {"hiringManagerName": "Persist Me"})
        db.init_db()
        _, opps = self.call("GET", "/api/opportunities")
        self.assertEqual(next(o for o in opps if o["id"] == "opp-1")["hiringManagerName"], "Persist Me")


if __name__ == "__main__":
    unittest.main()
