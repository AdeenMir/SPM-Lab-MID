"""Realistic sample data for the Smart Healthcare case study.

Everything is inserted through the service layer, so the sample data obeys the same
validation and change-control rules as data entered through the GUI.
"""
from datetime import timedelta

from .calculations import parse_date
from .services import ProjectService

STATUS_DATE = "2026-10-26"


def seed(svc: ProjectService):
    svc.save_charter({
        "name": "Smart Healthcare Project Management & Monitoring System",
        "client": "Network of five partner hospitals",
        "sponsor": "Hospital Network Board (CEO office)",
        "manager": "Ayesha Khan",
        "objectives": "1. Deliver an integrated system for patient appointments, laboratory reports, doctor "
                      "schedules, online consultations and hospital billing across 5 hospitals.\n"
                      "2. Go live within 16 weeks and within PKR 5,000,000.\n"
                      "3. Zero critical defects at go-live; 95% of appointments booked online within 3 months.",
        "stakeholders": "Hospital Network Board (sponsor); hospital administrators (5); doctors; lab staff; "
                        "billing department; patients; IT department; development team; QA.",
        "scope_in": "Web system for appointments, doctor schedules, lab reports, online consultations, billing, "
                    "patient records; deployment and staff training at 5 hospitals.",
        "scope_out": "Medical hardware procurement, insurance-claim integration, pharmacy inventory, data "
                     "migration of paper records older than 2 years.",
        "approved_budget": 5_000_000, "start_date": "2026-08-03", "deadline": "2026-11-22",
        "status": "Monitoring & Control"})
    svc.save_settings(STATUS_DATE, 0.95, 0.90, 0.95, 0.90)

    team = [("Ayesha Khan", "Project Manager", "Planning, stakeholder communication, change control, reporting", 12000),
            ("Usman Ali", "Backend Developer", "Appointments, consultations, APIs", 9000),
            ("Hamza Raza", "Backend Developer", "Doctor schedules, lab reports, AI module", 9000),
            ("Fatima Noor", "Frontend Developer", "UI/UX design, web front-end", 8000),
            ("Bilal Ahmed", "Frontend Developer", "Appointment and billing screens, mobile UI", 8000),
            ("Zainab Tariq", "Database Developer", "Database design, billing, patient records", 8500),
            ("Hassan Iqbal", "QA Engineer", "Test planning, integration testing, UAT", 7000)]
    for n, r, resp, rate in team:
        svc.save_member({"name": n, "role": r, "responsibility": resp, "daily_rate": rate,
                         "email": n.split()[0].lower() + "@healthsoft.pk"})
    M = {m["name"].split()[0]: m["id"] for m in svc.list_members()}

    reqs = [("Patient appointment booking, rescheduling and cancellation", "Must", True),
            ("Doctor schedule and availability management", "Must", True),
            ("Laboratory report upload, approval and patient access", "Must", True),
            ("Online video consultations", "Should", True),
            ("Hospital billing, invoices and payments", "Must", True),
            ("Patient record management (EMR basic)", "Must", True),
            ("Multi-hospital support for 5 branches", "Must", True),
            ("SMS appointment reminders", "Could", False)]
    for title, prio, approve in reqs:
        svc.save_requirement({"title": title, "priority": prio, "description": title})
    R = {r["code"]: r["id"] for r in svc.list_requirements()}
    for code in ["R01", "R02", "R03", "R04", "R05", "R06", "R07"]:
        svc.set_requirement_status(R[code], "Approved")

    def wbs(name, ntype, parent=None, req=None):
        svc.save_wbs({"name": name, "node_type": ntype, "parent_id": parent, "requirement_id": req})
        return svc.one("SELECT id FROM wbs WHERE name=?", (name,))["id"]

    root = wbs("Smart Healthcare PMS", "Project")
    pm = wbs("Project Management", "Deliverable", root)
    w_init = wbs("Initiation & Planning", "Work Package", pm)
    w_deploy = wbs("Deployment & Training", "Work Package", pm, R["R07"])
    rd = wbs("Requirements & Design", "Deliverable", root)
    w_req = wbs("Requirements Analysis", "Work Package", rd)
    w_arch = wbs("Architecture & Database Design", "Work Package", rd, R["R07"])
    w_ui = wbs("UI/UX Design", "Work Package", rd)
    core = wbs("Core Modules", "Deliverable", root)
    w_app = wbs("Patient Appointments", "Work Package", core, R["R01"])
    w_doc = wbs("Doctor Schedules", "Work Package", core, R["R02"])
    w_lab = wbs("Laboratory Reports", "Work Package", core, R["R03"])
    w_con = wbs("Online Consultations", "Work Package", core, R["R04"])
    w_bill = wbs("Hospital Billing", "Work Package", core, R["R05"])
    w_rec = wbs("Patient Records", "Work Package", core, R["R06"])
    w_fe = wbs("Web Front-end", "Work Package", core)
    qa = wbs("Testing & Quality Assurance", "Deliverable", root)
    w_it = wbs("Integration & System Testing", "Work Package", qa)
    w_fix = wbs("Defect Fixing & Regression", "Work Package", qa)
    w_uat = wbs("User Acceptance Testing", "Work Package", qa)
    w_inf = wbs("Infrastructure & Licences", "Work Package", rd)

    # code, name, wbs, assignee, duration, budget, preds
    tasks = [
        ("Project charter, kickoff & plan", w_init, "Ayesha", 5, 60000, []),
        ("Requirements elicitation (5 hospitals)", w_req, "Ayesha", 10, 150000, ["T01"]),
        ("System architecture & database design", w_arch, "Zainab", 10, 250000, ["T02"]),
        ("UI/UX design & prototypes", w_ui, "Fatima", 10, 110000, ["T02"]),
        ("Appointment module backend", w_app, "Usman", 18, 300000, ["T03"]),
        ("Appointment module frontend", w_app, "Bilal", 15, 180000, ["T04"]),
        ("Doctor schedule module", w_doc, "Hamza", 14, 220000, ["T03"]),
        ("Laboratory reports module", w_lab, "Hamza", 16, 260000, ["T07"]),
        ("Online consultation module", w_con, "Usman", 25, 420000, ["T05"]),
        ("Billing module", w_bill, "Zainab", 16, 280000, ["T03"]),
        ("Front-end for schedules, labs & billing", w_fe, "Fatima", 25, 300000, ["T04"]),
        ("Integration & system testing", w_it, "Hassan", 14, 200000, ["T06", "T08", "T09", "T10", "T11", "T17"]),
        ("Defect fixing & regression testing", w_fix, "Usman", 10, 180000, ["T12"]),
        ("User acceptance testing at hospitals", w_uat, "Hassan", 10, 150000, ["T13"]),
        ("Deployment to 5 hospitals & staff training", w_deploy, "Ayesha", 10, 350000, ["T14", "T16"]),
        ("Hosting, licences & server procurement", w_inf, "Zainab", 5, 900000, ["T03"]),
        ("Patient record (EMR) module", w_rec, "Zainab", 12, 200000, ["T03"]),
    ]
    code_to_id = {}
    for name, w, who, dur, bud, preds in tasks:
        tid = svc.save_task({"name": name, "wbs_id": w, "assignee_id": M[who], "duration": dur, "budget": bud})
        code_to_id[svc.one("SELECT code FROM tasks WHERE id=?", (tid,))["code"]] = tid
    for (name, w, who, dur, bud, preds), code in zip(tasks, sorted(code_to_id)):
        if preds:
            svc.set_dependencies(code_to_id[code], [code_to_id[p] for p in preds])
    T = code_to_id

    # actual progress at the status date (code: start, end, %, cost overrun PKR)
    progress = [("T01", "2026-08-03", "2026-08-07", 100, 0), ("T02", "2026-08-08", "2026-08-19", 100, 10000),
                ("T03", "2026-08-20", "2026-08-29", 100, 15000), ("T04", "2026-08-20", "2026-08-28", 100, 0),
                ("T05", "2026-08-30", "2026-09-18", 100, 40000), ("T06", "2026-08-29", "2026-09-14", 100, 0),
                ("T07", "2026-08-30", "2026-09-12", 100, 0), ("T08", "2026-09-13", "2026-09-30", 100, 30000),
                ("T09", "2026-09-19", "2026-10-15", 100, 80000), ("T10", "2026-08-30", "2026-09-16", 100, 20000),
                ("T11", "2026-08-29", "2026-09-25", 100, 20000), ("T16", "2026-08-30", "2026-09-03", 100, 60000),
                ("T17", "2026-08-30", "2026-09-12", 100, 25000), ("T12", "2026-10-16", None, 25, 20000)]
    for code, s, e, pct, extra in progress:
        svc.update_progress(T[code], s, e, pct)
        bud = svc.one("SELECT budget FROM tasks WHERE id=?", (T[code],))["budget"]
        total = bud * pct / 100 + extra
        start, end = parse_date(s), parse_date(e or STATUS_DATE)
        dates, d = [], start
        while d <= end:
            dates.append(d)
            d += timedelta(days=7)
        share = round(total / len(dates))
        for i, d in enumerate(dates):
            amt = share if i < len(dates) - 1 else total - share * (len(dates) - 1)
            svc.add_expense({"task_id": T[code], "exp_date": d.isoformat(), "amount": amt,
                             "description": "Labour & resources" if i else "Labour, tools & setup"})

    for name, code, who in [("M1 Charter approved & kickoff", "T01", "Ayesha"),
                            ("M2 Requirements & design signed off", "T03", "Zainab"),
                            ("M3 Core modules complete", "T09", "Usman"),
                            ("M4 System testing complete", "T13", "Hassan"),
                            ("M5 UAT sign-off", "T14", "Hassan"),
                            ("M6 Go-live at 5 hospitals (project closure)", "T15", "Ayesha")]:
        svc.save_milestone({"name": name, "task_id": T[code], "owner_id": M[who]})

    # change requests from hospital management
    svc.save_change_request({
        "title": "AI-based preliminary diagnosis module",
        "description": "Symptom checker suggesting a preliminary diagnosis and the right specialist before booking.",
        "justification": "Hospital management wants to reduce unnecessary specialist visits and triage load.",
        "requested_by": "Hospital Network Board", "request_date": "2026-09-28", "priority": "Should",
        "cost_impact": 450000, "schedule_impact": 12, "after_task_id": T["T13"], "before_task_id": T["T14"],
        "assignee_id": M["Hamza"]})
    cr1 = svc.one("SELECT id FROM change_requests WHERE code='CR-001'")["id"]
    t18_code = svc.approve_change_request(cr1, "Hospital Network Board / CCB",
                                          "Approved with +12 days and PKR 450,000.", "2026-10-05")
    t18 = svc.one("SELECT id FROM tasks WHERE code=?", (t18_code,))["id"]
    svc.save_change_request({
        "title": "Patient mobile application (Android/iOS)",
        "description": "Mobile app for booking appointments, viewing lab reports and joining consultations.",
        "justification": "More than 60% of patients use smartphones; administrators expect fewer call-centre bookings.",
        "requested_by": "Hospital administrators", "request_date": "2026-10-12", "priority": "Should",
        "cost_impact": 350000, "schedule_impact": 9, "after_task_id": t18,
        "before_task_id": T["T14"], "assignee_id": M["Bilal"]})
    svc.save_change_request({
        "title": "Blockchain-based patient record ledger",
        "description": "Store record hashes on a private blockchain.",
        "justification": "Suggested by one hospital's IT head for tamper-evidence.",
        "requested_by": "IT Head, Hospital 3", "request_date": "2026-10-01", "priority": "Could",
        "cost_impact": 600000, "schedule_impact": 20, "after_task_id": T["T17"], "before_task_id": T["T14"],
        "assignee_id": M["Zainab"]})
    cr3 = svc.one("SELECT id FROM change_requests WHERE code='CR-003'")["id"]
    svc.reject_change_request(cr3, "Change Control Board",
                              "Out of scope; audit trail in the database already gives tamper evidence.", "2026-10-08")

    defects = [
        ("Same doctor slot can be double-booked", "Patient Appointments", "Critical", "Usman", "Open", "2026-10-19", None, "T05"),
        ("Patient record overwritten on concurrent edits", "Patient Records", "Critical", "Zainab", "In Progress", "2026-10-20", None, "T17"),
        ("Appointment reminder shows wrong time zone", "Patient Appointments", "High", "Usman", "Resolved", "2026-10-17", "2026-10-22", "T05"),
        ("Billing tax rounding error of PKR 1", "Hospital Billing", "Medium", "Zainab", "Closed", "2026-10-17", "2026-10-21", "T10"),
        ("Lab report PDF not rendering on Safari", "Laboratory Reports", "Low", "Fatima", "Open", "2026-10-21", None, "T08"),
        ("Video consultation drops on low bandwidth", "Online Consultations", "High", "Usman", "Open", "2026-10-22", None, "T09"),
        ("Cancelled appointment still visible in doctor schedule", "Doctor Schedules", "High", "Hamza", "In Progress", "2026-10-23", None, "T07"),
    ]
    D = {}
    for title, mod, sev, who, st, rep, res, task in defects:
        did = svc.save_defect({"title": title, "module": mod, "severity": sev, "assigned_id": M[who], "status": st,
                               "reported_date": rep, "resolved_date": res, "task_id": T[task],
                               "description": f"Found during integration testing ({rep})."})
        D[title] = did

    checks = [
        (w_arch, "Database schema normalised to 3NF and reviewed", "Inspection", "Review sign-off, no blocking comments",
         "Pass", "Signed off by PM and DB developer", "Ayesha", "2026-08-29"),
        (w_app, "No double booking of a doctor time slot", "Test", "Second booking of same slot is rejected",
         "Fail", "Second booking accepted - two patients in same slot", "Hassan", "2026-10-19"),
        (w_app, "Appointment API response time under 500 ms", "Test", "p95 < 500 ms with 200 users",
         "Pass", "p95 = 340 ms", "Hassan", "2026-10-18"),
        (w_rec, "Concurrent edit protection on patient records", "Test", "Second editor gets conflict warning",
         "Fail", "Last write silently overwrote first", "Hassan", "2026-10-20"),
        (w_bill, "Invoice totals match manual calculation", "Test", "100 sample invoices match to the rupee",
         "Pass", "100/100 matched after fix D04", "Hassan", "2026-10-21"),
        (w_lab, "Lab reports up to 10 MB upload and open", "Test", "Upload + open < 5 s", "Pass", "3.1 s average",
         "Hassan", "2026-10-21"),
        (w_con, "Video consultation stable for 30 minutes", "Test", "No drop at 1 Mbps", None, None, None, None),
        (w_deploy, "Training material reviewed by hospital admins", "Inspection", "Approved by 5 admins", None, None, None, None),
    ]
    link = {"No double booking of a doctor time slot": "Same doctor slot can be double-booked",
            "Concurrent edit protection on patient records": "Patient record overwritten on concurrent edits"}
    for w, crit, typ, exp, res, act, who, d in checks:
        qid = svc.save_check({"wbs_id": w, "criterion": crit, "check_type": typ, "expected": exp})
        if res:
            if crit in link:  # link to the already-logged defect instead of raising a duplicate
                svc.conn.execute("UPDATE quality_checks SET defect_id=? WHERE id=?", (D[link[crit]], qid))
                svc.commit()
            svc.record_check_result(qid, {"result": res, "actual": act, "inspector_id": M[who], "check_date": d})

    risks = [
        ("Scope creep from hospital management", "Scope", None, 5, 4, "Ayesha", "Mitigating",
         [("Preventive", "Formal change control board; every request needs a CR with cost/schedule impact", "Ayesha", 1),
          ("Corrective", "Re-baseline schedule and budget only through approved CRs", "Ayesha", 1)]),
        ("Critical defects delay go-live", "Quality", w_it, 4, 5, "Hassan", "Open",
         [("Preventive", "Code reviews and unit tests before integration", "Usman", 1),
          ("Corrective", "Dedicated defect-fix sprint and daily triage of critical defects", "Hassan", 1),
          ("Corrective", "Phased go-live (2 hospitals first)", "Ayesha", 1)]),
        ("Budget overrun due to change requests and rework", "Cost", None, 4, 4, "Ayesha", "Open",
         [("Preventive", "Weekly EVM review with CPI/SPI thresholds", "Ayesha", 1),
          ("Corrective", "Use management reserve; descope 'Could' requirements", "Ayesha", 1)]),
        ("AI diagnosis gives inaccurate suggestions (liability)", "Technical", None, 3, 5, "Hamza", "Open",
         [("Preventive", "Label output as preliminary; doctor must confirm", "Hamza", 1),
          ("Corrective", "Disable module via feature flag if accuracy < 85%", "Hamza", 1)]),
        ("Poor internet at hospital sites affects consultations", "External", w_con, 4, 3, "Usman", "Open",
         [("Preventive", "Adaptive bitrate and audio-only fallback", "Usman", 1),
          ("Corrective", "Switch to phone consultation and reschedule", "Ayesha", 1)]),
        ("Patient data privacy breach", "Security", w_rec, 2, 5, "Zainab", "Open",
         [("Preventive", "Encryption at rest, role-based access, audit logging", "Zainab", 1),
          ("Corrective", "Incident response plan and breach notification", "Ayesha", 1)]),
        ("Integration issues with lab equipment exports", "Technical", w_lab, 3, 3, "Hamza", "Mitigating",
         [("Preventive", "Agree on HL7/CSV export format early", "Hamza", 1),
          ("Corrective", "Manual upload fallback for lab staff", "Fatima", 1)]),
        ("Key backend developer unavailable", "Resource", None, 2, 4, "Ayesha", "Open",
         [("Preventive", "Pair programming and documentation of modules", "Usman", 1),
          ("Corrective", "Hire a contract developer", "Ayesha", 0)]),
    ]
    for title, cat, w, l, i, owner, st, measures in risks:
        rid = svc.save_risk({"title": title, "category": cat, "wbs_id": w, "likelihood": l, "impact": i,
                             "owner_id": M[owner], "status": st, "description": title})
        for typ, act, who, feas in measures:
            svc.save_countermeasure({"risk_id": rid, "action_type": typ, "action": act,
                                     "owner_id": M[who], "feasible": feas})

    for section, text in svc.generate_plan().items():
        svc.save_plan_section(section, text)
    svc.log("Sample data loaded", "Smart Healthcare case study")
    svc.commit()
