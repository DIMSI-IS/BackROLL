"""The tests write users, connectors and audit entries: they must never reach a real database."""

import os
import tempfile

# Set before any test module imports the application, which reads it once.
os.environ["SQLITE_DIRECTORY"] = tempfile.mkdtemp()
os.environ.setdefault("JWT_SECRET", "x" * 40)


def pytest_sessionstart(session):
    from app import database

    url = str(database.init_db_connection().url)
    if not url.startswith("sqlite:///") or os.environ["SQLITE_DIRECTORY"] not in url:
        raise SystemExit(f"Refusing to run the tests on {url.split('@')[-1]}: it is not their temporary database.")
