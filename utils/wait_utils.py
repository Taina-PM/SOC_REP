from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_presence(driver, by, locator, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))

def wait_for_clickable(driver, by, locator, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, locator)))
  