"""Business/service layer: validation, CRUD, integration rules and analytics.

Every write goes through this layer, so the GUI and the tests share exactly the
same rules (scope control, dependency integrity, change control, closure checks).
"""
import html
import sqlite3
from datetime import datetime, timedelta

from . import calculations as calc

PRIORITIES = ("Must", "Should", "Could", "Won't")
REQ_STATUSES = ("Proposed", "Approved", "Rejected")
WBS_TYPES = ("Project", "Deliverable", "Work Package")
SEVERITIES = ("Critical", "High", "Medium", "Low")
DEFECT_STATUSES = ("Open", "In Progress", "Resolved", "Closed")
CHECK_TYPES = ("Inspection", "Test")
CHECK_RESULTS = ("Pending", "Pass", "Fail")
RISK_STATUSES = ("Open", "Mitigating", "Closed")
RISK_CATEGORIES = ("Scope", "Schedule", "Cost", "Quality", "Technical", "Resource", "Security", "External")
PROJECT_STATUSES = ("Initiated", "Planning", "Executing", "Monitoring & Control", "Closed")
PLAN_SECTIONS = ("Scope Management", "Schedule Management", "Cost Management",
                 "Quality Management", "Risk Management", "Communication")


class ValidationError(Exception):
    """User-facing validation error."""


# --------------------------------------------------------------------------- validators
def _text(data, key, label, required=True, max_len=2000):
    v = data.get(key)
    v = "" if v is None else str(v).strip()
    if required and not v:
        raise ValidationError(f"{label} is required.")
    if len(v) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters.")
    return v


def _date(value, label, required=True):
    if value is None or str(value).strip() == "":
        if required:
            raise ValidationError(f"{label} is required (format YYYY-MM-DD).")
        return None
    try:
        return calc.parse_date(value).isoformat()
    except (ValueError, TypeError):
        raise ValidationError(f"{label} '{value}' is not a valid date (use YYYY-MM-DD).")


def _number(value, label, minimum=None, maximum=None, integer=False, required=True):
    if value is None or str(value).strip() == "":
        if required:
            raise ValidationError(f"{label} is required.")
        return None
    try:
        s = str(value).replace(",", "").strip()
        n = int(s) if integer else float(s)
    except ValueError:
        raise ValidationError(f"{label} must be a{'n integer' if integer else ' number'}.")
    if minimum is not None and n < minimum:
        raise ValidationError(f"{label} must be at least {minimum}.")
    if maximum is not None and n > maximum:
        raise ValidationError(f"{label} must be at most {maximum}.")
    return n


def _choice(value, label, options):
    if value not in options:
        raise ValidationError(f"{label} must be one of: {', '.join(options)}.")
    return value


def _opt_id(value):
    if value in (None, "", 0, "0"):
        return None
    return int(value)


def money(v):
    return f"PKR {v:,.0f}"


class ProjectService:
    def __init__(self, conn):
        self.conn = conn

    # ------------------------------------------------------------------ helpers
    def q(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return dict(r) if r else None

    def _exec(self, sql, params=()):
        try:
            cur = self.conn.execute(sql, params)
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            msg = str(e)
            if "FOREIGN KEY" in msg:
                raise ValidationError("Operation blocked: this record is referenced by other records "
                                      "(tasks, defects, risks, milestones...). Remove those links first.")
            if "UNIQUE" in msg:
                raise ValidationError(f"Duplicate value: {msg.split(':')[-1].strip()} must be unique.")
            raise ValidationError(f"Database constraint failed: {msg}")
        return cur

    def commit(self):
        self.conn.commit()

    def log(self, action, details=""):
        self.conn.execute("INSERT INTO audit_log(ts, action, details) VALUES (?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d %H:%M"), action, details))

    def _next_code(self, table, prefix, width=2):
        rows = self.q(f"SELECT code FROM {table} WHERE code LIKE ?", (prefix + "%",))
        nums = [int(r["code"][len(prefix):]) for r in rows if r["code"][len(prefix):].isdigit()]
        return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"

    def _require(self, row, what):
        if not row:
            raise ValidationError(f"{what} not found.")
        return row

    def _check_open(self):
        p = self.get_project()
        if p and p["status"] == "Closed":
            raise ValidationError("The project is closed; records are read-only.")

    # ================================================================== MODULE 1
    # Project initiation, charter, plan, milestones, closure
    def get_project(self):
        return self.one("SELECT * FROM project WHERE id = 1")

    def save_charter(self, data):
        name = _text(data, "name", "Project name", max_len=200)
        objectives = _text(data, "objectives", "Objectives")
        stakeholders = _text(data, "stakeholders", "Stakeholders")
        scope_in = _text(data, "scope_in", "In-scope boundary")
        scope_out = _text(data, "scope_out", "Out-of-scope boundary", required=False)
        budget = _number(data.get("approved_budget"), "Approved budget", minimum=1)
        start = _date(data.get("start_date"), "Start date")
        deadline = _date(data.get("deadline"), "Deadline")
        if deadline <= start:
            raise ValidationError("Deadline must be after the start date.")
        client = _text(data, "client", "Client", required=False)
        sponsor = _text(data, "sponsor", "Sponsor", required=False)
        manager = _text(data, "manager", "Project manager", required=False)
        status = data.get("status") or "Initiated"
        _choice(status, "Status", PROJECT_STATUSES)
        existing = self.get_project()
        if existing:
            if existing["status"] == "Closed" or status == "Closed":
                if existing["status"] != status:
                    raise ValidationError("Use 'Close Project' to close the project (closure is final).")
            self._exec("""UPDATE project SET name=?, client=?, sponsor=?, manager=?, objectives=?,
                          stakeholders=?, scope_in=?, scope_out=?, approved_budget=?, start_date=?,
                          deadline=?, status=? WHERE id=1""",
                       (name, client, sponsor, manager, objectives, stakeholders, scope_in, scope_out,
                        budget, start, deadline, status))
            self.log("Charter updated", name)
        else:
            if status == "Closed":
                raise ValidationError("A new project cannot start as Closed.")
            self._exec("""INSERT INTO project(id, name, client, sponsor, manager, objectives, stakeholders,
                          scope_in, scope_out, approved_budget, baseline_budget, start_date, deadline,
                          baseline_deadline, status, status_date)
                          VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (name, client, sponsor, manager, objectives, stakeholders, scope_in, scope_out,
                        budget, budget, start, deadline, deadline, status, start))
            self.log("Charter created", name)
        self.commit()

    def save_settings(self, status_date, cpi_warn, cpi_crit, spi_warn, spi_crit):
        p = self._require(self.get_project(), "Project")
        sd = _date(status_date, "Status date")
        if sd < p["start_date"]:
            raise ValidationError("Status date cannot be before the project start date.")
        vals = [_number(v, n, minimum=0.1, maximum=1.5) for v, n in
                ((cpi_warn, "CPI warning"), (cpi_crit, "CPI critical"),
                 (spi_warn, "SPI warning"), (spi_crit, "SPI critical"))]
        if vals[1] > vals[0] or vals[3] > vals[2]:
            raise ValidationError("Critical threshold must be lower than or equal to the warning threshold.")
        latest = self.one("""SELECT MAX(d) AS d FROM (SELECT actual_start d FROM tasks UNION ALL
                             SELECT actual_end FROM tasks UNION ALL SELECT exp_date FROM expenses)""")
        if latest and latest["d"] and sd < latest["d"]:
            raise ValidationError(f"Status date cannot be earlier than recorded actuals ({latest['d']}).")
        self._exec("UPDATE project SET status_date=?, cpi_warn=?, cpi_crit=?, spi_warn=?, spi_crit=? WHERE id=1",
                   (sd, *vals))
        self.commit()

    # --- management plan
    def get_plan(self):
        rows = {r["section"]: r for r in self.q("SELECT * FROM plan_sections")}
        return {s: rows.get(s, {"content": "", "updated": None}) for s in PLAN_SECTIONS}

    def save_plan_section(self, section, content):
        _choice(section, "Plan section", PLAN_SECTIONS)
        self._exec("""INSERT INTO plan_sections(section, content, updated) VALUES (?,?,?)
                      ON CONFLICT(section) DO UPDATE SET content=excluded.content, updated=excluded.updated""",
                   (section, content.strip(), datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.commit()

    def generate_plan(self):
        """Build a project management plan from live data (scope, schedule, cost, quality...)."""
        p = self._require(self.get_project(), "Project")
        sch = self.schedule_analysis()
        ev = self.evm_analysis()
        reqs = self.q("SELECT code, title, priority FROM requirements WHERE status='Approved' ORDER BY code")
        wps = self.q("SELECT code, name FROM wbs WHERE node_type='Work Package' ORDER BY code")
        crit = [t["code"] for t in sch["tasks"] if t["critical"]]
        ms = sch["milestones"]
        q_total = self.one("SELECT COUNT(*) n FROM quality_checks")["n"]
        plan = {
            "Scope Management":
                f"In scope: {p['scope_in']}\nOut of scope: {p['scope_out'] or '-'}\n\n"
                f"Approved scope baseline ({len(reqs)} requirements):\n" +
                "\n".join(f"  {r['code']} [{r['priority']}] {r['title']}" for r in reqs) +
                f"\n\nWBS work packages: {len(wps)}\n" +
                "\n".join(f"  {w['code']} {w['name']}" for w in wps) +
                "\n\nChange control: every new requirement must enter through a change request; "
                "only approved requirements may be linked to WBS work packages.",
            "Schedule Management":
                f"Start: {p['start_date']}   Approved deadline: {p['deadline']} "
                f"(original {p['baseline_deadline']})\n"
                f"Planned finish (CPM): {calc.fmt(sch['planned_finish'])}\n"
                f"Activities: {len(sch['tasks'])}, critical path: {' -> '.join(crit)}\n"
                "Milestones:\n" + "\n".join(f"  {m['name']}: planned {m['planned']}" for m in ms) +
                "\n\nMethod: finish-to-start dependencies, forward/backward pass, weekly progress "
                "updates against the status date.",
            "Cost Management":
                f"Approved budget: {money(p['approved_budget'])} (original {money(p['baseline_budget'])})\n"
                f"Planned cost baseline (BAC): {money(ev['BAC'])}\n"
                f"Management reserve: {money(p['approved_budget'] - ev['BAC'])}\n"
                f"EVM thresholds: CPI warning < {p['cpi_warn']}, critical < {p['cpi_crit']}; "
                f"SPI warning < {p['spi_warn']}, critical < {p['spi_crit']}.\n"
                "Actual costs are recorded per activity as expenses; PV, EV, AC, CPI and SPI are "
                "computed automatically at each status date.",
            "Quality Management":
                f"Quality checklist items: {q_total}. Every deliverable is inspected or tested before "
                "acceptance. Failed checks raise defects.\nDefect severity: Critical / High / Medium / Low. "
                "Release criteria: zero open Critical defects, all checklist items Pass.",
            "Risk Management":
                "Risks are scored Likelihood x Impact (1-5 each) in the prioritization matrix. "
                "Score >= 15 High, 8-14 Medium, < 8 Low. High risks require preventive and corrective "
                "countermeasures in the PDPC.",
            "Communication":
                f"Sponsor: {p['sponsor'] or '-'}; Project manager: {p['manager'] or '-'}.\n"
                f"Stakeholders: {p['stakeholders']}\nWeekly status report generated from the dashboard.",
        }
        return plan

    # --- milestones
    def list_milestones(self):
        return self.q("""SELECT m.*, t.code AS task_code, t.name AS task_name, tm.name AS owner
                         FROM milestones m JOIN tasks t ON t.id = m.task_id
                         LEFT JOIN team_members tm ON tm.id = m.owner_id ORDER BY m.id""")

    def save_milestone(self, data, mid=None):
        self._check_open()
        name = _text(data, "name", "Milestone name", max_len=200)
        task_id = _opt_id(data.get("task_id"))
        if not task_id:
            raise ValidationError("A milestone must be linked to the activity whose completion marks it.")
        self._require(self.one("SELECT id FROM tasks WHERE id=?", (task_id,)), "Activity")
        owner = _opt_id(data.get("owner_id"))
        desc = _text(data, "description", "Description", required=False)
        if mid:
            self._exec("UPDATE milestones SET name=?, task_id=?, owner_id=?, description=? WHERE id=?",
                       (name, task_id, owner, desc, mid))
        else:
            self._exec("INSERT INTO milestones(name, task_id, owner_id, description) VALUES (?,?,?,?)",
                       (name, task_id, owner, desc))
        self.commit()

    def delete_milestone(self, mid):
        self._check_open()
        self._exec("DELETE FROM milestones WHERE id=?", (mid,))
        self.commit()

    # --- closure
    def closure_blockers(self):
        blockers = []
        n = self.one("SELECT COUNT(*) n FROM tasks WHERE percent < 100")["n"]
        if n:
            blockers.append(f"{n} activities are not 100% complete.")
        n = self.one("SELECT COUNT(*) n FROM defects WHERE severity='Critical' AND status NOT IN ('Resolved','Closed')")["n"]
        if n:
            blockers.append(f"{n} critical defects are unresolved.")
        n = self.one("SELECT COUNT(*) n FROM change_requests WHERE status='Pending'")["n"]
        if n:
            blockers.append(f"{n} change requests are still pending a decision.")
        n = self.one("SELECT COUNT(*) n FROM quality_checks WHERE result <> 'Pass'")["n"]
        if n:
            blockers.append(f"{n} quality checklist items are not passed.")
        return blockers

    def close_project(self, data):
        p = self._require(self.get_project(), "Project")
        if p["status"] == "Closed":
            raise ValidationError("Project is already closed.")
        blockers = self.closure_blockers()
        if blockers:
            raise ValidationError("Project cannot be closed:\n- " + "\n- ".join(blockers))
        closed = _date(data.get("closed_date"), "Closure date")
        accepted = _text(data, "accepted_by", "Accepted by")
        lessons = _text(data, "lessons", "Lessons learned")
        notes = _text(data, "notes", "Notes", required=False)
        final_cost = self.one("SELECT COALESCE(SUM(amount),0) s FROM expenses")["s"]
        self._exec("INSERT INTO closure(id, closed_date, final_cost, accepted_by, lessons, notes) VALUES (1,?,?,?,?,?)",
                   (closed, final_cost, accepted, lessons, notes))
        self._exec("UPDATE project SET status='Closed' WHERE id=1")
        self.log("Project closed", f"Accepted by {accepted}; final cost {money(final_cost)}")
        self.commit()

    def get_closure(self):
        return self.one("SELECT * FROM closure WHERE id=1")

    # ================================================================== TEAM
    def list_members(self):
        return self.q("""SELECT tm.*, (SELECT COUNT(*) FROM tasks t WHERE t.assignee_id = tm.id) AS task_count,
                         (SELECT GROUP_CONCAT(code, ', ') FROM tasks t WHERE t.assignee_id = tm.id) AS task_codes
                         FROM team_members tm ORDER BY tm.id""")

    def save_member(self, data, mid=None):
        self._check_open()
        name = _text(data, "name", "Name", max_len=100)
        role = _text(data, "role", "Role", max_len=100)
        resp = _text(data, "responsibility", "Responsibility", required=False)
        rate = _number(data.get("daily_rate"), "Daily rate", minimum=0)
        email = _text(data, "email", "Email", required=False)
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            raise ValidationError("Email address is not valid.")
        if mid:
            self._exec("UPDATE team_members SET name=?, role=?, responsibility=?, daily_rate=?, email=? WHERE id=?",
                       (name, role, resp, rate, email, mid))
        else:
            self._exec("INSERT INTO team_members(name, role, responsibility, daily_rate, email) VALUES (?,?,?,?,?)",
                       (name, role, resp, rate, email))
        self.commit()

    def delete_member(self, mid):
        self._check_open()
        refs = self.one("""SELECT (SELECT COUNT(*) FROM tasks WHERE assignee_id=?) +
                                  (SELECT COUNT(*) FROM defects WHERE assigned_id=?) +
                                  (SELECT COUNT(*) FROM risks WHERE owner_id=?) AS n""", (mid, mid, mid))["n"]
        if refs:
            raise ValidationError("This member is assigned to activities, defects or risks. Reassign them first.")
        self._exec("DELETE FROM team_members WHERE id=?", (mid,))
        self.commit()

    # ================================================================== MODULE 2
    # Requirements, WBS, change requests
    def list_requirements(self):
        return self.q("""SELECT r.*, cr.code AS cr_code,
                         (SELECT GROUP_CONCAT(code, ', ') FROM wbs w WHERE w.requirement_id = r.id) AS wbs_codes
                         FROM requirements r LEFT JOIN change_requests cr ON cr.id = r.cr_id
                         ORDER BY CASE r.priority WHEN 'Must' THEN 1 WHEN 'Should' THEN 2
                                  WHEN 'Could' THEN 3 ELSE 4 END, r.code""")

    def save_requirement(self, data, rid=None):
        self._check_open()
        title = _text(data, "title", "Title", max_len=200)
        desc = _text(data, "description", "Description", required=False)
        prio = _choice(data.get("priority"), "Priority", PRIORITIES)
        if rid:
            r = self._require(self.one("SELECT * FROM requirements WHERE id=?", (rid,)), "Requirement")
            self._exec("UPDATE requirements SET title=?, description=?, priority=? WHERE id=?",
                       (title, desc, prio, rid))
            self.log("Requirement updated", r["code"])
        else:
            code = self._next_code("requirements", "R")
            self._exec("""INSERT INTO requirements(code, title, description, priority, status, source, created)
                          VALUES (?,?,?,?, 'Proposed', 'Original', ?)""",
                       (code, title, desc, prio, self.get_project()["status_date"]))
            self.log("Requirement added", code)
        self.commit()

    def set_requirement_status(self, rid, status):
        self._check_open()
        _choice(status, "Status", REQ_STATUSES)
        r = self._require(self.one("SELECT * FROM requirements WHERE id=?", (rid,)), "Requirement")
        if r["source"] == "Change Request" and r["cr_id"]:
            raise ValidationError(f"{r['code']} came from a change request; approve or reject the change "
                                  "request instead (change control).")
        if status != "Approved":
            linked = self.one("SELECT COUNT(*) n FROM wbs WHERE requirement_id=?", (rid,))["n"]
            if linked:
                raise ValidationError(f"{r['code']} is part of the approved scope baseline and linked to "
                                      f"{linked} WBS element(s). Raise a change request to remove it.")
        self._exec("UPDATE requirements SET status=? WHERE id=?", (status, rid))
        self.log(f"Requirement {status.lower()}", r["code"])
        self.commit()

    def delete_requirement(self, rid):
        self._check_open()
        r = self._require(self.one("SELECT * FROM requirements WHERE id=?", (rid,)), "Requirement")
        if r["cr_id"]:
            raise ValidationError("Requirements created by a change request are managed through that CR.")
        if r["status"] == "Approved":
            raise ValidationError("Approved requirements are part of the baseline and cannot be deleted.")
        self._exec("DELETE FROM requirements WHERE id=?", (rid,))
        self.commit()

    # --- WBS
    def list_wbs(self):
        rows = self.q("""SELECT w.*, r.code AS req_code, r.status AS req_status,
                         (SELECT COUNT(*) FROM tasks t WHERE t.wbs_id = w.id) AS task_count,
                         (SELECT COALESCE(SUM(budget),0) FROM tasks t WHERE t.wbs_id = w.id) AS budget
                         FROM wbs w LEFT JOIN requirements r ON r.id = w.requirement_id""")
        return sorted(rows, key=lambda w: [int(x) for x in w["code"].split(".")])

    def wbs_rollup(self):
        """Budget rolled up through the hierarchy."""
        rows = self.list_wbs()
        by_id = {w["id"]: w for w in rows}
        for w in rows:
            w["rollup"] = 0.0
        for w in sorted(rows, key=lambda x: -len(x["code"].split("."))):
            w["rollup"] += w["budget"]
            if w["parent_id"] and w["parent_id"] in by_id:
                by_id[w["parent_id"]]["rollup"] += w["rollup"]
        return rows

    def _check_requirement_in_scope(self, req_id):
        if req_id:
            r = self._require(self.one("SELECT * FROM requirements WHERE id=?", (req_id,)), "Requirement")
            if r["status"] != "Approved":
                raise ValidationError(f"{r['code']} is '{r['status']}'. Only approved requirements can be "
                                      "included in the approved scope (WBS).")

    def save_wbs(self, data, wid=None):
        self._check_open()
        name = _text(data, "name", "Name", max_len=200)
        ntype = _choice(data.get("node_type"), "Type", WBS_TYPES)
        parent = _opt_id(data.get("parent_id"))
        req = _opt_id(data.get("requirement_id"))
        desc = _text(data, "description", "Description", required=False)
        self._check_requirement_in_scope(req)
        if ntype == "Project":
            existing = self.one("SELECT id FROM wbs WHERE node_type='Project'")
            if existing and existing["id"] != wid:
                raise ValidationError("Only one Project-level (root) WBS element is allowed.")
            parent = None
        else:
            if not parent:
                raise ValidationError("Deliverables and work packages need a parent WBS element.")
            prow = self._require(self.one("SELECT * FROM wbs WHERE id=?", (parent,)), "Parent WBS element")
            if prow["node_type"] == "Work Package":
                raise ValidationError("A work package is the lowest WBS level and cannot have children.")
            if wid and (parent == wid or parent in self._wbs_descendants(wid)):
                raise ValidationError("A WBS element cannot be moved under itself or its descendants.")
        if wid:
            cur = self._require(self.one("SELECT * FROM wbs WHERE id=?", (wid,)), "WBS element")
            if ntype != "Work Package" and self.one("SELECT COUNT(*) n FROM tasks WHERE wbs_id=?", (wid,))["n"]:
                raise ValidationError("This element has activities; it must remain a Work Package.")
            if ntype == "Work Package" and self.one("SELECT COUNT(*) n FROM wbs WHERE parent_id=?", (wid,))["n"]:
                raise ValidationError("This element has children and cannot become a Work Package.")
            code = cur["code"] if cur["parent_id"] == parent else self._next_wbs_code(parent)
            self._exec("UPDATE wbs SET code=?, name=?, parent_id=?, node_type=?, requirement_id=?, description=? WHERE id=?",
                       (code, name, parent, ntype, req, desc, wid))
        else:
            code = self._next_wbs_code(parent)
            self._exec("INSERT INTO wbs(code, name, parent_id, node_type, requirement_id, description) VALUES (?,?,?,?,?,?)",
                       (code, name, parent, ntype, req, desc))
        self.commit()
        return code

    def _next_wbs_code(self, parent_id):
        if not parent_id:
            return "1"
        pcode = self.one("SELECT code FROM wbs WHERE id=?", (parent_id,))["code"]
        kids = self.q("SELECT code FROM wbs WHERE parent_id=?", (parent_id,))
        n = max([int(k["code"].split(".")[-1]) for k in kids], default=0) + 1
        return f"{pcode}.{n}"

    def _wbs_descendants(self, wid):
        out, stack = set(), [wid]
        while stack:
            for r in self.q("SELECT id FROM wbs WHERE parent_id=?", (stack.pop(),)):
                out.add(r["id"])
                stack.append(r["id"])
        return out

    def _wbs_in_scope(self, wid):
        """A WBS element is in approved scope if it and all ancestors link only approved requirements."""
        cur = wid
        while cur:
            w = self.one("""SELECT w.parent_id, w.code, r.status, r.code AS rc FROM wbs w
                            LEFT JOIN requirements r ON r.id = w.requirement_id WHERE w.id=?""", (cur,))
            if w is None:
                return False, "WBS element not found"
            if w["status"] and w["status"] != "Approved":
                return False, f"WBS {w['code']} is linked to {w['rc']} which is {w['status']}"
            cur = w["parent_id"]
        return True, ""

    def delete_wbs(self, wid):
        self._check_open()
        if self.one("SELECT COUNT(*) n FROM wbs WHERE parent_id=?", (wid,))["n"]:
            raise ValidationError("Delete the child elements first.")
        if self.one("SELECT COUNT(*) n FROM tasks WHERE wbs_id=?", (wid,))["n"]:
            raise ValidationError("This work package has activities. Delete or move them first.")
        self._exec("DELETE FROM wbs WHERE id=?", (wid,))
        self.commit()

    # --- change requests
    def list_change_requests(self):
        return self.q("""SELECT cr.*, a.code AS after_code, b.code AS before_code, tm.name AS assignee,
                         r.code AS req_code, (SELECT code FROM tasks WHERE cr_id = cr.id) AS task_code
                         FROM change_requests cr
                         LEFT JOIN tasks a ON a.id = cr.after_task_id
                         LEFT JOIN tasks b ON b.id = cr.before_task_id
                         LEFT JOIN team_members tm ON tm.id = cr.assignee_id
                         LEFT JOIN requirements r ON r.cr_id = cr.id
                         ORDER BY cr.code""")

    def save_change_request(self, data, cid=None):
        self._check_open()
        title = _text(data, "title", "Title", max_len=200)
        desc = _text(data, "description", "Description", required=False)
        just = _text(data, "justification", "Justification")
        by = _text(data, "requested_by", "Requested by")
        rdate = _date(data.get("request_date"), "Request date")
        prio = _choice(data.get("priority"), "Priority", PRIORITIES)
        cost = _number(data.get("cost_impact"), "Cost impact (PKR)", minimum=0)
        sched = _number(data.get("schedule_impact"), "Schedule impact (days)", minimum=0, maximum=365, integer=True)
        after = _opt_id(data.get("after_task_id"))
        before = _opt_id(data.get("before_task_id"))
        assignee = _opt_id(data.get("assignee_id"))
        if sched > 0 and not after:
            raise ValidationError("Select the activity the new work follows (predecessor) so the schedule "
                                  "impact can be applied.")
        if after and before and after == before:
            raise ValidationError("Predecessor and successor activities must be different.")
        if before:
            b = self._require(self.one("SELECT * FROM tasks WHERE id=?", (before,)), "Successor activity")
            if b["actual_start"]:
                raise ValidationError(f"{b['code']} has already started; new work cannot be inserted before it.")
            preds = self._preds()
            if after and before in calc.upstream(after, preds) | {after}:
                raise ValidationError("The successor activity is upstream of the predecessor - this would "
                                      "create a dependency cycle.")
        if cid:
            cr = self._require(self.one("SELECT * FROM change_requests WHERE id=?", (cid,)), "Change request")
            if cr["status"] != "Pending":
                raise ValidationError("Only pending change requests can be edited.")
            self._exec("""UPDATE change_requests SET title=?, description=?, justification=?, requested_by=?,
                          request_date=?, priority=?, cost_impact=?, schedule_impact=?, after_task_id=?,
                          before_task_id=?, assignee_id=? WHERE id=?""",
                       (title, desc, just, by, rdate, prio, cost, sched, after, before, assignee, cid))
            self._exec("UPDATE requirements SET title=?, description=?, priority=? WHERE cr_id=?",
                       (title, desc, prio, cid))
            code = cr["code"]
        else:
            code = self._next_code("change_requests", "CR-", 3)
            cur = self._exec("""INSERT INTO change_requests(code, title, description, justification, requested_by,
                                request_date, priority, cost_impact, schedule_impact, after_task_id,
                                before_task_id, assignee_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                             (code, title, desc, just, by, rdate, prio, cost, sched, after, before, assignee))
            new_id = cur.lastrowid
            rcode = self._next_code("requirements", "R")
            self._exec("""INSERT INTO requirements(code, title, description, priority, status, source, cr_id, created)
                          VALUES (?,?,?,?, 'Proposed', 'Change Request', ?, ?)""",
                       (rcode, title, desc, prio, new_id, rdate))
            self.log("Change request raised", f"{code}: {title}")
        self.commit()
        return code

    def delete_change_request(self, cid):
        self._check_open()
        cr = self._require(self.one("SELECT * FROM change_requests WHERE id=?", (cid,)), "Change request")
        if cr["status"] == "Approved":
            raise ValidationError("Approved change requests are part of the baseline history and cannot be deleted.")
        self._exec("DELETE FROM requirements WHERE cr_id=?", (cid,))
        self._exec("DELETE FROM change_requests WHERE id=?", (cid,))
        self.commit()

    def preview_change_impact(self, cid):
        """What-if analysis: scope, schedule and budget before vs after approval."""
        cr = self._require(self.one("SELECT * FROM change_requests WHERE id=?", (cid,)), "Change request")
        p = self.get_project()
        before = self.schedule_analysis()
        ev = self.evm_analysis()
        tasks, preds = self._task_graph()
        if cr["schedule_impact"] > 0:
            nid = -1
            tasks[nid] = {"duration": cr["schedule_impact"], "actual_start": None, "actual_end": None,
                          "percent": 0}
            preds[nid] = {cr["after_task_id"]} if cr["after_task_id"] else set()
            if cr["before_task_id"]:
                preds[cr["before_task_id"]] = set(preds.get(cr["before_task_id"], set())) | {nid}
        planned, pf = calc.compute_planned_schedule({t: v["duration"] for t, v in tasks.items()}, preds,
                                                    p["start_date"])
        fc = calc.compute_forecast(tasks, preds, planned, p["status_date"])
        new_deadline = calc.parse_date(p["deadline"]) + timedelta(days=cr["schedule_impact"])
        n_req = self.one("SELECT COUNT(*) n FROM requirements WHERE status='Approved'")["n"]
        return {
            "cr": cr,
            "scope": (n_req, n_req + 1),
            "budget": (p["approved_budget"], p["approved_budget"] + cr["cost_impact"]),
            "bac": (ev["BAC"], ev["BAC"] + cr["cost_impact"]),
            "deadline": (p["deadline"], new_deadline.isoformat()),
            "planned_finish": (calc.fmt(before["planned_finish"]), calc.fmt(pf)),
            "forecast_finish": (calc.fmt(before["forecast_finish"]), calc.fmt(max(f["fe"] for f in fc.values()))),
        }

    def approve_change_request(self, cid, decided_by, notes="", decision_date=None):
        """Change control: approval updates scope (requirement + WBS + activity),
        schedule (dependency insertion + deadline) and budget (approved budget + BAC)."""
        self._check_open()
        cr = self._require(self.one("SELECT * FROM change_requests WHERE id=?", (cid,)), "Change request")
        if cr["status"] != "Pending":
            raise ValidationError(f"{cr['code']} is already {cr['status']}.")
        decided_by = _text({"v": decided_by}, "v", "Decided by")
        p = self.get_project()
        ddate = _date(decision_date or p["status_date"], "Decision date")
        if ddate < cr["request_date"]:
            raise ValidationError("Decision date cannot be before the request date.")
        if cr["before_task_id"]:
            b = self.one("SELECT code, actual_start FROM tasks WHERE id=?", (cr["before_task_id"],))
            if b["actual_start"]:
                raise ValidationError(f"{b['code']} has already started; the new work can no longer be inserted "
                                      "before it. Edit the change request first.")
        try:
            # requirement -> approved scope
            req = self.one("SELECT * FROM requirements WHERE cr_id=?", (cid,))
            self.conn.execute("UPDATE requirements SET status='Approved' WHERE cr_id=?", (cid,))
            # WBS deliverable + work package under the root
            root = self.one("SELECT id FROM wbs WHERE node_type='Project'")
            if not root:
                raise ValidationError("Create the root WBS element before approving change requests.")
            dcode = self._next_wbs_code(root["id"])
            cur = self.conn.execute("""INSERT INTO wbs(code, name, parent_id, node_type, requirement_id, description)
                                       VALUES (?,?,?, 'Deliverable', ?, ?)""",
                                    (dcode, cr["title"], root["id"], req["id"], f"Added by {cr['code']}"))
            deliverable = cur.lastrowid
            task_code = None
            if cr["schedule_impact"] > 0:
                cur = self.conn.execute("""INSERT INTO wbs(code, name, parent_id, node_type, requirement_id, description)
                                           VALUES (?,?,?, 'Work Package', ?, ?)""",
                                        (dcode + ".1", f"{cr['title']} - development", deliverable, req["id"],
                                         f"Added by {cr['code']}"))
                wp = cur.lastrowid
                task_code = self._next_code("tasks", "T")
                cur = self.conn.execute("""INSERT INTO tasks(code, name, wbs_id, assignee_id, duration, budget, cr_id, notes)
                                           VALUES (?,?,?,?,?,?,?,?)""",
                                        (task_code, cr["title"], wp, cr["assignee_id"], cr["schedule_impact"],
                                         cr["cost_impact"], cid, f"Created by approval of {cr['code']}"))
                tid = cur.lastrowid
                if cr["after_task_id"]:
                    self.conn.execute("INSERT INTO dependencies(task_id, pred_id) VALUES (?,?)",
                                      (tid, cr["after_task_id"]))
                if cr["before_task_id"]:
                    self.conn.execute("INSERT OR IGNORE INTO dependencies(task_id, pred_id) VALUES (?,?)",
                                      (cr["before_task_id"], tid))
                tasks, preds = self._task_graph()
                calc.topological_order(tasks.keys(), preds)  # raises CycleError -> rollback
            # baseline update
            new_budget = p["approved_budget"] + cr["cost_impact"]
            new_deadline = (calc.parse_date(p["deadline"]) + timedelta(days=cr["schedule_impact"])).isoformat()
            self.conn.execute("UPDATE project SET approved_budget=?, deadline=? WHERE id=1", (new_budget, new_deadline))
            self.conn.execute("""INSERT INTO baseline_history(change_date, cr_id, old_budget, new_budget,
                                 old_deadline, new_deadline, note) VALUES (?,?,?,?,?,?,?)""",
                              (ddate, cid, p["approved_budget"], new_budget, p["deadline"], new_deadline,
                               f"{cr['code']} approved: +{money(cr['cost_impact'])}, +{cr['schedule_impact']} days"))
            self.conn.execute("""UPDATE change_requests SET status='Approved', decision_date=?, decided_by=?,
                                 decision_notes=? WHERE id=?""", (ddate, decided_by, notes, cid))
            self.log("Change request approved",
                     f"{cr['code']}: budget {money(p['approved_budget'])} -> {money(new_budget)}, "
                     f"deadline {p['deadline']} -> {new_deadline}, activity {task_code or '-'}")
            self.conn.commit()
        except calc.CycleError as e:
            self.conn.rollback()
            raise ValidationError(f"Approval rolled back: {e}")
        except ValidationError:
            self.conn.rollback()
            raise
        except sqlite3.Error as e:
            self.conn.rollback()
            raise ValidationError(f"Approval rolled back (database error): {e}")
        return task_code

    def reject_change_request(self, cid, decided_by, notes="", decision_date=None):
        self._check_open()
        cr = self._require(self.one("SELECT * FROM change_requests WHERE id=?", (cid,)), "Change request")
        if cr["status"] != "Pending":
            raise ValidationError(f"{cr['code']} is already {cr['status']}.")
        decided_by = _text({"v": decided_by}, "v", "Decided by")
        ddate = _date(decision_date or self.get_project()["status_date"], "Decision date")
        self._exec("UPDATE requirements SET status='Rejected' WHERE cr_id=?", (cid,))
        self._exec("UPDATE change_requests SET status='Rejected', decision_date=?, decided_by=?, decision_notes=? WHERE id=?",
                   (ddate, decided_by, notes, cid))
        self.log("Change request rejected", cr["code"])
        self.commit()

    def baseline_history(self):
        return self.q("""SELECT b.*, cr.code AS cr_code FROM baseline_history b
                         LEFT JOIN change_requests cr ON cr.id = b.cr_id ORDER BY b.id""")

    # ================================================================== MODULE 3
    # Activities, dependencies, schedule
    def list_tasks(self):
        return self.q("""SELECT t.*, w.code AS wbs_code, w.name AS wbs_name, tm.name AS assignee,
                         tm.daily_rate, cr.code AS cr_code,
                         (SELECT COALESCE(SUM(amount),0) FROM expenses e WHERE e.task_id=t.id) AS actual_cost,
                         (SELECT GROUP_CONCAT(p.code, ', ') FROM dependencies d JOIN tasks p ON p.id=d.pred_id
                          WHERE d.task_id=t.id) AS pred_codes
                         FROM tasks t JOIN wbs w ON w.id=t.wbs_id
                         LEFT JOIN team_members tm ON tm.id=t.assignee_id
                         LEFT JOIN change_requests cr ON cr.id=t.cr_id ORDER BY t.id""")

    def _preds(self):
        preds = {r["id"]: set() for r in self.q("SELECT id FROM tasks")}
        for d in self.q("SELECT task_id, pred_id FROM dependencies"):
            preds[d["task_id"]].add(d["pred_id"])
        return preds

    def _task_graph(self):
        tasks = {t["id"]: {"duration": t["duration"], "actual_start": t["actual_start"],
                           "actual_end": t["actual_end"], "percent": t["percent"]}
                 for t in self.q("SELECT * FROM tasks")}
        return tasks, self._preds()

    def estimate_cost(self, assignee_id, duration):
        """Bottom-up estimate: duration x daily rate of the assignee."""
        m = self.one("SELECT daily_rate FROM team_members WHERE id=?", (assignee_id,)) if assignee_id else None
        d = _number(duration, "Duration", minimum=1, integer=True)
        if not m:
            raise ValidationError("Select an assignee to estimate labour cost.")
        return d * m["daily_rate"]

    def save_task(self, data, tid=None):
        self._check_open()
        name = _text(data, "name", "Activity name", max_len=200)
        wbs_id = _opt_id(data.get("wbs_id"))
        if not wbs_id:
            raise ValidationError("Select the WBS work package for this activity.")
        w = self._require(self.one("SELECT * FROM wbs WHERE id=?", (wbs_id,)), "WBS element")
        if w["node_type"] != "Work Package":
            raise ValidationError("Activities can only be defined under a WBS Work Package.")
        ok, why = self._wbs_in_scope(wbs_id)
        if not ok:
            raise ValidationError(f"Activity rejected - outside approved scope: {why}.")
        assignee = _opt_id(data.get("assignee_id"))
        if assignee:
            self._require(self.one("SELECT id FROM team_members WHERE id=?", (assignee,)), "Team member")
        duration = _number(data.get("duration"), "Duration (days)", minimum=1, maximum=365, integer=True)
        budget = _number(data.get("budget"), "Estimated cost (PKR)", minimum=0)
        notes = _text(data, "notes", "Notes", required=False)
        if tid:
            t = self._require(self.one("SELECT * FROM tasks WHERE id=?", (tid,)), "Activity")
            self._exec("UPDATE tasks SET name=?, wbs_id=?, assignee_id=?, duration=?, budget=?, notes=? WHERE id=?",
                       (name, wbs_id, assignee, duration, budget, notes, tid))
            code = t["code"]
        else:
            code = self._next_code("tasks", "T")
            cur = self._exec("""INSERT INTO tasks(code, name, wbs_id, assignee_id, duration, budget, notes)
                                VALUES (?,?,?,?,?,?,?)""", (code, name, wbs_id, assignee, duration, budget, notes))
            tid = cur.lastrowid
        self.commit()
        if "pred_ids" in data:
            self.set_dependencies(tid, data["pred_ids"])
        return tid

    def set_dependencies(self, tid, pred_ids):
        self._check_open()
        pred_ids = {int(p) for p in pred_ids}
        if tid in pred_ids:
            raise ValidationError("An activity cannot depend on itself.")
        preds = self._preds()
        unknown = pred_ids - set(preds)
        if unknown:
            raise ValidationError(f"Unknown predecessor ids: {sorted(unknown)}")
        if calc.would_create_cycle(tid, pred_ids, preds):
            raise ValidationError("These dependencies would create a cycle (circular dependency).")
        t = self.one("SELECT * FROM tasks WHERE id=?", (tid,))
        if t["actual_start"]:
            for p in pred_ids:
                pr = self.one("SELECT code, actual_end FROM tasks WHERE id=?", (p,))
                if not pr["actual_end"] or pr["actual_end"] >= t["actual_start"]:
                    raise ValidationError(f"{t['code']} already started on {t['actual_start']}; {pr['code']} "
                                          "did not finish before that (finish-to-start violation).")
        self._exec("DELETE FROM dependencies WHERE task_id=?", (tid,))
        for p in pred_ids:
            self._exec("INSERT INTO dependencies(task_id, pred_id) VALUES (?,?)", (tid, p))
        self.commit()

    def update_progress(self, tid, actual_start, actual_end, percent):
        self._check_open()
        t = self._require(self.one("SELECT * FROM tasks WHERE id=?", (tid,)), "Activity")
        p = self.get_project()
        a_s = _date(actual_start, "Actual start", required=False)
        a_e = _date(actual_end, "Actual finish", required=False)
        pct = _number(percent, "% complete", minimum=0, maximum=100, integer=True)
        if pct > 0 and not a_s:
            raise ValidationError("Enter the actual start date for an activity with progress > 0%.")
        if pct == 100 and not a_e:
            raise ValidationError("Enter the actual finish date for a 100% complete activity.")
        if a_e and pct != 100:
            raise ValidationError("An activity with an actual finish date must be 100% complete.")
        if a_e and not a_s:
            raise ValidationError("Actual finish requires an actual start.")
        if a_s and a_s < p["start_date"]:
            raise ValidationError("Actual start cannot be before the project start date.")
        if a_s and a_e and a_e < a_s:
            raise ValidationError("Actual finish cannot be before actual start.")
        for d, lbl in ((a_s, "Actual start"), (a_e, "Actual finish")):
            if d and d > p["status_date"]:
                raise ValidationError(f"{lbl} ({d}) cannot be after the status date ({p['status_date']}).")
        if a_s:
            for pr in self.q("""SELECT p.code, p.actual_end FROM dependencies d JOIN tasks p ON p.id=d.pred_id
                                WHERE d.task_id=?""", (tid,)):
                if not pr["actual_end"] or pr["actual_end"] >= a_s:
                    raise ValidationError(f"Predecessor {pr['code']} must finish before {t['code']} starts "
                                          "(finish-to-start dependency).")
        for s in self.q("""SELECT s.code, s.actual_start FROM dependencies d JOIN tasks s ON s.id=d.task_id
                           WHERE d.pred_id=? AND s.actual_start IS NOT NULL""", (tid,)):
            if not a_e or a_e >= s["actual_start"]:
                raise ValidationError(f"Successor {s['code']} already started on {s['actual_start']}; "
                                      f"{t['code']} must have finished before that.")
        first_exp = self.one("SELECT MIN(exp_date) d FROM expenses WHERE task_id=?", (tid,))["d"]
        if first_exp and (not a_s or first_exp < a_s):
            raise ValidationError(f"Expenses are recorded from {first_exp}; actual start must be on/before it.")
        self._exec("UPDATE tasks SET actual_start=?, actual_end=?, percent=? WHERE id=?", (a_s, a_e, pct, tid))
        self.commit()

    def delete_task(self, tid):
        self._check_open()
        t = self._require(self.one("SELECT * FROM tasks WHERE id=?", (tid,)), "Activity")
        if t["cr_id"]:
            raise ValidationError("This activity was created by an approved change request and is part of the baseline.")
        if self.one("SELECT COUNT(*) n FROM dependencies WHERE pred_id=?", (tid,))["n"]:
            raise ValidationError("Other activities depend on this one. Remove those dependencies first.")
        if self.one("SELECT COUNT(*) n FROM expenses WHERE task_id=?", (tid,))["n"]:
            raise ValidationError("This activity has recorded expenses and cannot be deleted.")
        if self.one("SELECT COUNT(*) n FROM milestones WHERE task_id=?", (tid,))["n"]:
            raise ValidationError("A milestone is linked to this activity.")
        self._exec("UPDATE defects SET task_id=NULL WHERE task_id=?", (tid,))
        self._exec("DELETE FROM tasks WHERE id=?", (tid,))
        self.commit()

    def schedule_analysis(self):
        """CPM schedule + forecast + delay impact + milestones."""
        p = self._require(self.get_project(), "Project")
        rows = self.list_tasks()
        tasks, preds = self._task_graph()
        if not tasks:
            start = calc.parse_date(p["start_date"])
            return {"tasks": [], "planned_finish": start, "forecast_finish": start,
                    "deadline": calc.parse_date(p["deadline"]), "slip": 0, "impacts": [], "milestones": [],
                    "critical_path": []}
        planned, pf = calc.compute_planned_schedule({t: v["duration"] for t, v in tasks.items()}, preds,
                                                    p["start_date"])
        fc = calc.compute_forecast(tasks, preds, planned, p["status_date"])
        by_id = {r["id"]: r for r in rows}
        for r in rows:
            pl, f = planned[r["id"]], fc[r["id"]]
            r.update(es=pl["es"], ef=pl["ef"], ls=pl["ls"], lf=pl["lf"], float=pl["float"],
                     critical=pl["critical"], fs=f["fs"], fe=f["fe"], delay=f["delay"],
                     own_delay=f["own_delay"], state=f["state"],
                     planned_pct=round(calc.planned_fraction(pl["es"], pl["ef"], p["status_date"]) * 100))
        ff = max(f["fe"] for f in fc.values())
        deadline = calc.parse_date(p["deadline"])
        impacts = calc.delay_impacts(fc, preds)
        for imp in impacts:
            imp["code"] = by_id[imp["task"]]["code"]
            imp["name"] = by_id[imp["task"]]["name"]
            imp["affected_codes"] = [f"{by_id[a]['code']} (+{max(fc[a]['delay'], 0)}d)" for a in imp["affected"]]
        ms = []
        for m in self.list_milestones():
            r = by_id[m["task_id"]]
            if r["actual_end"]:
                st = "Achieved" if calc.parse_date(r["actual_end"]) <= r["ef"] else "Achieved late"
            elif r["fe"] > deadline:
                st = "Missed deadline (forecast)"
            elif r["delay"] > 0:
                st = "At risk"
            else:
                st = "On track"
            ms.append({**m, "planned": calc.fmt(r["ef"]), "forecast": calc.fmt(r["fe"]),
                       "actual": r["actual_end"] or "", "status": st, "variance": r["delay"]})
        crit = [r["code"] for r in sorted(rows, key=lambda x: x["es"]) if r["critical"]]
        return {"tasks": rows, "planned_finish": pf, "forecast_finish": ff, "deadline": deadline,
                "slip": (ff - deadline).days, "impacts": impacts, "milestones": ms, "critical_path": crit}

    # ================================================================== MODULE 4
    # Cost and EVM
    def list_expenses(self, task_id=None):
        sql = """SELECT e.*, t.code AS task_code, t.name AS task_name FROM expenses e
                 JOIN tasks t ON t.id=e.task_id"""
        if task_id:
            return self.q(sql + " WHERE e.task_id=? ORDER BY e.exp_date", (task_id,))
        return self.q(sql + " ORDER BY e.exp_date DESC, e.id DESC")

    def add_expense(self, data):
        self._check_open()
        tid = _opt_id(data.get("task_id"))
        if not tid:
            raise ValidationError("Select the activity the expense belongs to.")
        t = self._require(self.one("SELECT * FROM tasks WHERE id=?", (tid,)), "Activity")
        d = _date(data.get("exp_date"), "Expense date")
        amount = _number(data.get("amount"), "Amount (PKR)", minimum=1)
        desc = _text(data, "description", "Description", required=False)
        p = self.get_project()
        if d > p["status_date"]:
            raise ValidationError("Expense date cannot be after the status date (actuals only).")
        if not t["actual_start"] or d < t["actual_start"]:
            raise ValidationError(f"{t['code']} has not started by {d}; costs can only be booked against started work.")
        self._exec("INSERT INTO expenses(task_id, exp_date, amount, description) VALUES (?,?,?,?)",
                   (tid, d, amount, desc))
        self.commit()

    def delete_expense(self, eid):
        self._check_open()
        self._exec("DELETE FROM expenses WHERE id=?", (eid,))
        self.commit()

    def evm_analysis(self):
        p = self._require(self.get_project(), "Project")
        sch = self.schedule_analysis()
        rows = sch["tasks"]
        if not rows:
            m = calc.evm_metrics({}, {}, {}, 0, p["status_date"])
            m.update(tasks=[], alerts=[], cpi_status="N/A", spi_status="N/A", curve=[], ac_curve=[])
            return m
        planned = {r["id"]: {"es": r["es"], "ef": r["ef"]} for r in rows}
        budgets = {r["id"]: r["budget"] for r in rows}
        pcts = {r["id"]: r["percent"] for r in rows}
        ac = self.one("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE exp_date <= ?", (p["status_date"],))["s"]
        m = calc.evm_metrics(budgets, planned, pcts, ac, p["status_date"])
        per = []
        for r in rows:
            pv = r["budget"] * calc.planned_fraction(r["es"], r["ef"], p["status_date"])
            ev = r["budget"] * r["percent"] / 100
            a = r["actual_cost"]
            per.append({"code": r["code"], "name": r["name"], "BAC": r["budget"], "PV": pv, "EV": ev, "AC": a,
                        "CV": ev - a, "SV": ev - pv, "CPI": ev / a if a else None, "SPI": ev / pv if pv else None})
        m["tasks"] = per
        m["cpi_status"] = calc.classify_index(m["CPI"], p["cpi_warn"], p["cpi_crit"])
        m["spi_status"] = calc.classify_index(m["SPI"], p["spi_warn"], p["spi_crit"])
        alerts = []
        if m["cpi_status"] != "OK" and m["CPI"] is not None:
            alerts.append((m["cpi_status"], f"Cost overrun: CPI = {m['CPI']:.3f} (threshold {p['cpi_warn']}). "
                                            f"Spent {money(m['AC'])} for {money(m['EV'])} of work."))
        if m["spi_status"] != "OK" and m["SPI"] is not None:
            alerts.append((m["spi_status"], f"Schedule deviation: SPI = {m['SPI']:.3f} (threshold {p['spi_warn']}). "
                                            f"Work behind plan by {money(-m['SV'])}."))
        if m["EAC"] > p["approved_budget"]:
            alerts.append(("CRITICAL", f"Forecast cost EAC {money(m['EAC'])} exceeds approved budget "
                                       f"{money(p['approved_budget'])}."))
        if m["BAC"] > p["approved_budget"]:
            alerts.append(("CRITICAL", f"Planned cost baseline {money(m['BAC'])} exceeds approved budget."))
        if sch["slip"] > 0:
            alerts.append(("CRITICAL", f"Forecast finish {calc.fmt(sch['forecast_finish'])} is {sch['slip']} days "
                                       f"after the approved deadline {p['deadline']}."))
        for t in per:
            if t["CPI"] is not None and t["CPI"] < p["cpi_crit"]:
                alerts.append(("WARNING", f"{t['code']} {t['name']}: activity CPI {t['CPI']:.2f}."))
        m["alerts"] = alerts
        m["curve"] = calc.pv_curve(budgets, planned, p["start_date"], sch["planned_finish"])
        cum, acc = 0.0, []
        for e in self.q("SELECT exp_date, SUM(amount) a FROM expenses WHERE exp_date <= ? GROUP BY exp_date ORDER BY exp_date",
                        (p["status_date"],)):
            cum += e["a"]
            acc.append((calc.parse_date(e["exp_date"]), cum))
        m["ac_curve"] = acc
        return m

    # ================================================================== MODULE 5
    # Quality and risk
    def list_defects(self):
        return self.q("""SELECT d.*, tm.name AS assignee, t.code AS task_code FROM defects d
                         LEFT JOIN team_members tm ON tm.id=d.assigned_id LEFT JOIN tasks t ON t.id=d.task_id
                         ORDER BY CASE d.status WHEN 'Open' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END,
                                  CASE d.severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
                                  WHEN 'Medium' THEN 3 ELSE 4 END, d.code""")

    def save_defect(self, data, did=None):
        self._check_open()
        title = _text(data, "title", "Title", max_len=200)
        desc = _text(data, "description", "Description", required=False)
        module = _text(data, "module", "Module")
        sev = _choice(data.get("severity"), "Severity", SEVERITIES)
        status = _choice(data.get("status") or "Open", "Status", DEFECT_STATUSES)
        assigned = _opt_id(data.get("assigned_id"))
        if not assigned:
            raise ValidationError("Assign the defect to a team member.")
        rep = _date(data.get("reported_date"), "Reported date")
        res = _date(data.get("resolved_date"), "Resolved date", required=False)
        task = _opt_id(data.get("task_id"))
        if status in ("Resolved", "Closed") and not res:
            raise ValidationError("Enter the resolved date for a resolved/closed defect.")
        if status in ("Open", "In Progress"):
            res = None
        if res and res < rep:
            raise ValidationError("Resolved date cannot be before the reported date.")
        if rep > self.get_project()["status_date"]:
            raise ValidationError("Reported date cannot be after the status date.")
        if did:
            self._exec("""UPDATE defects SET title=?, description=?, module=?, severity=?, assigned_id=?, status=?,
                          reported_date=?, resolved_date=?, task_id=? WHERE id=?""",
                       (title, desc, module, sev, assigned, status, rep, res, task, did))
            code = self.one("SELECT code FROM defects WHERE id=?", (did,))["code"]
        else:
            code = self._next_code("defects", "D")
            cur = self._exec("""INSERT INTO defects(code, title, description, module, severity, assigned_id, status,
                                reported_date, resolved_date, task_id) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                             (code, title, desc, module, sev, assigned, status, rep, res, task))
            did = cur.lastrowid
        self.log("Defect saved", f"{code} [{sev}] {status}")
        self.commit()
        return did

    def delete_defect(self, did):
        self._check_open()
        self._exec("DELETE FROM defects WHERE id=?", (did,))
        self.commit()

    def list_checks(self):
        return self.q("""SELECT q.*, w.code AS wbs_code, w.name AS wbs_name, tm.name AS inspector,
                         d.code AS defect_code FROM quality_checks q JOIN wbs w ON w.id=q.wbs_id
                         LEFT JOIN team_members tm ON tm.id=q.inspector_id
                         LEFT JOIN defects d ON d.id=q.defect_id ORDER BY q.code""")

    def save_check(self, data, qid=None):
        self._check_open()
        wbs_id = _opt_id(data.get("wbs_id"))
        if not wbs_id:
            raise ValidationError("Select the deliverable (WBS element) being checked.")
        self._require(self.one("SELECT id FROM wbs WHERE id=?", (wbs_id,)), "WBS element")
        crit = _text(data, "criterion", "Criterion", max_len=300)
        ctype = _choice(data.get("check_type"), "Check type", CHECK_TYPES)
        exp = _text(data, "expected", "Expected result")
        if qid:
            self._exec("UPDATE quality_checks SET wbs_id=?, criterion=?, check_type=?, expected=? WHERE id=?",
                       (wbs_id, crit, ctype, exp, qid))
        else:
            code = self._next_code("quality_checks", "Q")
            cur = self._exec("""INSERT INTO quality_checks(code, wbs_id, criterion, check_type, expected)
                                VALUES (?,?,?,?,?)""", (code, wbs_id, crit, ctype, exp))
            qid = cur.lastrowid
        self.commit()
        return qid

    def record_check_result(self, qid, data):
        """Record an inspection/test result. A failing result automatically raises a defect."""
        self._check_open()
        q = self._require(self.one("SELECT * FROM quality_checks WHERE id=?", (qid,)), "Checklist item")
        result = _choice(data.get("result"), "Result", CHECK_RESULTS)
        actual = _text(data, "actual", "Actual result", required=result != "Pending")
        inspector = _opt_id(data.get("inspector_id"))
        if result != "Pending" and not inspector:
            raise ValidationError("Select the inspector/tester.")
        d = _date(data.get("check_date"), "Check date", required=result != "Pending")
        defect_id = q["defect_id"]
        if result == "Fail" and not defect_id:
            w = self.one("SELECT name FROM wbs WHERE id=?", (q["wbs_id"],))
            defect_id = self.save_defect({
                "title": f"Failed {q['check_type'].lower()}: {q['criterion']}"[:200],
                "description": f"Expected: {q['expected']}\nActual: {actual}", "module": w["name"],
                "severity": data.get("severity") or "High", "status": "Open",
                "assigned_id": data.get("assign_to") or inspector, "reported_date": d})
        self._exec("UPDATE quality_checks SET actual=?, result=?, inspector_id=?, check_date=?, defect_id=? WHERE id=?",
                   (actual, result, inspector, d, defect_id, qid))
        self.commit()
        return defect_id

    def delete_check(self, qid):
        self._check_open()
        self._exec("DELETE FROM quality_checks WHERE id=?", (qid,))
        self.commit()

    def list_risks(self):
        rows = self.q("""SELECT r.*, tm.name AS owner, w.code AS wbs_code, w.name AS wbs_name FROM risks r
                         LEFT JOIN team_members tm ON tm.id=r.owner_id LEFT JOIN wbs w ON w.id=r.wbs_id""")
        return calc.rank_risks(rows)

    def save_risk(self, data, rid=None):
        self._check_open()
        title = _text(data, "title", "Risk / issue", max_len=200)
        desc = _text(data, "description", "Description", required=False)
        cat = _choice(data.get("category"), "Category", RISK_CATEGORIES)
        lik = _number(data.get("likelihood"), "Likelihood", minimum=1, maximum=5, integer=True)
        imp = _number(data.get("impact"), "Impact", minimum=1, maximum=5, integer=True)
        owner = _opt_id(data.get("owner_id"))
        wbs_id = _opt_id(data.get("wbs_id"))
        status = _choice(data.get("status") or "Open", "Status", RISK_STATUSES)
        if rid:
            self._exec("""UPDATE risks SET title=?, description=?, category=?, wbs_id=?, likelihood=?, impact=?,
                          owner_id=?, status=? WHERE id=?""", (title, desc, cat, wbs_id, lik, imp, owner, status, rid))
        else:
            code = self._next_code("risks", "RK")
            cur = self._exec("""INSERT INTO risks(code, title, description, category, wbs_id, likelihood, impact,
                                owner_id, status) VALUES (?,?,?,?,?,?,?,?,?)""",
                             (code, title, desc, cat, wbs_id, lik, imp, owner, status))
            rid = cur.lastrowid
        self.commit()
        return rid

    def delete_risk(self, rid):
        self._check_open()
        self._exec("DELETE FROM risks WHERE id=?", (rid,))
        self.commit()

    def list_countermeasures(self, risk_id=None):
        sql = """SELECT c.*, tm.name AS owner, r.code AS risk_code FROM countermeasures c
                 JOIN risks r ON r.id=c.risk_id LEFT JOIN team_members tm ON tm.id=c.owner_id"""
        if risk_id:
            return self.q(sql + " WHERE c.risk_id=? ORDER BY c.action_type DESC, c.id", (risk_id,))
        return self.q(sql + " ORDER BY c.risk_id, c.action_type DESC, c.id")

    def save_countermeasure(self, data, cid=None):
        self._check_open()
        rid = _opt_id(data.get("risk_id"))
        if not rid:
            raise ValidationError("Select the risk this countermeasure addresses.")
        self._require(self.one("SELECT id FROM risks WHERE id=?", (rid,)), "Risk")
        atype = _choice(data.get("action_type"), "Action type", ("Preventive", "Corrective"))
        action = _text(data, "action", "Action", max_len=300)
        owner = _opt_id(data.get("owner_id"))
        feasible = 1 if data.get("feasible") in (1, True, "1", "Yes", "yes") else 0
        if cid:
            self._exec("UPDATE countermeasures SET risk_id=?, action_type=?, action=?, owner_id=?, feasible=? WHERE id=?",
                       (rid, atype, action, owner, feasible, cid))
        else:
            self._exec("INSERT INTO countermeasures(risk_id, action_type, action, owner_id, feasible) VALUES (?,?,?,?,?)",
                       (rid, atype, action, owner, feasible))
        self.commit()

    def delete_countermeasure(self, cid):
        self._check_open()
        self._exec("DELETE FROM countermeasures WHERE id=?", (cid,))
        self.commit()

    def pdpc_tree(self):
        """Goal -> deliverable/activity area -> potential problem -> countermeasures."""
        p = self.get_project()
        groups = {}
        for r in self.list_risks():
            if r["status"] == "Closed":
                continue
            key = f"{r['wbs_code']} {r['wbs_name']}" if r["wbs_code"] else "Project-wide"
            r["measures"] = self.list_countermeasures(r["id"])
            groups.setdefault(key, []).append(r)
        return {"goal": p["name"] if p else "Project", "areas": groups}

    # ================================================================== MODULE 6
    # Integration, consistency, dashboard, report
    def consistency_check(self):
        issues = []
        for r in self.q("""SELECT t.code, t.wbs_id FROM tasks t"""):
            ok, why = self._wbs_in_scope(r["wbs_id"])
            if not ok:
                issues.append(("CRITICAL", f"{r['code']} is outside approved scope: {why}."))
        for r in self.q("""SELECT code, title FROM requirements WHERE status='Approved'
                           AND id NOT IN (SELECT requirement_id FROM wbs WHERE requirement_id IS NOT NULL)"""):
            issues.append(("WARNING", f"Approved requirement {r['code']} '{r['title']}' is not covered by the WBS."))
        for r in self.q("""SELECT code, name FROM wbs WHERE node_type='Work Package'
                           AND id NOT IN (SELECT wbs_id FROM tasks)"""):
            issues.append(("WARNING", f"Work package {r['code']} {r['name']} has no activities."))
        for r in self.q("""SELECT cr.code FROM change_requests cr WHERE cr.status='Approved' AND cr.schedule_impact > 0
                           AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.cr_id = cr.id)"""):
            issues.append(("CRITICAL", f"Approved {r['code']} has no activity in the schedule."))
        for r in self.q("""SELECT t.code, t.percent, d.code dc FROM defects d JOIN tasks t ON t.id=d.task_id
                           WHERE d.severity='Critical' AND d.status IN ('Open','In Progress') AND t.percent=100"""):
            issues.append(("WARNING", f"{r['code']} is marked complete but critical defect {r['dc']} is still open."))
        for r in self.q("SELECT code FROM tasks WHERE assignee_id IS NULL"):
            issues.append(("WARNING", f"{r['code']} has no assigned team member."))
        tasks, preds = self._task_graph()
        try:
            calc.topological_order(tasks.keys(), preds)
        except calc.CycleError as e:
            issues.append(("CRITICAL", str(e)))
        return issues

    def dashboard(self):
        p = self._require(self.get_project(), "Project")
        sch = self.schedule_analysis()
        ev = self.evm_analysis()
        delayed = [t for t in sch["tasks"] if t["state"] == "Delayed"]
        pending = self.q("SELECT * FROM change_requests WHERE status='Pending' ORDER BY code")
        crit = self.q("""SELECT d.*, tm.name AS assignee FROM defects d LEFT JOIN team_members tm ON tm.id=d.assigned_id
                         WHERE d.severity='Critical' AND d.status IN ('Open','In Progress') ORDER BY d.code""")
        open_def = self.one("SELECT COUNT(*) n FROM defects WHERE status IN ('Open','In Progress')")["n"]
        q = self.one("""SELECT SUM(result='Pass') pass, SUM(result='Fail') fail, SUM(result='Pending') pend,
                        COUNT(*) n FROM quality_checks""")
        risks = self.list_risks()
        alerts = list(ev["alerts"])
        for d in crit:
            alerts.append(("CRITICAL", f"Unresolved critical defect {d['code']}: {d['title']}"))
        for r in risks:
            if r["level"] == "High" and r["status"] != "Closed":
                alerts.append(("WARNING", f"High risk {r['code']} (score {r['score']}): {r['title']}"))
        alerts += self.consistency_check()
        order = {"CRITICAL": 0, "WARNING": 1, "OK": 2, "N/A": 3}
        alerts.sort(key=lambda a: order.get(a[0], 9))
        return {"project": p, "schedule": sch, "evm": ev, "delayed": delayed, "pending_crs": pending,
                "critical_defects": crit, "open_defects": open_def, "quality": q, "risks": risks,
                "alerts": alerts, "baseline": self.baseline_history()}

    def audit_log(self, limit=50):
        return self.q("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))

    def export_report(self, path):
        """Write a self-contained HTML status report."""
        d = self.dashboard()
        p, sch, ev = d["project"], d["schedule"], d["evm"]
        e = html.escape

        def tbl(headers, rows):
            h = "".join(f"<th>{e(str(x))}</th>" for x in headers)
            b = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in rows)
            return f"<table><tr>{h}</tr>{b}</table>" if rows else "<p><i>None</i></p>"

        f2 = lambda v: "-" if v is None else f"{v:.3f}"
        alerts = "".join(f"<li class='{a[0]}'><b>{a[0]}</b> {e(a[1])}</li>" for a in d["alerts"])
        body = f"""
<h1>{e(p['name'])} - Project Status Report</h1>
<p>Status date: <b>{p['status_date']}</b> | Project status: <b>{e(p['status'])}</b> |
Generated {datetime.now():%Y-%m-%d %H:%M}</p>
<h2>Overall progress</h2>
{tbl(['Indicator', 'Value'], [
    ['Work complete (EV/BAC)', f"{ev['pct_complete']:.1f}%"], ['Planned complete (PV/BAC)', f"{ev['pct_planned']:.1f}%"],
    ['Start date', p['start_date']], ['Approved deadline', p['deadline']], ['Original deadline', p['baseline_deadline']],
    ['Planned finish (CPM)', calc.fmt(sch['planned_finish'])], ['Forecast finish', calc.fmt(sch['forecast_finish'])],
    ['Schedule slip vs deadline', f"{sch['slip']} days"], ['Critical path', ' -> '.join(sch['critical_path'])]])}
<h2>Budget status (EVM)</h2>
{tbl(['Approved budget', 'BAC', 'PV', 'EV', 'AC', 'CV', 'SV', 'CPI', 'SPI', 'EAC', 'VAC'], [[
    money(p['approved_budget']), money(ev['BAC']), money(ev['PV']), money(ev['EV']), money(ev['AC']),
    money(ev['CV']), money(ev['SV']), f2(ev['CPI']), f2(ev['SPI']), money(ev['EAC']), money(ev['VAC'])]])}
<h2>Alerts</h2><ul>{alerts or '<li>None</li>'}</ul>
<h2>Delayed activities</h2>
{tbl(['Code', 'Activity', 'Planned finish', 'Forecast finish', 'Delay (days)', 'Own delay', '% done'],
     [[t['code'], t['name'], calc.fmt(t['ef']), calc.fmt(t['fe']), t['delay'], t['own_delay'], t['percent']]
      for t in d['delayed']])}
<h2>Delay impact on dependent activities</h2>
{tbl(['Root cause', 'Own delay', 'Affected activities'],
     [[f"{i['code']} {i['name']}", f"{i['own_delay']} d", ', '.join(i['affected_codes']) or '-'] for i in sch['impacts']])}
<h2>Milestones</h2>
{tbl(['Milestone', 'Owner', 'Planned', 'Forecast', 'Actual', 'Status'],
     [[m['name'], m['owner'] or '', m['planned'], m['forecast'], m['actual'], m['status']] for m in sch['milestones']])}
<h2>Pending change requests</h2>
{tbl(['Code', 'Title', 'Cost impact', 'Schedule impact', 'Requested'],
     [[c['code'], c['title'], money(c['cost_impact']), f"{c['schedule_impact']} d", c['request_date']] for c in d['pending_crs']])}
<h2>Baseline changes (approved CRs)</h2>
{tbl(['Date', 'CR', 'Budget', 'Deadline'],
     [[b['change_date'], b['cr_code'], f"{money(b['old_budget'])} -> {money(b['new_budget'])}",
       f"{b['old_deadline']} -> {b['new_deadline']}"] for b in d['baseline']])}
<h2>Unresolved critical defects</h2>
{tbl(['Code', 'Title', 'Module', 'Assigned', 'Status', 'Reported'],
     [[x['code'], x['title'], x['module'], x['assignee'] or '', x['status'], x['reported_date']] for x in d['critical_defects']])}
<h2>Top risks</h2>
{tbl(['Rank', 'Code', 'Risk', 'L', 'I', 'Score', 'Level'],
     [[r['rank'], r['code'], r['title'], r['likelihood'], r['impact'], r['score'], r['level']] for r in d['risks'][:8]])}
"""
        css = """body{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#1f2937}h1{color:#0f4c81}
h2{border-bottom:2px solid #0f4c81;padding-bottom:4px;margin-top:28px}table{border-collapse:collapse;width:100%}
th,td{border:1px solid #cbd5e1;padding:6px 8px;text-align:left;font-size:13px}th{background:#e2e8f0}
li.CRITICAL{color:#b91c1c}li.WARNING{color:#b45309}"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>Status Report</title>"
                    f"<style>{css}</style></head><body>{body}</body></html>")
        return path
