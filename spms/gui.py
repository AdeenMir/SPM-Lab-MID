"""Tkinter GUI - one window, one tab per project management module."""
import os
import traceback
import webbrowser
from datetime import timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from . import calculations as calc
from . import db, seed
from .services import (ProjectService, ValidationError, money, PRIORITIES, SEVERITIES, DEFECT_STATUSES,
                       CHECK_TYPES, CHECK_RESULTS, RISK_STATUSES, RISK_CATEGORIES, PROJECT_STATUSES, PLAN_SECTIONS)
from .widgets import (Table, Form, FormDialog, Card, ScrollCanvas, button_bar, ask_text, PRIMARY, BG, CARD, TEXT,
                      MUTED, RED, AMBER, GREEN, BLUE, STATUS_COLORS, FONT, FONT_B, SIDEBAR, SIDEBAR_HI)

NONE = (None, "- none -")
f3 = lambda v: "-" if v is None else f"{v:.3f}"
pkr = lambda v: "" if v is None else f"{v:,.0f}"


# =============================================================================== APP
class App(tk.Tk):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.conn = db.connect(db_path)
        self.svc = ProjectService(self.conn)
        if db.is_empty(self.conn):
            seed.seed(self.svc)
        self.title("Smart Healthcare - Software Project Management System")
        self.geometry("1420x880")
        self.minsize(1100, 700)
        self.configure(background=BG)
        self._style()
        self._sidebar()
        main = ttk.Frame(self)
        main.pack(side="left", fill="both", expand=True)
        self._header(main)
        self.nb = ttk.Notebook(main, style="Hidden.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.tabs = [DashboardTab(self), InitiationTab(self), ScopeTab(self), ScheduleTab(self),
                     CostTab(self), QualityTab(self), RiskTab(self)]
        for t in self.tabs:
            self.nb.add(t, text=t.TITLE)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab())
        self._highlight_nav()
        self.refresh_all()

    def _on_tab(self):
        self._highlight_nav()
        self.current_tab().refresh()

    def _sidebar(self):
        sb = tk.Frame(self, background=SIDEBAR, width=230)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Label(sb, text="SPMS", background=SIDEBAR, foreground="white",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=20, pady=(22, 0))
        tk.Label(sb, text="Smart Healthcare\nProject Control Center", background=SIDEBAR, foreground="#94a3b8",
                 font=("Segoe UI", 9), justify="left").pack(anchor="w", padx=20, pady=(0, 18))
        tk.Frame(sb, background=SIDEBAR_HI, height=1).pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(sb, text="MODULES", background=SIDEBAR, foreground="#64748b",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=20, pady=(4, 6))
        self.nav = []
        names = ["Overview dashboard", "Initiation & integration", "Scope & WBS", "Schedule & resources",
                 "Cost & earned value", "Quality management", "Risk control"]
        for i, name in enumerate(names):
            b = tk.Label(sb, text=f"  {i:>2}   {name}" if i else f"   \u25cf   {name}", anchor="w",
                         background=SIDEBAR, foreground="#cbd5e1", font=("Segoe UI", 10), padx=10, pady=9,
                         cursor="hand2")
            b.pack(fill="x", padx=10, pady=1)
            b.bind("<Button-1>", lambda e, i=i: self.nb.select(i))
            b.bind("<Enter>", lambda e, b=b: b.configure(background=SIDEBAR_HI) if b not in self._active else None)
            b.bind("<Leave>", lambda e, b=b: b.configure(background=SIDEBAR) if b not in self._active else None)
            self.nav.append(b)
        self._active = []
        bottom = tk.Frame(sb, background=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=14, pady=16)
        tk.Label(bottom, text="ACTIONS", background=SIDEBAR, foreground="#64748b",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=6, pady=(0, 6))
        for text, cmd in [("Export HTML report", self.export_report), ("Export SQL", self.export_sql),
                          ("Reset demo data", self.reset_data)]:
            b = tk.Label(bottom, text=text, background=SIDEBAR_HI, foreground="white", font=("Segoe UI", 9),
                         pady=7, cursor="hand2")
            b.pack(fill="x", pady=3)
            b.bind("<Button-1>", lambda e, cmd=cmd: cmd())
            b.bind("<Enter>", lambda e, b=b: b.configure(background=PRIMARY))
            b.bind("<Leave>", lambda e, b=b: b.configure(background=SIDEBAR_HI))

    def _highlight_nav(self):
        idx = self.nb.index(self.nb.select()) if self.nb.select() else 0
        self._active = [self.nav[idx]]
        for i, b in enumerate(self.nav):
            on = i == idx
            b.configure(background=PRIMARY if on else SIDEBAR, foreground="white" if on else "#cbd5e1",
                        font=("Segoe UI", 10, "bold" if on else "normal"))

    # -------------------------------------------------------------- look & feel
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=FONT)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG)
        s.configure("H1.TLabel", font=("Segoe UI", 15, "bold"), foreground=TEXT, background="white")
        s.configure("H2.TLabel", font=("Segoe UI", 12, "bold"), foreground="#0f172a")
        s.configure("Page.TLabel", font=("Segoe UI", 16, "bold"), foreground="#0f172a")
        s.configure("Hidden.TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.layout("Hidden.TNotebook.Tab", [])
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 9, "bold"), background="#e2e8f0",
                    foreground="#475569", borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
        s.configure("Treeview", rowheight=26, font=("Segoe UI", 9), fieldbackground="white", borderwidth=0)
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#0f172a", foreground="white",
                    relief="flat")
        s.map("Treeview.Heading", background=[("active", "#1e293b")])
        s.map("Treeview", background=[("selected", "#99f6e4")], foreground=[("selected", TEXT)])
        s.configure("TButton", padding=(12, 5), background="white", borderwidth=1)
        s.configure("Accent.TButton", background=PRIMARY, foreground="white")
        s.map("Accent.TButton", background=[("active", "#0f766e")])
        s.configure("Danger.TButton", foreground=RED)
        s.configure("TLabelframe", background=BG)
        s.configure("TLabelframe.Label", background=BG, foreground="#0f172a", font=FONT_B)
        s.configure("TLabelframe", bordercolor="#cbd5e1")

    def _header(self, master):
        h = tk.Frame(master, background="white", highlightbackground="#e2e8f0", highlightthickness=1)
        h.pack(fill="x", pady=(0, 12))
        left = tk.Frame(h, background="white")
        left.pack(side="left", padx=18, pady=10)
        self.h_title = ttk.Label(left, text="", style="H1.TLabel")
        self.h_title.pack(anchor="w")
        self.chips = tk.Frame(left, background="white")
        self.chips.pack(anchor="w", pady=(4, 0))

    def refresh_header(self):
        p = self.svc.get_project()
        self.h_title.configure(text=p["name"])
        for w in self.chips.winfo_children():
            w.destroy()
        for label, value, col in [("Status", p["status"], PRIMARY), ("Status date", p["status_date"], "#475569"),
                                  ("Budget", money(p["approved_budget"]), "#475569"),
                                  ("Deadline", p["deadline"], "#475569"),
                                  ("Database", os.path.basename(self.db_path), "#94a3b8")]:
            tk.Label(self.chips, text=f" {label}: {value} ", background="#f1f5f9", foreground=col,
                     font=("Segoe UI", 9, "bold" if label == "Status" else "normal"), padx=6, pady=2).pack(
                side="left", padx=(0, 6))

    # -------------------------------------------------------------- plumbing
    def current_tab(self):
        return self.tabs[self.nb.index(self.nb.select())]

    def refresh_all(self):
        self.refresh_header()
        for t in self.tabs:
            try:
                t.refresh()
            except Exception:  # keep the app alive even if one view fails
                traceback.print_exc()

    def run(self, fn, *args, success=None, **kw):
        """Execute a service call with validation/exception handling and refresh views."""
        try:
            result = fn(*args, **kw)
        except ValidationError as e:
            messagebox.showerror("Validation error", str(e), parent=self)
            return None
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            messagebox.showerror("Unexpected error", f"{type(e).__name__}: {e}", parent=self)
            return None
        self.refresh_all()
        if success:
            messagebox.showinfo("Done", success, parent=self)
        return result if result is not None else True

    def need(self, table):
        sel = table.selected_int()
        if sel is None:
            messagebox.showwarning("Select a row", "Please select a record first.", parent=self)
        return sel

    # option lists for combo boxes
    def members(self, none=True):
        return ([NONE] if none else []) + [(m["id"], f"{m['name']} ({m['role']})") for m in self.svc.list_members()]

    def tasks(self, none=True, exclude=None):
        return ([NONE] if none else []) + [(t["id"], f"{t['code']} {t['name']}") for t in self.svc.list_tasks()
                                           if t["id"] != exclude]

    def wbs_opts(self, packages_only=False, none=False):
        rows = self.svc.list_wbs()
        return ([NONE] if none else []) + [(w["id"], f"{w['code']} {w['name']}") for w in rows
                                           if not packages_only or w["node_type"] == "Work Package"]

    # -------------------------------------------------------------- header actions
    def export_report(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".html", initialfile="status_report.html",
                                            filetypes=[("HTML", "*.html")])
        if path and self.run(self.svc.export_report, path):
            if messagebox.askyesno("Report exported", f"Saved to {path}.\nOpen it now?", parent=self):
                webbrowser.open("file://" + os.path.abspath(path))

    def export_sql(self):
        folder = filedialog.askdirectory(parent=self, title="Folder for schema.sql and sample_data.sql")
        if folder:
            self.run(db.export_sql, self.conn, os.path.join(folder, "schema.sql"),
                     os.path.join(folder, "sample_data.sql"), success=f"schema.sql and sample_data.sql written to {folder}")

    def reset_data(self):
        if messagebox.askyesno("Reset demo data", "Delete ALL records and reload the case-study sample data?",
                               parent=self):
            db.reset(self.conn)
            self.run(seed.seed, self.svc, success="Sample data reloaded.")


class Tab(ttk.Frame):
    TITLE = ""

    def __init__(self, app):
        super().__init__(app.nb, padding=10)
        self.app, self.svc = app, app.svc
        if self.TITLE != "Dashboard":
            ttk.Label(self, text=self.TITLE.split(" ", 1)[1], style="Page.TLabel").pack(anchor="w", pady=(0, 8))
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass


def state_tag(r):
    return {"Completed": "ok", "Delayed": "crit", "In Progress": "info"}.get(r.get("state"), "")


# =============================================================================== DASHBOARD (Module 6)
class DashboardTab(Tab):
    TITLE = "Dashboard"

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Overview dashboard", style="Page.TLabel").pack(side="left")
        self.progress = ttk.Progressbar(top, length=260, maximum=100)
        self.progress.pack(side="right", padx=6)
        self.prog_lbl = ttk.Label(top, text="")
        self.prog_lbl.pack(side="right")

        grid = ttk.Frame(self)
        grid.pack(fill="x", pady=8)
        names = ["Overall progress", "Budget status", "Cost Performance (CPI)", "Schedule Performance (SPI)",
                 "Forecast finish", "Delayed activities", "Pending change requests", "Unresolved critical defects"]
        self.cards = {}
        for i, n in enumerate(names):
            c = Card(grid, n)
            c.grid(row=i // 4, column=i % 4, sticky="nsew", padx=4, pady=4)
            grid.columnconfigure(i % 4, weight=1)
            self.cards[n] = c

        st = ttk.LabelFrame(self, text="Monitoring settings (status date & EVM thresholds)", padding=8)
        st.pack(fill="x", pady=(0, 8))
        self.sv = {k: tk.StringVar() for k in ("status_date", "cpi_warn", "cpi_crit", "spi_warn", "spi_crit")}
        for i, (k, lbl) in enumerate([("status_date", "Status date"), ("cpi_warn", "CPI warning <"),
                                      ("cpi_crit", "CPI critical <"), ("spi_warn", "SPI warning <"),
                                      ("spi_crit", "SPI critical <")]):
            ttk.Label(st, text=lbl).pack(side="left", padx=(10 if i else 0, 4))
            ttk.Entry(st, textvariable=self.sv[k], width=11 if i == 0 else 6).pack(side="left")
        ttk.Button(st, text="Apply", style="Accent.TButton", command=self.apply).pack(side="left", padx=12)
        ttk.Button(st, text="Consistency check", command=self.consistency).pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        lf = ttk.LabelFrame(body, text="Alerts & warnings", padding=4)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        self.alerts = Table(lf, [("sev", "Level", 90), ("msg", "Message", 720)], height=8)
        self.alerts.pack(fill="both", expand=True)
        lf = ttk.LabelFrame(body, text="Delayed activities", padding=4)
        lf.grid(row=0, column=1, sticky="nsew", pady=(0, 6))
        self.delayed = Table(lf, [("code", "Code", 50), ("name", "Activity", 220), ("ef", "Planned", 85),
                                  ("fe", "Forecast", 85), ("delay", "Delay d", 60, "e")], height=8)
        self.delayed.pack(fill="both", expand=True)
        lf = ttk.LabelFrame(body, text="Pending change requests", padding=4)
        lf.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.crs = Table(lf, [("code", "Code", 70), ("title", "Title", 330), ("cost_impact", "Cost impact", 110, "e"),
                              ("schedule_impact", "Days", 60, "e"), ("request_date", "Requested", 90)], height=5)
        self.crs.pack(fill="both", expand=True)
        lf = ttk.LabelFrame(body, text="Unresolved critical defects", padding=4)
        lf.grid(row=1, column=1, sticky="nsew")
        self.defects = Table(lf, [("code", "Code", 50), ("title", "Defect", 250), ("assignee", "Assigned", 100),
                                  ("status", "Status", 80)], height=5)
        self.defects.pack(fill="both", expand=True)

    def refresh(self):
        d = self.svc.dashboard()
        p, ev, sch = d["project"], d["evm"], d["schedule"]
        for k in self.sv:
            self.sv[k].set(p[k])
        self.progress["value"] = ev["pct_complete"]
        self.prog_lbl.configure(text=f"Work complete {ev['pct_complete']:.1f}%  (planned {ev['pct_planned']:.1f}%)  ")
        c = self.cards
        c["Overall progress"].set(f"{ev['pct_complete']:.1f}%", f"Planned {ev['pct_planned']:.1f}% at {p['status_date']}",
                                  AMBER if ev["pct_complete"] < ev["pct_planned"] else GREEN)
        over = ev["EAC"] > p["approved_budget"]
        c["Budget status"].set(money(ev["EAC"]), f"EAC vs approved {money(p['approved_budget'])}\n"
                                                 f"Spent (AC) {money(ev['AC'])}", RED if over else
                               (AMBER if ev["VAC"] < 0 else GREEN))
        c["Cost Performance (CPI)"].set(f3(ev["CPI"]), f"{ev['cpi_status']}  |  CV {money(ev['CV'])}",
                                        STATUS_COLORS[ev["cpi_status"]])
        c["Schedule Performance (SPI)"].set(f3(ev["SPI"]), f"{ev['spi_status']}  |  SV {money(ev['SV'])}",
                                            STATUS_COLORS[ev["spi_status"]])
        c["Forecast finish"].set(calc.fmt(sch["forecast_finish"]),
                                 f"Deadline {p['deadline']}  |  {'+' if sch['slip'] > 0 else ''}{sch['slip']} days",
                                 RED if sch["slip"] > 0 else GREEN)
        c["Delayed activities"].set(str(len(d["delayed"])), ", ".join(t["code"] for t in d["delayed"]) or "None",
                                    RED if d["delayed"] else GREEN)
        c["Pending change requests"].set(str(len(d["pending_crs"])), ", ".join(x["code"] for x in d["pending_crs"]) or "None",
                                         AMBER if d["pending_crs"] else GREEN)
        c["Unresolved critical defects"].set(str(len(d["critical_defects"])), f"{d['open_defects']} open defects in total",
                                             RED if d["critical_defects"] else GREEN)
        self.alerts.load([{"sev": a[0], "msg": a[1]} for a in d["alerts"]], iid=None,
                         tag=lambda r: "crit" if r["sev"] == "CRITICAL" else "warn")
        self.delayed.load(d["delayed"], tag=lambda r: "crit")
        self.crs.load(d["pending_crs"])
        self.defects.load(d["critical_defects"], tag=lambda r: "crit")

    def apply(self):
        v = {k: s.get() for k, s in self.sv.items()}
        self.app.run(self.svc.save_settings, v["status_date"], v["cpi_warn"], v["cpi_crit"], v["spi_warn"], v["spi_crit"])

    def consistency(self):
        issues = self.svc.consistency_check()
        text = "\n".join(f"[{a}] {m}" for a, m in issues) or "No consistency problems found."
        messagebox.showinfo("Consistency check", text, parent=self)


# =============================================================================== INITIATION (Module 1)
class InitiationTab(Tab):
    TITLE = "1 Initiation & Integration"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_charter, self.f_plan, self.f_ms, self.f_team, self.f_close, self.f_log = (ttk.Frame(nb, padding=10)
                                                                                         for _ in range(6))
        for f, t in [(self.f_charter, "Project charter"), (self.f_plan, "Project management plan"),
                     (self.f_ms, "Status & milestones"), (self.f_team, "Team & responsibilities"),
                     (self.f_close, "Project closure"), (self.f_log, "Baseline & audit log")]:
            nb.add(f, text=t)
        self._build_charter()
        self._build_plan()
        self._build_milestones()
        self._build_team()
        self._build_closure()
        self._build_log()

    # --- charter
    def _build_charter(self):
        ttk.Label(self.f_charter, text="Project charter", style="H2.TLabel").pack(anchor="w")
        self.charter_box = ttk.Frame(self.f_charter)
        self.charter_box.pack(fill="both", expand=True, pady=6)
        bar = button_bar(self.f_charter, [("Save charter", self.save_charter, "Accent.TButton")])
        bar.pack(anchor="w")
        self.charter_form = None

    def _charter_fields(self):
        return [{"key": "name", "label": "Project name", "width": 90},
                {"key": "client", "label": "Client", "width": 90},
                {"key": "sponsor", "label": "Sponsor", "width": 90},
                {"key": "manager", "label": "Project manager", "width": 90},
                {"key": "objectives", "label": "Objectives", "kind": "text", "height": 4, "width": 90},
                {"key": "stakeholders", "label": "Stakeholders", "kind": "text", "height": 3, "width": 90},
                {"key": "scope_in", "label": "Scope boundary - IN", "kind": "text", "height": 3, "width": 90},
                {"key": "scope_out", "label": "Scope boundary - OUT", "kind": "text", "height": 2, "width": 90},
                {"key": "approved_budget", "label": "Approved budget (PKR)", "width": 20,
                 "hint": "changes after approval only via change requests"},
                {"key": "start_date", "label": "Start date", "width": 20, "hint": "YYYY-MM-DD"},
                {"key": "deadline", "label": "Deadline", "width": 20, "hint": "YYYY-MM-DD"},
                {"key": "status", "label": "Project status", "kind": "combo", "width": 22,
                 "options": [(s, s) for s in PROJECT_STATUSES if s != "Closed"] +
                            ([("Closed", "Closed")] if self.svc.get_project()["status"] == "Closed" else [])},
                {"key": "baseline", "label": "Original baseline", "kind": "label"}]

    def save_charter(self):
        self.app.run(self.svc.save_charter, self.charter_form.values(), success="Charter saved.")

    # --- plan
    def _build_plan(self):
        left = ttk.Frame(self.f_plan)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Plan sections", style="H2.TLabel").pack(anchor="w")
        self.sec_list = tk.Listbox(left, height=10, width=26, font=FONT, exportselection=False)
        for s in PLAN_SECTIONS:
            self.sec_list.insert("end", s)
        self.sec_list.pack(fill="y", pady=6)
        self.sec_list.bind("<<ListboxSelect>>", lambda e: self._show_section())
        ttk.Button(left, text="Generate all from project data", command=self.generate_plan).pack(fill="x", pady=2)
        ttk.Button(left, text="Save section", style="Accent.TButton", command=self.save_section).pack(fill="x", pady=2)
        right = ttk.Frame(self.f_plan)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.sec_title = ttk.Label(right, text="", style="H2.TLabel")
        self.sec_title.pack(anchor="w")
        self.sec_text = tk.Text(right, wrap="word", font=("Consolas", 10), relief="solid", borderwidth=1)
        self.sec_text.pack(fill="both", expand=True, pady=6)
        self.sec_list.selection_set(0)
        self._cur_section = None

    def _show_section(self):
        sel = self.sec_list.curselection()
        if not sel:
            return
        s = PLAN_SECTIONS[sel[0]]
        self._cur_section = s
        plan = self.svc.get_plan()[s]
        self.sec_title.configure(text=f"{s}   (last updated: {plan.get('updated') or 'never'})")
        self.sec_text.delete("1.0", "end")
        self.sec_text.insert("1.0", plan.get("content", ""))

    def save_section(self):
        if self._cur_section:
            self.app.run(self.svc.save_plan_section, self._cur_section, self.sec_text.get("1.0", "end"))
            self._show_section()

    def generate_plan(self):
        if not messagebox.askyesno("Generate plan", "Regenerate all plan sections from current scope, schedule, "
                                                    "cost and quality data? Manual edits will be replaced.", parent=self):
            return

        def go():
            for s, txt in self.svc.generate_plan().items():
                self.svc.save_plan_section(s, txt)
        self.app.run(go)
        self._show_section()

    # --- milestones
    def _build_milestones(self):
        self.status_lbl = ttk.Label(self.f_ms, text="", style="H2.TLabel")
        self.status_lbl.pack(anchor="w")
        self.status_sub = ttk.Label(self.f_ms, text="", style="Muted.TLabel")
        self.status_sub.pack(anchor="w", pady=(0, 6))
        button_bar(self.f_ms, [("Add milestone", self.add_ms, "Accent.TButton"), ("Edit", self.edit_ms),
                               ("Delete", self.del_ms, "Danger.TButton")]).pack(anchor="w", pady=4)
        self.ms_table = Table(self.f_ms, [("name", "Milestone", 300), ("task_code", "Marked by", 80),
                                          ("owner", "Responsible", 140), ("planned", "Planned", 90),
                                          ("forecast", "Forecast", 90), ("actual", "Actual", 90),
                                          ("variance", "Variance d", 80, "e"), ("status", "Status", 180)],
                              height=10, on_double=self.edit_ms)
        self.ms_table.pack(fill="both", expand=True)

    def _ms_fields(self):
        return [{"key": "name", "label": "Milestone"},
                {"key": "task_id", "label": "Achieved when activity finishes", "kind": "combo",
                 "options": self.app.tasks(none=False)},
                {"key": "owner_id", "label": "Responsible", "kind": "combo", "options": self.app.members()},
                {"key": "description", "label": "Description", "kind": "text", "height": 3}]

    def add_ms(self):
        FormDialog(self, "Add milestone", self._ms_fields(),
                   on_submit=lambda v: self._submit(self.svc.save_milestone, v)).show()

    def edit_ms(self):
        mid = self.app.need(self.ms_table)
        if mid:
            m = self.svc.one("SELECT * FROM milestones WHERE id=?", (mid,))
            FormDialog(self, "Edit milestone", self._ms_fields(), m,
                       on_submit=lambda v: self._submit(self.svc.save_milestone, v, mid)).show()

    def _submit(self, fn, *args):
        """Used inside dialogs: raise so the dialog stays open on error."""
        fn(*args)
        self.app.refresh_all()

    def del_ms(self):
        mid = self.app.need(self.ms_table)
        if mid and messagebox.askyesno("Delete", "Delete this milestone?", parent=self):
            self.app.run(self.svc.delete_milestone, mid)

    # --- team
    def _build_team(self):
        button_bar(self.f_team, [("Add member", self.add_member, "Accent.TButton"), ("Edit", self.edit_member),
                                 ("Delete", self.del_member, "Danger.TButton")]).pack(anchor="w", pady=4)
        self.team = Table(self.f_team, [("name", "Name", 140), ("role", "Role", 150),
                                        ("responsibility", "Responsibilities", 380), ("daily_rate", "Daily rate", 90, "e"),
                                        ("task_count", "# Activities", 80, "e"), ("task_codes", "Assigned activities", 260),
                                        ("email", "Email", 180)], height=12, on_double=self.edit_member)
        self.team.pack(fill="both", expand=True)

    def _member_fields(self):
        return [{"key": "name", "label": "Name"}, {"key": "role", "label": "Role"},
                {"key": "responsibility", "label": "Responsibilities", "kind": "text", "height": 3},
                {"key": "daily_rate", "label": "Daily rate (PKR)"}, {"key": "email", "label": "Email"}]

    def add_member(self):
        FormDialog(self, "Add team member", self._member_fields(),
                   on_submit=lambda v: self._submit(self.svc.save_member, v)).show()

    def edit_member(self):
        mid = self.app.need(self.team)
        if mid:
            m = self.svc.one("SELECT * FROM team_members WHERE id=?", (mid,))
            FormDialog(self, "Edit team member", self._member_fields(), m,
                       on_submit=lambda v: self._submit(self.svc.save_member, v, mid)).show()

    def del_member(self):
        mid = self.app.need(self.team)
        if mid and messagebox.askyesno("Delete", "Delete this team member?", parent=self):
            self.app.run(self.svc.delete_member, mid)

    # --- closure
    def _build_closure(self):
        ttk.Label(self.f_close, text="Project closure", style="H2.TLabel").pack(anchor="w")
        ttk.Label(self.f_close, text="The project can only be closed when all activities are complete, no critical "
                                     "defects are open, no CRs are pending and all quality checks pass.",
                  style="Muted.TLabel").pack(anchor="w")
        self.block_lbl = ttk.Label(self.f_close, text="", foreground=RED, font=FONT_B, justify="left")
        self.block_lbl.pack(anchor="w", pady=8)
        self.close_form = Form(self.f_close, [
            {"key": "closed_date", "label": "Closure date"}, {"key": "accepted_by", "label": "Accepted by (client)"},
            {"key": "lessons", "label": "Lessons learned", "kind": "text", "height": 5, "width": 80},
            {"key": "notes", "label": "Closure notes", "kind": "text", "height": 3, "width": 80}])
        self.close_form.pack(anchor="w")
        ttk.Button(self.f_close, text="Close project", style="Accent.TButton",
                   command=self.close_project).pack(anchor="w", pady=8)
        self.closure_rec = ttk.Label(self.f_close, text="", font=FONT_B, foreground=GREEN, justify="left")
        self.closure_rec.pack(anchor="w")

    def close_project(self):
        if messagebox.askyesno("Close project", "Closing is final and makes all records read-only. Continue?",
                               parent=self):
            self.app.run(self.svc.close_project, self.close_form.values(), success="Project closed.")

    # --- log
    def _build_log(self):
        ttk.Label(self.f_log, text="Baseline changes (approved change requests)", style="H2.TLabel").pack(anchor="w")
        self.base = Table(self.f_log, [("change_date", "Date", 90), ("cr_code", "CR", 70),
                                       ("old_budget", "Old budget", 110, "e"), ("new_budget", "New budget", 110, "e"),
                                       ("old_deadline", "Old deadline", 100), ("new_deadline", "New deadline", 100),
                                       ("note", "Note", 420)], height=5)
        self.base.pack(fill="x", pady=(4, 10))
        ttk.Label(self.f_log, text="Audit log", style="H2.TLabel").pack(anchor="w")
        self.log = Table(self.f_log, [("ts", "Time", 130), ("action", "Action", 220), ("details", "Details", 700)],
                         height=12)
        self.log.pack(fill="both", expand=True, pady=4)

    def refresh(self):
        p = self.svc.get_project()
        for w in self.charter_box.winfo_children():
            w.destroy()
        init = dict(p, baseline=f"{money(p['baseline_budget'])}  /  deadline {p['baseline_deadline']}")
        self.charter_form = Form(self.charter_box, self._charter_fields(), init)
        self.charter_form.pack(fill="both", expand=True)
        self._show_section()
        sch = self.svc.schedule_analysis()
        self.status_lbl.configure(text=f"Project status: {p['status']}")
        self.status_sub.configure(text=f"Start {p['start_date']}  |  Deadline {p['deadline']} (original "
                                       f"{p['baseline_deadline']})  |  Forecast finish {calc.fmt(sch['forecast_finish'])}"
                                       f"  |  Critical path: {' > '.join(sch['critical_path'])}")
        self.ms_table.load(sch["milestones"], tag=lambda r: "ok" if r["status"] == "Achieved" else
                           ("crit" if "Missed" in r["status"] else "warn" if r["status"] != "On track" else ""))
        self.team.load(self.svc.list_members())
        bl = self.svc.closure_blockers()
        closure = self.svc.get_closure()
        self.block_lbl.configure(text=("Closure blocked:\n  - " + "\n  - ".join(bl)) if bl and not closure else "")
        self.closure_rec.configure(text=(f"CLOSED on {closure['closed_date']} - accepted by {closure['accepted_by']}, "
                                         f"final cost {money(closure['final_cost'])}\nLessons: {closure['lessons']}")
                                   if closure else "")
        if not self.close_form.get("closed_date"):
            self.close_form.set("closed_date", p["status_date"])
        self.base.load(self.svc.baseline_history())
        self.log.load(self.svc.audit_log(200))


# =============================================================================== SCOPE (Module 2)
class ScopeTab(Tab):
    TITLE = "2 Scope & WBS"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_req, self.f_wbs, self.f_cr = (ttk.Frame(nb, padding=10) for _ in range(3))
        nb.add(self.f_req, text="Requirements")
        nb.add(self.f_wbs, text="Work Breakdown Structure")
        nb.add(self.f_cr, text="Change requests")
        # requirements
        ttk.Label(self.f_req, text="Only APPROVED requirements form the scope baseline and can be linked to the WBS. "
                                   "Requirements raised by change requests are approved through the CR.",
                  style="Muted.TLabel").pack(anchor="w")
        button_bar(self.f_req, [("Add requirement", self.add_req, "Accent.TButton"), ("Edit", self.edit_req),
                                ("Approve", lambda: self.set_req("Approved")), ("Reject", lambda: self.set_req("Rejected")),
                                ("Back to proposed", lambda: self.set_req("Proposed")),
                                ("Delete", self.del_req, "Danger.TButton")]).pack(anchor="w", pady=6)
        self.req = Table(self.f_req, [("code", "Code", 60), ("title", "Requirement", 420), ("priority", "Priority", 80),
                                      ("status", "Status", 90), ("source", "Source", 120), ("cr_code", "CR", 70),
                                      ("wbs_codes", "In WBS", 120)], height=16, on_double=self.edit_req)
        self.req.pack(fill="both", expand=True)
        # wbs
        button_bar(self.f_wbs, [("Add child element", self.add_wbs, "Accent.TButton"), ("Edit", self.edit_wbs),
                                ("Delete", self.del_wbs, "Danger.TButton"), ("Expand all", self.expand)]).pack(anchor="w", pady=6)
        self.wbs = Table(self.f_wbs, [("type", "Type", 110), ("req", "Requirement", 90), ("rstatus", "Req. status", 90),
                                      ("tasks", "Activities", 80, "e"), ("budget", "Budget (rolled up)", 140, "e")],
                         height=20, show="tree headings")
        self.wbs.tree.heading("#0", text="WBS code / element")
        self.wbs.tree.column("#0", width=430)
        self.wbs.pack(fill="both", expand=True)
        # change requests
        button_bar(self.f_cr, [("New change request", self.add_cr, "Accent.TButton"), ("Edit", self.edit_cr),
                               ("Preview impact", self.preview_cr), ("Approve", self.approve_cr),
                               ("Reject", self.reject_cr), ("Delete", self.del_cr, "Danger.TButton")]).pack(anchor="w", pady=6)
        self.cr = Table(self.f_cr, [("code", "Code", 70), ("title", "Title", 280), ("status", "Status", 80),
                                    ("priority", "Priority", 70), ("cost_impact", "Cost impact", 100, "e"),
                                    ("schedule_impact", "Days", 50, "e"), ("after_code", "After", 55),
                                    ("before_code", "Before", 55), ("req_code", "Req.", 50), ("task_code", "Activity", 65),
                                    ("requested_by", "Requested by", 160), ("request_date", "Requested", 85),
                                    ("decision_date", "Decided", 85)], height=8, on_double=self.edit_cr)
        self.cr.pack(fill="both", expand=True)
        self.cr.tree.bind("<<TreeviewSelect>>", lambda e: self._cr_detail())
        self.cr_detail = tk.Text(self.f_cr, height=7, wrap="word", font=FONT, relief="solid", borderwidth=1,
                                 background="#fbfcfe")
        self.cr_detail.pack(fill="x", pady=6)

    def refresh(self):
        self.req.load(self.svc.list_requirements(),
                      tag=lambda r: {"Approved": "ok", "Proposed": "warn", "Rejected": "muted"}[r["status"]])
        t = self.wbs.tree
        known = set(self._all(t))
        open_ids = {i for i in known if t.item(i, "open")} if known else None
        t.delete(*t.get_children())
        for w in self.svc.wbs_rollup():
            parent = str(w["parent_id"]) if w["parent_id"] else ""
            tag = "crit" if w["req_status"] and w["req_status"] != "Approved" else (
                "info" if w["node_type"] != "Work Package" else "")
            t.insert(parent, "end", iid=str(w["id"]), text=f"{w['code']}  {w['name']}",
                     values=(w["node_type"], w["req_code"] or "", w["req_status"] or "",
                             w["task_count"] if w["node_type"] == "Work Package" else "", f"{w['rollup']:,.0f}"),
                     open=open_ids is None or str(w["id"]) not in known or str(w["id"]) in open_ids,
                     tags=(tag,) if tag else ())
        self.cr.load(self.svc.list_change_requests(),
                     tag=lambda r: {"Approved": "ok", "Pending": "warn", "Rejected": "muted"}[r["status"]])
        self._cr_detail()

    def _all(self, t, parent=""):
        for c in t.get_children(parent):
            yield c
            yield from self._all(t, c)

    def expand(self):
        for i in self._all(self.wbs.tree):
            self.wbs.tree.item(i, open=True)

    def _submit(self, fn, *a):
        fn(*a)
        self.app.refresh_all()

    # requirements
    def _req_fields(self):
        return [{"key": "title", "label": "Title"}, {"key": "priority", "label": "Priority (MoSCoW)", "kind": "combo",
                                                      "options": [(p, p) for p in PRIORITIES], "default": "Must"},
                {"key": "description", "label": "Description", "kind": "text"}]

    def add_req(self):
        FormDialog(self, "Add requirement", self._req_fields(),
                   on_submit=lambda v: self._submit(self.svc.save_requirement, v)).show()

    def edit_req(self):
        rid = self.app.need(self.req)
        if rid:
            r = self.svc.one("SELECT * FROM requirements WHERE id=?", (rid,))
            FormDialog(self, f"Edit {r['code']}", self._req_fields(), r,
                       on_submit=lambda v: self._submit(self.svc.save_requirement, v, rid)).show()

    def set_req(self, status):
        rid = self.app.need(self.req)
        if rid:
            self.app.run(self.svc.set_requirement_status, rid, status)

    def del_req(self):
        rid = self.app.need(self.req)
        if rid and messagebox.askyesno("Delete", "Delete this requirement?", parent=self):
            self.app.run(self.svc.delete_requirement, rid)

    # wbs
    def _wbs_fields(self, root=False):
        reqs = [NONE] + [(r["id"], f"{r['code']} {r['title']}") for r in self.svc.list_requirements()
                         if r["status"] == "Approved"]
        types = [("Project", "Project (root)")] if root else [("Deliverable", "Deliverable"),
                                                              ("Work Package", "Work Package")]
        return [{"key": "name", "label": "Name"},
                {"key": "node_type", "label": "Type", "kind": "combo", "options": types, "default": types[0][0]},
                {"key": "parent_id", "label": "Parent", "kind": "combo", "options": self.app.wbs_opts(none=True)},
                {"key": "requirement_id", "label": "Approved requirement", "kind": "combo", "options": reqs},
                {"key": "description", "label": "Description", "kind": "text", "height": 3}]

    def add_wbs(self):
        sel = self.wbs.selected()
        has_root = self.svc.one("SELECT id FROM wbs WHERE node_type='Project'")
        if not has_root:
            FormDialog(self, "Create WBS root", self._wbs_fields(root=True),
                       on_submit=lambda v: self._submit(self.svc.save_wbs, v)).show()
            return
        if not sel:
            messagebox.showwarning("Select parent", "Select the parent element first.", parent=self)
            return
        FormDialog(self, "Add WBS element", self._wbs_fields(), {"parent_id": int(sel), "node_type": "Work Package"},
                   on_submit=lambda v: self._submit(self.svc.save_wbs, v)).show()

    def edit_wbs(self):
        sel = self.wbs.selected()
        if not sel:
            return messagebox.showwarning("Select", "Select a WBS element.", parent=self)
        w = self.svc.one("SELECT * FROM wbs WHERE id=?", (int(sel),))
        FormDialog(self, f"Edit WBS {w['code']}", self._wbs_fields(root=w["node_type"] == "Project"), w,
                   on_submit=lambda v: self._submit(self.svc.save_wbs, v, int(sel))).show()

    def del_wbs(self):
        sel = self.wbs.selected()
        if sel and messagebox.askyesno("Delete", "Delete this WBS element?", parent=self):
            self.app.run(self.svc.delete_wbs, int(sel))

    # change requests
    def _cr_fields(self):
        return [{"key": "title", "label": "Change title"},
                {"key": "description", "label": "Description", "kind": "text", "height": 3},
                {"key": "justification", "label": "Justification", "kind": "text", "height": 3},
                {"key": "requested_by", "label": "Requested by"},
                {"key": "request_date", "label": "Request date", "default": self.svc.get_project()["status_date"]},
                {"key": "priority", "label": "Priority", "kind": "combo", "options": [(p, p) for p in PRIORITIES],
                 "default": "Should"},
                {"key": "cost_impact", "label": "Cost impact (PKR)", "default": "0"},
                {"key": "schedule_impact", "label": "Schedule impact (days)", "default": "0",
                 "hint": "becomes a new activity"},
                {"key": "after_task_id", "label": "New work follows activity", "kind": "combo", "options": self.app.tasks()},
                {"key": "before_task_id", "label": "...and must finish before", "kind": "combo",
                 "options": self.app.tasks()},
                {"key": "assignee_id", "label": "Assign new work to", "kind": "combo", "options": self.app.members()}]

    def add_cr(self):
        FormDialog(self, "New change request", self._cr_fields(),
                   on_submit=lambda v: self._submit(self.svc.save_change_request, v)).show()

    def edit_cr(self):
        cid = self.app.need(self.cr)
        if cid:
            c = self.svc.one("SELECT * FROM change_requests WHERE id=?", (cid,))
            FormDialog(self, f"Edit {c['code']}", self._cr_fields(), c,
                       on_submit=lambda v: self._submit(self.svc.save_change_request, v, cid)).show()

    def del_cr(self):
        cid = self.app.need(self.cr)
        if cid and messagebox.askyesno("Delete", "Delete this change request?", parent=self):
            self.app.run(self.svc.delete_change_request, cid)

    def _impact_text(self, imp):
        rows = [("Approved scope (requirements)", *imp["scope"]), ("Approved budget", *map(money, imp["budget"])),
                ("Planned cost baseline (BAC)", *map(money, imp["bac"])), ("Approved deadline", *imp["deadline"]),
                ("Planned finish (CPM)", *imp["planned_finish"]), ("Forecast finish", *imp["forecast_finish"])]
        return "\n".join(f"{a:<32}{str(b):>18}  ->  {c}" for a, b, c in rows)

    def preview_cr(self):
        cid = self.app.need(self.cr)
        if cid:
            imp = self.app.run(self.svc.preview_change_impact, cid)
            if imp:
                messagebox.showinfo(f"Impact of {imp['cr']['code']}", self._impact_text(imp), parent=self)

    def approve_cr(self):
        cid = self.app.need(self.cr)
        if not cid:
            return
        try:
            imp = self.svc.preview_change_impact(cid)
        except ValidationError as e:
            return messagebox.showerror("Error", str(e), parent=self)
        if imp["cr"]["status"] != "Pending":
            return messagebox.showerror("Not pending", f"{imp['cr']['code']} is already {imp['cr']['status']}.", parent=self)
        if not messagebox.askyesno("Approve change request",
                                   f"Approving {imp['cr']['code']} will change the baseline:\n\n{self._impact_text(imp)}"
                                   "\n\nApprove?", parent=self):
            return
        who = ask_text(self, "Decision", "Approved by", "Change Control Board")
        if who:
            code = self.app.run(self.svc.approve_change_request, cid, who, "Approved via GUI")
            if code:
                messagebox.showinfo("Approved", f"{imp['cr']['code']} approved.\n"
                                                f"New activity: {code if code is not True else '-'}\n"
                                                f"Budget now {money(imp['budget'][1])}, deadline {imp['deadline'][1]}.",
                                    parent=self)

    def reject_cr(self):
        cid = self.app.need(self.cr)
        if cid:
            who = ask_text(self, "Decision", "Rejected by", "Change Control Board")
            if who:
                self.app.run(self.svc.reject_change_request, cid, who, "Rejected via GUI")

    def _cr_detail(self):
        self.cr_detail.delete("1.0", "end")
        cid = self.cr.selected_int()
        if cid:
            c = self.svc.one("SELECT * FROM change_requests WHERE id=?", (cid,))
            if c:
                self.cr_detail.insert("1.0", f"{c['code']} - {c['title']}  [{c['status']}]\n"
                                             f"Description: {c['description'] or '-'}\nJustification: {c['justification']}\n"
                                             f"Impact: +{money(c['cost_impact'])}, +{c['schedule_impact']} days\n"
                                             f"Decision: {c['decided_by'] or '-'} on {c['decision_date'] or '-'} - "
                                             f"{c['decision_notes'] or ''}")
        else:
            self.cr_detail.insert("1.0", "Select a change request to see its details. Approving a CR automatically: "
                                         "approves its requirement, adds a WBS deliverable + work package, inserts a new "
                                         "activity into the dependency network, and raises the approved budget and deadline.")


# =============================================================================== SCHEDULE (Module 3)
class ScheduleTab(Tab):
    TITLE = "3 Schedule & Resources"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_act, self.f_delay, self.f_gantt = (ttk.Frame(nb, padding=10) for _ in range(3))
        nb.add(self.f_act, text="Activities")
        nb.add(self.f_delay, text="Delay analysis")
        nb.add(self.f_gantt, text="Gantt chart")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.draw_gantt())
        button_bar(self.f_act, [("Add activity", self.add_task, "Accent.TButton"), ("Edit", self.edit_task),
                                ("Dependencies", self.edit_deps), ("Update progress", self.progress),
                                ("Delete", self.del_task, "Danger.TButton")]).pack(anchor="w", pady=(0, 6))
        self.tbl = Table(self.f_act, [
            ("code", "Code", 50), ("name", "Activity", 230), ("wbs_code", "WBS", 55), ("assignee", "Assigned", 100),
            ("duration", "Dur d", 45, "e"), ("pred_codes", "Predecessors", 120), ("es", "Plan start", 85),
            ("ef", "Plan finish", 85), ("float", "Float", 45, "e"), ("crit", "Critical", 55),
            ("actual_start", "Act. start", 85), ("actual_end", "Act. finish", 85), ("percent", "%", 40, "e"),
            ("fe", "Forecast fin.", 90), ("delay", "Delay", 45, "e"), ("state", "Status", 85),
            ("budget", "Budget", 85, "e")], height=20, on_double=self.edit_task)
        self.tbl.pack(fill="both", expand=True)
        ttk.Label(self.f_act, text="Planned dates are generated by the Critical Path Method from durations and "
                                   "finish-to-start dependencies. Red = delayed, green = completed, blue = in progress.",
                  style="Muted.TLabel").pack(anchor="w", pady=4)
        # delay analysis
        self.sum_lbl = ttk.Label(self.f_delay, text="", font=("Segoe UI", 11, "bold"), justify="left")
        self.sum_lbl.pack(anchor="w", pady=(0, 8))
        ttk.Label(self.f_delay, text="Root-cause delays and their impact on dependent activities", style="H2.TLabel").pack(anchor="w")
        self.imp = Table(self.f_delay, [("code", "Activity", 60), ("name", "Name", 250), ("own_delay", "Own delay d", 90, "e"),
                                        ("total_delay", "Total delay d", 90, "e"), ("open", "Status", 90),
                                        ("aff", "Affected downstream activities (forecast slip)", 700)], height=9)
        self.imp.pack(fill="both", expand=True, pady=4)
        ttk.Label(self.f_delay, text="Delayed activities", style="H2.TLabel").pack(anchor="w", pady=(8, 0))
        self.dl = Table(self.f_delay, [("code", "Code", 60), ("name", "Activity", 280), ("assignee", "Assigned", 120),
                                       ("ef", "Planned finish", 100), ("fe", "Forecast finish", 100),
                                       ("delay", "Delay d", 70, "e"), ("percent", "%", 50, "e"),
                                       ("planned_pct", "Planned %", 70, "e"), ("crit", "Critical", 60)], height=7)
        self.dl.pack(fill="both", expand=True, pady=4)
        # gantt
        top = ttk.Frame(self.f_gantt)
        top.pack(fill="x")
        ttk.Label(top, text="Gantt chart - baseline (grey) vs forecast (coloured)", style="H2.TLabel").pack(side="left")
        ttk.Label(top, text="Zoom px/day").pack(side="right")
        self.zoom = tk.IntVar(value=7)
        ttk.Spinbox(top, from_=3, to=20, textvariable=self.zoom, width=4, command=self.draw_gantt).pack(side="right", padx=4)
        self.gantt = ScrollCanvas(self.f_gantt)
        self.gantt.pack(fill="both", expand=True, pady=6)

    def refresh(self):
        self.sch = self.svc.schedule_analysis()
        rows = self.sch["tasks"]
        for r in rows:
            r["crit"] = "Yes" if r["critical"] else ""
        self.tbl.load(rows, tag=state_tag)
        s, p = self.sch, self.svc.get_project()
        self.sum_lbl.configure(text=f"Planned finish (CPM): {calc.fmt(s['planned_finish'])}     Forecast finish: "
                                    f"{calc.fmt(s['forecast_finish'])}     Approved deadline: {calc.fmt(s['deadline'])}     "
                                    f"Deadline variance: {'+' if s['slip'] > 0 else ''}{s['slip']} days\n"
                                    f"Status date: {p['status_date']}     Critical path: {' > '.join(s['critical_path'])}",
                               foreground=RED if s["slip"] > 0 else GREEN)
        by = {t["id"]: t for t in rows}
        self.imp.load([{"id": i["task"], "code": i["code"], "name": i["name"], "own_delay": i["own_delay"],
                        "total_delay": i["total_delay"], "open": by[i["task"]]["state"],
                        "aff": ", ".join(i["affected_codes"]) or "-"} for i in s["impacts"]],
                      tag=lambda r: "crit" if r["open"] != "Completed" else "warn")
        self.dl.load([t for t in rows if t["state"] == "Delayed"], tag=lambda r: "crit")
        self.draw_gantt()

    # --- forms
    def _task_fields(self, tid=None):
        def estimate(form):
            try:
                form.set("budget", self.svc.estimate_cost(form.get("assignee_id"), form.get("duration")))
            except ValidationError as e:
                messagebox.showerror("Estimate", str(e), parent=form)
        return [{"key": "name", "label": "Activity name"},
                {"key": "wbs_id", "label": "WBS work package", "kind": "combo", "options": self.app.wbs_opts(True)},
                {"key": "assignee_id", "label": "Assigned to", "kind": "combo", "options": self.app.members()},
                {"key": "duration", "label": "Duration (days)", "default": "5"},
                {"key": "budget", "label": "Estimated cost (PKR)", "button": ("Estimate = duration x rate", estimate)},
                {"key": "pred_ids", "label": "Predecessors (finish-to-start)", "kind": "multi", "height": 8,
                 "options": self.app.tasks(none=False, exclude=tid)},
                {"key": "notes", "label": "Notes", "kind": "text", "height": 2}]

    def _submit(self, fn, *a):
        fn(*a)
        self.app.refresh_all()

    def add_task(self):
        FormDialog(self, "Add activity", self._task_fields(),
                   on_submit=lambda v: self._submit(self.svc.save_task, v)).show()

    def edit_task(self):
        tid = self.app.need(self.tbl)
        if tid:
            t = self.svc.one("SELECT * FROM tasks WHERE id=?", (tid,))
            t["pred_ids"] = [d["pred_id"] for d in self.svc.q("SELECT pred_id FROM dependencies WHERE task_id=?", (tid,))]
            FormDialog(self, f"Edit {t['code']}", self._task_fields(tid), t,
                       on_submit=lambda v: self._submit(self.svc.save_task, v, tid)).show()

    def edit_deps(self):
        tid = self.app.need(self.tbl)
        if tid:
            cur = [d["pred_id"] for d in self.svc.q("SELECT pred_id FROM dependencies WHERE task_id=?", (tid,))]
            FormDialog(self, "Dependencies", [{"key": "pred_ids", "label": "Predecessors", "kind": "multi", "height": 14,
                                               "options": self.app.tasks(none=False, exclude=tid)}], {"pred_ids": cur},
                       on_submit=lambda v: self._submit(self.svc.set_dependencies, tid, v["pred_ids"])).show()

    def progress(self):
        tid = self.app.need(self.tbl)
        if tid:
            t = self.svc.one("SELECT * FROM tasks WHERE id=?", (tid,))
            FormDialog(self, f"Progress - {t['code']} {t['name']}", [
                {"key": "actual_start", "label": "Actual start", "hint": "YYYY-MM-DD"},
                {"key": "actual_end", "label": "Actual finish", "hint": "blank if not finished"},
                {"key": "percent", "label": "% complete", "hint": "0-100"}], t,
                on_submit=lambda v: self._submit(self.svc.update_progress, tid, v["actual_start"], v["actual_end"],
                                                 v["percent"])).show()

    def del_task(self):
        tid = self.app.need(self.tbl)
        if tid and messagebox.askyesno("Delete", "Delete this activity?", parent=self):
            self.app.run(self.svc.delete_task, tid)

    # --- gantt
    def draw_gantt(self):
        if not hasattr(self, "sch"):
            return
        c = self.gantt.canvas
        c.delete("all")
        rows = sorted(self.sch["tasks"], key=lambda t: (t["es"], t["code"]))
        if not rows:
            return
        p = self.svc.get_project()
        px = max(3, int(self.zoom.get() or 7))
        start = calc.parse_date(p["start_date"])
        end = max(self.sch["forecast_finish"], self.sch["deadline"], self.sch["planned_finish"]) + timedelta(days=7)
        L, top, rh = 300, 60, 30
        X = lambda d: L + (d - start).days * px
        ms = self.sch["milestones"]
        n_rows = len(rows) + len(ms)
        H = top + n_rows * rh + 10
        # week grid
        d = start
        while d <= end:
            x = X(d)
            c.create_line(x, top - 10, x, H, fill="#eef1f5")
            c.create_text(x + 2, top - 18, text=d.strftime("%d %b"), anchor="w", font=("Segoe UI", 8), fill=MUTED)
            d += timedelta(days=7)
        c.create_text(10, top - 18, text="Activity", anchor="w", font=FONT_B)
        pos = {}
        for i, t in enumerate(rows):
            y = top + i * rh
            if i % 2 == 0:
                c.create_rectangle(0, y, X(end), y + rh, fill="#fafbfc", outline="")
            label = f"{t['code']}  {t['name'][:34]}"
            c.create_text(10, y + rh / 2, text=label, anchor="w", font=("Segoe UI", 9, "bold" if t["critical"] else "normal"),
                          fill=RED if t["critical"] else TEXT)
            # baseline bar
            c.create_rectangle(X(t["es"]), y + 5, X(t["ef"]) + px, y + 12, fill="#cfd6df", outline="")
            # forecast bar
            color = {"Completed": GREEN, "In Progress": BLUE, "Delayed": AMBER}.get(t["state"], "#7f8c8d")
            if t["state"] == "Delayed" and t["percent"] == 0:
                color = "#e59866"
            x1, x2 = X(t["fs"]), X(t["fe"]) + px
            c.create_rectangle(x1, y + 14, x2, y + 25, fill="white", outline=color, width=2 if t["critical"] else 1)
            c.create_rectangle(x1, y + 14, x1 + (x2 - x1) * t["percent"] / 100, y + 25, fill=color, outline="")
            c.create_text(x2 + 4, y + 19, text=f"{t['percent']}%" + (f"  +{t['delay']}d" if t["delay"] > 0 else ""),
                          anchor="w", font=("Segoe UI", 8), fill=RED if t["delay"] > 0 else MUTED)
            pos[t["id"]] = (x1, x2, y + 19)
        # dependency arrows
        preds = self.svc.q("SELECT task_id, pred_id FROM dependencies")
        for dpd in preds:
            if dpd["task_id"] in pos and dpd["pred_id"] in pos:
                _, px2, py = pos[dpd["pred_id"]]
                sx1, _, sy = pos[dpd["task_id"]]
                c.create_line(px2, py, px2 + 4, py, px2 + 4, sy, sx1, sy, fill="#9aa5b1", arrow="last",
                              arrowshape=(5, 6, 3))
        # milestones
        base = top + len(rows) * rh
        for j, m in enumerate(ms):
            y = base + j * rh + rh / 2
            c.create_text(10, y, text=m["name"][:40], anchor="w", font=("Segoe UI", 9, "italic"), fill=PRIMARY)
            for dstr, col in ((m["planned"], "#95a5a6"), (m["forecast"], RED if m["variance"] > 0 else GREEN)):
                x = X(calc.parse_date(dstr)) + px
                c.create_polygon(x, y - 7, x + 7, y, x, y + 7, x - 7, y, fill=col, outline="")
        # reference lines
        for k, (dstr, col, name, dash) in enumerate(((p["status_date"], BLUE, "Status date", (4, 2)),
                                                     (p["deadline"], RED, "Approved deadline", None),
                                                     (p["baseline_deadline"], "#7f8c8d", "Original deadline", (2, 3)))):
            x = X(calc.parse_date(dstr))
            c.create_line(x, top - 8, x, H, fill=col, width=2, dash=dash)
            c.create_text(x + 3, H - 8 - k * 12, text=name, anchor="w", font=("Segoe UI", 8, "bold"), fill=col)
        # legend
        lx = 10
        for txt, col in (("Baseline", "#cfd6df"), ("Completed", GREEN), ("In progress", BLUE), ("Delayed", AMBER),
                         ("Not started", "#7f8c8d")):
            c.create_rectangle(lx, 12, lx + 14, 24, fill=col, outline="")
            c.create_text(lx + 18, 18, text=txt, anchor="w", font=("Segoe UI", 8))
            lx += 100
        c.create_text(lx, 18, text="Red labels = critical path   |   arrows = finish-to-start dependencies   |   "
                                   "diamonds = milestones (grey planned, coloured forecast)", anchor="w",
                      font=("Segoe UI", 8), fill=MUTED)
        self.gantt.finish()


# =============================================================================== COST (Module 4)
class CostTab(Tab):
    TITLE = "4 Cost & EVM"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_evm, self.f_exp = ttk.Frame(nb, padding=10), ttk.Frame(nb, padding=10)
        nb.add(self.f_evm, text="Earned Value Management")
        nb.add(self.f_exp, text="Cost estimates & expenditure")
        grid = ttk.Frame(self.f_evm)
        grid.pack(fill="x")
        self.cards = {}
        for i, k in enumerate(["BAC", "PV", "EV", "AC", "CPI", "SPI", "CV", "SV", "EAC", "VAC", "ETC", "TCPI"]):
            card = Card(grid, {"BAC": "BAC - planned budget", "PV": "Planned Value", "EV": "Earned Value",
                               "AC": "Actual Cost", "CPI": "CPI = EV / AC", "SPI": "SPI = EV / PV",
                               "CV": "CV = EV - AC", "SV": "SV = EV - PV", "EAC": "EAC = BAC / CPI",
                               "VAC": "VAC = BAC - EAC", "ETC": "ETC = EAC - AC",
                               "TCPI": "TCPI (to-complete)"}[k])
            card.grid(row=i // 6, column=i % 6, sticky="nsew", padx=3, pady=3)
            grid.columnconfigure(i % 6, weight=1)
            self.cards[k] = card
        mid = ttk.Frame(self.f_evm)
        mid.pack(fill="both", expand=True, pady=6)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(1, weight=1)
        af = ttk.LabelFrame(mid, text="Automatic cost / schedule warnings", padding=4)
        af.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.alerts = Table(af, [("sev", "Level", 90), ("msg", "Message", 1100)], height=4)
        self.alerts.pack(fill="x")
        tf = ttk.LabelFrame(mid, text="EVM per activity", padding=4)
        tf.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
        self.tbl = Table(tf, [("code", "Code", 45), ("name", "Activity", 170), ("BAC", "BAC", 80, "e"),
                              ("PV", "PV", 80, "e"), ("EV", "EV", 80, "e"), ("AC", "AC", 80, "e"),
                              ("CPI", "CPI", 50, "e", f3), ("SPI", "SPI", 50, "e", f3)], height=10)
        self.tbl.pack(fill="both", expand=True)
        cf = ttk.LabelFrame(mid, text="S-curve: cumulative PV vs AC, EV at status date", padding=4)
        cf.grid(row=1, column=1, sticky="nsew", pady=(6, 0))
        self.chart = tk.Canvas(cf, background="white", highlightthickness=0, height=300)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda e: self.draw_curve())
        # expenditure
        button_bar(self.f_exp, [("Record expense", self.add_exp, "Accent.TButton"),
                                ("Delete expense", self.del_exp, "Danger.TButton")]).pack(anchor="w", pady=(0, 6))
        pan = ttk.Frame(self.f_exp)
        pan.pack(fill="both", expand=True)
        pan.columnconfigure(0, weight=3)
        pan.columnconfigure(1, weight=2)
        pan.rowconfigure(0, weight=1)
        lf = ttk.LabelFrame(pan, text="Activity cost estimates vs actuals", padding=4)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.est = Table(lf, [("code", "Code", 45), ("name", "Activity", 220), ("assignee", "Assigned", 100),
                              ("duration", "Days", 45, "e"), ("labour", "Labour est.", 90, "e"),
                              ("budget", "Budget", 90, "e"), ("bcwp", "Budgeted cost of work done", 120, "e"),
                              ("actual_cost", "Actual", 90, "e"), ("var", "Variance", 90, "e")], height=18)
        self.est.pack(fill="both", expand=True)
        self.tot = ttk.Label(lf, text="", font=FONT_B)
        self.tot.pack(anchor="w", pady=4)
        rf = ttk.LabelFrame(pan, text="Expense ledger (actual expenditure)", padding=4)
        rf.grid(row=0, column=1, sticky="nsew")
        self.exp = Table(rf, [("exp_date", "Date", 85), ("task_code", "Activity", 60), ("amount", "Amount", 90, "e"),
                              ("description", "Description", 200)], height=18)
        self.exp.pack(fill="both", expand=True)

    def refresh(self):
        self.ev = ev = self.svc.evm_analysis()
        p = self.svc.get_project()
        for k, card in self.cards.items():
            v = ev[k]
            if k in ("CPI", "SPI"):
                st = ev["cpi_status" if k == "CPI" else "spi_status"]
                card.set(f3(v), st, STATUS_COLORS[st])
            elif k == "TCPI":
                card.set(f3(v), "efficiency needed for rest", AMBER if v and v > 1.05 else GREEN)
            else:
                neg = k in ("CV", "SV", "VAC") and v < 0
                card.set(f"{v:,.0f}", "PKR", RED if neg else PRIMARY)
        self.alerts.load([{"sev": a, "msg": m} for a, m in sorted(ev["alerts"], key=lambda x: x[0] != "CRITICAL")], iid=None,
                         tag=lambda r: "crit" if r["sev"] == "CRITICAL" else "warn")
        self.tbl.load(ev["tasks"], iid="code",
                      tag=lambda r: "crit" if r["CPI"] is not None and r["CPI"] < p["cpi_crit"] else
                      ("warn" if r["CPI"] is not None and r["CPI"] < p["cpi_warn"] else ""))
        rows = self.svc.list_tasks()
        for r in rows:
            r["labour"] = r["duration"] * (r["daily_rate"] or 0)
            r["bcwp"] = r["budget"] * r["percent"] / 100
            r["var"] = r["bcwp"] - r["actual_cost"]
        self.est.load(rows, tag=lambda r: "crit" if r["var"] < 0 else "")
        self.tot.configure(text=f"Total planned budget (BAC): {money(sum(r['budget'] for r in rows))}    |    "
                                f"Approved budget: {money(p['approved_budget'])}    |    Reserve: "
                                f"{money(p['approved_budget'] - sum(r['budget'] for r in rows))}    |    "
                                f"Actual spent: {money(sum(r['actual_cost'] for r in rows))}")
        self.exp.load(self.svc.list_expenses())
        self.draw_curve()

    def draw_curve(self):
        if not hasattr(self, "ev"):
            return
        c = self.chart
        c.delete("all")
        ev = self.ev
        W, H = max(c.winfo_width(), 400), max(c.winfo_height(), 260)
        L, R, T, B = 70, 20, 20, 52
        curve, acc = ev["curve"], ev["ac_curve"]
        if not curve:
            return
        p = self.svc.get_project()
        sd = calc.parse_date(p["status_date"])
        d0, d1 = curve[0][0], max(curve[-1][0], sd)
        ymax = max([v for _, v in curve] + [v for _, v in acc] + [ev["EAC"], 1]) * 1.05
        X = lambda d: L + (d - d0).days / max((d1 - d0).days, 1) * (W - L - R)
        Y = lambda v: H - B - v / ymax * (H - T - B)
        for i in range(6):
            v = ymax * i / 5
            c.create_line(L, Y(v), W - R, Y(v), fill="#eef1f5")
            c.create_text(L - 6, Y(v), text=f"{v / 1e6:.1f}M", anchor="e", font=("Segoe UI", 8), fill=MUTED)
        c.create_line(L, H - B, W - R, H - B)
        c.create_line(L, T, L, H - B)
        step = max(1, len(curve) // 6)
        for d, _ in curve[::step]:
            c.create_text(X(d), H - B + 12, text=d.strftime("%d %b"), font=("Segoe UI", 8), fill=MUTED)
        c.create_line(*[xy for d, v in curve for xy in (X(d), Y(v))], fill=BLUE, width=2)
        if len(acc) > 1:
            c.create_line(*[xy for d, v in acc for xy in (X(d), Y(v))], fill=RED, width=2)
        x = X(sd)
        c.create_line(x, T, x, H - B, fill="#95a5a6", dash=(3, 2))
        c.create_oval(x - 5, Y(ev["EV"]) - 5, x + 5, Y(ev["EV"]) + 5, fill=GREEN, outline="")
        labels = sorted([(Y(ev[k]), k, col) for k, col in (("EV", GREEN), ("AC", RED), ("PV", BLUE))])
        last = -99
        for y, k, col in labels:  # keep labels at least 14 px apart
            y = max(y, last + 14)
            last = y
            c.create_text(x - 8, y, text=f"{k} {ev[k] / 1e6:.2f}M", anchor="e", font=("Segoe UI", 8, "bold"), fill=col)
        c.create_line(L, Y(p["approved_budget"]), W - R, Y(p["approved_budget"]), fill=AMBER, dash=(5, 3))
        c.create_text(W - R, Y(p["approved_budget"]) + 8, text="Approved budget", anchor="e", font=("Segoe UI", 8), fill=AMBER)
        for i, (t, col) in enumerate((("PV (planned)", BLUE), ("AC (actual)", RED), ("EV (earned)", GREEN))):
            c.create_rectangle(L + 10 + i * 110, H - 14, L + 22 + i * 110, H - 4, fill=col, outline="")
            c.create_text(L + 26 + i * 110, H - 9, text=t, anchor="w", font=("Segoe UI", 8))

    def add_exp(self):
        started = [(t["id"], f"{t['code']} {t['name']}") for t in self.svc.list_tasks() if t["actual_start"]]
        FormDialog(self, "Record expense", [
            {"key": "task_id", "label": "Activity (started only)", "kind": "combo", "options": started},
            {"key": "exp_date", "label": "Date", "default": self.svc.get_project()["status_date"]},
            {"key": "amount", "label": "Amount (PKR)"}, {"key": "description", "label": "Description"}],
            on_submit=lambda v: (self.svc.add_expense(v), self.app.refresh_all())).show()

    def del_exp(self):
        eid = self.app.need(self.exp)
        if eid and messagebox.askyesno("Delete", "Delete this expense?", parent=self):
            self.app.run(self.svc.delete_expense, eid)


# =============================================================================== QUALITY (Module 5a)
class QualityTab(Tab):
    TITLE = "5 Quality"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_def, self.f_chk = ttk.Frame(nb, padding=10), ttk.Frame(nb, padding=10)
        nb.add(self.f_def, text="Defect tracking")
        nb.add(self.f_chk, text="Quality checklist & test results")
        self.def_sum = ttk.Label(self.f_def, text="", font=FONT_B)
        self.def_sum.pack(anchor="w")
        button_bar(self.f_def, [("Log defect", self.add_def, "Accent.TButton"), ("Edit / change status", self.edit_def),
                                ("Delete", self.del_def, "Danger.TButton")]).pack(anchor="w", pady=6)
        self.defs = Table(self.f_def, [("code", "Code", 50), ("title", "Defect", 330), ("module", "Module", 150),
                                       ("severity", "Severity", 75), ("assignee", "Assigned to", 120),
                                       ("status", "Status", 85), ("reported_date", "Reported", 85),
                                       ("resolved_date", "Resolved", 85), ("task_code", "Activity", 60)],
                          height=18, on_double=self.edit_def)
        self.defs.pack(fill="both", expand=True)
        self.chk_sum = ttk.Label(self.f_chk, text="", font=FONT_B)
        self.chk_sum.pack(anchor="w")
        button_bar(self.f_chk, [("Add checklist item", self.add_chk, "Accent.TButton"), ("Edit", self.edit_chk),
                                ("Record inspection/test result", self.record, "Accent.TButton"),
                                ("Delete", self.del_chk, "Danger.TButton")]).pack(anchor="w", pady=6)
        self.chk = Table(self.f_chk, [("code", "Code", 45), ("wbs_code", "WBS", 55), ("wbs_name", "Deliverable", 170),
                                      ("criterion", "Criterion", 270), ("check_type", "Type", 75),
                                      ("expected", "Expected", 200), ("actual", "Actual", 200), ("result", "Result", 60),
                                      ("inspector", "Inspector", 100), ("check_date", "Date", 85),
                                      ("defect_code", "Defect", 55)], height=18, on_double=self.record)
        self.chk.pack(fill="both", expand=True)

    def refresh(self):
        rows = self.svc.list_defects()
        self.defs.load(rows, tag=lambda r: "crit" if r["severity"] == "Critical" and r["status"] in ("Open", "In Progress")
                       else ("warn" if r["status"] in ("Open", "In Progress") else "ok"))
        open_ = [r for r in rows if r["status"] in ("Open", "In Progress")]
        by_sev = {s: sum(1 for r in open_ if r["severity"] == s) for s in SEVERITIES}
        self.def_sum.configure(text=f"Open defects: {len(open_)}  (" + ", ".join(f"{k}: {v}" for k, v in by_sev.items()) +
                                    f")   |   Resolved/closed: {len(rows) - len(open_)}")
        cks = self.svc.list_checks()
        self.chk.load(cks, tag=lambda r: {"Pass": "ok", "Fail": "crit"}.get(r["result"], "warn"))
        n = len(cks) or 1
        ps = sum(1 for c in cks if c["result"] == "Pass")
        self.chk_sum.configure(text=f"Checklist: {ps}/{len(cks)} passed ({ps / n * 100:.0f}%), "
                                    f"{sum(1 for c in cks if c['result'] == 'Fail')} failed, "
                                    f"{sum(1 for c in cks if c['result'] == 'Pending')} pending")

    def _def_fields(self):
        return [{"key": "title", "label": "Defect title"},
                {"key": "description", "label": "Description", "kind": "text", "height": 3},
                {"key": "module", "label": "Module / deliverable"},
                {"key": "severity", "label": "Severity", "kind": "combo", "options": [(s, s) for s in SEVERITIES],
                 "default": "High"},
                {"key": "assigned_id", "label": "Assigned to", "kind": "combo", "options": self.app.members(False)},
                {"key": "status", "label": "Status", "kind": "combo", "options": [(s, s) for s in DEFECT_STATUSES],
                 "default": "Open"},
                {"key": "reported_date", "label": "Reported date", "default": self.svc.get_project()["status_date"]},
                {"key": "resolved_date", "label": "Resolved date", "hint": "required when Resolved/Closed"},
                {"key": "task_id", "label": "Related activity", "kind": "combo", "options": self.app.tasks()}]

    def add_def(self):
        FormDialog(self, "Log defect", self._def_fields(),
                   on_submit=lambda v: (self.svc.save_defect(v), self.app.refresh_all())).show()

    def edit_def(self):
        did = self.app.need(self.defs)
        if did:
            d = self.svc.one("SELECT * FROM defects WHERE id=?", (did,))
            FormDialog(self, f"Edit {d['code']}", self._def_fields(), d,
                       on_submit=lambda v: (self.svc.save_defect(v, did), self.app.refresh_all())).show()

    def del_def(self):
        did = self.app.need(self.defs)
        if did and messagebox.askyesno("Delete", "Delete this defect?", parent=self):
            self.app.run(self.svc.delete_defect, did)

    def _chk_fields(self):
        return [{"key": "wbs_id", "label": "Deliverable (WBS)", "kind": "combo", "options": self.app.wbs_opts()},
                {"key": "criterion", "label": "Quality criterion"},
                {"key": "check_type", "label": "Type", "kind": "combo", "options": [(c, c) for c in CHECK_TYPES],
                 "default": "Test"},
                {"key": "expected", "label": "Expected result"}]

    def add_chk(self):
        FormDialog(self, "Add checklist item", self._chk_fields(),
                   on_submit=lambda v: (self.svc.save_check(v), self.app.refresh_all())).show()

    def edit_chk(self):
        qid = self.app.need(self.chk)
        if qid:
            q = self.svc.one("SELECT * FROM quality_checks WHERE id=?", (qid,))
            FormDialog(self, f"Edit {q['code']}", self._chk_fields(), q,
                       on_submit=lambda v: (self.svc.save_check(v, qid), self.app.refresh_all())).show()

    def record(self):
        qid = self.app.need(self.chk)
        if not qid:
            return
        q = self.svc.one("SELECT * FROM quality_checks WHERE id=?", (qid,))
        init = dict(q, check_date=q["check_date"] or self.svc.get_project()["status_date"])

        def submit(v):
            new_def = self.svc.record_check_result(qid, v)
            self.app.refresh_all()
            if v["result"] == "Fail" and new_def and not q["defect_id"]:
                messagebox.showinfo("Defect raised", "The failed check automatically raised a defect.", parent=self)
        FormDialog(self, f"Record result - {q['code']} {q['criterion']}", [
            {"key": "result", "label": "Result", "kind": "combo", "options": [(r, r) for r in CHECK_RESULTS]},
            {"key": "actual", "label": "Actual result / observation", "kind": "text", "height": 3},
            {"key": "inspector_id", "label": "Inspector / tester", "kind": "combo", "options": self.app.members()},
            {"key": "check_date", "label": "Date"},
            {"key": "severity", "label": "Severity if failed", "kind": "combo", "options": [(s, s) for s in SEVERITIES],
             "default": "High"},
            {"key": "assign_to", "label": "Assign raised defect to", "kind": "combo", "options": self.app.members()}],
            init, on_submit=submit).show()

    def del_chk(self):
        qid = self.app.need(self.chk)
        if qid and messagebox.askyesno("Delete", "Delete this checklist item?", parent=self):
            self.app.run(self.svc.delete_check, qid)


# =============================================================================== RISK (Module 5b)
class RiskTab(Tab):
    TITLE = "5 Risk control (Matrix & PDPC)"

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.f_mx, self.f_pdpc = ttk.Frame(nb, padding=10), ttk.Frame(nb, padding=10)
        nb.add(self.f_mx, text="Prioritization matrix")
        nb.add(self.f_pdpc, text="PDPC - risk response chart")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.draw())
        button_bar(self.f_mx, [("Add risk / issue", self.add_risk, "Accent.TButton"), ("Edit", self.edit_risk),
                               ("Delete", self.del_risk, "Danger.TButton")]).pack(anchor="w", pady=(0, 6))
        pan = ttk.Frame(self.f_mx)
        pan.pack(fill="both", expand=True)
        pan.columnconfigure(1, weight=1)
        pan.rowconfigure(0, weight=1)
        self.mx = tk.Canvas(pan, width=470, height=470, background="white", highlightthickness=0)
        self.mx.grid(row=0, column=0, sticky="n", padx=(0, 10))
        self.risks = Table(pan, [("rank", "Rank", 45, "e"), ("code", "Code", 50), ("title", "Risk / issue", 300),
                                 ("category", "Category", 85), ("likelihood", "L", 30, "e"), ("impact", "I", 30, "e"),
                                 ("score", "Score", 50, "e"), ("level", "Level", 65), ("owner", "Owner", 110),
                                 ("status", "Status", 80)], height=20, on_double=self.edit_risk)
        self.risks.grid(row=0, column=1, sticky="nsew")
        # PDPC
        button_bar(self.f_pdpc, [("Add countermeasure", self.add_cm, "Accent.TButton"), ("Edit", self.edit_cm),
                                 ("Delete", self.del_cm, "Danger.TButton")]).pack(anchor="w", pady=(0, 6))
        self.pdpc = ScrollCanvas(self.f_pdpc)
        self.pdpc.pack(fill="both", expand=True)
        self.cms = Table(self.f_pdpc, [("risk_code", "Risk", 55), ("action_type", "Type", 85), ("action", "Action", 600),
                                       ("owner", "Owner", 120), ("feas", "Feasible", 60)], height=6, on_double=self.edit_cm)
        self.cms.pack(fill="x", pady=(6, 0))

    def refresh(self):
        self.rows = self.svc.list_risks()
        self.risks.load(self.rows, tag=lambda r: {"High": "crit", "Medium": "warn", "Low": "ok"}[r["level"]])
        cms = self.svc.list_countermeasures()
        for c in cms:
            c["feas"] = "O (yes)" if c["feasible"] else "X (no)"
        self.cms.load(cms)
        self.draw()

    def draw(self):
        if not hasattr(self, "rows"):
            return
        self._draw_matrix()
        self._draw_pdpc()

    def _draw_matrix(self):
        c = self.mx
        c.delete("all")
        L, T, S = 70, 30, 76
        c.create_text(L + 2.5 * S, 12, text="Risk prioritization matrix (Likelihood x Impact)", font=FONT_B, fill=PRIMARY)
        cells = {}
        for r in self.rows:
            if r["status"] != "Closed":
                cells.setdefault((r["likelihood"], r["impact"]), []).append(r["code"])
        for li in range(1, 6):
            for im in range(1, 6):
                score = li * im
                col = "#f5b7b1" if score >= 15 else ("#fad7a0" if score >= 8 else "#abebc6")
                x, y = L + (im - 1) * S, T + (5 - li) * S
                c.create_rectangle(x, y, x + S, y + S, fill=col, outline="white", width=2)
                c.create_text(x + S - 6, y + 8, text=str(score), anchor="e", font=("Segoe UI", 7), fill="#555")
                codes = cells.get((li, im), [])
                c.create_text(x + S / 2, y + S / 2 + 4, text="\n".join(codes), font=("Segoe UI", 9, "bold"), fill=TEXT)
            c.create_text(L - 10, T + (5 - li) * S + S / 2, text=str(li), font=FONT_B)
        for im in range(1, 6):
            c.create_text(L + (im - 1) * S + S / 2, T + 5 * S + 12, text=str(im), font=FONT_B)
        c.create_text(L + 2.5 * S, T + 5 * S + 32, text="IMPACT  (1 negligible ... 5 severe)", font=("Segoe UI", 9))
        c.create_text(18, T + 2.5 * S, text="LIKELIHOOD", angle=90, font=("Segoe UI", 9))
        for i, (t, col) in enumerate((("High >= 15", "#f5b7b1"), ("Medium 8-14", "#fad7a0"), ("Low < 8", "#abebc6"))):
            c.create_rectangle(L + i * 125, T + 5 * S + 46, L + i * 125 + 14, T + 5 * S + 58, fill=col, outline="")
            c.create_text(L + i * 125 + 18, T + 5 * S + 52, text=t, anchor="w", font=("Segoe UI", 8))

    def _draw_pdpc(self):
        tree = self.svc.pdpc_tree()
        c = self.pdpc.canvas
        c.delete("all")
        cols = [(20, 190), (240, 200), (470, 250), (750, 380)]
        heads = ["Goal", "Activity / deliverable", "Potential problem (ranked risk)", "Countermeasures (O feasible / X not)"]
        for (x, w), h in zip(cols, heads):
            c.create_text(x, 14, text=h, anchor="w", font=FONT_B, fill=PRIMARY)
        y, gap, top = 40, 8, 40
        area_mid = []

        def box(x, y, w, h, text, fill, outline, bold=False):
            c.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline, width=1.5)
            c.create_text(x + 8, y + h / 2, text=text, anchor="w", width=w - 14,
                          font=("Segoe UI", 9, "bold" if bold else "normal"), fill=TEXT)
            return y + h / 2

        for area, risks in tree["areas"].items():
            area_top = y
            risk_mids = []
            for r in sorted(risks, key=lambda x: x["rank"]):
                ms = r["measures"] or [{"action_type": "-", "action": "No countermeasure defined", "feasible": 0}]
                rtop = y
                m_mids = []
                for m in ms:
                    col = "#e8f6ef" if m["action_type"] == "Preventive" else ("#eaf2fb" if m["action_type"] == "Corrective" else "#fdecea")
                    mark = "O" if m["feasible"] else "X"
                    m_mids.append(box(cols[3][0], y, cols[3][1], 40, f"[{mark}] {m['action_type']}: {m['action']}",
                                      col, GREEN if m["feasible"] else RED))
                    y += 40 + gap
                rh = y - gap - rtop
                lvl_col = {"High": "#fadbd8", "Medium": "#fdebd0", "Low": "#d5f5e3"}[r["level"]]
                rm = box(cols[2][0], rtop + rh / 2 - 26, cols[2][1], 52,
                         f"#{r['rank']} {r['code']} (score {r['score']}, {r['level']})\n{r['title']}", lvl_col, AMBER)
                for mm in m_mids:
                    c.create_line(cols[2][0] + cols[2][1], rm, cols[3][0] - 14, rm, cols[3][0] - 14, mm, cols[3][0], mm,
                                  fill="#7f8c8d", arrow="last", arrowshape=(6, 7, 3))
                risk_mids.append(rm)
                y += 6
            ah = y - area_top
            am = box(cols[1][0], area_top + ah / 2 - 24, cols[1][1], 48, area, "#eef2f7", PRIMARY, bold=True)
            for rm in risk_mids:
                c.create_line(cols[1][0] + cols[1][1], am, cols[2][0] - 14, am, cols[2][0] - 14, rm, cols[2][0], rm,
                              fill="#7f8c8d", arrow="last", arrowshape=(6, 7, 3))
            area_mid.append(am)
            y += 14
        if area_mid:
            gm = box(cols[0][0], min(area_mid[0] - 40, (top + y) / 2 - 40), cols[0][1], 80, tree["goal"], "#d6e4f0",
                     PRIMARY, bold=True)
            for am in area_mid:
                c.create_line(cols[0][0] + cols[0][1], gm, cols[1][0] - 14, gm, cols[1][0] - 14, am, cols[1][0], am,
                              fill=PRIMARY, arrow="last", arrowshape=(6, 7, 3))
        self.pdpc.finish()

    def _risk_fields(self):
        return [{"key": "title", "label": "Risk / issue"},
                {"key": "description", "label": "Description", "kind": "text", "height": 3},
                {"key": "category", "label": "Category", "kind": "combo", "options": [(c, c) for c in RISK_CATEGORIES]},
                {"key": "wbs_id", "label": "Affected deliverable", "kind": "combo", "options": self.app.wbs_opts(none=True)},
                {"key": "likelihood", "label": "Likelihood (1-5)", "default": "3"},
                {"key": "impact", "label": "Impact (1-5)", "default": "3"},
                {"key": "owner_id", "label": "Owner", "kind": "combo", "options": self.app.members()},
                {"key": "status", "label": "Status", "kind": "combo", "options": [(s, s) for s in RISK_STATUSES],
                 "default": "Open"}]

    def add_risk(self):
        FormDialog(self, "Add risk / issue", self._risk_fields(),
                   on_submit=lambda v: (self.svc.save_risk(v), self.app.refresh_all())).show()

    def edit_risk(self):
        rid = self.app.need(self.risks)
        if rid:
            r = self.svc.one("SELECT * FROM risks WHERE id=?", (rid,))
            FormDialog(self, f"Edit {r['code']}", self._risk_fields(), r,
                       on_submit=lambda v: (self.svc.save_risk(v, rid), self.app.refresh_all())).show()

    def del_risk(self):
        rid = self.app.need(self.risks)
        if rid and messagebox.askyesno("Delete", "Delete this risk and its countermeasures?", parent=self):
            self.app.run(self.svc.delete_risk, rid)

    def _cm_fields(self):
        return [{"key": "risk_id", "label": "Risk", "kind": "combo",
                 "options": [(r["id"], f"{r['code']} {r['title']}") for r in self.rows]},
                {"key": "action_type", "label": "Type", "kind": "combo",
                 "options": [("Preventive", "Preventive (before it happens)"), ("Corrective", "Corrective (if it happens)")]},
                {"key": "action", "label": "Action", "kind": "text", "height": 3},
                {"key": "owner_id", "label": "Owner", "kind": "combo", "options": self.app.members()},
                {"key": "feasible", "label": "Feasible (O)", "kind": "check", "default": True}]

    def add_cm(self):
        sel = self.risks.selected_int()
        FormDialog(self, "Add countermeasure", self._cm_fields(), {"risk_id": sel, "action_type": "Preventive", "feasible": 1},
                   on_submit=lambda v: (self.svc.save_countermeasure(v), self.app.refresh_all())).show()

    def edit_cm(self):
        cid = self.app.need(self.cms)
        if cid:
            m = self.svc.one("SELECT * FROM countermeasures WHERE id=?", (cid,))
            FormDialog(self, "Edit countermeasure", self._cm_fields(), m,
                       on_submit=lambda v: (self.svc.save_countermeasure(v, cid), self.app.refresh_all())).show()

    def del_cm(self):
        cid = self.app.need(self.cms)
        if cid and messagebox.askyesno("Delete", "Delete this countermeasure?", parent=self):
            self.app.run(self.svc.delete_countermeasure, cid)
