"""Reusable Tkinter widgets: sortable tables, form builder, modal dialogs, KPI cards."""
import tkinter as tk
from tkinter import ttk, messagebox

from .services import ValidationError

PRIMARY = "#0d9488"
BG = "#eef2f6"
SIDEBAR = "#0f172a"
SIDEBAR_HI = "#1e293b"
CARD = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
RED, AMBER, GREEN, BLUE = "#dc2626", "#d97706", "#16a34a", "#2563eb"
STATUS_COLORS = {"CRITICAL": RED, "WARNING": AMBER, "OK": GREEN, "N/A": MUTED}
FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")


def fmt_value(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, float):
        return f"{v:,.0f}"
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


class Table(ttk.Frame):
    """Treeview with headings, scrollbars, sorting and row tags.

    columns: list of (key, heading, width[, anchor[, formatter]])
    """
    TAGS = {"crit": "#fde2e1", "warn": "#fff3cd", "ok": "#e3f4e8", "info": "#e3eefa", "muted": "#f1f1f1"}

    def __init__(self, master, columns, height=10, on_double=None, show="headings"):
        super().__init__(master)
        self.columns = columns
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show=show, height=height,
                                 selectmode="browse")
        for c in columns:
            key, head, width = c[0], c[1], c[2]
            anchor = c[3] if len(c) > 3 else "w"
            self.tree.heading(key, text=head, command=lambda k=key: self._sort(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=True)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for tag, color in self.TAGS.items():
            self.tree.tag_configure(tag, background=color)
        self.tree.tag_configure("bold", font=FONT_B)
        if on_double:
            self.tree.bind("<Double-1>", lambda e: on_double())
        self._asc = {}

    def load(self, rows, iid="id", tag=None):
        sel = self.selected()
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            vals = []
            for c in self.columns:
                v = r.get(c[0])
                vals.append(c[4](v) if len(c) > 4 and c[4] else fmt_value(v))
            rid = str(r.get(iid, i)) if iid else str(i)
            tags = (tag(r),) if tag and tag(r) else ()
            self.tree.insert("", "end", iid=rid, values=vals, tags=tags)
        if sel and self.tree.exists(sel):
            self.tree.selection_set(sel)

    def selected(self):
        s = self.tree.selection()
        return s[0] if s else None

    def selected_int(self):
        s = self.selected()
        return int(s) if s is not None else None

    def _sort(self, key):
        items = [(self.tree.set(k, key), k) for k in self.tree.get_children("")]

        def conv(v):
            try:
                return (0, float(v.replace(",", "").replace("%", "")))
            except ValueError:
                return (1, v.lower())
        asc = not self._asc.get(key, False)
        self._asc[key] = asc
        items.sort(key=lambda x: conv(x[0]), reverse=not asc)
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)


class Form(ttk.Frame):
    """Simple form builder.

    field dict: key, label, kind (entry|text|combo|check|multi|label), options [(value, label)],
                width, height, hint, readonly, button=(text, callback(form))
    """

    def __init__(self, master, fields, initial=None):
        super().__init__(master)
        self.fields = fields
        self.vars, self.widgets = {}, {}
        initial = initial or {}
        for i, f in enumerate(fields):
            key, kind = f["key"], f.get("kind", "entry")
            ttk.Label(self, text=f["label"]).grid(row=i, column=0, sticky="nw", padx=(0, 10), pady=4)
            val = initial.get(key, f.get("default", ""))
            width = f.get("width", 44)
            if kind == "text":
                w = tk.Text(self, width=width, height=f.get("height", 4), wrap="word", font=FONT,
                            relief="solid", borderwidth=1)
                w.insert("1.0", "" if val is None else str(val))
            elif kind == "combo":
                opts = f["options"]
                var = tk.StringVar(value=next((lbl for v, lbl in opts if str(v) == str(val)), ""))
                w = ttk.Combobox(self, textvariable=var, values=[lbl for _, lbl in opts], state="readonly",
                                 width=width - 2)
                self.vars[key] = var
            elif kind == "check":
                var = tk.BooleanVar(value=bool(val) and val not in ("0", 0))
                w = ttk.Checkbutton(self, variable=var)
                self.vars[key] = var
            elif kind == "multi":
                w = tk.Listbox(self, selectmode="multiple", height=f.get("height", 6), width=width,
                               exportselection=False, font=FONT)
                sel = {str(x) for x in (val or [])}
                for j, (v, lbl) in enumerate(f["options"]):
                    w.insert("end", lbl)
                    if str(v) in sel:
                        w.selection_set(j)
            elif kind == "label":
                var = tk.StringVar(value=fmt_value(val))
                w = ttk.Label(self, textvariable=var, foreground=MUTED)
                self.vars[key] = var
            else:
                var = tk.StringVar(value=fmt_value(val) if not isinstance(val, float) else f"{val:.0f}")
                w = ttk.Entry(self, textvariable=var, width=width)
                if f.get("readonly"):
                    w.state(["readonly"])
                self.vars[key] = var
            w.grid(row=i, column=1, sticky="ew", pady=4)
            self.widgets[key] = w
            extra = None
            if f.get("button"):
                txt, cb = f["button"]
                extra = ttk.Button(self, text=txt, command=lambda cb=cb: cb(self))
            elif f.get("hint"):
                extra = ttk.Label(self, text=f["hint"], foreground=MUTED)
            if extra:
                extra.grid(row=i, column=2, sticky="w", padx=6)
        self.columnconfigure(1, weight=1)

    def get(self, key):
        f = next(x for x in self.fields if x["key"] == key)
        kind = f.get("kind", "entry")
        w = self.widgets[key]
        if kind == "text":
            return w.get("1.0", "end").strip()
        if kind == "combo":
            lbl = self.vars[key].get()
            return next((v for v, l in f["options"] if l == lbl), None)
        if kind == "check":
            return self.vars[key].get()
        if kind == "multi":
            return [f["options"][i][0] for i in w.curselection()]
        return self.vars[key].get().strip()

    def set(self, key, value):
        if key in self.vars:
            self.vars[key].set(fmt_value(value) if not isinstance(value, float) else f"{value:.0f}")

    def values(self):
        return {f["key"]: self.get(f["key"]) for f in self.fields if f.get("kind") != "label"}


class FormDialog(tk.Toplevel):
    """Modal form. on_submit(values) may raise ValidationError; the dialog then stays open."""

    def __init__(self, master, title, fields, initial=None, on_submit=None, ok_text="Save"):
        super().__init__(master)
        self.title(title)
        self.configure(background=BG)
        self.transient(master.winfo_toplevel())
        self.result = None
        self.on_submit = on_submit
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=title, style="H2.TLabel").pack(anchor="w", pady=(0, 8))
        self.form = Form(outer, fields, initial)
        self.form.pack(fill="both", expand=True)
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text=ok_text, style="Accent.TButton", command=self._ok).pack(side="right", padx=6)
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = master.winfo_toplevel().winfo_rootx() + 120
        y = master.winfo_toplevel().winfo_rooty() + 80
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.focus_set()

    def _ok(self):
        vals = self.form.values()
        try:
            if self.on_submit:
                self.on_submit(vals)
            self.result = vals
            self.destroy()
        except ValidationError as e:
            messagebox.showerror("Validation error", str(e), parent=self)
        except Exception as e:  # noqa: BLE001 - shown to user, never crash the GUI
            messagebox.showerror("Error", f"{type(e).__name__}: {e}", parent=self)

    def show(self):
        self.wait_window()
        return self.result


class Card(tk.Frame):
    """KPI card with coloured accent bar."""

    def __init__(self, master, title):
        super().__init__(master, background=CARD, highlightbackground="#e2e8f0", highlightthickness=1)
        self.bar = tk.Frame(self, background=PRIMARY, height=4)
        self.bar.pack(side="top", fill="x")
        inner = tk.Frame(self, background=CARD, padx=14, pady=10)
        inner.pack(side="top", fill="both", expand=True)
        tk.Label(inner, text=title, background=CARD, foreground=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.value = tk.Label(inner, text="-", background=CARD, foreground=TEXT, font=("Segoe UI", 18, "bold"))
        self.value.pack(anchor="w")
        self.sub = tk.Label(inner, text="", background=CARD, foreground=MUTED, font=("Segoe UI", 9),
                            justify="left", wraplength=230)
        self.sub.pack(anchor="w")

    def set(self, value, sub="", color=PRIMARY):
        self.value.configure(text=value, foreground=color if color != PRIMARY else TEXT)
        self.sub.configure(text=sub)
        self.bar.configure(background=color)


class ScrollCanvas(ttk.Frame):
    """Canvas with both scrollbars."""

    def __init__(self, master, **kw):
        super().__init__(master)
        self.canvas = tk.Canvas(self, background="white", highlightthickness=0, **kw)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def finish(self):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(0, 0, bbox[2] + 20, bbox[3] + 20))


def button_bar(master, buttons):
    bar = ttk.Frame(master)
    for text, cmd, *style in buttons:
        ttk.Button(bar, text=text, command=cmd, style=style[0] if style else "TButton").pack(side="left", padx=(0, 6))
    return bar


def ask_text(master, title, label, default=""):
    d = FormDialog(master, title, [{"key": "v", "label": label, "default": default}], ok_text="OK")
    r = d.show()
    return r["v"] if r else None
