# Smart Healthcare – Software Project Management System (SPMS)

CSE-494 Software Project Management – Mid-term (CLO-6). Desktop application (Python 3 + Tkinter + SQLite) for planning, executing, monitoring and controlling the Smart Healthcare project from the case study.

## Run

```
python main.py                       # first run creates spms.db with the case-study sample data
python -m unittest discover -s tests -v   # 35 automated test cases -> TEST_CASES.md
python main.py --export-sql          # writes schema.sql + sample_data.sql
python make_screenshots.py           # screenshots/ of every module
build_exe.bat                        # Windows .exe via PyInstaller -> dist\SmartHealthcareSPMS.exe
```

Python 3.10+ only; no third-party packages needed to run (Pillow only for screenshots, PyInstaller only for the .exe).

## Structure

| File | Purpose |
|---|---|
| `main.py` | Entry point |
| `spms/db.py` | SQLite schema (15 tables, FK + CHECK constraints), export |
| `spms/calculations.py` | CPM forward/backward pass, critical path, delay forecast & propagation, EVM, risk scoring |
| `spms/services.py` | Validation, CRUD, change control, scope control, closure rules, dashboard, HTML report |
| `spms/seed.py` | Realistic case-study data (7-person team, 18 activities, 3 CRs, defects, risks) |
| `spms/gui.py`, `spms/widgets.py` | Tkinter GUI |
| `tests/test_spms.py` | Test cases with expected vs actual results |
| `schema.sql`, `sample_data.sql` | Database schema and sample data dump |

## Requirement → implementation map

| Module (marks) | Where in the app |
|---|---|
| 1 Initiation & Integration (4) | Tab 1: charter (objectives, stakeholders, scope in/out, budget, deadline); management plan (scope/schedule/cost/quality/risk/communication, auto-generated from live data); project status + milestones (planned/forecast/actual, auto status); team responsibilities; closure (blocked until all work done, no critical defects, no pending CRs, all checks pass → project becomes read-only); baseline history + audit log |
| 2 Scope & WBS (4) | Tab 2: requirements (add/edit/MoSCoW priority/approve/reject); hierarchical WBS tree with auto codes and rolled-up budget; change requests with justification, cost & schedule impact, approval status, impact preview; **unapproved requirements cannot enter the WBS, and activities cannot be created outside approved scope** |
| 3 Schedule & Resources (5) | Tab 3: activities with assignee, duration, FS dependencies (cycle detection); CPM schedule (ES/EF/LS/LF/float/critical path); progress tracking; forecast that identifies delayed activities and computes impact on every dependent activity and the deadline; Gantt chart (baseline vs forecast, dependencies, milestones, status date, deadline) |
| 4 Cost & EVM (5) | Tab 4: activity cost estimates (duration × daily rate), BAC, expense ledger (actual cost), budgeted cost of work performed; PV, EV, AC, CV, SV, **CPI, SPI**, EAC, ETC, VAC, TCPI; configurable thresholds with automatic WARNING/CRITICAL messages; S-curve |
| 5 Quality & Risk (4) | Tab 5 Quality: defect tracking (severity, assignee, status, dates); quality checklist per deliverable with inspection/test results (a failed check auto-raises a defect). Tab 5 Risk: 5×5 Likelihood × Impact prioritization matrix with ranking; PDPC chart (goal → deliverable → potential problem → preventive/corrective countermeasures, O/X feasibility) |
| 6 Integration & Reporting (3) | One SQLite DB shared by all modules; validation on every write; consistency check; dashboard (progress, budget, CPI/SPI, forecast finish, delayed activities, pending CRs, unresolved critical defects, alerts); HTML status report export |

## How an approved change request affects the project (mandatory req. 4)

Approving a CR (Tab 2 → Change requests → Approve) in one transaction:
1. **Scope** – its requirement becomes Approved; a WBS deliverable + work package is added.
2. **Schedule** – a new activity (duration = schedule impact) is inserted after the chosen predecessor and before the chosen successor; CPM recalculates, so every downstream date moves.
3. **Budget** – approved budget += cost impact; the activity's budget raises BAC; EVM recomputes.
4. The deadline is extended, recorded in baseline history and the audit log. Any error rolls everything back.

Sample data: CR-001 (AI diagnosis, +PKR 450,000, +12 days) is approved, CR-002 (mobile app, +PKR 350,000, +9 days) is **pending for the live demo** (together = +PKR 800,000, +3 weeks as in the case), CR-003 (blockchain) was rejected.

## Demo script (≈5 min)

1. **Dashboard** – status date 2026-10-26: 74.2% complete vs 78.3% planned, CPI 0.920 / SPI 0.947 (warnings), forecast 13 days late, 2 critical defects (double-booking, record overwrite).
2. **Tab 3 → Delay analysis** – T12 integration testing (25%) is the root cause; shows the slip on T13, T18, T14, T15 and the deadline. Open the **Gantt chart**.
3. **Tab 2 → Change requests** – select CR-002 → *Preview impact* → *Approve*. Show the budget 5.45M → 5.80M, deadline 2026-12-04 → 12-13, new WBS 1.6 and activity T19 in the Gantt.
4. **Validation** – R08 (Proposed) is not offered when adding a WBS element; set T01 to depend on T15 (cycle), or set 100% without a finish date: each is rejected with a message.
5. **Tab 4** – change the CPI warning threshold on the Dashboard to 0.90 and see the warning disappear.
6. **Tab 5** – record a failing result for Q07 (video consultation) → a defect is raised automatically; show the risk matrix and PDPC.
7. **Tab 1 → Project closure** – shows why closure is blocked. Export the HTML report.

*Reset demo data* (header) restores the original sample data at any time.
