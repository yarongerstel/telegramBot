from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
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


def run_web(id, year, specialty):
    logger.info(f"Starting Chrome for specialty={specialty}")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        logger.info("Navigating to Clalit login page")
        driver.get('https://e-services.clalit.co.il/onlinewebquick/nvgq/tamuz/he-il')

        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userId"]').send_keys(id)
        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userYearOfBirth"]').send_keys(year)
        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_btnLogin_lblInnerText"]').click()
        logger.info("Login submitted")

        time.sleep(1)
        driver.get('https://e-services.clalit.co.il/OnlineWebQuick/QuickServices/Tamuz/TamuzTransferContentByService.aspx')
        driver.find_element(By.ID, "ProfessionVisitButton").click()

        select = Select(driver.find_element(By.NAME, 'SelectedSpecializationCode'))
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
    finally:
        driver.quit()
        logger.info("Chrome closed")
