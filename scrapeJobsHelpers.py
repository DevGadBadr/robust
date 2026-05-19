from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, ElementNotInteractableException

JOB_TYPES = {
    "geturl": "Get URL",
    "inputfield": "Input Field",
    "clickbutton": "Click Button"
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
    driver.get(url)
    return "Done", jobuuid, direction

def inputFieldJob(driver, **kwargs):
    field_identifier = kwargs.get("field_identifier")
    identifier_value = kwargs.get("identifier_value")
    value = kwargs.get("value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        field = driver.find_element(field_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Field not found", jobuuid, direction
    try:
        field.clear()
        field.send_keys(value)
    except ElementNotInteractableException:
        return "Error: Field not interactable", jobuuid, direction
    return "Done", jobuuid, direction

def clickButtonJob(driver, **kwargs):
    button_identifier = kwargs.get("button_identifier")
    identifier_value = kwargs.get("identifier_value")
    jobuuid = kwargs.get("uuid")
    direction = kwargs.get("direction", "forward")
    try:
        button = driver.find_element(button_identifier, identifier_value)
    except NoSuchElementException:
        return "Error: Button not found", jobuuid, direction
    try:
        button.click()
    except ElementNotInteractableException:
        return "Error: Button not interactable", jobuuid, direction
    except ElementClickInterceptedException:
        return "Error: Button click intercepted", jobuuid, direction
    return "Done", jobuuid, direction