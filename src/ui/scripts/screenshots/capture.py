"""Takes the screenshots of the BackROLL documentation (English and French).

It starts mock_server.py (fictional data, no real backend) on a free local port, drives the
installed Chrome (or Edge) with Playwright, logs in through the real login page and saves one PNG
per page in public/docs/<language>/.

    python capture.py [--dist <built UI folder>] [--only dashboard,policies] [--langs en,fr]

No browser is downloaded: the installed Chrome or Edge is used (Playwright `channel`).
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

HERE = Path(__file__).resolve().parent
UI_ROOT = HERE.parents[1]
OUTPUT = UI_ROOT / "public" / "docs"
DEFAULT_DIST = Path(tempfile.gettempdir()) / "ui-docs-build"
USERNAME = "admin"
PASSWORD = "demo-admin-pass"  # the credentials of the mock only
VIEWPORT = {"width": 1440, "height": 900}

NAMES = ["dashboard", "topbar", "policies", "policy-form", "pools", "hypervisors", "virtual-machines",
         "virtual-machine", "backup-files", "tasks-backup", "kickstart", "drp", "users", "audit-log",
         "settings", "cleanup", "connectors", "storage", "external-hooks", "dashboard-attention", "directory"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(dist: Path, port: int) -> subprocess.Popen:
    process = subprocess.Popen([sys.executable, str(HERE / "mock_server.py"), str(dist), "--port", str(port)])
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/auth/setup", timeout=1)
            return process
        except Exception:
            if process.poll() is not None:
                raise SystemExit("The mock server did not start.")
            time.sleep(0.2)
    process.kill()
    raise SystemExit("The mock server did not answer.")


class Shooter:
    def __init__(self, page: Page, base: str, language: str):
        self.page = page
        self.base = base
        self.language = language
        self.folder = OUTPUT / language
        self.folder.mkdir(parents=True, exist_ok=True)

    # -- helpers ------------------------------------------------------------------------------

    def settle(self, texts=(), extra_ms=600, timeout=20000):
        """Waits for the data (no spinner, the given texts displayed) and for the toasts to go."""
        page = self.page
        for text in texts:
            page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
        page.wait_for_function(
            """() => !document.querySelector(
                '[class*="spinner"], .va-inner-loading__overlay, .va-data-table--loading, .va-button--loading')""",
            timeout=timeout)
        page.wait_for_function("() => !document.querySelector('.va-toast')", timeout=30000)
        # The top bar shows the time of the last refresh once the lists are loaded.
        page.locator(".refresh-control__time").wait_for(state="visible", timeout=timeout)
        page.wait_for_timeout(extra_ms)

    def go(self, route: str, texts=(), **kwargs):
        self.page.goto(f"{self.base}{route}")
        self.settle(texts, **kwargs)

    def shot(self, name: str, clip=None):
        path = self.folder / f"{name}.png"
        self.page.screenshot(path=str(path), clip=clip)
        optimise(path)
        print(f"  {self.language}/{name}.png ({path.stat().st_size // 1024} KB)")

    def pick(self, select_index: int, option_text: str):
        """Opens the n-th select of the page and chooses an option by its text."""
        page = self.page
        page.locator(".va-card .va-select").nth(select_index).click()
        option = page.locator(".va-select-option-list__option", has_text=option_text).first
        option.wait_for(state="visible", timeout=10000)
        option.click()
        page.wait_for_timeout(500)

    def scroll_content(self, selector_text: str, offset: int = 0):
        """Scrolls the scrollable main area so that an element is near the top."""
        self.page.evaluate(
            """([text, offset]) => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                let target = null;
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.children.length === 0 && node.textContent.trim() === text) { target = node; break; }
                }
                if (!target) return;
                let parent = target.parentElement;
                while (parent && parent.scrollHeight <= parent.clientHeight + 4) parent = parent.parentElement;
                const scroller = parent || document.scrollingElement;
                scroller.scrollTop += target.getBoundingClientRect().top - offset;
            }""", [selector_text, offset])
        self.page.wait_for_timeout(400)

    # -- login --------------------------------------------------------------------------------

    def login(self):
        page = self.page
        page.goto(f"{self.base}/login")
        page.locator("input[type=password]").wait_for(state="visible")
        page.locator("input").first.fill(USERNAME)
        page.locator("input[type=password]").fill(PASSWORD)
        page.keyboard.press("Enter")
        page.wait_for_url("**/admin/dashboard", timeout=20000)
        self.settle()

    # -- pages --------------------------------------------------------------------------------

    def dashboard(self):
        self.go("/admin/dashboard", ["mail-01", "BACKUP_STORAGE"], extra_ms=2500)
        self.shot("dashboard")

    def dashboard_attention(self):
        """The red card of a machine whose backups are stopped, with the button that resumes them."""
        self.page.request.post(f"{self.base}/__mock/attention")
        self.go("/admin/dashboard", ["i-535-18737-VM"], extra_ms=800)
        box = self.page.locator(".attention").bounding_box()
        self.shot("dashboard-attention", clip={"x": max(box["x"] - 16, 0), "y": max(box["y"] - 12, 0),
                                              "width": box["width"] + 32, "height": box["height"] + 24})
        self.page.request.post(f"{self.base}/api/v1/attention/0498dae1/resolve")

    def directory(self):
        self.go("/admin/auth/directory", ["BackROLL-Admins"], extra_ms=800)
        self.shot("directory")

    def topbar(self):
        self.go("/admin/dashboard", ["BACKUP_STORAGE"])
        box = self.page.locator(".va-navbar, header").first.bounding_box()
        height = int(box["height"] + box["y"]) if box else 64
        self.shot("topbar", clip={"x": 0, "y": 0, "width": VIEWPORT["width"], "height": max(height, 56)})

    def policies(self):
        self.go("/admin/configuration/policies", ["daily-backup", "weekly-archive"])
        self.shot("policies")

    def policy_form(self):
        self.go("/admin/configuration/policies", ["daily-backup"])
        self.page.locator("tbody tr", has_text="daily-backup").locator("button").nth(1).click()
        self.page.wait_for_url("**/admin/configuration/policy/*")
        self.page.locator("textarea").first.wait_for(state="visible")
        self.page.wait_for_function("() => document.querySelector('textarea').value.includes('/var/www')")
        self.page.locator("textarea").first.scroll_into_view_if_needed()
        # The folders field and the four retention sliders must be visible together.
        sliders = self.page.locator(".va-slider").first
        sliders.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)
        self.shot("policy-form")

    def pools(self):
        self.go("/admin/resources/pools", ["PRODUCTION", "STAGING"])
        self.shot("pools")

    def hypervisors(self):
        self.go("/admin/resources/hypervisors", ["KVM-01", "10.0.0.12"])
        self.shot("hypervisors")

    def virtual_machines(self):
        self.go("/admin/resources/virtualmachines", ["WEB-01", "APP-01"])
        self.shot("virtual-machines")

    def open_vm_backups(self):
        from_uuid = None
        self.go("/admin/resources/virtualmachines", ["WEB-01"])
        self.page.locator("tr", has_text="WEB-01").locator("button").first.click()
        self.page.wait_for_url("**/resources/virtualmachines/*")
        self.settle(["web-01"])
        self.page.locator(".va-tab").nth(1).click()
        self.page.locator("tbody tr").nth(3).wait_for(state="visible")
        self.settle()
        return from_uuid

    def virtual_machine(self):
        self.open_vm_backups()
        self.shot("virtual-machine")

    def backup_files(self):
        self.open_vm_backups()
        row = self.page.locator("tbody tr").filter(has=self.page.locator("span.ml-2", has_text=re.compile(r"^etc$"))).first
        row.locator("button").nth(1).click()
        self.page.wait_for_url("**/files**")
        self.settle(["etc", "var"])
        self.page.locator(".entry", has_text=re.compile(r"etc\s*$")).click()
        self.settle(["nginx"])
        self.page.locator(".entry", has_text=re.compile(r"nginx\s*$")).click()
        self.settle(["nginx.conf"])
        self.shot("backup-files")

    def tasks_backup(self):
        self.go("/admin/tasks/backup", ["mail-01"])
        self.shot("tasks-backup")

    def kickstart(self):
        self.go("/admin/tasks/backup", ["mail-01"])
        self.page.locator(".va-card__title .va-button").first.click()
        self.page.wait_for_url("**/admin/tasks/kickstart**")
        self.settle()
        self.page.wait_for_timeout(500)
        # The backup task is preselected: choose the machine to back up.
        self.pick(1, "web-01")
        self.settle(extra_ms=400)
        self.shot("kickstart")

    def drp(self):
        self.go("/admin/tasks/drp", [], extra_ms=800)
        self.page.get_by_text("web-01-restored").first.wait_for(state="visible")  # the history
        self.settle()
        # Step 1: the storage, the machine (index 1), then its disk archive (index 2).
        self.pick(0, "backup_storage")
        self.pick(1, "web-01")
        self.page.locator("tbody tr").first.wait_for(state="visible")
        # Step 2: connector (3), then domain (4), zone (5), offering (6), template (7), network (8).
        self.pick(3, "cloudstack-lab")
        self.page.wait_for_function("() => document.querySelectorAll('.va-card .va-select').length >= 9")
        self.page.wait_for_timeout(500)
        self.pick(5, "zone-lab")
        self.pick(6, "Medium Instance")
        self.pick(7, "debian-12")
        self.pick(8, "demo-network")
        self.settle()
        # Taller window: the form and the history are visible together.
        self.page.set_viewport_size({"width": VIEWPORT["width"], "height": 1300})
        self.page.wait_for_timeout(600)
        self.shot("drp")
        self.page.set_viewport_size(VIEWPORT)

    def users(self):
        self.go("/admin/auth/users", ["operator", "auditor"])
        self.shot("users")

    def audit_log(self):
        self.go("/admin/auth/audit", ["backup.start"])
        self.shot("audit-log")

    def settings(self):
        self.go("/admin/auth/settings", [])
        self.page.wait_for_function("() => document.querySelector('input[type=number]')?.value === '2'")
        self.shot("settings")

    def cleanup(self):
        self.go("/admin/tasks/cleanup", [])
        self.page.wait_for_function("() => document.body.innerText.includes('backup_storage')")
        self.shot("cleanup")

    def connectors(self):
        self.go("/admin/configuration/connectors", ["cloudstack-lab"])
        self.shot("connectors")

    def storage(self):
        self.go("/admin/configuration/storage", ["BACKUP_STORAGE"])
        self.shot("storage")

    def external_hooks(self):
        self.go("/admin/configuration/externalhooks", ["slack-notifications"])
        self.shot("external-hooks")


def optimise(path: Path):
    """Reduces the size of the PNG when Pillow is installed (optional)."""
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as image:
        quantised = image.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        quantised.save(path, optimize=True)


def launch(playwright):
    last = None
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except PlaywrightError as error:
            last = error
    raise SystemExit(f"Neither Chrome nor Edge could be started: {last}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="folder of the built UI")
    parser.add_argument("--only", help="comma separated names of the pictures to take")
    parser.add_argument("--langs", default="en,fr")
    args = parser.parse_args()
    names = args.only.split(",") if args.only else NAMES

    port = free_port()
    server = start_server(args.dist, port)
    base = f"http://127.0.0.1:{port}"
    failures = []
    try:
        with sync_playwright() as playwright:
            browser = launch(playwright)
            for language in args.langs.split(","):
                print(f"Language {language}")
                context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, service_workers="block",
                                              locale="en-GB" if language == "en" else "fr-FR",
                                              timezone_id="Europe/Paris")
                context.add_init_script(f"localStorage.setItem('backroll.language', '{language}')")
                page = context.new_page()
                shooter = Shooter(page, base, language)
                shooter.login()
                for name in names:
                    try:
                        getattr(shooter, name.replace("-", "_"))()
                    except Exception as error:  # keep going: report at the end
                        failures.append(f"{language}/{name}: {str(error).splitlines()[0]}")
                        print(f"  FAILED {language}/{name}: {error}")
                        page.screenshot(path=str(Path(tempfile.gettempdir()) / f"failed-{language}-{name}.png"))
                context.close()
            browser.close()
    finally:
        server.terminate()
    if failures:
        print("\nFailures:\n" + "\n".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
