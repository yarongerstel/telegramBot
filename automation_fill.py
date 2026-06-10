from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import time

SPECIALTIES = {
    "אורטופדיה": "58",
    "אף אוזן גרון": "62",
    "חירורג שד": "501",
    "נשים": "63",
    "עור": "31",
    "עיניים": "61",
}


def run_web(id, year, specialty):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)  # Selenium Manager handles driver automatically
    try:
        driver.get('https://e-services.clalit.co.il/onlinewebquick/nvgq/tamuz/he-il')

        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userId"]').send_keys(id)
        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userYearOfBirth"]').send_keys(year)
        driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_btnLogin_lblInnerText"]').click()

        time.sleep(1)
        driver.get('https://e-services.clalit.co.il/OnlineWebQuick/QuickServices/Tamuz/TamuzTransferContentByService.aspx')
        driver.find_element(By.ID, "ProfessionVisitButton").click()

        select = Select(driver.find_element(By.NAME, 'SelectedSpecializationCode'))
        select.select_by_value(SPECIALTIES[specialty])
        driver.find_element(By.XPATH, '//*[@id="professionSection"]/div[2]/div[1]/table/tbody/tr[4]/td[3]/input').click()
        time.sleep(1)

        try:
            driver.find_element(By.XPATH, '//*[@id="CloseButton"]').click()
        except Exception:
            pass

        times = []
        name_doctor = ""
        date = ""
        location = ""

        try:
            date = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[3]').text
            name_doctor = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[1]').text
        except Exception:
            pass

        location = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[3]/div[1]/a').text
        driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[3]/div[2]/div/a[1]').click()

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

        return date, location, name_doctor, times
    finally:
        driver.quit()
