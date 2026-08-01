"""Load and drive the in-page element picker script."""
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parent / "js" / "elementPicker.js"
_cached = None

# Matches IDENTIFIER_VALUES keys in scrapeJobsHelpers.py
LOCATOR_TYPES = ("ID", "NAME", "XPATH", "CSS_SELECTOR", "CLASS_NAME", "TAG_NAME")


def get_picker_js():
    global _cached
    if _cached is None:
        _cached = _JS_PATH.read_text(encoding="utf-8")
    return _cached


def inject(driver):
    driver.execute_script(get_picker_js())


def start(driver, jobuuid):
    driver.execute_script(
        "if (!window.__robustPicker) { throw new Error('picker not injected'); }"
        "window.__robustPicker.start(arguments[0]);",
        str(jobuuid),
    )


def cancel(driver):
    driver.execute_script(
        "if (window.__robustPicker) { window.__robustPicker.cancel(); }"
        "try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }"
    )


def poll(driver):
    result = driver.execute_script(
        "var r = window.__robustPickResult || null;"
        "if (r) {"
        "  try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }"
        "}"
        "return r;"
    )
    if not result or not isinstance(result, dict):
        return None
    status = result.get("status")
    if status == "picked":
        loc_type = result.get("type")
        if loc_type not in LOCATOR_TYPES:
            return {"status": "cancelled", "jobuuid": result.get("jobuuid")}
        return {
            "status": "picked",
            "jobuuid": result.get("jobuuid"),
            "type": loc_type,
            "value": result.get("value") or "",
        }
    if status == "cancelled":
        return {"status": "cancelled", "jobuuid": result.get("jobuuid")}
    return None
