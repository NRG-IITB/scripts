"""
A robust web scraper to download statistical reports from the ECI website.
Handles pagination for legacy years (pre-2024).

Setup Instructions
1. Install the browser and driver:
   sudo apt update
   sudo apt install chromium-browser chromium-chromedriver

2. Install the required Python library:
   pip install selenium
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def wait_for_downloads_to_complete(folder_path, timeout=300):
    """
    Waits for all Chrome '.crdownload' temporary files in a folder to disappear,
    ensuring all downloads have finished before proceeding.
    """
    print("  -> Verifying all files have finished downloading...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if any temporary download files exist
        if not any(f.endswith('.crdownload') for f in os.listdir(folder_path)):
            print("  -> All downloads for this year are complete.")
            return
        time.sleep(1)
    print(f"  -> WARNING: Download wait timed out after {timeout} seconds. Some files may be incomplete.")

# --- Configuration ---
YEARS_TO_DOWNLOAD = ["2024", "2019", "2014", "2009"]
MAIN_DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")

# --- Main Script ---
# Create the main download directory if it doesn't exist
os.makedirs(MAIN_DOWNLOAD_FOLDER, exist_ok=True)
print(f"Main download directory is: {MAIN_DOWNLOAD_FOLDER}")

for year in YEARS_TO_DOWNLOAD:
    print(f"\n--- Starting process for year: {year} ---")

    # Create a dedicated subfolder for each year's data
    download_folder = os.path.join(MAIN_DOWNLOAD_FOLDER, f"election_data_{year}")
    os.makedirs(download_folder, exist_ok=True)

    # --- Configure Chrome Options ---
    options = Options()
    # Run Chrome in headless mode (no UI window) for server/background execution
    # options.add_argument("--headless")
    # Set a standard window size to prevent mobile layouts in headless mode
    options.add_argument("--window-size=1920,1080")
    # Set a common User-Agent to avoid being identified as a bot
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    
    # Set the custom download folder for this session
    options.add_experimental_option("prefs", {
       "download.default_directory": download_folder,
       "download.prompt_for_download": False,
       "download.directory_upgrade": True,
       "safebrowsing.enabled": True
    })
    
    # Initialize the Selenium WebDriver
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # Navigate to the main reports page
        driver.get('https://www.eci.gov.in/statistical-reports')
        
        # Find and click the link for the target year
        print(f"  -> Navigating to the page for year {year}...")
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, year))).click()

        # --- Logic Switch: Choose the correct download flow based on the year ---
        if int(year) >= 2024:
            print("  -> Using modern (2024) download flow.")
            try:
                # Wait for download icons to be present and get a count
                icons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "fa-file-excel")))
                print(f"  -> Found {len(icons)} Excel files to download.")
                
                # Loop through each icon to download the file
                for i in range(len(icons)):
                    # Re-find elements each loop to avoid "stale element" errors
                    icon = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "fa-file-excel")))[i]
                    print(f"    - Downloading file {i+1}/{len(icons)}...")
                    
                    # Use JavaScript to scroll and click, which is robust against overlapping elements
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon)
                    time.sleep(0.5) # Brief pause for scroll to finish
                    driver.execute_script("arguments[0].click();", icon)
                    
                    # Click the "I agree" button in the confirmation popup
                    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='I agree']"))).click()
                    time.sleep(2) # Politeness cooldown
            except TimeoutException:
                print("  -> No download icons found for this year.")
        
        else: # For years before 2024, use the multi-page legacy flow
            print("  -> Using legacy (pre-2024) download flow.")
            wait.until(EC.number_of_windows_to_be(2))
            driver.switch_to.window(driver.window_handles[1]) # Switch to the newly opened tab
            print(f"  -> Switched to new tab for {year}'s data.")
            
            # --- Pagination Logic ---
            urls_to_process = []
            page_num = 1
            current_page_links = [] # To check for staleness

            while True:
                print(f"  -> Scraping file links from page {page_num}...")
                try:
                    # Wait for the file links on the current page to be present
                    page_links = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h4.ipsDataItem_title a"))
                    )
                    # Get href attribute, but only if it's not None
                    new_urls = [el.get_attribute('href') for el in page_links if el.get_attribute('href')]
                    
                    if not new_urls:
                         print("     -> No links found on this page, but checking for 'next'...")
                    
                    print(f"     -> Found {len(new_urls)} links on this page.")
                    urls_to_process.extend(new_urls)
                    
                    # Store the first link element for the staleness check
                    if page_links:
                        current_page_links = page_links
                
                except TimeoutException:
                    print("     -> No file links found on this page.")
                    # This is fine, might be last page. We'll check for 'next' button.
                    pass 

                # Check for a "Next" page button
                try:
                    # Find the 'Next' button's link.
                    # This selector finds the <li> with class 'ipsPagination_next'
                    # that *does not* have the class 'ipsPagination_inactive'.
                    next_page_button = driver.find_element(By.CSS_SELECTOR, "li.ipsPagination_next:not(.ipsPagination_inactive) a")
                    
                    print("  -> Found 'Next Page' button. Clicking...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_button)
                    time.sleep(0.5) # Brief pause for scroll
                    driver.execute_script("arguments[0].click();", next_page_button) # Use JS click for reliability
                    page_num += 1
                    
                    # Wait for the page to transition by waiting for the old links to go stale
                    if current_page_links:
                        wait.until(EC.staleness_of(current_page_links[0]))
                    else:
                        time.sleep(2) # Fallback wait if no links were on the page

                except NoSuchElementException:
                    # If find_element fails, it means no active 'next' button was found
                    print("  -> No more 'Next Page' buttons found. All pages scraped.")
                    break # Exit the while loop
                except Exception as e:
                    print(f"  -> Error during pagination: {e}. Stopping page search.")
                    break # Exit on other errors
            # --- End of Pagination Logic ---

            print(f"\n  -> Total files found across all pages: {len(urls_to_process)}.")

            for i, url in enumerate(urls_to_process):
                print(f"    - Processing file {i+1}/{len(urls_to_process)}...")
                
                if not url:
                    print("      -> Skipping empty or invalid URL.")
                    continue
                
                driver.get(url)
                
                # Click through the two download confirmation prompts
                try:
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.ipsButton_important"))).click()
                    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Agree & Download')]"))).click()
                except TimeoutException:
                    print(f"      -> ERROR: Could not find 'Agree' buttons for URL: {url}. Skipping file.")
                    continue # Skip to the next URL
                
                # Special handling for 2009 (PDFs) vs. other legacy years (XLS)
                try:
                    if year <= "2009":
                        download_xpath = "//li[contains(., '.pdf')]//a[@data-action='download']"
                        file_type = "PDF"
                    else:
                        download_xpath = "//li[contains(., '.xls')]//a[@data-action='download']"
                        file_type = "Excel"
                    
                    wait.until(EC.element_to_be_clickable((By.XPATH, download_xpath))).click()
                    print(f"      -> Clicked the {file_type} download button.")
                except TimeoutException:
                    print(f"      -> ERROR: Could not find the final {file_type} download link for URL: {url}.")
                
                time.sleep(2) # Politeness cooldown

        print(f"\n--- Finished clicking all download buttons for {year}. ---")

    except Exception as e:
        print(f"An error occurred while processing year {year}: {e}")
        
    finally:
        # Crucial step: Wait for all files to be saved before closing the browser
        wait_for_downloads_to_complete(download_folder)
        print("  -> Closing browser session.")
        driver.quit()

print(f"\nAll specified years have been processed!")
