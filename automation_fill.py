from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

logger = logging.getLogger(__name__)

SPECIALTIES = {
    "אורטופדיה": "58",
    "אף אוזן גרון": "62",
    "חירורג שד": "501",
    "נשים": "63",
    "עור": "31",
    "עיניים": "61",
}


def _make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def start_login(user_id, year):
    """Opens browser, submits ID+year login. Returns driver (now on OTP page)."""
    logger.info(f"Starting login for user_id={user_id}")
    driver = _make_driver()
    driver.get("https://e-services.clalit.co.il/onlinewebquick/nvgq/tamuz/he-il")

    driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userId"]').send_keys(user_id)
    driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userYearOfBirth"]').send_keys(year)
    driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_btnLogin_lblInnerText"]').click()

    time.sleep(2)
    logger.info(f"After login click — URL: {driver.current_url}, title: {driver.title}")

    # Log all visible inputs so we can identify the OTP field
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        logger.info(f"  Input found: type={inp.get_attribute('type')!r}, "
                    f"id={inp.get_attribute('id')!r}, name={inp.get_attribute('name')!r}")

    return driver


def enter_otp(driver, otp_code):
    """Enters the SMS OTP code and submits. Returns True on success."""
    logger.info(f"Entering OTP: {otp_code}")
    logger.info(f"Current URL before OTP: {driver.current_url}")

    # Try common XPath patterns for the OTP field
    otp_xpaths = [
        '//*[contains(@id, "SmsCode") or contains(@id, "smsCode") or contains(@id, "Otp") or contains(@id, "otp")]',
        '//*[contains(@name, "SmsCode") or contains(@name, "smsCode")]',
        '//input[@type="text" and not(contains(@id, "userId")) and not(contains(@id, "Year"))]',
        '//input[@type="number"]',
        '//input[@type="tel"]',
    ]

    otp_input = None
    for xpath in otp_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                otp_input = elements[0]
                logger.info(f"OTP field found with xpath: {xpath}, id={otp_input.get_attribute('id')!r}")
                break
        except Exception:
            continue

    if otp_input is None:
        # Log page source excerpt to help debug
        logger.error("OTP input not found. Page title: " + driver.title)
        logger.error("Page source (first 3000 chars):\n" + driver.page_source[:3000])
        raise RuntimeError("לא נמצא שדה קוד OTP בעמוד")

    otp_input.clear()
    otp_input.send_keys(otp_code)

    # Find and click submit button
    submit_xpaths = [
        '//*[contains(@id, "btnSend") or contains(@id, "btnLogin") or contains(@id, "btnConfirm") or contains(@id, "btnOtp")]',
        '//input[@type="submit"]',
        '//button[@type="submit"]',
        '//*[contains(@class, "btn") and (contains(text(), "אישור") or contains(text(), "המשך") or contains(text(), "שלח"))]',
    ]
    submit_btn = None
    for xpath in submit_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                submit_btn = elements[0]
                logger.info(f"Submit button found: {xpath}, id={submit_btn.get_attribute('id')!r}")
                break
        except Exception:
            continue

    if submit_btn is None:
        logger.error("Submit button not found after OTP entry")
        raise RuntimeError("לא נמצא כפתור אישור לאחר הזנת OTP")

    submit_btn.click()
    time.sleep(2)
    logger.info(f"After OTP submit — URL: {driver.current_url}, title: {driver.title}")
    return True


def search_once(driver, specialty):
    """Search for appointments using an existing logged-in session."""
    logger.info(f"Searching for specialty={specialty}")
    driver.get("https://e-services.clalit.co.il/OnlineWebQuick/QuickServices/Tamuz/TamuzTransferContentByService.aspx")
    time.sleep(1)
    logger.info(f"Tamuz page URL: {driver.current_url}, title: {driver.title}")

    driver.find_element(By.ID, "ProfessionVisitButton").click()

    select = Select(driver.find_element(By.NAME, "SelectedSpecializationCode"))
    select.select_by_value(SPECIALTIES[specialty])
    logger.info(f"Selected specialty: {specialty} (code {SPECIALTIES[specialty]})")
    driver.find_element(By.XPATH, '//*[@id="professionSection"]/div[2]/div[1]/table/tbody/tr[4]/td[3]/input').click()
    time.sleep(1)

    try:
        driver.find_element(By.XPATH, '//*[@id="CloseButton"]').click()
        logger.info("Closed popup banner")
    except Exception:
        pass

    times = []
    name_doctor = ""
    date = ""
    location = ""

    try:
        date = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[3]').text
        name_doctor = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[1]').text
        logger.info(f"First result: doctor={name_doctor}, date={date}")
    except Exception:
        logger.warning("Could not read doctor/date from diariesList")

    location = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[3]/div[1]/a').text
    driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[3]/div[2]/div/a[1]').click()
    logger.info(f"Location: {location}")

    # morning
    driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[2]/ul/li[1]/a').click()
    if driver.find_element(By.XPATH, '//*[@id="morning-noAvailableQueues"]').text != "אין תורים בשעות האלו":
        try:
            driver.find_element(By.XPATH, '//*[@id="morning-moreVisits"]/a').click()
        except Exception:
            pass
        for i in range(1, 20):
            try:
                times.append(driver.find_element(By.XPATH, f'//*[@id="morning-panel"]/ul/li[{i}]/span[1]').text)
            except Exception:
                break

    # noon
    try:
        driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[2]/ul/li[2]/a').click()
        if driver.find_element(By.XPATH, '//*[@id="noon-noAvailableQueues"]/span').text != "אין תורים בשעות האלו":
            try:
                driver.find_element(By.XPATH, '//*[@id="noon-moreVisits"]/a').click()
            except Exception:
                pass
            for i in range(1, 20):
                try:
                    times.append(driver.find_element(By.XPATH, f'//*[@id="noon-panel"]/ul/li[{i}]/span[1]').text)
                except Exception:
                    break
    except Exception:
        pass

    # evening
    try:
        driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[1]/ul/li[3]/a').click()
        if driver.find_element(By.XPATH, '//*[@id="evening-noAvailableQueues"]').text != "אין תורים בשעות האלו":
            try:
                driver.find_element(By.XPATH, '//*[@id="evening-moreVisits"]/a').click()
            except Exception:
                pass
            for i in range(1, 20):
                try:
                    times.append(driver.find_element(By.XPATH, f'//*[@id="evening-panel"]/ul/li[{i}]/span[1]').text)
                except Exception:
                    break
    except Exception:
        pass

    logger.info(f"Found {len(times)} time slots")
    return date, location, name_doctor, times
