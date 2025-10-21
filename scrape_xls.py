import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

wait_for_page_to_load = lambda x: time.sleep(x) # wrapper function to wait for page load

# configure Chrome options
options = Options()
options.headless = True  # enable headless mode

# Set the path to the Chromedriver
DRIVER_PATH = '/home/gmangipu/chrome/chromedriver-linux64/chromedriver'

# initialize the Chrome driver with the specified options
chrome_service = webdriver.ChromeService(executable_path=DRIVER_PATH)
driver = webdriver.Chrome(options=options, service=chrome_service)

# visit eci.gov.in and navigate to the 2024 election data
driver.get('https://www.eci.gov.in/statistical-reports')
wait_for_page_to_load(5)
election_2024 = driver.find_element(By.LINK_TEXT, "2024")
election_2024.click()
wait_for_page_to_load(5)

# download all PDF files
pdfs = driver.find_elements(By.CLASS_NAME, "fa-file-excel") # find all PDFs
actions = ActionChains(driver)
for p in pdfs:
    actions.move_to_element(p).click().perform() # scroll to element before clicking, will crash otherwise
    wait_for_page_to_load(1)
    for b in driver.find_elements(By.TAG_NAME, "button"):
        if b.text == "I agree": # this button has no class/id, so check text
            b.click()
            break
    time.sleep(1) # cooldown between downloads to avoid flagging by server

driver.quit()