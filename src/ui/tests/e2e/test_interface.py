"""Tests of the interface in a real browser, with the mock backend of src/ui/scripts/screenshots.

They check what a person does: the controls are there and can be used, the search filters, the name is
copied, a deletion needs a confirmation. They would have found the switches that were not displayed.

    python -m pip install pytest playwright uvicorn fastapi
    NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service build --dest <dir>
    UI_DIST=<dir> python -m pytest src/ui/tests/e2e -q

The installed Chrome or Edge is used: no browser is downloaded.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

SCREENSHOTS = Path(__file__).resolve().parents[2] / "scripts" / "screenshots"
sys.path.insert(0, str(SCREENSHOTS))

playwright_sync = pytest.importorskip("playwright.sync_api")

import capture  # noqa: E402

DIST = Path(os.environ.get("UI_DIST") or Path(tempfile.gettempdir()) / "ui-docs-build")
pytestmark = pytest.mark.skipif(not (DIST / "index.html").is_file(),
                                reason="build the interface first and give its folder in UI_DIST")


@pytest.fixture(scope="session")
def base():
    port = capture.free_port()
    server = capture.start_server(DIST, port)
    yield f"http://127.0.0.1:{port}"
    server.terminate()


@pytest.fixture(scope="session")
def browser():
    with playwright_sync.sync_playwright() as playwright:
        browser = capture.launch(playwright)
        yield browser
        browser.close()


def open_page(browser, base, language="en", permissions=()):
    context = browser.new_context(viewport=capture.VIEWPORT, service_workers="block",
                                  locale="en-GB" if language == "en" else "fr-FR", timezone_id="Europe/Paris",
                                  permissions=list(permissions))
    context.add_init_script(f"localStorage.setItem('backroll.language', '{language}')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)[:200]))
    shooter = capture.Shooter(page, base, language)
    shooter.login()
    page.errors = errors
    return shooter, page, context


@pytest.fixture
def english(browser, base):
    shooter, page, context = open_page(browser, base, "en", ["clipboard-read", "clipboard-write"])
    yield shooter, page
    context.close()


@pytest.fixture
def french(browser, base):
    shooter, page, context = open_page(browser, base, "fr")
    yield shooter, page
    context.close()


def visible(locator):
    box = locator.bounding_box()
    return box is not None and box["width"] > 4 and box["height"] > 4


# -- the tasks pages: search and copy of the name ----------------------------------------------------------

def test_the_search_filters_the_backups_and_can_be_cleared(english):
    shooter, page = english
    shooter.go("/admin/tasks/backup", ["web-01"])
    rows = page.locator("tbody tr")
    total = rows.count()
    assert total >= 4

    search = page.locator(".task-search input")
    search.fill("mail-01")
    page.wait_for_timeout(300)
    assert 0 < rows.count() < total
    assert all("mail-01" in text for text in rows.all_inner_texts())

    # The state is searched too, in the language of the page.
    search.fill("FAILURE")
    page.wait_for_timeout(300)
    assert all("FAILURE" in text for text in rows.all_inner_texts())

    search.fill("no machine is called like this")
    page.wait_for_timeout(300)
    assert "No items" in page.locator(".va-data-table").inner_text()

    search.fill("")
    page.wait_for_timeout(300)
    assert rows.count() == total


def test_a_backup_skipped_because_the_machine_is_off_is_not_shown_as_a_success(english):
    shooter, page = english
    shooter.go("/admin/tasks/backup", ["web-01"])
    chip = page.locator(".skipped-state")
    assert chip.count() == 1
    assert chip.inner_text().strip() == "SKIPPED"
    # The reason is the hint of the chip, and the counter of the page has its own color.
    assert "not running" in chip.get_attribute("title")
    assert page.locator(".skipped-count").count() == 1
    # The row of the skipped backup does not say success.
    row = page.locator("tbody tr", has=page.locator(".skipped-state"))
    assert "SUCCESS" not in row.inner_text()


def test_the_skipped_state_is_in_french_and_can_be_searched(french):
    shooter, page = french
    shooter.go("/admin/tasks/backup", ["web-01"])
    assert page.locator(".skipped-state").inner_text().strip().upper() == "IGNORÉE"
    page.locator(".task-search input").fill("ignorée")
    page.wait_for_timeout(300)
    assert page.locator("tbody tr").count() == 1


def test_the_search_is_in_french_in_the_french_interface(french):
    shooter, page = french
    shooter.go("/admin/tasks/backup", ["web-01"])
    assert "Rechercher" in page.locator(".task-search input").get_attribute("placeholder")
    page.locator(".task-search input").fill("ÉCHEC")
    page.wait_for_timeout(300)
    assert all("ÉCHEC" in text.upper() for text in page.locator("tbody tr").all_inner_texts())


def test_the_name_of_a_machine_is_copied(english):
    shooter, page = english
    shooter.go("/admin/tasks/backup", ["web-01"])
    button = page.locator("button.copy-name").first
    assert visible(button)
    name = button.locator("xpath=preceding-sibling::*[1]").inner_text().strip()
    button.click()
    assert page.evaluate("navigator.clipboard.readText()") == name
    page.get_by_text("copied", exact=False).first.wait_for(state="visible", timeout=5000)


def test_the_restore_page_has_the_same_search(english):
    shooter, page = english
    shooter.go("/admin/tasks/restore", [])
    assert page.locator(".task-search input").count() == 1


# -- the controls that were not displayed ---------------------------------------------------------------

def test_the_switches_of_the_cleaning_are_displayed_and_work(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    switches = page.locator(".simple-checkbox--toggle")
    assert switches.count() == 2
    assert all(visible(switches.nth(i).locator(".simple-checkbox__box")) for i in range(2))

    # The schedule fields appear with the second switch, and go with it.
    scheduled = switches.nth(1)
    assert scheduled.locator("input").is_checked()
    assert page.get_by_text("Frequency").first.is_visible()
    scheduled.locator(".simple-checkbox__box").click()
    page.wait_for_timeout(300)
    assert not scheduled.locator("input").is_checked()
    assert page.get_by_text("Frequency").count() == 0
    scheduled.locator(".simple-checkbox__box").click()
    page.wait_for_timeout(300)
    assert page.get_by_text("Frequency").first.is_visible()

    # The cron expression can be typed instead.
    raw = page.locator(".simple-checkbox", has_text="cron expression").first
    assert visible(raw.locator(".simple-checkbox__box"))
    raw.locator(".simple-checkbox__box").click()
    page.wait_for_timeout(300)
    page.wait_for_function("() => [...document.querySelectorAll('input')].some(input => input.value === '0 4 * * 0')")


def test_the_repositories_of_deleted_machines_are_chosen_and_confirmed(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    page.get_by_role("button", name="Look for them").click()
    page.get_by_text("i-2-100-VM").first.wait_for(state="visible", timeout=15000)

    boxes = page.locator(".va-data-table .simple-checkbox input")
    assert boxes.count() == 2
    # Nothing is selected by default, and nothing can be deleted before a choice.
    assert not any(boxes.nth(i).is_checked() for i in range(2))
    delete = page.get_by_role("button", name="Delete the selected")
    assert delete.is_disabled()

    page.locator(".va-data-table .simple-checkbox__box").first.click()
    assert delete.is_enabled()
    delete.click()
    # The confirmation word has to be typed.
    ok = page.locator(".va-modal button", has_text="Delete").last
    assert ok.is_disabled()
    page.locator(".va-modal input").fill("DELETE")
    assert ok.is_enabled()
    page.locator(".va-modal input").fill("delet")
    assert ok.is_disabled()


def run_simulation(page):
    page.locator(".simulate-button").click()
    page.get_by_text("web-01").first.wait_for(state="visible", timeout=15000)


def test_the_simulation_ticks_everything_and_lets_the_administrator_untick(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    run_simulation(page)

    # Two repositories, everything ticked by default, nothing shown in detail yet.
    assert page.locator(".sim-repo").count() == 2
    assert page.locator(".repo-box input").evaluate_all("boxes => boxes.every(box => box.checked)")
    assert "5 backups selected" in page.locator(".sim-count").inner_text()
    assert page.locator(".archive-box").count() == 0

    # The backups of a repository are shown, one box each, all ticked.
    page.locator(".expand-button").first.click()
    assert page.locator(".archive-box").count() == 3
    assert page.locator(".archive-box input").evaluate_all("boxes => boxes.every(box => box.checked)")

    # Unticking one backup keeps it, and the box of its repository is no longer ticked.
    page.locator(".archive-box .simple-checkbox__box").nth(1).click()
    assert "4 backups selected" in page.locator(".sim-count").inner_text()
    assert not page.locator(".repo-box input").first.is_checked()

    # Unticking a repository unticks all its backups.
    page.locator(".repo-box .simple-checkbox__box").nth(1).click()
    assert "2 backups selected" in page.locator(".sim-count").inner_text()


def test_only_the_ticked_backups_are_sent_after_the_confirmation_word(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    run_simulation(page)
    page.locator(".expand-button").first.click()
    page.locator(".archive-box .simple-checkbox__box").nth(1).click()   # vda_x_2 is kept

    page.locator(".delete-selection").click()
    ok = page.locator(".va-modal button", has_text="Delete").last
    assert ok.is_disabled()
    page.locator(".va-modal input").fill("DELETE")
    assert ok.is_enabled()
    ok.click()
    page.wait_for_timeout(800)

    calls = page.evaluate("fetch('/__mock/selection-calls').then(r => r.json())")
    assert len(calls) == 1
    assert calls[0]["backups"] == {"web-01": ["vda_x_1", "files_etc_3"], "db-01": ["vda_y_1", "vda_y_2"]}


def test_nothing_can_be_deleted_when_everything_is_unticked(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    run_simulation(page)
    page.get_by_role("button", name="Select none").first.click()
    assert page.locator(".delete-selection").is_disabled()
    page.get_by_role("button", name="Select all").first.click()
    assert page.locator(".delete-selection").is_enabled()


def test_the_example_and_the_warning_for_a_low_number_of_days(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    assert "Example with 3 days" in page.locator(".keep-example").inner_text()
    assert page.locator(".low-days").count() == 0

    days = page.locator("input[type=number]").first
    days.fill("1")
    page.wait_for_timeout(300)
    assert page.locator(".low-days").is_visible()
    assert "1 day" in page.locator(".low-days").inner_text()
    # An unsaved number of days is not simulated: the saved value is the one used.
    assert page.locator(".unsaved").is_visible()
    assert page.locator(".simulate-button").is_disabled()

    days.fill("30")
    page.wait_for_timeout(300)
    assert page.locator(".low-days").count() == 0 and page.locator(".unsaved").count() == 0
    assert page.locator(".simulate-button").is_enabled()


def test_the_simulation_is_in_french_in_the_french_interface(french):
    shooter, page = french
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    assert "Exemple avec 3 jours" in page.locator(".keep-example").inner_text()
    run_simulation(page)
    assert "5 sauvegardes sélectionnées" in page.locator(".sim-count").inner_text()
    page.locator(".delete-selection").click()
    assert page.locator(".va-modal").inner_text().count("5 sauvegardes") == 1


def saved_policy(page, policy_number, expected_name):
    import mock_server
    page.evaluate("fetch('/__mock/policy-patches')")   # warms the page up, the list is read after the click
    return mock_server.rid("policy", policy_number)


def storage_is_shown(page):
    """The storage is a required field of the form: it is saved once the select shows it."""
    page.wait_for_function("() => [...document.querySelectorAll('input')].some(input => (input.value || '').includes('BACKUP_STORAGE'))",
                           timeout=10000)


def test_saving_a_policy_keeps_it_enabled_with_its_folders_and_its_hook(english):
    """Saving a policy sent no `enabled`: its schedule was removed and its backups stopped."""
    shooter, page = english
    policy = saved_policy(page, 1, "daily-backup")
    # The form is saved once the storage of the policy is shown: before, a required field is still empty.
    shooter.go(f"/admin/configuration/policy/{policy}", ["daily-backup"])
    storage_is_shown(page)
    page.get_by_role("button", name="Update").click()
    page.wait_for_function("() => fetch('/__mock/policy-patches').then(r => r.json()).then(list => list.length > 0)",
                           timeout=8000)
    patches = page.evaluate("fetch('/__mock/policy-patches').then(r => r.json())")
    body = patches[-1]
    assert body["id"] == policy
    assert body["enabled"] is True
    assert body["file_paths"] == ["/etc", "/var/www"]
    # The hook is not asserted: the other tests of the session may have deleted it from the demo.


def test_the_storage_of_a_policy_is_chosen_when_the_page_is_opened_before_the_storages_are_known(english):
    """A page opened directly gets the policy first: the storage field stayed empty and had to be chosen again."""
    import time
    shooter, page = english

    def slow(route):
        time.sleep(2)
        route.continue_()
    page.route("**/api/v1/storage", slow)
    policy = saved_policy(page, 2, "weekly-archive")
    shooter.go(f"/admin/configuration/policy/{policy}", ["weekly-archive"])
    storage_is_shown(page)


def test_a_disabled_policy_stays_disabled_when_it_is_saved(english):
    shooter, page = english
    policy = saved_policy(page, 2, "weekly-archive")
    shooter.go(f"/admin/configuration/policy/{policy}", ["weekly-archive"])
    storage_is_shown(page)
    page.get_by_role("button", name="Update").click()
    page.wait_for_function("() => fetch('/__mock/policy-patches').then(r => r.json()).then(list => list.some(item => item.name === 'weekly-archive'))",
                           timeout=8000)
    body = page.evaluate("fetch('/__mock/policy-patches').then(r => r.json())")[-1]
    assert body["id"] == policy and body["enabled"] is False
    assert body["externalhook"] is None


def test_the_cleaning_is_not_started_with_a_number_of_days_that_is_not_saved(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    run = page.locator(".run-button")
    assert run.is_enabled()
    page.locator("input[type=number]").first.fill("365")
    page.wait_for_timeout(300)
    # The confirmation would have named 365 days while the saved 30 are the ones applied.
    assert run.is_disabled() and page.locator(".simulate-button").is_disabled()
    page.locator("input[type=number]").first.fill("30")
    page.wait_for_timeout(300)
    assert run.is_enabled()


def test_the_page_of_a_machine_that_does_not_exist_says_so_instead_of_breaking(english):
    """The gear of a task of a machine that was deleted opened a broken card and an error in the console."""
    shooter, page = english
    shooter.go("/resources/virtualmachines/11111111-2222-3333-4444-555555555555", [], extra_ms=1500)
    page.locator(".vm-not-found").wait_for(state="visible", timeout=10000)
    assert "does not exist any more" in page.locator(".vm-not-found").inner_text()
    assert page.errors == []


def test_the_page_of_an_existing_machine_still_shows_it(english):
    import mock_server
    shooter, page = english
    web01 = next(vm for vm in mock_server.VMS if vm["name"] == "web-01")
    shooter.go(f"/resources/virtualmachines/{web01['uuid']}", ["web-01"])
    assert page.locator(".vm-not-found").count() == 0
    assert page.errors == []


def test_a_refresh_does_not_pile_up_requests_while_the_workers_do_not_answer(english):
    """Each refresh started ten chains that asked again every 2 seconds until the end of their task: with a
    worker stopped or busy they piled up and flooded the API. The new request of a list replaces the old one."""
    import time
    shooter, page = english
    shooter.go("/admin/dashboard", [], extra_ms=800)
    asked = []

    def pending(route):
        asked.append(time.time())
        route.fulfill(status=200, content_type="application/json", body='{"state":"PENDING"}')
    page.route("**/api/v1/status/**", pending)

    refresh = "document.querySelector('#app').__vue_app__.config.globalProperties.$store.dispatch('refreshAll')"
    for _ in range(6):
        page.evaluate(refresh)
        page.wait_for_timeout(400)
    page.wait_for_timeout(3000)
    asked.clear()
    page.wait_for_timeout(4000)
    # About one request every 2 seconds for each of the lists (nine at most): 4 seconds, 2 or 3 rounds. With six
    # chains per list, the same 4 seconds gave more than a hundred.
    assert len(asked) < 40, f"{len(asked)} requests in 4 seconds"


def test_the_disaster_recovery_options_are_displayed(english):
    shooter, page = english
    shooter.go("/admin/tasks/drp", [], extra_ms=800)
    shooter.pick(0, "backup_storage")
    shooter.pick(1, "web-01")
    page.locator("tbody tr").first.wait_for(state="visible")
    # The options of the restore are shown once the CloudStack environment is chosen.
    shooter.pick(3, "cloudstack-lab")
    page.wait_for_function("() => document.querySelectorAll('.va-card .va-select').length >= 9")
    # The disk of the backup can be included, and the two options of the restore can be ticked.
    disk = page.locator("tbody tr").first.locator(".simple-checkbox")
    assert visible(disk.locator(".simple-checkbox__box"))
    assert disk.locator("input").is_checked()
    options = page.locator(".simple-checkbox", has_text="Delete the new")
    assert options.count() == 1 and visible(options.locator(".simple-checkbox__box"))
    assert not options.locator("input").is_checked()
    options.locator(".simple-checkbox__box").click()
    assert options.locator("input").is_checked()
    # The hook of Slack is offered, and chosen when there is only one: the end of the restore is told there.
    hook = page.locator(".drp-hook")
    assert hook.count() == 1
    # The chosen option is displayed in the select, in its text or in its field.
    shown = hook.evaluate("el => el.textContent + ' ' + [...el.querySelectorAll('input')].map(input => input.value).join(' ')")
    assert "slack-notifications" in shown, shown


def test_the_filters_and_toggles_of_the_other_pages_are_displayed(english):
    shooter, page = english
    shooter.go("/admin/auth/audit", ["backup.start"])
    failed_only = page.locator(".simple-checkbox", has_text="Failed only")
    assert visible(failed_only.locator(".simple-checkbox__box"))
    failed_only.locator(".simple-checkbox__box").click()
    page.wait_for_timeout(500)
    assert failed_only.locator("input").is_checked()

    shooter.go("/admin/resources/virtualmachines", [])
    assert visible(page.locator(".simple-checkbox", has_text="Exact match").locator(".simple-checkbox__box"))

    shooter.go("/admin/auth/users", ["operator"])
    page.get_by_text("operator").first.wait_for(state="visible")
    page.locator("tr", has_text="operator").locator("button").first.click()
    page.locator(".va-modal").wait_for(state="visible")
    assert visible(page.locator(".va-modal .simple-checkbox--toggle .simple-checkbox__box"))


# -- the machines whose backups are stopped ------------------------------------------------------------------------

def test_a_machine_that_needs_attention_is_shown_and_its_backups_can_be_resumed(english):
    shooter, page = english
    page.request.post(f"{shooter.base}/__mock/attention")
    shooter.go("/admin/dashboard", ["i-535-18737-VM"])
    card = page.locator(".attention")
    assert "needs attention" in card.inner_text().lower()
    assert "overlay" in card.inner_text()
    page.get_by_role("button", name="I checked it, resume").click()
    # The administrator has to confirm that the disks were checked.
    confirm = page.locator(".va-modal button", has_text="Resume the backups").last
    assert "i-535-18737-VM" in page.locator(".va-modal").inner_text()
    confirm.click()
    page.wait_for_function("() => !document.querySelector('.attention')")


def test_a_connector_that_does_not_answer_is_told_on_the_dashboard_and_on_the_list_of_machines(english):
    shooter, page = english
    page.request.post(f"{shooter.base}/__mock/vm-warnings")
    try:
        shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
        warning = page.locator("[data-testid=machine-list-warning]")
        # The warnings are asked once the list of the machines is known.
        warning.first.wait_for(timeout=20000)
        assert "connector CS could not be listed" in warning.first.inner_text()
        shooter.go("/admin/resources/virtualmachines", ["WEB-01"])
        warning.first.wait_for(timeout=20000)
        assert "only CloudStack knows" in warning.first.inner_text()
    finally:
        page.request.delete(f"{shooter.base}/__mock/vm-warnings")


def test_no_warning_is_shown_when_every_connector_answers(english):
    shooter, page = english
    shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
    # Long enough for the list of the machines and then its warnings to have been asked.
    page.wait_for_timeout(2500)
    assert page.locator("[data-testid=machine-list-warning]").count() == 0


def test_the_alert_of_a_machine_is_in_french_in_the_french_interface(french):
    shooter, page = french
    page.request.post(f"{shooter.base}/__mock/attention")
    shooter.go("/admin/dashboard", ["i-535-18737-VM"])
    assert "à surveiller" in page.locator(".attention").inner_text().lower()
    assert page.get_by_role("button", name="J'ai vérifié, reprendre").count() == 1
    page.request.post(f"{shooter.base}/api/v1/attention/0498dae1/resolve")


def test_the_machines_that_are_not_running_are_counted_apart_and_listed_on_request(english):
    shooter, page = english
    shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
    counter = page.locator(".stopped")
    assert counter.inner_text().strip().startswith("1")
    # They are neither "at risk" nor "never backed up": the card keeps its meaning for the running machines.
    assert page.locator(".va-list-item", has_text="old-test").count() == 0
    # Nothing is hidden: the list opens on a click, with the reason and the last backup of each machine.
    counter.click()
    row = page.locator(".stopped-list .va-list-item", has_text="old-test")
    row.wait_for(state="visible")
    assert "No backup yet" in row.inner_text()
    assert "not running (Shutoff)" in row.locator(".not-running").inner_text()
    counter.click()
    page.wait_for_function("() => !document.querySelector('.stopped-list')")


def test_a_long_list_of_machines_that_are_not_running_shows_ten_then_more_and_can_be_searched(english):
    shooter, page = english
    page.request.post(f"{shooter.base}/__mock/machines?stopped=100")
    try:
        shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
        counter = page.locator(".stopped")
        page.wait_for_function("() => document.querySelector('.stopped')?.innerText.trim().startsWith('101')")
        counter.click()
        rows = page.locator(".stopped-list .va-list-item")
        rows.first.wait_for(state="visible")
        # Not a wall of 100 lines: the first ten, the machines that were never backed up first.
        assert rows.count() == 10
        more = page.locator(".stopped-list .more button")
        assert "Show 10 more (91 left)" in more.inner_text()
        more.click()
        page.wait_for_function("() => document.querySelectorAll('.stopped-list .va-list-item').length === 20")
        assert "Show 10 more (81 left)" in more.inner_text()
        # The search looks in all the machines, not only in the ones that are shown.
        search = page.locator(".stopped-list .search input")
        search.fill("stopped-077")
        page.wait_for_function("() => document.querySelectorAll('.stopped-list .va-list-item').length === 1")
        assert "stopped-077" in rows.first.inner_text()
        assert page.locator(".stopped-list .more").count() == 0
        search.fill("no-such-machine")
        page.locator(".stopped-list .no-match").wait_for(state="visible")
        assert "No machine has this name." in page.locator(".stopped-list .no-match").inner_text()
        # Clearing the search starts again from the first ten.
        search.fill("")
        page.wait_for_function("() => document.querySelectorAll('.stopped-list .va-list-item').length === 10")
    finally:
        page.request.delete(f"{shooter.base}/__mock/machines")


def test_a_long_list_of_machines_to_look_at_is_cut_in_the_same_way(english):
    shooter, page = english
    page.request.post(f"{shooter.base}/__mock/machines?running=15")
    try:
        shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
        rows = page.locator(".problem-list .va-list-item")
        rows.first.wait_for(state="visible")
        # The 15 machines never backed up and the two of the demo (one never backed up, one at risk): ten, the others behind a button.
        assert rows.count() == 10
        more = page.locator(".problem-list .more button")
        assert "Show 7 more (7 left)" in more.inner_text()
        more.click()
        page.wait_for_function("() => document.querySelectorAll('.problem-list .va-list-item').length === 17")
        assert page.locator(".problem-list .more").count() == 0
    finally:
        page.request.delete(f"{shooter.base}/__mock/machines")


def test_a_short_list_has_neither_search_nor_button(english):
    shooter, page = english
    shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
    page.locator(".stopped").click()
    page.locator(".stopped-list .va-list-item").first.wait_for(state="visible")
    assert page.locator(".stopped-list .search").count() == 0 and page.locator(".stopped-list .more").count() == 0


def test_the_long_list_is_in_french_in_the_french_interface(french):
    shooter, page = french
    page.request.post(f"{shooter.base}/__mock/machines?stopped=30")
    try:
        shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
        page.wait_for_function("() => document.querySelector('.stopped')?.innerText.trim().startsWith('31')")
        page.locator(".stopped").click()
        page.locator(".stopped-list .more button").wait_for(state="visible")
        assert "Voir 10 de plus (21 restantes)" in page.locator(".stopped-list .more button").inner_text()
        assert page.locator(".stopped-list .search input").get_attribute("placeholder") == "Rechercher une machine"
    finally:
        page.request.delete(f"{shooter.base}/__mock/machines")


def test_the_dashboard_shows_no_alert_when_nothing_waits(english):
    shooter, page = english
    shooter.go("/admin/dashboard", ["BACKUP_STORAGE"])
    assert page.locator(".attention").count() == 0


# -- the Slack hooks ---------------------------------------------------------------------------------------------

def test_the_hooks_page_hides_the_address_and_the_test_button_sends_a_test(english):
    shooter, page = english
    before = page.request.get(f"{shooter.base}/__mock/hook-tests").json()["count"]
    shooter.go("/admin/configuration/externalhooks", ["slack-notifications"])
    row = page.locator("tbody tr", has_text="slack-notifications")
    # The address of the webhook is a secret: the list shows a mask, and the page never holds the address.
    assert "MASKED" in row.inner_text()
    assert "hooks.slack.com/services" not in page.content()
    row.locator("button").first.click()
    page.get_by_text("Test messages were posted", exact=False).first.wait_for(state="visible", timeout=5000)
    assert page.request.get(f"{shooter.base}/__mock/hook-tests").json()["count"] == before + 1


def test_the_form_of_a_hook_keeps_the_masked_address(english):
    shooter, page = english
    shooter.go("/admin/configuration/externalhooks", ["slack-notifications"])
    page.locator("tbody tr", has_text="slack-notifications").locator("a[href*='/externalhooks/']").first.click()
    page.wait_for_function("() => [...document.querySelectorAll('input')].some(input => input.value.includes('…'))")
    values = page.eval_on_selector_all("input", "inputs => inputs.map(input => input.value)")
    # What the form holds, and sends back unchanged, is the mask: the server keeps the address it has.
    assert any(value.startswith("https://hooks.slack.com/…") for value in values)
    assert not any("/services/" in value for value in values)


def test_the_documentation_says_that_the_secrets_of_the_connectors_and_hooks_are_encrypted(english):
    shooter, page = english
    shooter.go("/admin/documentation", [])
    connectors = page.locator("[data-section=connectors]").inner_text()
    hooks = page.locator("[data-section=hooks]").inner_text()
    assert "encrypted" in connectors and "SECRETS_KEY" in connectors and "type the secret again" in connectors
    assert "encrypted" in hooks and "masked" in hooks


def test_the_french_documentation_says_that_the_secrets_are_encrypted(french):
    shooter, page = french
    shooter.go("/admin/documentation", [])
    connectors = page.locator("[data-section=connectors]").inner_text()
    hooks = page.locator("[data-section=hooks]").inner_text()
    assert "chiffrée" in connectors and "SECRETS_KEY" in connectors and "retapez le secret" in connectors
    assert "chiffrée" in hooks and "masquée" in hooks


# -- the Active Directory -----------------------------------------------------------------------------------------------

def test_the_directory_page_shows_the_connection_and_the_groups_without_the_password(english):
    shooter, page = english
    shooter.go("/admin/auth/directory", ["BackROLL-Admins"])
    values = page.eval_on_selector_all("input", "inputs => inputs.map(input => input.value)")
    assert "ldaps://dc01.corp.local:636" in values and "DC=corp,DC=local" in values
    # The password of the service account is never given back: the field is empty and says it is kept.
    password = page.locator("input[type=password]")
    assert password.input_value() == "" and password.get_attribute("placeholder") == "Unchanged"
    assert page.locator(".groups tbody tr").count() == 3
    # Each group shows its role in a select.
    roles = page.eval_on_selector_all(
        ".groups .role-select", "els => els.map(e => (e.textContent + ' ' + [...e.querySelectorAll('input')].map(i => i.value).join(' ')).trim())")
    assert len(roles) == 3 and all(roles)


def test_the_directory_settings_can_be_saved_only_when_something_changed_and_valid(english):
    shooter, page = english
    shooter.go("/admin/auth/directory", ["BackROLL-Admins"])
    save = page.locator("button.save")
    assert save.is_disabled()
    field = page.locator("input[type=number]").first
    field.fill("20")
    assert save.is_enabled()
    # An address that is not ldap(s):// can not be saved.
    page.get_by_label("Address of the directory").fill("dc01.corp.local")
    assert save.is_disabled()
    page.get_by_label("Address of the directory").fill("ldaps://dc01.corp.local:636")
    assert save.is_enabled()
    save.click()
    page.get_by_text("settings of the directory are saved", exact=False).first.wait_for(state="visible", timeout=5000)
    page.wait_for_function("() => document.querySelector('button.save').disabled")


def test_the_connection_test_says_whether_the_directory_answers(english):
    shooter, page = english
    shooter.go("/admin/auth/directory", ["BackROLL-Admins"])
    page.locator("button.test-connection").click()
    assert "The directory answers" in page.locator(".test-result").first.inner_text()
    page.get_by_label("Address of the directory").fill("ldaps://unreachable.corp.local:636")
    page.locator("button.test-connection").click()
    page.wait_for_function("() => document.querySelector('.test-result')?.innerText.includes('could not be reached')")


def test_a_group_is_given_a_role_changed_and_removed_after_a_confirmation(english):
    shooter, page = english
    shooter.go("/admin/auth/directory", ["BackROLL-Admins"])
    rows = page.locator(".groups tbody tr")
    before = rows.count()
    page.locator(".group-input input").first.fill("BackROLL-Auditors")
    page.locator("button.add-button").click()
    page.get_by_text("BackROLL-Auditors", exact=False).first.wait_for(state="visible", timeout=5000)
    assert rows.count() == before + 1
    row = page.locator(".groups tbody tr", has_text="BackROLL-Auditors")
    row.locator("button").last.click()
    confirm = page.locator(".va-modal button", has_text="Remove").last
    assert "BackROLL-Auditors" in page.locator(".va-modal").inner_text()
    confirm.click()
    page.wait_for_function("() => ![...document.querySelectorAll('.groups tbody tr')].some(row => row.innerText.includes('BackROLL-Auditors'))")


def test_a_user_can_be_looked_up_to_see_the_role_he_would_get(english):
    shooter, page = english
    shooter.go("/admin/auth/directory", ["BackROLL-Admins"])
    page.get_by_label("User name").fill("bob")
    page.locator("button.lookup-button").click()
    result = page.locator(".lookup-result")
    result.wait_for(state="visible")
    assert "BackROLL-Operators" in result.inner_text() and "would get the role" in result.inner_text()
    page.get_by_label("User name").fill("frank")
    page.locator("button.lookup-button").click()
    page.wait_for_function("() => document.querySelector('.lookup-result')?.innerText.includes('none of the groups')")


def test_the_users_of_the_directory_are_marked_and_their_role_is_not_edited_here(english):
    shooter, page = english
    shooter.go("/admin/auth/users", ["alice"])
    row = page.locator("tbody tr", has_text="alice")
    assert "Active Directory" in row.locator(".source").inner_text()
    assert "Local" in page.locator("tbody tr", has_text="operator").locator(".source").inner_text()
    row.locator("button").first.click()
    modal = page.locator(".va-modal")
    modal.wait_for(state="visible")
    # His role comes from his groups and his password from the directory: nothing to type for them.
    assert modal.locator(".directory-note").count() == 1
    assert modal.locator("input[type=password]").count() == 0


def test_the_audit_log_can_be_limited_to_the_users_of_the_directory(english):
    shooter, page = english
    shooter.go("/admin/auth/audit", ["alice"])
    assert "Active Directory" in page.locator("tbody tr", has_text="alice").first.locator(".source").inner_text()
    page.get_by_label("Source").click()
    page.locator(".va-select-option-list__option", has_text="Active Directory").first.click()
    page.wait_for_function("() => [...document.querySelectorAll('tbody tr')].every(row => /alice|frank/.test(row.innerText))")
    # Only the users of the directory are left: look at the column of the user, not at the details.
    users = page.eval_on_selector_all("tbody tr", "rows => rows.map(row => row.children[1].innerText.trim())")
    assert users and set(users) <= {"alice", "frank"}


def test_the_login_page_tells_that_the_active_directory_account_can_be_used(browser, base):
    context = browser.new_context(viewport=capture.VIEWPORT, service_workers="block", locale="en-GB")
    context.add_init_script("localStorage.setItem('backroll.language', 'en')")
    page = context.new_page()
    page.goto(f"{base}/login")
    page.get_by_text("Active Directory account", exact=False).first.wait_for(state="visible", timeout=10000)
    context.close()


# -- the settings --------------------------------------------------------------------------------------------

def test_the_settings_can_be_saved_only_when_something_changed(english):
    shooter, page = english
    shooter.go("/admin/auth/settings", [])
    page.wait_for_function("() => document.querySelector('input[type=number]')?.value")
    save = page.get_by_role("button", name="Save")
    assert save.is_disabled()
    field = page.locator("input[type=number]").first
    field.fill("5")
    assert save.is_enabled()
    field.fill("0")
    assert save.is_disabled()


def test_the_settings_show_the_limit_of_the_storage_alert(english):
    shooter, page = english
    shooter.go("/admin/auth/settings", [])
    page.wait_for_function("() => document.querySelector('input[type=number]')?.value")
    # The labels are shown in capitals by the page: the text is compared without the case.
    text = page.locator("body").inner_text().lower()
    assert "tell slack when a backup storage is this full" in text and "% used" in text
    values = page.eval_on_selector_all("input[type=number]", "inputs => inputs.map(input => input.value)")
    assert "85" in values


def test_the_settings_are_in_french_with_the_storage_alert(french):
    shooter, page = french
    shooter.go("/admin/auth/settings", [])
    page.wait_for_function("() => document.querySelector('input[type=number]')?.value")
    text = page.locator("body").inner_text().lower()
    assert "prévenir slack quand un stockage de sauvegarde est plein" in text and "% utilisés" in text


# -- the language ----------------------------------------------------------------------------------------------

def test_the_language_follows_the_choice_and_is_remembered(english):
    shooter, page = english
    shooter.go("/admin/tasks/cleanup", ["backup_storage"])
    assert page.get_by_text("Run now").count() > 0
    # The flag of the top bar opens the choice of the language.
    page.locator(".language-dropdown .va-dropdown__anchor").click()
    page.get_by_text("French", exact=True).click()
    page.wait_for_timeout(500)
    assert page.get_by_text("Lancer maintenant").count() > 0
    assert page.get_by_text("Run now", exact=True).count() == 0
    # The choice is remembered for the next visit.
    assert page.evaluate("localStorage.getItem('backroll.language')") == "fr"


@pytest.mark.parametrize("route", [
    "/admin/dashboard", "/admin/tasks/backup", "/admin/tasks/cleanup", "/admin/tasks/kickstart",
    "/admin/tasks/drp", "/admin/auth/settings", "/admin/documentation"])
def test_no_page_raises_an_error(english, route):
    shooter, page = english
    shooter.go(route, [])
    page.wait_for_timeout(800)
    assert page.errors == []
