"""Load and drive the in-page element picker script."""
import json
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from scrapeJobsHelpers import IDENTIFIER_VALUES, LocatorContextError, resetContext, resolveElement

_JS_PATH = Path(__file__).resolve().parent / "js" / "elementPicker.js"
_cached = None

# Matches IDENTIFIER_VALUES keys in scrapeJobsHelpers.py
LOCATOR_TYPES = tuple(IDENTIFIER_VALUES.keys())

FRAME_TAGS = "iframe, frame"
MAX_FRAME_DEPTH = 4
MAX_FRAMES_PER_LEVEL = 12
_CDP_ATTR = "_robustPickerCdpScript"

_POLL_JS = """
var out = {};
var result = window.__robustPickResult || null;
if (result) {
  try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }
  out.result = result;
}
out.health = window.__robustPicker ? window.__robustPicker.status() : null;
return out;
"""

_DESCRIBE_FRAME_JS = (
    "return window.__robustPicker ? window.__robustPicker.describeFrame(arguments[0]) : null;"
)

_INIT_JS = (
    "window.__robustPickerInit(arguments[0]);"
    "if (arguments[1] !== null) { return window.__robustPicker.armWhenReady(arguments[1]); }"
    "return true;"
)


def get_picker_js():
    global _cached
    if _cached is None:
        _cached = _JS_PATH.read_text(encoding="utf-8")
    return _cached


def _install(driver, framePath, frameChain, jobuuid):
    try:
        driver.execute_script(get_picker_js())
        driver.execute_script(
            _INIT_JS,
            {"framePath": list(framePath), "frames": list(frameChain)},
            None if jobuuid is None else str(jobuuid),
        )
        return True
    except WebDriverException:
        return False


def _describeFrame(driver, frameElement, index):
    descriptor = None
    try:
        descriptor = driver.execute_script(_DESCRIBE_FRAME_JS, frameElement)
    except WebDriverException:
        descriptor = None
    descriptor = descriptor if isinstance(descriptor, dict) else {}
    entry = {"index": index}
    for key in ("selector", "name", "id"):
        value = descriptor.get(key)
        if value:
            entry[key] = str(value)
    return entry


def _enterPath(driver, framePath):
    """Re-enter a frame path from the top, for when climbing out fails."""
    try:
        driver.switch_to.default_content()
        for index in framePath:
            frames = driver.find_elements(By.CSS_SELECTOR, FRAME_TAGS)
            if index >= len(frames):
                return False
            driver.switch_to.frame(frames[index])
        return True
    except WebDriverException:
        return False


def _walkFrames(driver, visit, framePath=(), frameChain=(), depth=0):
    """Depth first walk of every reachable frame, visiting each once.

    The driver is left in the frame it started in.
    """
    visit(framePath, frameChain)
    if depth >= MAX_FRAME_DEPTH:
        return
    try:
        frames = driver.find_elements(By.CSS_SELECTOR, FRAME_TAGS)
    except WebDriverException:
        return
    for index, frameElement in enumerate(frames[:MAX_FRAMES_PER_LEVEL]):
        entry = _describeFrame(driver, frameElement, index)
        try:
            driver.switch_to.frame(frameElement)
        except WebDriverException:
            continue
        try:
            _walkFrames(driver, visit, tuple(framePath) + (index,), tuple(frameChain) + (entry,), depth + 1)
        finally:
            try:
                driver.switch_to.parent_frame()
            except WebDriverException:
                if not _enterPath(driver, framePath):
                    print("Failed to re-enter frame path", framePath, "after leaving a child frame")


def _registerPersistent(driver, jobuuid):
    """Keep the picker alive across navigations that happen while it is armed."""
    _unregisterPersistent(driver)
    source = (
        get_picker_js()
        + "\n;(function () { try {"
        + " if (window.top !== window) { return; }"
        + " window.__robustPickerInit({framePath: [], frames: []});"
        + " window.__robustPicker.armWhenReady(" + json.dumps(str(jobuuid)) + ");"
        + " } catch (e) {} })();\n"
    )
    try:
        result = driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": source}
        )
        setattr(driver, _CDP_ATTR, (result or {}).get("identifier"))
    except Exception:
        setattr(driver, _CDP_ATTR, None)


def _unregisterPersistent(driver):
    identifier = getattr(driver, _CDP_ATTR, None)
    if identifier is None:
        return
    try:
        driver.execute_cdp_cmd(
            "Page.removeScriptToEvaluateOnNewDocument", {"identifier": identifier}
        )
    except Exception:
        pass
    setattr(driver, _CDP_ATTR, None)


def inject(driver, jobuuid=None):
    """Inject (and optionally arm) the picker in the top document and every frame.

    Returns the number of frames the picker was installed in.
    """
    installed = [0]

    def visit(framePath, frameChain):
        if _install(driver, framePath, frameChain, jobuuid):
            installed[0] += 1

    resetContext(driver)
    try:
        _walkFrames(driver, visit)
    finally:
        resetContext(driver)
    return installed[0]


def start(driver, jobuuid):
    installed = inject(driver, jobuuid=jobuuid)
    if not installed:
        raise WebDriverException("picker could not be installed in any frame")
    _registerPersistent(driver, jobuuid)
    return installed


def cancel(driver):
    _unregisterPersistent(driver)

    def visit(_framePath, _frameChain):
        try:
            driver.execute_script("if (window.__robustPicker) { window.__robustPicker.cancel(); }")
        except WebDriverException:
            pass

    resetContext(driver)
    try:
        _walkFrames(driver, visit)
    finally:
        resetContext(driver)
        try:
            driver.execute_script(
                "try { delete window.__robustPickResult; } catch (e) { window.__robustPickResult = null; }"
            )
        except WebDriverException:
            pass


def _cleanContext(context):
    if not isinstance(context, dict):
        return None
    frames = []
    for frame in context.get("frames") or []:
        if not isinstance(frame, dict):
            continue
        entry = {}
        try:
            entry["index"] = int(frame.get("index", -1))
        except (TypeError, ValueError):
            entry["index"] = -1
        for key in ("selector", "name", "id"):
            value = frame.get(key)
            if value:
                entry[key] = str(value)
        frames.append(entry)
    hosts = [str(host) for host in (context.get("hosts") or []) if host]
    cleaned = {}
    if frames:
        cleaned["frames"] = frames
    if hosts:
        cleaned["hosts"] = hosts
    return cleaned or None


def poll(driver):
    """Read a pending pick from the top document.

    Returns None when nothing happened yet, a picked/cancelled result, or
    {"status": "lost"} when the picker is gone (usually a navigation wiped it),
    which the caller should recover from by re-arming.
    """
    resetContext(driver)
    try:
        raw = driver.execute_script(_POLL_JS)
    except WebDriverException:
        return {"status": "lost", "reason": "page not reachable"}
    if not isinstance(raw, dict):
        return {"status": "lost", "reason": "picker not present"}
    result = raw.get("result")
    if isinstance(result, dict):
        status = result.get("status")
        if status == "picked":
            locatorType = result.get("type")
            if locatorType not in LOCATOR_TYPES:
                return {"status": "cancelled", "jobuuid": result.get("jobuuid")}
            return {
                "status": "picked",
                "jobuuid": result.get("jobuuid"),
                "type": locatorType,
                "value": result.get("value") or "",
                "context": _cleanContext(result.get("context")),
            }
        if status == "cancelled":
            return {"status": "cancelled", "jobuuid": result.get("jobuuid")}
    health = raw.get("health")
    if not isinstance(health, dict) or not health.get("armed"):
        return {"status": "lost", "reason": "picker not armed"}
    return None


def verify(driver, locatorType, value, context=None):
    """Resolve a picked locator the same way a job will, before offering it.

    Returns (ok, message).
    """
    by = IDENTIFIER_VALUES.get(locatorType)
    if by is None:
        return False, "Unknown identifier type " + str(locatorType)
    try:
        element = resolveElement(driver, by, value, context)
    except LocatorContextError as error:
        return False, str(error)
    except WebDriverException as error:
        message = getattr(error, "msg", None) or str(error)
        return False, message.strip().splitlines()[0] if message else "locator did not resolve"
    finally:
        resetContext(driver)
    return element is not None, ""
