# Contributing

Every new feature and every fix comes with tests, and the tests run by themselves (GitHub Actions, on every push).

| What changes | Test to add | Where |
|---|---|---|
| An API route | A test of its behaviour. The access control (401 without a token, 403 for a viewer on a write) is checked for every route by `test_route_security.py`: a route without a guard fails it. | `src/core/python_project/tests/` |
| A rule of the backend (retention, cleaning, queue, history...) | A test that fails without the change | `src/core/python_project/tests/` |
| A screen or a control | A test in a real browser (Playwright) with the mock backend | `src/ui/tests/e2e/` |
| A text of the interface | The key in both languages (`en` and `fr`) | `src/ui/src/i18n/pages/`, checked by `src/ui/scripts/i18n_check.py` |
| A bug | A test that reproduces it, written first | where the bug lives |

Run them:

    cd src/core/python_project && pytest tests -q
    python src/ui/scripts/i18n_check.py
    UI_DIST=<build folder> python -m pytest src/ui/tests/e2e -q

The workflow `.github/workflows/tests.yml` runs the three on every push and every pull request. Do not merge while it is red.
