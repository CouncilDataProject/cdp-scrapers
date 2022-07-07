import selenium
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
# PATH = "/Users/fpw/Desktop/CDP/chromedriver"
# driver = webdriver.Chrome(PATH)

driver.get("https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3587&Format=Minutes")
#print(driver.title)
#print(driver.page_source)

# driver.close()
body_name = driver.find_element(By.ID, "ContentPlaceHolder1_lblMeetingGroup").text
print(body_name)
video_link = driver.find_element(By.ID, "MediaPlayer1_html5_api").get_attribute("src")
print(video_link)

titles = driver.find_elements(By.CSS_SELECTOR,"td[class='Title'][colspan='10']")
for title in titles:
    try:
        if (len(title.text)!= 0):
            minute = title.text
            print(minute)
    except selenium.common.exceptions.NoSuchElementException:
        pass

# for title in titles:
#     try:
#         minute = title.find_element(By.TAG_NAME, 'strong').text
#         print(minute)
#     except selenium.common.exceptions.NoSuchElementException:
#         pass

matters = driver.find_elements(By.CSS_SELECTOR,"td[class='Title'][colspan='9']")
for matter in matters:
    try:
        item = matter.find_element(By.CLASS_NAME, 'AgendaOutlineLink').text
        if (len(item)!= 0):
            matter_name = item[0:9]
            matter_title = item[12:]
            matter_type = " ".join(re.split('BY |FROM',matter_title)[0].split(' ')[1:-1])
            print(matter_type)
            link = driver.find_element("link text", item)
            link.click()
            dates = WebDriverWait(driver,10).until(
                #EC.presence_of_all_elements_located((By.CLASS_NAME,"Date"))
                EC.presence_of_all_elements_located((By.XPATH, "/html/body/form/table/tbody/tr/td[2]/div[2]/div/div/div[4]/div[7]/div/table/tbody"))
                #EC.presence_of_all_elements_located((By.XPATH,"//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr[9]/td[1]/a[contains(text(),'Apr 18, 2022 11:00 AM')]"))
            )
            for date in dates:
                print(date)
                # try:
                #     decision = date.find_element(By.CLASS_NAME, 'Result').text
                #     print(decision)
                # except selenium.common.exceptions.NoSuchElementException:
                #     pass

            # link = driver.find_element("link text", item)
            # link.click()
            # results = WebDriverWait(driver,10).until(
            #     EC.presence_of_all_elements_located((By.CLASS_NAME,"VoteResultRow"))
            # )
            # print(len(results))
            # for result in results:
            #     try:
            #         decision = result.find_element(By.CLASS_NAME, 'Result').text
            #         print(decision)
            #     except selenium.common.exceptions.NoSuchElementException:
            #         pass
    except selenium.common.exceptions.NoSuchElementException:
        pass


# try:
#     element = WebDriverWait(driver,10).until(
#         EC.presence_of_element_located(By.LINK_TEXT, item)
#     )
#     element.click()
# except:
#     pass

agenda_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicAgendaFile").get_attribute("oldhref")
#print("https://atlantacityga.iqm2.com/Citizens/" + agenda_link)
minutes_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicMinutesFile").get_attribute("oldhref")
#print("https://atlantacityga.iqm2.com/Citizens/" + minutes_link)

driver.quit()


# from cdp_backend.pipeline import ingestion_models
# from datetime import datetime

# event = ingestion_models.EventIngestionModel(
#     body=ingestion_models.Body(body_name, is_active=True),
#     sessions=[
#         ingestion_models.Session(
#             video_uri=video_link,
#             session_index=0,
#             session_datetime=datetime.utcnow()
#         )
#     ],
#     event_minutes_items = [
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("CALL TO ORDER")
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("INTRODUCTION OF MEMBERS")
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("ADOPTION OF AGENDA"),
#             decision = "ADOPTED"
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("APPROVAL OF MINUTES"),
#             decision = "ADOPTED"
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("ADOPTION OF FULL COUNCIL AGENDA"),
#             decision = "ADOPTED"
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("PUBLIC COMMENT")
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("COMMUNICATION(S)"),
#             matter = #How to add more matters
#                 ingestion_models.Matter(
#                 "22-C-5024 (1)", 
#                 matter_type = "COMMUNICATION",
#                 title = "A COMMUNICATION FROM TONYA GRIER, COUNTY CLERK TO THE FULTON COUNTY BOARD OF COMMISSIONERS, SUBMITTING THE APPOINTMENT OF MS. NATALIE HORNE TO THE ATLANTA BELTLINE TAX ALLOCATION DISTRICT (TAD) ADVISORY COMMITTEE. THIS APPOINTMENT IS FOR A TERM OF TWO (2) YEARS.",
#                 result_status = "FAVORABLE"
#             ),
#             decision = "FAVORABLE"
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("PAPER(S) HELD IN COMMITTEE"),
#             matter = #How to add more matters
#                 ingestion_models.Matter(
#                 "22-O-1150 (9)", 
#                 matter_type = "PAPER(S) HELD IN COMMITTEE",
#                 title = "A SUBSTITUTE ORDINANCE BY COMMITTEE ON COUNCIL TO AMEND CITY OF ATLANTA CODE OF ORDINANCES SECTION 66-2 \"PRECINCT BOUNDARY LINES AND POLLING PLACES\" BY AMENDING THE 2017 PRECINCTS AND POLLING PLACES ORDINANCE IN FULTON COUNTY PRECINCTS 02L2, 03I, 03C, 06R, 07M, 08A, 08G AND 11R DUE TO FACILITIES UNABLE TO ACCOMMODATE POLLING OPERATIONS; FACILITY UNDERGOING RENOVATIONS AND FACILITY VOTING SITE IS NOT HANDICAP ACCESSIBLE",
#                 result_status = "FAVORABLE"
#                 # sponsors be the committe on council? have role but no seat?
#             ),
#             decision = "FAVORABLE"
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("WALK-IN LEGISLATION")
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("REQUESTED ITEMS")
#         ),
#         ingestion_models.EventMinutesItem(
#             minutes_item = ingestion_models.MinutesItem("ADJOURNMENT")
#         )
#     ],
#     agenda_uri = "https://atlantacityga.iqm2.com/Citizens/" + agenda_link,
#     minutes_uri = "https://atlantacityga.iqm2.com/Citizens/" + minutes_link
# )

# with open("april-18th", "w") as open_f:
#     open_f.write(event.to_json(indent=4))
