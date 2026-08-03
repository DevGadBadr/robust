from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, ElementNotInteractableException, WebDriverException, InvalidSelectorException, StaleElementReferenceException, NoSuchFrameException

JOB_TYPES = {
    "geturl": "Get URL",
    "inputfield": "Input Field",
    "clickbutton": "Click Button",
    "extracttext": "Extract Text",
    "extractlinks": "Extract Links"
}

IDENTIFIER_VALUES = {
    "ID": By.ID,
    "NAME": By.NAME,
    "XPATH": By.XPATH, #//*[contains(text(),"text")] For text 
    "CSS_SELECTOR": By.CSS_SELECTOR,
    "CLASS_NAME": By.CLASS_NAME,
    "TAG_NAME": By.TAG_NAME
}

FRAME_TAGS = "iframe, frame"

# Walks a chain of shadow hosts and resolves the locator inside the innermost
# shadow root, which is the only way a shadow scoped element can be reached.
_SHADOW_RESOLVE_JS = """
var hosts = arguments[0] || [];
var selector = arguments[1];
var root = document;
for (var i = 0; i < hosts.length; i++) {
  var host = root.querySelector(hosts[i]);
  if (!host || !host.shadowRoot) return null;
  root = host.shadowRoot;
}
return root.querySelector(selector);
"""


class LocatorContextError(Exception):
    """The frame or shadow host chain a locator was picked in no longer exists."""


def cssEscape(value):
    out = []
    for char in str(value):
        if char.isalnum() or char in "-_" or ord(char) > 127:
            out.append(char)
        else:
            out.append("\\" + char)
    return "".join(out)


def cssQuote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def cssFromLocator(by, value):
    """Express a locator as CSS, since shadow roots only support CSS lookups."""
    if by == By.CSS_SELECTOR:
        return value
    if by == By.ID:
        return "#" + cssEscape(value)
    if by == By.NAME:
        return "[name=" + cssQuote(value) + "]"
    if by == By.CLASS_NAME:
        return "." + cssEscape(value)
    if by == By.TAG_NAME:
        return value
    return None


def resetContext(driver):
    try:
        driver.switch_to.default_content()
    except WebDriverException:
        pass


def enterFrames(driver, frames):
    for entry in frames:
        if not isinstance(entry, dict):
            continue
        frameElement = None
        selector = entry.get("selector")
        if selector:
            try:
                for candidate in driver.find_elements(By.CSS_SELECTOR, selector):
                    if candidate.tag_name.lower() in ("iframe", "frame"):
                        frameElement = candidate
                        break
            except WebDriverException:
                frameElement = None
        if frameElement is None:
            index = entry.get("index", -1)
            try:
                allFrames = driver.find_elements(By.CSS_SELECTOR, FRAME_TAGS)
            except WebDriverException:
                allFrames = []
            if isinstance(index, int) and 0 <= index < len(allFrames):
                frameElement = allFrames[index]
        if frameElement is None:
            raise LocatorContextError("Frame not found: " + str(selector or entry.get("index")))
        try:
            driver.switch_to.frame(frameElement)
        except (NoSuchFrameException, StaleElementReferenceException, WebDriverException):
            raise LocatorContextError("Unable to enter frame: " + str(selector or entry.get("index")))


def resolveElement(driver, by, value, context=None):
    """Find an element, first entering the frame and shadow context it was picked in.

    The caller is responsible for calling resetContext() once it is done with the
    returned element, since a WebElement can only be used while its own frame is
    the active one.
    """
    context = context if isinstance(context, dict) else {}
    frames = context.get("frames") or []
    hosts = context.get("hosts") or []
    resetContext(driver)
    if frames:
        enterFrames(driver, frames)
    if not hosts:
        return driver.find_element(by, value)
    selector = cssFromLocator(by, value)
    if selector is None:
        raise LocatorContextError("Shadow DOM locators must be CSS based, not " + str(by))
    element = driver.execute_script(_SHADOW_RESOLVE_JS, list(hosts), selector)
    if element is None:
        raise NoSuchElementException("No element in shadow root for selector: " + str(selector))
    return element


def findTarget(driver, by, value, context, missingMessage):
    """Resolve an element and turn every lookup failure into a job error string."""
    try:
        return resolveElement(driver, by, value, context), None
    except NoSuchElementException:
        return None, missingMessage
    except InvalidSelectorException:
        return None, "Error: Invalid selector"
    except LocatorContextError as error:
        return None, "Error: " + str(error)
    except StaleElementReferenceException:
        return None, missingMessage
    except WebDriverException:
        return None, missingMessage

def getUrlJob(driver, **kwargs):
    url = kwargs.get("url")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    resetContext(driver)
    try:
        driver.get(url)
    except WebDriverException:
        return "Error: Unable to navigate to URL", jobuuid, direction, None
    return "Done", jobuuid, direction, None

def inputFieldJob(driver, **kwargs):
    field_identifier = kwargs.get("field_identifier")
    identifier_value = kwargs.get("identifier_value")
    value = kwargs.get("value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        field, error = findTarget(driver, field_identifier, identifier_value, kwargs.get("context"), "Error: Field not found")
        if error:
            return error, jobuuid, direction, None
        try:
            field.clear()
            field.send_keys(value)
        except ElementNotInteractableException:
            return "Error: Field not interactable", jobuuid, direction, None
        except StaleElementReferenceException:
            return "Error: Field went stale", jobuuid, direction, None
    finally:
        resetContext(driver)
    return "Done", jobuuid, direction, None

def clickButtonJob(driver, **kwargs):
    button_identifier = kwargs.get("button_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        button, error = findTarget(driver, button_identifier, identifier_value, kwargs.get("context"), "Error: Button not found")
        if error:
            return error, jobuuid, direction, None
        try:
            button.click()
        except ElementNotInteractableException:
            return "Error: Button not interactable", jobuuid, direction, None
        except ElementClickInterceptedException:
            return "Error: Button click intercepted", jobuuid, direction, None
        except StaleElementReferenceException:
            return "Error: Button went stale", jobuuid, direction, None
    finally:
        resetContext(driver)
    return "Done", jobuuid, direction, None

def extractTextJob(driver, **kwargs):
    text_identifier = kwargs.get("text_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        element, error = findTarget(driver, text_identifier, identifier_value, kwargs.get("context"), "Error: Element not found")
        if error:
            return error, jobuuid, direction, None
        try:
            text = element.text or element.get_attribute("value") or ""
        except StaleElementReferenceException:
            return "Error: Element went stale", jobuuid, direction, None
    finally:
        resetContext(driver)
    return "Done", jobuuid, direction, text

def extractLinksJob(driver, **kwargs):
    link_identifier = kwargs.get("link_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        element, error = findTarget(driver, link_identifier, identifier_value, kwargs.get("context"), "Error: Element not found")
        if error:
            return error, jobuuid, direction, None
        links = []
        try:
            if element.tag_name.lower() == "a":
                href = element.get_attribute("href")
                if href:
                    links.append(href)
            for a in element.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href")
                if href and href not in links:
                    links.append(href)
        except StaleElementReferenceException:
            return "Error: Element went stale", jobuuid, direction, None
    finally:
        resetContext(driver)
    return "Done", jobuuid, direction, links
