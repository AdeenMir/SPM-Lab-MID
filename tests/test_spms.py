"""Automated test cases for the SPMS.

Run:  python -m unittest discover -s tests -v
Each test records (ID, description, expected, actual, result) and the run writes
TEST_CASES.md (expected vs actual table) in the project folder.
"""
import os
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from spms import calculations as calc, db, seed  # noqa: E402
from spms.services import ProjectService, ValidationError  # noqa: E402

RESULTS = []


def seeded():
    svc = ProjectService(db.connect(":memory:"))
    seed.seed(svc)
    return svc


def minimal():
    """Tiny project: one work package, two activities A -> B."""
    svc = ProjectService(db.connect(":memory:"))
    svc.save_charter({"name": "Mini", "objectives": "o", "stakeholders": "s", "scope_in": "i",
                      "approved_budget": 100000, "start_date": "2026-01-01", "deadline": "2026-01-31"})
    svc.save_settings("2026-01-10", 0.95, 0.9, 0.95, 0.9)
    svc.save_member({"name": "Dev", "role": "Developer", "daily_rate": 1000})
    svc.save_wbs({"name": "Root", "node_type": "Project"})
    svc.save_wbs({"name": "WP", "node_type": "Work Package", "parent_id": 1})
    a = svc.save_task({"name": "A", "wbs_id": 2, "assignee_id": 1, "duration": 3, "budget": 3000})
    b = svc.save_task({"name": "B", "wbs_id": 2, "assignee_id": 1, "duration": 2, "budget": 2000})
    svc.set_dependencies(b, [a])
    return svc, a, b


def raises(fn, *a):
    try:
        fn(*a)
    except ValidationError as e:
        return f"ValidationError: {str(e).splitlines()[0][:70]}"
    return "no error"


class Base(unittest.TestCase):
    def check(self, tc, desc, expected, actual, cmp=None):
        ok = cmp(expected, actual) if cmp else expected == actual
        RESULTS.append((tc, desc, str(expected), str(actual), "PASS" if ok else "FAIL"))
        self.assertTrue(ok, f"{tc}: expected {expected!r}, got {actual!r}")

    def check_error(self, tc, desc, fn, *a):
        out = raises(fn, *a)
        RESULTS.append((tc, desc, "ValidationError (rejected)", out, "PASS" if out.startswith("ValidationError") else "FAIL"))
        self.assertTrue(out.startswith("ValidationError"), f"{tc}: {out}")


class TestScheduling(Base):
    def test_tc01_forward_pass(self):
        durs = {1: 3, 2: 2, 3: 4}
        res, finish = calc.compute_planned_schedule(durs, {1: set(), 2: {1}, 3: set()}, "2026-01-01")
        self.check("TC01", "CPM forward pass: A(3d)->B(2d) from 2026-01-01; B finishes",
                   "2026-01-05", res[2]["ef"].isoformat())

    def test_tc02_critical_path(self):
        res, _ = calc.compute_planned_schedule({1: 3, 2: 2, 3: 4}, {1: set(), 2: {1}, 3: set()}, "2026-01-01")
        self.check("TC02", "Critical path and float (A,B critical; C float 1 day)",
                   (True, True, False, 1), (res[1]["critical"], res[2]["critical"], res[3]["critical"], res[3]["float"]))

    def test_tc03_cycle(self):
        svc, a, b = minimal()
        self.check_error("TC03", "Circular dependency B->A while A->B exists is rejected", svc.set_dependencies, a, [b])

    def test_tc04_self_dependency(self):
        svc, a, b = minimal()
        self.check_error("TC04", "Activity depending on itself is rejected", svc.set_dependencies, a, [a])

    def test_tc05_delay_forecast(self):
        svc = seeded()
        t = {r["code"]: r for r in svc.schedule_analysis()["tasks"]}
        self.check("TC05", "T12 at 25% of 14 days on 2026-10-26 -> forecast finish / delay",
                   ("2026-11-05", 13), (t["T12"]["fe"].isoformat(), t["T12"]["delay"]))

    def test_tc06_delay_propagation(self):
        svc = seeded()
        s = svc.schedule_analysis()
        t12 = next(i for i in s["impacts"] if i["code"] == "T12")
        self.check("TC06", "T12 delay propagates to dependants and final deadline",
                   (True, 13), ("T15 (+13d)" in t12["affected_codes"], s["slip"]))


class TestEVM(Base):
    def test_tc07_evm_values(self):
        e = seeded().evm_analysis()
        self.check("TC07", "EVM at status date: PV, EV, AC, CPI, SPI",
                   (3884000, 3680000, 4000000, 0.92, 0.947),
                   (round(e["PV"]), round(e["EV"]), round(e["AC"]), round(e["CPI"], 3), round(e["SPI"], 3)))

    def test_tc08_thresholds(self):
        svc = seeded()
        first = (svc.evm_analysis()["cpi_status"], svc.evm_analysis()["spi_status"])
        svc.save_settings("2026-10-26", 0.90, 0.85, 0.90, 0.85)
        e = svc.evm_analysis()
        self.check("TC08", "CPI/SPI warnings at 0.95 threshold; OK after lowering to 0.90",
                   (("WARNING", "WARNING"), ("OK", "OK")), (first, (e["cpi_status"], e["spi_status"])))

    def test_tc09_budget_overrun_alert(self):
        svc = seeded()
        svc.add_expense({"task_id": 12, "exp_date": "2026-10-26", "amount": 2000000, "description": "overrun"})
        e = svc.evm_analysis()
        self.check("TC09", "Large overspend -> CPI critical and EAC > approved budget alert",
                   ("CRITICAL", True), (e["cpi_status"], any("exceeds approved budget" in m for _, m in e["alerts"])))

    def test_tc10_planned_fraction(self):
        v = calc.planned_fraction(date(2026, 1, 1), date(2026, 1, 10), "2026-01-05")
        self.check("TC10", "Planned % at day 5 of a 10-day activity", 0.5, v)


class TestScopeAndChange(Base):
    def test_tc11_unapproved_requirement_blocked(self):
        svc = seeded()
        r08 = svc.one("SELECT id FROM requirements WHERE code='R08'")["id"]
        self.check_error("TC11", "WBS element linked to unapproved requirement R08 is rejected",
                         svc.save_wbs, {"name": "SMS", "node_type": "Work Package", "parent_id": 1, "requirement_id": r08})

    def test_tc12_cr_requirement_direct_approval(self):
        svc = seeded()
        r = svc.one("SELECT id FROM requirements WHERE source='Change Request' AND status='Proposed'")["id"]
        self.check_error("TC12", "CR-sourced requirement cannot be approved directly", svc.set_requirement_status,
                         r, "Approved")

    def test_tc13_cr_approval_effects(self):
        svc = seeded()
        p0, s0, e0 = svc.get_project(), svc.schedule_analysis(), svc.evm_analysis()
        cid = svc.one("SELECT id FROM change_requests WHERE code='CR-002'")["id"]
        code = svc.approve_change_request(cid, "CCB")
        p1, s1, e1 = svc.get_project(), svc.schedule_analysis(), svc.evm_analysis()
        req = svc.one("SELECT status FROM requirements WHERE cr_id=?", (cid,))["status"]
        dep = svc.one("""SELECT COUNT(*) n FROM dependencies d JOIN tasks t ON t.id=d.task_id
                         WHERE t.code='T14' AND d.pred_id=(SELECT id FROM tasks WHERE code=?)""", (code,))["n"]
        self.check("TC13", "Approve CR-002: budget +350k, deadline +9d, BAC +350k, finish +9d, req approved, T14 depends on new activity",
                   (350000, 9, 350000, 9, "Approved", 1),
                   (p1["approved_budget"] - p0["approved_budget"],
                    (calc.parse_date(p1["deadline"]) - calc.parse_date(p0["deadline"])).days,
                    round(e1["BAC"] - e0["BAC"]), (s1["planned_finish"] - s0["planned_finish"]).days, req, dep))

    def test_tc14_double_approval(self):
        svc = seeded()
        self.check_error("TC14", "Approving an already-approved CR is rejected", svc.approve_change_request, 1, "CCB")

    def test_tc15_reject(self):
        svc = seeded()
        b0 = svc.get_project()["approved_budget"]
        svc.reject_change_request(2, "CCB")
        self.check("TC15", "Rejecting CR-002 leaves budget unchanged and rejects its requirement",
                   (b0, "Rejected"), (svc.get_project()["approved_budget"],
                                      svc.one("SELECT status FROM requirements WHERE cr_id=2")["status"]))

    def test_tc16_baseline_requirement_locked(self):
        svc = seeded()
        r01 = svc.one("SELECT id FROM requirements WHERE code='R01'")["id"]
        self.check_error("TC16", "Approved requirement in WBS cannot be rejected without a CR",
                         svc.set_requirement_status, r01, "Rejected")

    def test_tc17_preview_matches_approval(self):
        svc = seeded()
        prev = svc.preview_change_impact(2)
        svc.approve_change_request(2, "CCB")
        s = svc.schedule_analysis()
        self.check("TC17", "Impact preview forecast finish equals actual result after approval",
                   prev["forecast_finish"][1], calc.fmt(s["forecast_finish"]))


class TestValidation(Base):
    def test_tc18_progress_100_without_finish(self):
        svc, a, b = minimal()
        self.check_error("TC18", "100% complete without actual finish date", svc.update_progress, a, "2026-01-01", "", 100)

    def test_tc19_future_actual(self):
        svc, a, b = minimal()
        self.check_error("TC19", "Actual start after status date", svc.update_progress, a, "2026-01-20", "", 10)

    def test_tc20_fs_violation(self):
        svc, a, b = minimal()
        self.check_error("TC20", "Successor B started before predecessor A finished", svc.update_progress, b,
                         "2026-01-02", "", 10)

    def test_tc21_bad_date(self):
        svc, a, b = minimal()
        d = {"name": "Mini", "objectives": "o", "stakeholders": "s", "scope_in": "i", "approved_budget": 1,
             "start_date": "2026-13-45", "deadline": "2026-01-31"}
        self.check_error("TC21", "Invalid date format in charter", svc.save_charter, d)

    def test_tc22_deadline_before_start(self):
        svc, a, b = minimal()
        d = {"name": "Mini", "objectives": "o", "stakeholders": "s", "scope_in": "i", "approved_budget": 1,
             "start_date": "2026-02-01", "deadline": "2026-01-31"}
        self.check_error("TC22", "Deadline before start date", svc.save_charter, d)

    def test_tc23_non_numeric_budget(self):
        svc, a, b = minimal()
        self.check_error("TC23", "Non-numeric activity cost", svc.save_task,
                         {"name": "X", "wbs_id": 2, "duration": 2, "budget": "abc"})

    def test_tc24_expense_before_start(self):
        svc, a, b = minimal()
        self.check_error("TC24", "Expense booked on an activity that has not started", svc.add_expense,
                         {"task_id": a, "exp_date": "2026-01-05", "amount": 500})

    def test_tc25_member_delete_blocked(self):
        svc, a, b = minimal()
        self.check_error("TC25", "Deleting a team member assigned to activities", svc.delete_member, 1)


class TestQualityRisk(Base):
    def test_tc26_defect_resolved_date(self):
        svc = seeded()
        self.check_error("TC26", "Resolved defect without resolved date", svc.save_defect,
                         {"title": "x", "module": "m", "severity": "Low", "assigned_id": 1, "status": "Resolved",
                          "reported_date": "2026-10-20"})

    def test_tc27_failed_check_raises_defect(self):
        svc = seeded()
        n0 = svc.one("SELECT COUNT(*) n FROM defects")["n"]
        q = svc.one("SELECT id FROM quality_checks WHERE result='Pending'")["id"]
        svc.record_check_result(q, {"result": "Fail", "actual": "Dropped at 12 min", "inspector_id": 7,
                                    "check_date": "2026-10-26", "severity": "Critical"})
        self.check("TC27", "Failed quality check automatically raises a linked defect",
                   (n0 + 1, True), (svc.one("SELECT COUNT(*) n FROM defects")["n"],
                                    svc.one("SELECT defect_id FROM quality_checks WHERE id=?", (q,))["defect_id"] is not None))

    def test_tc28_risk_ranking(self):
        ranked = calc.rank_risks([{"code": "A", "likelihood": 5, "impact": 4}, {"code": "B", "likelihood": 4, "impact": 5},
                                  {"code": "C", "likelihood": 2, "impact": 2}])
        self.check("TC28", "Prioritization: equal score 20 -> higher impact first; levels",
                   [("B", 20, "High"), ("A", 20, "High"), ("C", 4, "Low")],
                   [(r["code"], r["score"], r["level"]) for r in ranked])

    def test_tc29_likelihood_range(self):
        svc = seeded()
        self.check_error("TC29", "Risk likelihood 7 (outside 1-5)", svc.save_risk,
                         {"title": "x", "category": "Scope", "likelihood": 7, "impact": 3})

    def test_tc30_pdpc(self):
        tree = seeded().pdpc_tree()
        n = sum(len(v) for v in tree["areas"].values())
        self.check("TC30", "PDPC contains every open risk with countermeasures", (8, True),
                   (n, all(r["measures"] for v in tree["areas"].values() for r in v)))


class TestIntegration(Base):
    def test_tc31_closure_blocked(self):
        svc = seeded()
        self.check_error("TC31", "Closing project with open activities/critical defects/pending CRs",
                         svc.close_project, {"closed_date": "2026-10-26", "accepted_by": "x", "lessons": "y"})

    def test_tc32_closure_ok_and_readonly(self):
        svc, a, b = minimal()
        svc.update_progress(a, "2026-01-01", "2026-01-03", 100)
        svc.update_progress(b, "2026-01-04", "2026-01-05", 100)
        svc.close_project({"closed_date": "2026-01-10", "accepted_by": "Client", "lessons": "Plan buffers"})
        out = raises(svc.save_member, {"name": "New", "role": "QA", "daily_rate": 1})
        self.check("TC32", "Complete project closes; afterwards records are read-only",
                   ("Closed", True), (svc.get_project()["status"], out.startswith("ValidationError")))

    def test_tc33_persistence(self):
        path = os.path.join(tempfile.mkdtemp(), "t.db")
        svc = ProjectService(db.connect(path))
        seed.seed(svc)
        svc.conn.close()
        svc2 = ProjectService(db.connect(path))
        self.check("TC33", "Data persists in SQLite file after reopening (activities, CRs, defects)",
                   (18, 3, 7), (svc2.one("SELECT COUNT(*) n FROM tasks")["n"],
                                svc2.one("SELECT COUNT(*) n FROM change_requests")["n"],
                                svc2.one("SELECT COUNT(*) n FROM defects")["n"]))

    def test_tc34_consistency(self):
        svc = seeded()
        svc.save_requirement({"title": "Audit trail report", "priority": "Should"})
        rid = svc.one("SELECT id FROM requirements WHERE title='Audit trail report'")["id"]
        svc.set_requirement_status(rid, "Approved")
        self.check("TC34", "Consistency check flags approved requirement not covered by the WBS", True,
                   any("Audit trail report" in m for _, m in svc.consistency_check()))

    def test_tc35_dashboard_and_report(self):
        svc = seeded()
        d = svc.dashboard()
        path = os.path.join(tempfile.mkdtemp(), "r.html")
        svc.export_report(path)
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        self.check("TC35", "Dashboard counts (delayed, pending CRs, critical defects) and report exported",
                   (5, 1, 2, True), (len(d["delayed"]), len(d["pending_crs"]), len(d["critical_defects"]),
                                     "Pending change requests" in txt and "Budget status" in txt))


def tearDownModule():
    RESULTS.sort()
    passed = sum(r[4] == "PASS" for r in RESULTS)
    with open(os.path.join(ROOT, "TEST_CASES.md"), "w", encoding="utf-8") as f:
        f.write("# Test cases - Smart Healthcare SPMS\n\n")
        f.write(f"Automated run: {passed}/{len(RESULTS)} passed. Re-run with "
                "`python -m unittest discover -s tests -v`.\n\n")
        f.write("| ID | Test case | Expected result | Actual result | Status |\n|---|---|---|---|---|\n")
        for r in RESULTS:
            f.write("| " + " | ".join(x.replace("|", "/") for x in r) + " |\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
