-- Smart Healthcare SPMS - database schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS project (
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

CREATE TABLE IF NOT EXISTS plan_sections (
    section  TEXT PRIMARY KEY,
    content  TEXT NOT NULL DEFAULT '',
    updated  TEXT
);

CREATE TABLE IF NOT EXISTS team_members (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    role           TEXT NOT NULL,
    responsibility TEXT,
    daily_rate     REAL NOT NULL CHECK (daily_rate >= 0),
    email          TEXT
);

CREATE TABLE IF NOT EXISTS change_requests (
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

CREATE TABLE IF NOT EXISTS requirements (
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

CREATE TABLE IF NOT EXISTS wbs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    parent_id      INTEGER REFERENCES wbs(id),
    node_type      TEXT NOT NULL CHECK (node_type IN ('Project','Deliverable','Work Package')),
    requirement_id INTEGER REFERENCES requirements(id),
    description    TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
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

CREATE TABLE IF NOT EXISTS dependencies (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    pred_id INTEGER NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (task_id, pred_id),
    CHECK (task_id <> pred_id)
);

CREATE TABLE IF NOT EXISTS milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    owner_id    INTEGER REFERENCES team_members(id),
    description TEXT
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    exp_date    TEXT NOT NULL,
    amount      REAL NOT NULL CHECK (amount > 0),
    description TEXT
);

CREATE TABLE IF NOT EXISTS baseline_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    change_date  TEXT NOT NULL,
    cr_id        INTEGER REFERENCES change_requests(id),
    old_budget   REAL NOT NULL,
    new_budget   REAL NOT NULL,
    old_deadline TEXT NOT NULL,
    new_deadline TEXT NOT NULL,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS defects (
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

CREATE TABLE IF NOT EXISTS quality_checks (
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

CREATE TABLE IF NOT EXISTS risks (
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

CREATE TABLE IF NOT EXISTS countermeasures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id     INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('Preventive','Corrective')),
    action      TEXT NOT NULL,
    owner_id    INTEGER REFERENCES team_members(id),
    feasible    INTEGER NOT NULL DEFAULT 1 CHECK (feasible IN (0,1))
);

CREATE TABLE IF NOT EXISTS closure (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    closed_date TEXT NOT NULL,
    final_cost  REAL NOT NULL,
    accepted_by TEXT NOT NULL,
    lessons     TEXT NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    action  TEXT NOT NULL,
    details TEXT
);
