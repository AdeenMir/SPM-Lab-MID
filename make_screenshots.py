"""Capture a screenshot of every module (works on Windows; on Linux needs an X display).

    python make_screenshots.py            -> screenshots/*.png  (uses a temporary demo database)
"""
import os
import tempfile
from tkinter import ttk

from PIL import ImageGrab

from spms.gui import App

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")


def grab(app, name):
    app.update()
    app.after(300)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(os.path.join(OUT, name + ".png"))
    print("saved", name)


def main():
    os.makedirs(OUT, exist_ok=True)
    db = os.path.join(tempfile.mkdtemp(), "demo.db")
    app = App(db)
    app.geometry("1420x880+0+0")
    app.update()
    n = 1
    for i, tab in enumerate(app.tabs):
        app.nb.select(i)
        inner = [w for w in tab.winfo_children() if isinstance(w, ttk.Notebook)]
        if inner:
            nb = inner[0]
            for j in range(len(nb.tabs())):
                nb.select(j)
                name = f"{n:02d}_{tab.TITLE}_{nb.tab(j, 'text')}".replace(" ", "_").replace("&", "and").replace("/", "-")
                grab(app, name)
                n += 1
        else:
            grab(app, f"{n:02d}_{tab.TITLE}".replace(" ", "_"))
            n += 1
    # demonstrate change-request approval: CR-002 (mobile app) before -> after
    svc = app.svc
    cr2 = svc.one("SELECT id FROM change_requests WHERE code='CR-002'")["id"]
    svc.approve_change_request(cr2, "Change Control Board", "Approved for demo")
    app.refresh_all()
    app.nb.select(0)
    grab(app, f"{n:02d}_AFTER_CR-002_approval_Dashboard")
    app.nb.select(2)
    scope_nb = [w for w in app.tabs[2].winfo_children() if isinstance(w, ttk.Notebook)][0]
    scope_nb.select(1)
    grab(app, f"{n + 1:02d}_AFTER_CR-002_approval_WBS")
    scope_nb.select(2)
    grab(app, f"{n + 2:02d}_AFTER_CR-002_approval_Change_requests")
    app.nb.select(3)
    sch_nb = [w for w in app.tabs[3].winfo_children() if isinstance(w, ttk.Notebook)][0]
    sch_nb.select(2)
    grab(app, f"{n + 3:02d}_AFTER_CR-002_approval_Gantt")
    app.destroy()


if __name__ == "__main__":
    main()
