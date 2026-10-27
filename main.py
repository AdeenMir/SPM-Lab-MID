"""Smart Healthcare SPMS - entry point.

Usage:
    python main.py                 # run the GUI (creates spms.db with sample data on first run)
    python main.py --db other.db   # use another database file
    python main.py --export-sql    # write schema.sql and sample_data.sql next to this file
"""
import argparse
import os
import sys


def base_dir():
    # next to the .exe when frozen by PyInstaller, otherwise next to this file
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Smart Healthcare Software Project Management System")
    ap.add_argument("--db", default=os.path.join(base_dir(), "spms.db"), help="SQLite database file")
    ap.add_argument("--export-sql", action="store_true", help="export schema.sql and sample_data.sql and exit")
    args = ap.parse_args()

    if args.export_sql:
        from spms import db, seed
        from spms.services import ProjectService
        conn = db.connect(":memory:")
        seed.seed(ProjectService(conn))
        out = base_dir()
        db.export_sql(conn, os.path.join(out, "schema.sql"), os.path.join(out, "sample_data.sql"))
        print("Wrote schema.sql and sample_data.sql to", out)
        return

    from spms.gui import App
    App(args.db).mainloop()


if __name__ == "__main__":
    main()
