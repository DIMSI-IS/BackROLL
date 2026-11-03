"""Visits every page of the interface in both languages with the demo data and reports:
- the errors of the browser console and of the page,
- the texts that look like a translation key that was not found (pages.xxx),
- in French, the lines that contain English words (a text that was not translated),
- the pages that stay empty or show an error.

    python audit.py [--dist <built UI folder>] [--langs en,fr]
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from capture import DEFAULT_DIST, VIEWPORT, Shooter, free_port, launch, start_server

ROUTES = [
    "/admin/dashboard", "/admin/tasks/backup", "/admin/tasks/restore", "/admin/tasks/cleanup",
    "/admin/tasks/drp", "/admin/tasks/kickstart", "/admin/resources/pools", "/admin/resources/pools/new",
    "/admin/resources/hypervisors", "/admin/resources/hypervisors/new", "/admin/resources/virtualmachines",
    "/admin/configuration/policies", "/admin/configuration/policies/new", "/admin/configuration/storage",
    "/admin/configuration/storage/new", "/admin/configuration/connectors", "/admin/configuration/connectors/new",
    "/admin/configuration/externalhooks", "/admin/configuration/externalhooks/new", "/admin/auth/users",
    "/admin/auth/audit", "/admin/auth/settings", "/admin/auth/changePassword", "/admin/documentation",
]

# Words that show a text was not translated. Product names and technical terms are not in this list.
ENGLISH = re.compile(
    r"\b(the|and|with|from|your|select|selected|failed|unable|delete|deleted|cancel|name|save|search|"
    r"description|optional|loading|running|waiting|success|error|warning|enabled|disabled|settings|"
    r"storage|backup|backups|restore|policy|policies|hypervisor|hypervisors|machine|machines|user|users|"
    r"password|login|logout|close|open|start|stop|refresh|add|new|edit|update|create|no items|items|"
    r"last|next|previous|show|hide|status|date|time|result|results|log|history|details|detail)\b",
    re.IGNORECASE)
# Allowed in French pages: names of products, of the demo data, of routes and technical values.
ALLOWED_LINES = re.compile(
    r"(BACKROLL|BackROLL|Borg|CloudStack|Slack|libguestfs|KVM|cron|SSH|backup_storage|BACKUP_STORAGE|"
    r"daily-backup|weekly-archive|cloudstack-lab|slack-notifications|admin|operator|auditor|"
    r"\bvda\b|\bvdb\b|FILES|v2\.0\.0)")
KEY = re.compile(r"\b(pages|menu|dashboard|navigationRoutes)\.[A-Za-z0-9_.]+")


def visible_lines(page) -> list[str]:
    text = page.evaluate("() => document.querySelector('#app')?.innerText || ''")
    return [line.strip() for line in text.splitlines() if line.strip()]


def audit_language(browser, base: str, language: str, routes: list[str]) -> list[str]:
    problems: list[str] = []
    context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, service_workers="block",
                                  locale="en-GB" if language == "en" else "fr-FR", timezone_id="Europe/Paris")
    context.add_init_script(f"localStorage.setItem('backroll.language', '{language}')")
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(f"page error: {str(error)[:200]}"))
    page.on("console", lambda message: errors.append(f"console {message.type}: {message.text[:200]}")
            if message.type == "error" and "service worker" not in message.text.lower() else None)

    shooter = Shooter(page, base, language)
    shooter.login()
    for route in routes:
        errors.clear()
        try:
            page.goto(f"{base}{route}")
            page.wait_for_function(
                "() => !document.querySelector('[class*=\"spinner\"], .va-inner-loading__overlay')", timeout=20000)
            page.wait_for_timeout(1500)
        except Exception as error:
            problems.append(f"[{language}] {route}: did not load ({str(error).splitlines()[0]})")
            continue
        lines = visible_lines(page)
        if len(lines) < 5:
            problems.append(f"[{language}] {route}: almost empty page ({len(lines)} lines)")
        for error in errors:
            problems.append(f"[{language}] {route}: {error}")
        for line in lines:
            if KEY.search(line):
                problems.append(f"[{language}] {route}: translation key displayed: “{line[:100]}”")
            if language == "fr" and ENGLISH.search(line) and not ALLOWED_LINES.search(line):
                problems.append(f"[fr] {route}: English text: “{line[:110]}”")
    context.close()
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--langs", default="fr,en")
    args = parser.parse_args()

    port = free_port()
    server = start_server(args.dist, port)
    problems: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = launch(playwright)
            for language in args.langs.split(","):
                print(f"Language {language}: {len(ROUTES)} pages")
                problems += audit_language(browser, f"http://127.0.0.1:{port}", language, ROUTES)
            browser.close()
    finally:
        server.terminate()

    report = Path(tempfile.gettempdir()) / "ui-audit.txt"
    unique = list(dict.fromkeys(problems))
    report.write_text("\n".join(unique), encoding="utf-8")
    print("\n".join(unique))
    print(f"\n{len(unique)} finding(s). Report: {report}")
    sys.exit(1 if unique else 0)


if __name__ == "__main__":
    main()
