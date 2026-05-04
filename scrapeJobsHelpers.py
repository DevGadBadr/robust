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