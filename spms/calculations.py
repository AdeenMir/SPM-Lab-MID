"""Pure calculation engine: scheduling (CPM), delay forecasting, EVM, risk scoring.

All functions are free of database/GUI code so they can be unit-tested directly.
Durations are in calendar days. A task with duration d starting on day S finishes
on day S + d - 1 (inclusive); its finish-to-start successor starts the next day.
"""
import math
from collections import deque
from datetime import date, datetime, timedelta


class CycleError(ValueError):
    """Raised when task dependencies contain a cycle."""


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def fmt(d):
    return d.isoformat() if d else ""


# --------------------------------------------------------------------------- graph
def successors_map(preds):
    succ = {t: set() for t in preds}
    for t, ps in preds.items():
        for p in ps:
            succ.setdefault(p, set()).add(t)
    return succ


def topological_order(task_ids, preds):
    """Kahn's algorithm. preds: {task_id: set(pred_ids)}. Raises CycleError."""
    task_ids = list(task_ids)
    indeg = {t: 0 for t in task_ids}
    succ = {t: [] for t in task_ids}
    for t in task_ids:
        for p in preds.get(t, ()):
            if p not in indeg:
                raise ValueError(f"Unknown predecessor id {p} for task {t}")
            indeg[t] += 1
            succ[p].append(t)
    queue = deque(sorted(t for t in task_ids if indeg[t] == 0))
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for s in sorted(succ[n]):
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    if len(order) != len(task_ids):
        stuck = sorted(t for t in task_ids if indeg[t] > 0)
        raise CycleError(f"Dependency cycle detected among tasks {stuck}")
    return order


def would_create_cycle(task_id, new_preds, preds):
    """True if setting task_id's predecessors to new_preds creates a cycle."""
    trial = {t: set(ps) for t, ps in preds.items()}
    trial[task_id] = set(new_preds)
    for p in new_preds:
        trial.setdefault(p, set())
    try:
        topological_order(trial.keys(), trial)
        return False
    except CycleError:
        return True


def downstream(task_id, succ):
    """All tasks transitively dependent on task_id."""
    seen, stack = set(), list(succ.get(task_id, ()))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(succ.get(n, ()))
    return seen


def upstream(task_id, preds):
    seen, stack = set(), list(preds.get(task_id, ()))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(preds.get(n, ()))
    return seen


# --------------------------------------------------------------------------- CPM
def compute_planned_schedule(durations, preds, project_start):
    """Critical Path Method forward + backward pass.

    durations: {task_id: int days}; preds: {task_id: set(pred ids)}
    Returns ({task_id: {es, ef, ls, lf, float, critical}}, project_finish)
    """
    start = parse_date(project_start)
    order = topological_order(durations.keys(), preds)
    res = {}
    for t in order:
        ps = preds.get(t, ())
        es = max((res[p]["ef"] for p in ps), default=start - timedelta(days=1)) + timedelta(days=1)
        ef = es + timedelta(days=durations[t] - 1)
        res[t] = {"es": es, "ef": ef}
    if not res:
        return {}, start
    finish = max(r["ef"] for r in res.values())
    succ = successors_map({t: set(preds.get(t, ())) for t in durations})
    for t in reversed(order):
        ss = succ.get(t, ())
        lf = min((res[s]["ls"] for s in ss), default=finish + timedelta(days=1)) - timedelta(days=1)
        ls = lf - timedelta(days=durations[t] - 1)
        res[t].update(lf=lf, ls=ls)
        res[t]["float"] = (ls - res[t]["es"]).days
        res[t]["critical"] = res[t]["float"] == 0
    return res, finish


def compute_forecast(tasks, preds, planned, status_date):
    """Forecast start/finish using actual progress at the status (data) date.

    tasks: {id: {duration, actual_start, actual_end, percent}}
    Completed  -> actual dates.
    In progress-> remaining = ceil(duration * (100-percent)/100) days counted from status date.
    Not started-> cannot start before predecessors finish nor before the status date.
    Returns {id: {fs, fe, delay, inherited, own_delay, state}}
    """
    sd = parse_date(status_date)
    order = topological_order(tasks.keys(), preds)
    out = {}
    for t in order:
        info = tasks[t]
        dur = int(info["duration"])
        a_s, a_e = parse_date(info.get("actual_start")), parse_date(info.get("actual_end"))
        pct = int(info.get("percent") or 0)
        ps = preds.get(t, ())
        pred_ready = max((out[p]["fe"] for p in ps), default=None)
        earliest = pred_ready + timedelta(days=1) if pred_ready else planned[t]["es"]
        if a_e:
            fs, fe, state = a_s, a_e, "Completed"
        elif a_s:
            remaining = math.ceil(dur * (100 - pct) / 100)
            fs = a_s
            fe = max(fs, sd + timedelta(days=max(remaining, 1) - 1))
            state = "In Progress"
        else:
            fs = max(earliest, sd)
            fe = fs + timedelta(days=dur - 1)
            state = "Not Started"
        delay = (fe - planned[t]["ef"]).days
        inherited = max((max(out[p]["delay"], 0) for p in ps), default=0)
        own = max(delay, 0) - inherited if delay > 0 else 0
        if state != "Completed" and delay > 0:
            state = "Delayed"
        elif state == "Not Started" and planned[t]["es"] < sd:
            state = "Delayed"
        out[t] = {"fs": fs, "fe": fe, "delay": delay, "inherited": inherited,
                  "own_delay": max(own, 0), "state": state}
    return out


def delay_impacts(forecast, preds):
    """Root-cause delayed tasks and the downstream slip each one causes."""
    succ = successors_map({t: set(preds.get(t, ())) for t in forecast})
    impacts = []
    for t, f in forecast.items():
        if f["own_delay"] > 0:
            ds = downstream(t, succ)
            impacts.append({"task": t, "own_delay": f["own_delay"], "total_delay": f["delay"],
                            "affected": sorted(ds, key=lambda x: forecast[x]["fs"])})
    impacts.sort(key=lambda i: -i["own_delay"])
    return impacts


# --------------------------------------------------------------------------- EVM
def planned_fraction(es, ef, status_date):
    sd = parse_date(status_date)
    if sd < es:
        return 0.0
    if sd >= ef:
        return 1.0
    total = (ef - es).days + 1
    return ((sd - es).days + 1) / total


def evm_metrics(budgets, planned, percents, actual_cost, status_date):
    """budgets/percents: {task_id: value}; planned: CPM result. Returns indicator dict."""
    bac = sum(budgets.values())
    pv = sum(budgets[t] * planned_fraction(planned[t]["es"], planned[t]["ef"], status_date)
             for t in budgets)
    ev = sum(budgets[t] * (percents.get(t, 0) / 100.0) for t in budgets)
    ac = float(actual_cost)
    cpi = ev / ac if ac > 0 else None
    spi = ev / pv if pv > 0 else None
    eac = bac / cpi if cpi else bac
    tcpi = (bac - ev) / (bac - ac) if (bac - ac) != 0 else None
    return {"BAC": bac, "PV": pv, "EV": ev, "AC": ac, "CV": ev - ac, "SV": ev - pv,
            "CPI": cpi, "SPI": spi, "EAC": eac, "ETC": eac - ac, "VAC": bac - eac, "TCPI": tcpi,
            "pct_complete": (ev / bac * 100) if bac else 0.0,
            "pct_planned": (pv / bac * 100) if bac else 0.0}


def classify_index(value, warn, crit):
    if value is None:
        return "N/A"
    if value < crit:
        return "CRITICAL"
    if value < warn:
        return "WARNING"
    return "OK"


def pv_curve(budgets, planned, start, finish, step_days=7):
    """Cumulative planned value at regular intervals (for the S-curve)."""
    pts, d = [], parse_date(start)
    finish = parse_date(finish)
    while True:
        pv = sum(budgets[t] * planned_fraction(planned[t]["es"], planned[t]["ef"], d) for t in budgets)
        pts.append((d, pv))
        if d >= finish:
            break
        d = min(d + timedelta(days=step_days), finish)
    return pts


# --------------------------------------------------------------------------- risk
def risk_score(likelihood, impact):
    return int(likelihood) * int(impact)


def risk_level(score):
    if score >= 15:
        return "High"
    if score >= 8:
        return "Medium"
    return "Low"


def rank_risks(risks):
    """Sort by score desc, then impact desc (impact breaks ties), then code."""
    ranked = sorted(risks, key=lambda r: (-risk_score(r["likelihood"], r["impact"]),
                                          -int(r["impact"]), r["code"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
        r["score"] = risk_score(r["likelihood"], r["impact"])
        r["level"] = risk_level(r["score"])
    return ranked
