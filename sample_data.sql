-- Smart Healthcare SPMS - schema + sample data dump
BEGIN TRANSACTION;
CREATE TABLE audit_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    action  TEXT NOT NULL,
    details TEXT
);
INSERT INTO "audit_log" VALUES(1,'2026-10-25 18:46','Charter created','Smart Healthcare Project Management & Monitoring System');
INSERT INTO "audit_log" VALUES(2,'2026-10-25 18:46','Requirement added','R01');
INSERT INTO "audit_log" VALUES(3,'2026-10-25 18:46','Requirement added','R02');
INSERT INTO "audit_log" VALUES(4,'2026-10-25 18:46','Requirement added','R03');
INSERT INTO "audit_log" VALUES(5,'2026-10-25 18:46','Requirement added','R04');
INSERT INTO "audit_log" VALUES(6,'2026-10-25 18:46','Requirement added','R05');
INSERT INTO "audit_log" VALUES(7,'2026-10-25 18:46','Requirement added','R06');
INSERT INTO "audit_log" VALUES(8,'2026-10-25 18:46','Requirement added','R07');
INSERT INTO "audit_log" VALUES(9,'2026-10-25 18:46','Requirement added','R08');
INSERT INTO "audit_log" VALUES(10,'2026-10-25 18:46','Requirement approved','R01');
INSERT INTO "audit_log" VALUES(11,'2026-10-25 18:46','Requirement approved','R02');
INSERT INTO "audit_log" VALUES(12,'2026-10-25 18:46','Requirement approved','R03');
INSERT INTO "audit_log" VALUES(13,'2026-10-25 18:46','Requirement approved','R04');
INSERT INTO "audit_log" VALUES(14,'2026-10-25 18:46','Requirement approved','R05');
INSERT INTO "audit_log" VALUES(15,'2026-10-25 18:46','Requirement approved','R06');
INSERT INTO "audit_log" VALUES(16,'2026-10-25 18:46','Requirement approved','R07');
INSERT INTO "audit_log" VALUES(17,'2026-10-25 18:46','Change request raised','CR-001: AI-based preliminary diagnosis module');
INSERT INTO "audit_log" VALUES(18,'2026-10-25 18:46','Change request approved','CR-001: budget PKR 5,000,000 -> PKR 5,450,000, deadline 2026-11-22 -> 2026-12-04, activity T18');
INSERT INTO "audit_log" VALUES(19,'2026-10-25 18:46','Change request raised','CR-002: Patient mobile application (Android/iOS)');
INSERT INTO "audit_log" VALUES(20,'2026-10-25 18:46','Change request raised','CR-003: Blockchain-based patient record ledger');
INSERT INTO "audit_log" VALUES(21,'2026-10-25 18:46','Change request rejected','CR-003');
INSERT INTO "audit_log" VALUES(22,'2026-10-25 18:46','Defect saved','D01 [Critical] Open');
INSERT INTO "audit_log" VALUES(23,'2026-10-25 18:46','Defect saved','D02 [Critical] In Progress');
INSERT INTO "audit_log" VALUES(24,'2026-10-25 18:46','Defect saved','D03 [High] Resolved');
INSERT INTO "audit_log" VALUES(25,'2026-10-25 18:46','Defect saved','D04 [Medium] Closed');
INSERT INTO "audit_log" VALUES(26,'2026-10-25 18:46','Defect saved','D05 [Low] Open');
INSERT INTO "audit_log" VALUES(27,'2026-10-25 18:46','Defect saved','D06 [High] Open');
INSERT INTO "audit_log" VALUES(28,'2026-10-25 18:46','Defect saved','D07 [High] In Progress');
INSERT INTO "audit_log" VALUES(29,'2026-10-25 18:46','Sample data loaded','Smart Healthcare case study');
CREATE TABLE baseline_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    change_date  TEXT NOT NULL,
    cr_id        INTEGER REFERENCES change_requests(id),
    old_budget   REAL NOT NULL,
    new_budget   REAL NOT NULL,
    old_deadline TEXT NOT NULL,
    new_deadline TEXT NOT NULL,
    note         TEXT
);
INSERT INTO "baseline_history" VALUES(1,'2026-10-05',1,5000000.0,5450000.0,'2026-11-22','2026-12-04','CR-001 approved: +PKR 450,000, +12 days');
CREATE TABLE change_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT,
    justification   TEXT NOT NULL,
    requested_by    TEXT NOT NULL,
    request_date    TEXT NOT NULL,
    priority        TEXT NOT NULL CHECK (priority IN ('Must','Should','Could','Won''t')),
    cost_impact     REAL NOT NULL CHECK (cost_impact >= 0),
    schedule_impact INTEGER NOT NULL CHECK (schedule_impact >= 0),
    after_task_id   INTEGER REFERENCES tasks(id),
    before_task_id  INTEGER REFERENCES tasks(id),
    assignee_id     INTEGER REFERENCES team_members(id),
    status          TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Rejected')),
    decision_date   TEXT,
    decided_by      TEXT,
    decision_notes  TEXT
);
INSERT INTO "change_requests" VALUES(1,'CR-001','AI-based preliminary diagnosis module','Symptom checker suggesting a preliminary diagnosis and the right specialist before booking.','Hospital management wants to reduce unnecessary specialist visits and triage load.','Hospital Network Board','2026-09-28','Should',450000.0,12,13,14,3,'Approved','2026-10-05','Hospital Network Board / CCB','Approved with +12 days and PKR 450,000.');
INSERT INTO "change_requests" VALUES(2,'CR-002','Patient mobile application (Android/iOS)','Mobile app for booking appointments, viewing lab reports and joining consultations.','More than 60% of patients use smartphones; administrators expect fewer call-centre bookings.','Hospital administrators','2026-10-12','Should',350000.0,9,18,14,5,'Pending',NULL,NULL,NULL);
INSERT INTO "change_requests" VALUES(3,'CR-003','Blockchain-based patient record ledger','Store record hashes on a private blockchain.','Suggested by one hospital''s IT head for tamper-evidence.','IT Head, Hospital 3','2026-10-01','Could',600000.0,20,17,14,6,'Rejected','2026-10-08','Change Control Board','Out of scope; audit trail in the database already gives tamper evidence.');
CREATE TABLE closure (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    closed_date TEXT NOT NULL,
    final_cost  REAL NOT NULL,
    accepted_by TEXT NOT NULL,
    lessons     TEXT NOT NULL,
    notes       TEXT
);
CREATE TABLE countermeasures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id     INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('Preventive','Corrective')),
    action      TEXT NOT NULL,
    owner_id    INTEGER REFERENCES team_members(id),
    feasible    INTEGER NOT NULL DEFAULT 1 CHECK (feasible IN (0,1))
);
INSERT INTO "countermeasures" VALUES(1,1,'Preventive','Formal change control board; every request needs a CR with cost/schedule impact',1,1);
INSERT INTO "countermeasures" VALUES(2,1,'Corrective','Re-baseline schedule and budget only through approved CRs',1,1);
INSERT INTO "countermeasures" VALUES(3,2,'Preventive','Code reviews and unit tests before integration',2,1);
INSERT INTO "countermeasures" VALUES(4,2,'Corrective','Dedicated defect-fix sprint and daily triage of critical defects',7,1);
INSERT INTO "countermeasures" VALUES(5,2,'Corrective','Phased go-live (2 hospitals first)',1,1);
INSERT INTO "countermeasures" VALUES(6,3,'Preventive','Weekly EVM review with CPI/SPI thresholds',1,1);
INSERT INTO "countermeasures" VALUES(7,3,'Corrective','Use management reserve; descope ''Could'' requirements',1,1);
INSERT INTO "countermeasures" VALUES(8,4,'Preventive','Label output as preliminary; doctor must confirm',3,1);
INSERT INTO "countermeasures" VALUES(9,4,'Corrective','Disable module via feature flag if accuracy < 85%',3,1);
INSERT INTO "countermeasures" VALUES(10,5,'Preventive','Adaptive bitrate and audio-only fallback',2,1);
INSERT INTO "countermeasures" VALUES(11,5,'Corrective','Switch to phone consultation and reschedule',1,1);
INSERT INTO "countermeasures" VALUES(12,6,'Preventive','Encryption at rest, role-based access, audit logging',6,1);
INSERT INTO "countermeasures" VALUES(13,6,'Corrective','Incident response plan and breach notification',1,1);
INSERT INTO "countermeasures" VALUES(14,7,'Preventive','Agree on HL7/CSV export format early',3,1);
INSERT INTO "countermeasures" VALUES(15,7,'Corrective','Manual upload fallback for lab staff',4,1);
INSERT INTO "countermeasures" VALUES(16,8,'Preventive','Pair programming and documentation of modules',2,1);
INSERT INTO "countermeasures" VALUES(17,8,'Corrective','Hire a contract developer',1,0);
CREATE TABLE defects (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    description   TEXT,
    module        TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('Critical','High','Medium','Low')),
    assigned_id   INTEGER REFERENCES team_members(id),
    status        TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','In Progress','Resolved','Closed')),
    reported_date TEXT NOT NULL,
    resolved_date TEXT,
    task_id       INTEGER REFERENCES tasks(id)
);
INSERT INTO "defects" VALUES(1,'D01','Same doctor slot can be double-booked','Found during integration testing (2026-10-19).','Patient Appointments','Critical',2,'Open','2026-10-19',NULL,5);
INSERT INTO "defects" VALUES(2,'D02','Patient record overwritten on concurrent edits','Found during integration testing (2026-10-20).','Patient Records','Critical',6,'In Progress','2026-10-20',NULL,17);
INSERT INTO "defects" VALUES(3,'D03','Appointment reminder shows wrong time zone','Found during integration testing (2026-10-17).','Patient Appointments','High',2,'Resolved','2026-10-17','2026-10-22',5);
INSERT INTO "defects" VALUES(4,'D04','Billing tax rounding error of PKR 1','Found during integration testing (2026-10-17).','Hospital Billing','Medium',6,'Closed','2026-10-17','2026-10-21',10);
INSERT INTO "defects" VALUES(5,'D05','Lab report PDF not rendering on Safari','Found during integration testing (2026-10-21).','Laboratory Reports','Low',4,'Open','2026-10-21',NULL,8);
INSERT INTO "defects" VALUES(6,'D06','Video consultation drops on low bandwidth','Found during integration testing (2026-10-22).','Online Consultations','High',2,'Open','2026-10-22',NULL,9);
INSERT INTO "defects" VALUES(7,'D07','Cancelled appointment still visible in doctor schedule','Found during integration testing (2026-10-23).','Doctor Schedules','High',3,'In Progress','2026-10-23',NULL,7);
CREATE TABLE dependencies (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    pred_id INTEGER NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (task_id, pred_id),
    CHECK (task_id <> pred_id)
);
INSERT INTO "dependencies" VALUES(2,1);
INSERT INTO "dependencies" VALUES(3,2);
INSERT INTO "dependencies" VALUES(4,2);
INSERT INTO "dependencies" VALUES(5,3);
INSERT INTO "dependencies" VALUES(6,4);
INSERT INTO "dependencies" VALUES(7,3);
INSERT INTO "dependencies" VALUES(8,7);
INSERT INTO "dependencies" VALUES(9,5);
INSERT INTO "dependencies" VALUES(10,3);
INSERT INTO "dependencies" VALUES(11,4);
INSERT INTO "dependencies" VALUES(12,6);
INSERT INTO "dependencies" VALUES(12,8);
INSERT INTO "dependencies" VALUES(12,9);
INSERT INTO "dependencies" VALUES(12,10);
INSERT INTO "dependencies" VALUES(12,11);
INSERT INTO "dependencies" VALUES(12,17);
INSERT INTO "dependencies" VALUES(13,12);
INSERT INTO "dependencies" VALUES(14,13);
INSERT INTO "dependencies" VALUES(15,16);
INSERT INTO "dependencies" VALUES(15,14);
INSERT INTO "dependencies" VALUES(16,3);
INSERT INTO "dependencies" VALUES(17,3);
INSERT INTO "dependencies" VALUES(18,13);
INSERT INTO "dependencies" VALUES(14,18);
CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    exp_date    TEXT NOT NULL,
    amount      REAL NOT NULL CHECK (amount > 0),
    description TEXT
);
INSERT INTO "expenses" VALUES(1,1,'2026-08-03',60000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(2,2,'2026-08-08',80000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(3,2,'2026-08-15',80000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(4,3,'2026-08-20',132500.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(5,3,'2026-08-27',132500.0,'Labour & resources');
INSERT INTO "expenses" VALUES(6,4,'2026-08-20',55000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(7,4,'2026-08-27',55000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(8,5,'2026-08-30',113333.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(9,5,'2026-09-06',113333.0,'Labour & resources');
INSERT INTO "expenses" VALUES(10,5,'2026-09-13',113334.0,'Labour & resources');
INSERT INTO "expenses" VALUES(11,6,'2026-08-29',60000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(12,6,'2026-09-05',60000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(13,6,'2026-09-12',60000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(14,7,'2026-08-30',110000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(15,7,'2026-09-06',110000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(16,8,'2026-09-13',96667.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(17,8,'2026-09-20',96667.0,'Labour & resources');
INSERT INTO "expenses" VALUES(18,8,'2026-09-27',96666.0,'Labour & resources');
INSERT INTO "expenses" VALUES(19,9,'2026-09-19',125000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(20,9,'2026-09-26',125000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(21,9,'2026-10-03',125000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(22,9,'2026-10-10',125000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(23,10,'2026-08-30',100000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(24,10,'2026-09-06',100000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(25,10,'2026-09-13',100000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(26,11,'2026-08-29',80000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(27,11,'2026-09-05',80000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(28,11,'2026-09-12',80000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(29,11,'2026-09-19',80000.0,'Labour & resources');
INSERT INTO "expenses" VALUES(30,16,'2026-08-30',960000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(31,17,'2026-08-30',112500.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(32,17,'2026-09-06',112500.0,'Labour & resources');
INSERT INTO "expenses" VALUES(33,12,'2026-10-16',35000.0,'Labour, tools & setup');
INSERT INTO "expenses" VALUES(34,12,'2026-10-23',35000.0,'Labour & resources');
CREATE TABLE milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    owner_id    INTEGER REFERENCES team_members(id),
    description TEXT
);
INSERT INTO "milestones" VALUES(1,'M1 Charter approved & kickoff',1,1,'');
INSERT INTO "milestones" VALUES(2,'M2 Requirements & design signed off',3,6,'');
INSERT INTO "milestones" VALUES(3,'M3 Core modules complete',9,2,'');
INSERT INTO "milestones" VALUES(4,'M4 System testing complete',13,7,'');
INSERT INTO "milestones" VALUES(5,'M5 UAT sign-off',14,7,'');
INSERT INTO "milestones" VALUES(6,'M6 Go-live at 5 hospitals (project closure)',15,1,'');
CREATE TABLE plan_sections (
    section  TEXT PRIMARY KEY,
    content  TEXT NOT NULL DEFAULT '',
    updated  TEXT
);
INSERT INTO "plan_sections" VALUES('Scope Management','In scope: Web system for appointments, doctor schedules, lab reports, online consultations, billing, patient records; deployment and staff training at 5 hospitals.
Out of scope: Medical hardware procurement, insurance-claim integration, pharmacy inventory, data migration of paper records older than 2 years.

Approved scope baseline (8 requirements):
  R01 [Must] Patient appointment booking, rescheduling and cancellation
  R02 [Must] Doctor schedule and availability management
  R03 [Must] Laboratory report upload, approval and patient access
  R04 [Should] Online video consultations
  R05 [Must] Hospital billing, invoices and payments
  R06 [Must] Patient record management (EMR basic)
  R07 [Must] Multi-hospital support for 5 branches
  R09 [Should] AI-based preliminary diagnosis module

WBS work packages: 17
  1.1.1 Initiation & Planning
  1.1.2 Deployment & Training
  1.2.1 Requirements Analysis
  1.2.2 Architecture & Database Design
  1.2.3 UI/UX Design
  1.2.4 Infrastructure & Licences
  1.3.1 Patient Appointments
  1.3.2 Doctor Schedules
  1.3.3 Laboratory Reports
  1.3.4 Online Consultations
  1.3.5 Hospital Billing
  1.3.6 Patient Records
  1.3.7 Web Front-end
  1.4.1 Integration & System Testing
  1.4.2 Defect Fixing & Regression
  1.4.3 User Acceptance Testing
  1.5.1 AI-based preliminary diagnosis module - development

Change control: every new requirement must enter through a change request; only approved requirements may be linked to WBS work packages.','2026-10-25 18:46');
INSERT INTO "plan_sections" VALUES('Schedule Management','Start: 2026-08-03   Approved deadline: 2026-12-04 (original 2026-11-22)
Planned finish (CPM): 2026-12-04
Activities: 18, critical path: T01 -> T02 -> T03 -> T05 -> T09 -> T12 -> T13 -> T14 -> T15 -> T18
Milestones:
  M1 Charter approved & kickoff: planned 2026-08-07
  M2 Requirements & design signed off: planned 2026-08-27
  M3 Core modules complete: planned 2026-10-09
  M4 System testing complete: planned 2026-11-02
  M5 UAT sign-off: planned 2026-11-24
  M6 Go-live at 5 hospitals (project closure): planned 2026-12-04

Method: finish-to-start dependencies, forward/backward pass, weekly progress updates against the status date.','2026-10-25 18:46');
INSERT INTO "plan_sections" VALUES('Cost Management','Approved budget: PKR 5,450,000 (original PKR 5,000,000)
Planned cost baseline (BAC): PKR 4,960,000
Management reserve: PKR 490,000
EVM thresholds: CPI warning < 0.95, critical < 0.9; SPI warning < 0.95, critical < 0.9.
Actual costs are recorded per activity as expenses; PV, EV, AC, CPI and SPI are computed automatically at each status date.','2026-10-25 18:46');
INSERT INTO "plan_sections" VALUES('Quality Management','Quality checklist items: 8. Every deliverable is inspected or tested before acceptance. Failed checks raise defects.
Defect severity: Critical / High / Medium / Low. Release criteria: zero open Critical defects, all checklist items Pass.','2026-10-25 18:46');
INSERT INTO "plan_sections" VALUES('Risk Management','Risks are scored Likelihood x Impact (1-5 each) in the prioritization matrix. Score >= 15 High, 8-14 Medium, < 8 Low. High risks require preventive and corrective countermeasures in the PDPC.','2026-10-25 18:46');
INSERT INTO "plan_sections" VALUES('Communication','Sponsor: Hospital Network Board (CEO office); Project manager: Ayesha Khan.
Stakeholders: Hospital Network Board (sponsor); hospital administrators (5); doctors; lab staff; billing department; patients; IT department; development team; QA.
Weekly status report generated from the dashboard.','2026-10-25 18:46');
CREATE TABLE project (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    name              TEXT    NOT NULL,
    client            TEXT,
    sponsor           TEXT,
    manager           TEXT,
    objectives        TEXT    NOT NULL,
    stakeholders      TEXT    NOT NULL,
    scope_in          TEXT    NOT NULL,
    scope_out         TEXT,
    approved_budget   REAL    NOT NULL CHECK (approved_budget > 0),
    baseline_budget   REAL    NOT NULL CHECK (baseline_budget > 0),
    start_date        TEXT    NOT NULL,
    deadline          TEXT    NOT NULL,
    baseline_deadline TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'Planning'
                      CHECK (status IN ('Initiated','Planning','Executing','Monitoring & Control','Closed')),
    status_date       TEXT    NOT NULL,
    cpi_warn          REAL    NOT NULL DEFAULT 0.95,
    cpi_crit          REAL    NOT NULL DEFAULT 0.90,
    spi_warn          REAL    NOT NULL DEFAULT 0.95,
    spi_crit          REAL    NOT NULL DEFAULT 0.90
);
INSERT INTO "project" VALUES(1,'Smart Healthcare Project Management & Monitoring System','Network of five partner hospitals','Hospital Network Board (CEO office)','Ayesha Khan','1. Deliver an integrated system for patient appointments, laboratory reports, doctor schedules, online consultations and hospital billing across 5 hospitals.
2. Go live within 16 weeks and within PKR 5,000,000.
3. Zero critical defects at go-live; 95% of appointments booked online within 3 months.','Hospital Network Board (sponsor); hospital administrators (5); doctors; lab staff; billing department; patients; IT department; development team; QA.','Web system for appointments, doctor schedules, lab reports, online consultations, billing, patient records; deployment and staff training at 5 hospitals.','Medical hardware procurement, insurance-claim integration, pharmacy inventory, data migration of paper records older than 2 years.',5450000.0,5000000.0,'2026-08-03','2026-12-04','2026-11-22','Monitoring & Control','2026-10-26',0.95,0.9,0.95,0.9);
CREATE TABLE quality_checks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL UNIQUE,
    wbs_id       INTEGER NOT NULL REFERENCES wbs(id),
    criterion    TEXT NOT NULL,
    check_type   TEXT NOT NULL CHECK (check_type IN ('Inspection','Test')),
    expected     TEXT,
    actual       TEXT,
    result       TEXT NOT NULL DEFAULT 'Pending' CHECK (result IN ('Pending','Pass','Fail')),
    inspector_id INTEGER REFERENCES team_members(id),
    check_date   TEXT,
    defect_id    INTEGER REFERENCES defects(id) ON DELETE SET NULL
);
INSERT INTO "quality_checks" VALUES(1,'Q01',7,'Database schema normalised to 3NF and reviewed','Inspection','Review sign-off, no blocking comments','Signed off by PM and DB developer','Pass',1,'2026-08-29',NULL);
INSERT INTO "quality_checks" VALUES(2,'Q02',10,'No double booking of a doctor time slot','Test','Second booking of same slot is rejected','Second booking accepted - two patients in same slot','Fail',7,'2026-10-19',1);
INSERT INTO "quality_checks" VALUES(3,'Q03',10,'Appointment API response time under 500 ms','Test','p95 < 500 ms with 200 users','p95 = 340 ms','Pass',7,'2026-10-18',NULL);
INSERT INTO "quality_checks" VALUES(4,'Q04',15,'Concurrent edit protection on patient records','Test','Second editor gets conflict warning','Last write silently overwrote first','Fail',7,'2026-10-20',2);
INSERT INTO "quality_checks" VALUES(5,'Q05',14,'Invoice totals match manual calculation','Test','100 sample invoices match to the rupee','100/100 matched after fix D04','Pass',7,'2026-10-21',NULL);
INSERT INTO "quality_checks" VALUES(6,'Q06',12,'Lab reports up to 10 MB upload and open','Test','Upload + open < 5 s','3.1 s average','Pass',7,'2026-10-21',NULL);
INSERT INTO "quality_checks" VALUES(7,'Q07',13,'Video consultation stable for 30 minutes','Test','No drop at 1 Mbps',NULL,'Pending',NULL,NULL,NULL);
INSERT INTO "quality_checks" VALUES(8,'Q08',4,'Training material reviewed by hospital admins','Inspection','Approved by 5 admins',NULL,'Pending',NULL,NULL,NULL);
CREATE TABLE requirements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT,
    priority    TEXT NOT NULL CHECK (priority IN ('Must','Should','Could','Won''t')),
    status      TEXT NOT NULL DEFAULT 'Proposed' CHECK (status IN ('Proposed','Approved','Rejected')),
    source      TEXT NOT NULL DEFAULT 'Original' CHECK (source IN ('Original','Change Request')),
    cr_id       INTEGER REFERENCES change_requests(id) ON DELETE CASCADE,
    created     TEXT
);
INSERT INTO "requirements" VALUES(1,'R01','Patient appointment booking, rescheduling and cancellation','Patient appointment booking, rescheduling and cancellation','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(2,'R02','Doctor schedule and availability management','Doctor schedule and availability management','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(3,'R03','Laboratory report upload, approval and patient access','Laboratory report upload, approval and patient access','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(4,'R04','Online video consultations','Online video consultations','Should','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(5,'R05','Hospital billing, invoices and payments','Hospital billing, invoices and payments','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(6,'R06','Patient record management (EMR basic)','Patient record management (EMR basic)','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(7,'R07','Multi-hospital support for 5 branches','Multi-hospital support for 5 branches','Must','Approved','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(8,'R08','SMS appointment reminders','SMS appointment reminders','Could','Proposed','Original',NULL,'2026-10-26');
INSERT INTO "requirements" VALUES(9,'R09','AI-based preliminary diagnosis module','Symptom checker suggesting a preliminary diagnosis and the right specialist before booking.','Should','Approved','Change Request',1,'2026-09-28');
INSERT INTO "requirements" VALUES(10,'R10','Patient mobile application (Android/iOS)','Mobile app for booking appointments, viewing lab reports and joining consultations.','Should','Proposed','Change Request',2,'2026-10-12');
INSERT INTO "requirements" VALUES(11,'R11','Blockchain-based patient record ledger','Store record hashes on a private blockchain.','Could','Rejected','Change Request',3,'2026-10-01');
CREATE TABLE risks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT,
    category    TEXT NOT NULL,
    wbs_id      INTEGER REFERENCES wbs(id),
    likelihood  INTEGER NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
    impact      INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    owner_id    INTEGER REFERENCES team_members(id),
    status      TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Mitigating','Closed'))
);
INSERT INTO "risks" VALUES(1,'RK01','Scope creep from hospital management','Scope creep from hospital management','Scope',NULL,5,4,1,'Mitigating');
INSERT INTO "risks" VALUES(2,'RK02','Critical defects delay go-live','Critical defects delay go-live','Quality',18,4,5,7,'Open');
INSERT INTO "risks" VALUES(3,'RK03','Budget overrun due to change requests and rework','Budget overrun due to change requests and rework','Cost',NULL,4,4,1,'Open');
INSERT INTO "risks" VALUES(4,'RK04','AI diagnosis gives inaccurate suggestions (liability)','AI diagnosis gives inaccurate suggestions (liability)','Technical',NULL,3,5,3,'Open');
INSERT INTO "risks" VALUES(5,'RK05','Poor internet at hospital sites affects consultations','Poor internet at hospital sites affects consultations','External',13,4,3,2,'Open');
INSERT INTO "risks" VALUES(6,'RK06','Patient data privacy breach','Patient data privacy breach','Security',15,2,5,6,'Open');
INSERT INTO "risks" VALUES(7,'RK07','Integration issues with lab equipment exports','Integration issues with lab equipment exports','Technical',12,3,3,3,'Mitigating');
INSERT INTO "risks" VALUES(8,'RK08','Key backend developer unavailable','Key backend developer unavailable','Resource',NULL,2,4,1,'Open');
CREATE TABLE tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    wbs_id       INTEGER NOT NULL REFERENCES wbs(id),
    assignee_id  INTEGER REFERENCES team_members(id),
    duration     INTEGER NOT NULL CHECK (duration > 0),
    budget       REAL    NOT NULL CHECK (budget >= 0),
    actual_start TEXT,
    actual_end   TEXT,
    percent      INTEGER NOT NULL DEFAULT 0 CHECK (percent BETWEEN 0 AND 100),
    cr_id        INTEGER REFERENCES change_requests(id),
    notes        TEXT
);
INSERT INTO "tasks" VALUES(1,'T01','Project charter, kickoff & plan',3,1,5,60000.0,'2026-08-03','2026-08-07',100,NULL,'');
INSERT INTO "tasks" VALUES(2,'T02','Requirements elicitation (5 hospitals)',6,1,10,150000.0,'2026-08-08','2026-08-19',100,NULL,'');
INSERT INTO "tasks" VALUES(3,'T03','System architecture & database design',7,6,10,250000.0,'2026-08-20','2026-08-29',100,NULL,'');
INSERT INTO "tasks" VALUES(4,'T04','UI/UX design & prototypes',8,4,10,110000.0,'2026-08-20','2026-08-28',100,NULL,'');
INSERT INTO "tasks" VALUES(5,'T05','Appointment module backend',10,2,18,300000.0,'2026-08-30','2026-09-18',100,NULL,'');
INSERT INTO "tasks" VALUES(6,'T06','Appointment module frontend',10,5,15,180000.0,'2026-08-29','2026-09-14',100,NULL,'');
INSERT INTO "tasks" VALUES(7,'T07','Doctor schedule module',11,3,14,220000.0,'2026-08-30','2026-09-12',100,NULL,'');
INSERT INTO "tasks" VALUES(8,'T08','Laboratory reports module',12,3,16,260000.0,'2026-09-13','2026-09-30',100,NULL,'');
INSERT INTO "tasks" VALUES(9,'T09','Online consultation module',13,2,25,420000.0,'2026-09-19','2026-10-15',100,NULL,'');
INSERT INTO "tasks" VALUES(10,'T10','Billing module',14,6,16,280000.0,'2026-08-30','2026-09-16',100,NULL,'');
INSERT INTO "tasks" VALUES(11,'T11','Front-end for schedules, labs & billing',16,4,25,300000.0,'2026-08-29','2026-09-25',100,NULL,'');
INSERT INTO "tasks" VALUES(12,'T12','Integration & system testing',18,7,14,200000.0,'2026-10-16',NULL,25,NULL,'');
INSERT INTO "tasks" VALUES(13,'T13','Defect fixing & regression testing',19,2,10,180000.0,NULL,NULL,0,NULL,'');
INSERT INTO "tasks" VALUES(14,'T14','User acceptance testing at hospitals',20,7,10,150000.0,NULL,NULL,0,NULL,'');
INSERT INTO "tasks" VALUES(15,'T15','Deployment to 5 hospitals & staff training',4,1,10,350000.0,NULL,NULL,0,NULL,'');
INSERT INTO "tasks" VALUES(16,'T16','Hosting, licences & server procurement',21,6,5,900000.0,'2026-08-30','2026-09-03',100,NULL,'');
INSERT INTO "tasks" VALUES(17,'T17','Patient record (EMR) module',15,6,12,200000.0,'2026-08-30','2026-09-12',100,NULL,'');
INSERT INTO "tasks" VALUES(18,'T18','AI-based preliminary diagnosis module',23,3,12,450000.0,NULL,NULL,0,1,'Created by approval of CR-001');
CREATE TABLE team_members (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    role           TEXT NOT NULL,
    responsibility TEXT,
    daily_rate     REAL NOT NULL CHECK (daily_rate >= 0),
    email          TEXT
);
INSERT INTO "team_members" VALUES(1,'Ayesha Khan','Project Manager','Planning, stakeholder communication, change control, reporting',12000.0,'ayesha@healthsoft.pk');
INSERT INTO "team_members" VALUES(2,'Usman Ali','Backend Developer','Appointments, consultations, APIs',9000.0,'usman@healthsoft.pk');
INSERT INTO "team_members" VALUES(3,'Hamza Raza','Backend Developer','Doctor schedules, lab reports, AI module',9000.0,'hamza@healthsoft.pk');
INSERT INTO "team_members" VALUES(4,'Fatima Noor','Frontend Developer','UI/UX design, web front-end',8000.0,'fatima@healthsoft.pk');
INSERT INTO "team_members" VALUES(5,'Bilal Ahmed','Frontend Developer','Appointment and billing screens, mobile UI',8000.0,'bilal@healthsoft.pk');
INSERT INTO "team_members" VALUES(6,'Zainab Tariq','Database Developer','Database design, billing, patient records',8500.0,'zainab@healthsoft.pk');
INSERT INTO "team_members" VALUES(7,'Hassan Iqbal','QA Engineer','Test planning, integration testing, UAT',7000.0,'hassan@healthsoft.pk');
CREATE TABLE wbs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    parent_id      INTEGER REFERENCES wbs(id),
    node_type      TEXT NOT NULL CHECK (node_type IN ('Project','Deliverable','Work Package')),
    requirement_id INTEGER REFERENCES requirements(id),
    description    TEXT
);
INSERT INTO "wbs" VALUES(1,'1','Smart Healthcare PMS',NULL,'Project',NULL,'');
INSERT INTO "wbs" VALUES(2,'1.1','Project Management',1,'Deliverable',NULL,'');
INSERT INTO "wbs" VALUES(3,'1.1.1','Initiation & Planning',2,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(4,'1.1.2','Deployment & Training',2,'Work Package',7,'');
INSERT INTO "wbs" VALUES(5,'1.2','Requirements & Design',1,'Deliverable',NULL,'');
INSERT INTO "wbs" VALUES(6,'1.2.1','Requirements Analysis',5,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(7,'1.2.2','Architecture & Database Design',5,'Work Package',7,'');
INSERT INTO "wbs" VALUES(8,'1.2.3','UI/UX Design',5,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(9,'1.3','Core Modules',1,'Deliverable',NULL,'');
INSERT INTO "wbs" VALUES(10,'1.3.1','Patient Appointments',9,'Work Package',1,'');
INSERT INTO "wbs" VALUES(11,'1.3.2','Doctor Schedules',9,'Work Package',2,'');
INSERT INTO "wbs" VALUES(12,'1.3.3','Laboratory Reports',9,'Work Package',3,'');
INSERT INTO "wbs" VALUES(13,'1.3.4','Online Consultations',9,'Work Package',4,'');
INSERT INTO "wbs" VALUES(14,'1.3.5','Hospital Billing',9,'Work Package',5,'');
INSERT INTO "wbs" VALUES(15,'1.3.6','Patient Records',9,'Work Package',6,'');
INSERT INTO "wbs" VALUES(16,'1.3.7','Web Front-end',9,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(17,'1.4','Testing & Quality Assurance',1,'Deliverable',NULL,'');
INSERT INTO "wbs" VALUES(18,'1.4.1','Integration & System Testing',17,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(19,'1.4.2','Defect Fixing & Regression',17,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(20,'1.4.3','User Acceptance Testing',17,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(21,'1.2.4','Infrastructure & Licences',5,'Work Package',NULL,'');
INSERT INTO "wbs" VALUES(22,'1.5','AI-based preliminary diagnosis module',1,'Deliverable',9,'Added by CR-001');
INSERT INTO "wbs" VALUES(23,'1.5.1','AI-based preliminary diagnosis module - development',22,'Work Package',9,'Added by CR-001');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('audit_log',29);
INSERT INTO "sqlite_sequence" VALUES('team_members',7);
INSERT INTO "sqlite_sequence" VALUES('requirements',11);
INSERT INTO "sqlite_sequence" VALUES('wbs',23);
INSERT INTO "sqlite_sequence" VALUES('tasks',18);
INSERT INTO "sqlite_sequence" VALUES('expenses',34);
INSERT INTO "sqlite_sequence" VALUES('milestones',6);
INSERT INTO "sqlite_sequence" VALUES('change_requests',3);
INSERT INTO "sqlite_sequence" VALUES('baseline_history',1);
INSERT INTO "sqlite_sequence" VALUES('defects',7);
INSERT INTO "sqlite_sequence" VALUES('quality_checks',8);
INSERT INTO "sqlite_sequence" VALUES('risks',8);
INSERT INTO "sqlite_sequence" VALUES('countermeasures',17);
COMMIT;
