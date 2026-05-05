from selenium.webdriver.common.by import By

JOP_TYPES = {
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
    driver.get(url)
    return "Done"

def inputFieldJob(driver, **kwargs):
    field_identifier = kwargs.get("field_identifier")
    identifier_value = kwargs.get("identifier_value")
    value = kwargs.get("value")
    field = driver.find_element(field_identifier, identifier_value)
    field.clear()
    field.send_keys(value)
    return "Done"

def clickButtonJob(driver, **kwargs):
    button_identifier = kwargs.get("button_identifier")
    identifier_value = kwargs.get("identifier_value")
    button = driver.find_element(button_identifier, identifier_value)
    button.click()
    return "Done"