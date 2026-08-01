from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, ElementNotInteractableException, WebDriverException, InvalidSelectorException

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

def getUrlJob(driver, **kwargs):
    url = kwargs.get("url")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
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
        field = driver.find_element(field_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Field not found", jobuuid, direction, None
    except InvalidSelectorException:
        return "Error: Invalid selector", jobuuid, direction, None
    try:
        field.clear()
        field.send_keys(value)
    except ElementNotInteractableException:
        return "Error: Field not interactable", jobuuid, direction, None
    return "Done", jobuuid, direction, None

def clickButtonJob(driver, **kwargs):
    button_identifier = kwargs.get("button_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        button = driver.find_element(button_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Button not found", jobuuid, direction, None
    except InvalidSelectorException:
        return "Error: Invalid selector", jobuuid, direction, None
    try:
        button.click()
    except ElementNotInteractableException:
        return "Error: Button not interactable", jobuuid, direction, None
    except ElementClickInterceptedException:
        return "Error: Button click intercepted", jobuuid, direction, None
    return "Done", jobuuid, direction, None

def extractTextJob(driver, **kwargs):
    text_identifier = kwargs.get("text_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        element = driver.find_element(text_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Element not found", jobuuid, direction, None
    except InvalidSelectorException:
        return "Error: Invalid selector", jobuuid, direction, None
    text = element.text or element.get_attribute("value") or ""
    return "Done", jobuuid, direction, text

def extractLinksJob(driver, **kwargs):
    link_identifier = kwargs.get("link_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        element = driver.find_element(link_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Element not found", jobuuid, direction, None
    except InvalidSelectorException:
        return "Error: Invalid selector", jobuuid, direction, None
    links = []
    if element.tag_name.lower() == "a":
        href = element.get_attribute("href")
        if href:
            links.append(href)
    for a in element.find_elements(By.TAG_NAME, "a"):
        href = a.get_attribute("href")
        if href and href not in links:
            links.append(href)
    return "Done", jobuuid, direction, links