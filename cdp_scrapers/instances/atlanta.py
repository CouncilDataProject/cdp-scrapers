import selenium
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
# Q & To do
# put indivual items in to string
# Style requirements
# Put the matters in the minutes along with the Titles
# Decision Constant
# Person In the same script
# get different meetings in the wannted time period
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3587&Format=Minutes")

# functions

def get_voting_result(driver, i, j):
    sub_content =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]")
    sub_content_role = sub_content.find_element(By.CLASS_NAME, "Role").text
    if "AYES" in sub_content_role:
        # people voted yes
        v_yes = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
        #print("yes:" + v_yes)
    if "NAYS" in sub_content_role:
        # people voted no
        v_no = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
        #print("no:" + v_no)

def get_matter_decision(driver, i):
    result =  driver.find_element(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table")
    decision = result.find_element(By.CLASS_NAME, "Result").text # vote result
    sub_sections = result.find_elements(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr")
    #print(decision)
    return sub_sections

def parse_single_matter(driver, matter):
    try:
        test = matter.find_element(By.CLASS_NAME, 'ItemVoteResult').text
        if "Held in Committee" not in test: # remove the matters that are not mentioned in the meeting
            item = matter.find_element(By.CLASS_NAME, 'AgendaOutlineLink').text
            #print(item)
            if (len(item)!=0):
                matter_name = item[0:9] # name of the matter eg. "22-C-5024", "22-R-3404"
                matter_title = item[12:] # the paragraph the describes the matter eg. "A COMMUNICATION FROM TONYA GRIER, COUNTY CLERK TO THE FULTON COUNTY BOARD OF COMMISSIONERS..."
                matter_type = " ".join(re.split('BY |FROM',matter_title)[0].split(' ')[1:-1]) # the type of the matter eg. "COMMUNICATION", "SUBSTITUTE ORDINANCE"
                link = driver.find_element("link text", item)
                link.click()
                # get to the specific page for each matter 
                s_matter = WebDriverWait(driver,10).until(
                    EC.presence_of_all_elements_located((By.XPATH,
                    "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr"))
                )
                sponsor = driver.find_element(By.XPATH, "//*[@id=\"tblLegiFileInfo\"]/tbody/tr[1]/td[2]").text #sponsor for the matter not done yet
                #print(driver.find_element(By.XPATH, "//*[@id=\"ContentPlaceHolder1_lblResNum\"]").text)
                s_rows = (len(s_matter))
                for i in range(1, s_rows+1, 2):
                    header =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i) + "]")
                    date = header.find_element(By.CLASS_NAME, "Date").text
                    s_word = "Apr 18, 2022 11:00 AM"
                    if s_word in date: # match the current meeting date
                        sub_sections = get_matter_decision(driver, i) # get the decision of the matter
                        for j in range(1, len(sub_sections)+1):
                            get_voting_result(driver, i, j)

    except selenium.common.exceptions.NoSuchElementException:
        pass


body_name = driver.find_element(By.ID, "ContentPlaceHolder1_lblMeetingGroup").text #body name 
video_link = driver.find_element(By.ID, "MediaPlayer1_html5_api").get_attribute("src") # video link (mp4)

titles = driver.find_elements(By.CSS_SELECTOR,"td[class='Title'][colspan='10']")
minute = "" # minutes name
for title in titles:
    try:
        if (len(title.text)!= 0):
            minute = title.text
    except selenium.common.exceptions.NoSuchElementException:
        pass

matters = driver.find_elements(By.CSS_SELECTOR,"td[class='Title'][colspan='9']")
for matter in matters:
    parse_single_matter(driver, matter)

agenda_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicAgendaFile").get_attribute("oldhref")
minutes_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicMinutesFile").get_attribute("oldhref")

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
