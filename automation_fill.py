from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import time


def run_web(id, year, specialty):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get('https://e-services.clalit.co.il/onlinewebquick/nvgq/tamuz/he-il')

    id_box = driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userId"]')
    # input id from the user
    id_box.send_keys(id)

    year_box = driver.find_element(By.XPATH, '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_userYearOfBirth"]')
    # input tear from the user
    year_box.send_keys(year)

    continue_button = driver.find_element(By.XPATH,
                                          '//*[@id="ctl00_ctl00_cphBody_bodyContent_ucQuickLogin_btnLogin_lblInnerText"]')
    continue_button.click()

    time.sleep(1)
    driver.get('https://e-services.clalit.co.il/OnlineWebQuick/QuickServices/Tamuz/TamuzTransferContentByService.aspx')
    driver.find_element(By.ID, "ProfessionVisitButton").click()
    select = Select(driver.find_element(By.NAME, 'SelectedSpecializationCode'))
    switcher = {
        "אורטופדיה": "58",
        "אף אוזן גרון": "62",
        "חירורג שד": "501",
        "נשים": "63",
        "עור": "31",
        "עיניים": "61"
    }
    specialty_number = switcher.get(specialty)
    select.select_by_value(f'{specialty_number}')
    driver.find_element(By.XPATH, '//*[@id="professionSection"]/div[2]/div[1]/table/tbody/tr[4]/td[3]/input').click()
    time.sleep(1)

    # if pop banner about faraway queue close that
    try:
        driver.find_element(By.XPATH, '//*[@id="CloseButton"]').click()
    except:
        pass

    times = []  # str of all the free queue's
    name_doctor = ""
    date = ""
    location = ""

    try:
        # the date
        date = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[3]').text
        # name of doctor
        name_doctor = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[2]/div[1]').text
    except:
        pass
    # the location
    location = driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[1]/div[3]/div[1]/a').text

    driver.find_element(By.XPATH, '//*[@id="diariesList"]/li[1]/div[3]/div[2]/div/a[1]').click()

    # find all free queue's:

    # morning
    driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[2]/ul/li[1]/a').click()
    if driver.find_element(By.XPATH, '//*[@id="morning-noAvailableQueues"]').text != "אין תורים בשעות האלו":
        try:
            driver.find_element(By.XPATH, '//*[@id="morning-moreVisits"]/a').click()
        except:
            pass
        # Puts all the free time on the list
        for i in range(1, 20):
            try:
                times.append(
                    driver.find_element(By.XPATH, '//*[@id="morning-panel"]/ ul/li[' + str(i) + ']/ span[1]').text)
            except:
                break
    # noon
    try:
        driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[2]/ul/li[2]/a').click()
        if driver.find_element(By.XPATH, '//*[@id="noon-noAvailableQueues"]/span').text != "אין תורים בשעות האלו":
            try:
                driver.find_element(By.XPATH, '//*[@id="noon-moreVisits"]/a').click()
            except:
                pass
            # Puts all the free time on the list
            for i in range(1, 20):
                try:
                    times.append(
                        driver.find_element(By.XPATH, '//*[@id="noon-panel"]/ ul/li[' + str(i) + ']/ span[1]').text)
                except:
                    break
    except:
        pass

    # evening
    try:
        driver.find_element(By.XPATH, '//*[@id="filter-wrapper"]/div[1]/ul/li[3]/a').click()
        if driver.find_element(By.XPATH, '//*[@id="evening-noAvailableQueues"]').text != "אין תורים בשעות האלו":
            try:
                driver.find_element(By.XPATH, '//*[@id="evening-moreVisits"]/a').click()
            except:
                pass
            # Puts all the free time on the list.
            for i in range(1, 20):
                try:
                    times.append(
                        driver.find_element(By.XPATH, '//*[@id="evening-panel"]/ ul/li[' + str(i) + ']/ span[1]').text)
                except:
                    break
    except:
        pass

    return date, location, name_doctor, times
