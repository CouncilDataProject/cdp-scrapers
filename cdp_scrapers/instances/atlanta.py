from ast import For
from http.client import CONTINUE
from typing import Tuple
from xml.dom.minidom import Element
import selenium
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from cdp_backend.pipeline import ingestion_models
from cdp_backend.database import constants as db_constants
from datetime import datetime
from dateutil.parser import parse

MINUTE_INDEX = [chr(i) for i in range(ord('A'),ord('Z')+1)]

def convert_decision_constant(decision:str) -> db_constants:
    d_constant = ''
    if 'FAVORABLE' in decision:
        d_constant = db_constants.VoteDecision.APPROVE
    return d_constant

def get_voting_result(driver:webdriver, sub_sections:Element, i:int) -> dict:
    for j in range(1, len(sub_sections)+1):
        Yes_list = []
        No_list = []
        sub_content =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]")
        sub_content_role = sub_content.find_element(By.CLASS_NAME, "Role").text
        if "AYES" in sub_content_role: 
            # people voted yes
            v_yes = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Yes_list = v_yes.split(",")
            #print("yes:" + v_yes)
        if "NAYS" in sub_content_role:
            # people voted no
            v_no = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            No_list = v_no.split(",")
            #print("no:" + v_no)
        # ABSENT 
    voting_result_dict = {"AYES" : Yes_list, "NAYS": No_list}
    return voting_result_dict

def get_matter_decision(driver:webdriver, i:int)-> Tuple[Element,Element]: #unsure about the type for two return items
    result =  driver.find_element(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table")
    decision = result.find_element(By.CLASS_NAME, "Result").text # vote result
    sub_sections = result.find_elements(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr")
    decision_constant = convert_decision_constant(decision)
    return sub_sections, decision_constant

def parse_single_matter(driver:webdriver, matter:Element) -> ingestion_models.EventIngestionModel:
    try:
        test = matter.find_element(By.CLASS_NAME, 'ItemVoteResult').text
        if "Held in Committee" not in test: # remove the matters that are not mentioned in the meeting
            item = matter.find_element(By.CLASS_NAME, 'AgendaOutlineLink').text
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
                s_rows = (len(s_matter))
                for i in range(1, s_rows+1, 2):
                    header =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i) + "]")
                    date = header.find_element(By.CLASS_NAME, "Date").text
                    s_word = driver.find_element(By.ID, "ContentPlaceHolder1_lblMeetingDate").text
                    if parse(s_word) == parse(date[:-6]): # match the current meeting date
                        sub_sections, decision = get_matter_decision(driver, i) # get the decision of the matter
                        voting_result_dict = get_voting_result(driver, sub_sections, i)
                            #voting_result_dict = get_voting_result(driver, i, j)
                            #print(voting_result_dict)
                return ingestion_models.EventMinutesItem(
                    minutes_item = ingestion_models.MinutesItem(matter_name),
                    matter = ingestion_models.Matter(matter_name, 
                        matter_type = matter_type,
                        title = matter_title,
                        result_status = decision
                    ),
                    decision = decision
                    )
    except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException):
        pass

def parse_event(url: str) -> ingestion_models.EventIngestionModel:

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)

    body_name = driver.find_element(By.ID, "ContentPlaceHolder1_lblMeetingGroup").text #body name 
    video_link = driver.find_element(By.ID, "MediaPlayer1_html5_api").get_attribute("src") # video link (mp4)

    event_minutes_items = []
    i = 1

    while len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr["+str(i)+"]")) != 0 :
        try:
            if (len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr["+str(i)+"]/td[1]/strong"))) != 0 and (len(driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr["+str(i)+"]/td[1]/strong").text)) != 0:
                if (driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr["+str(i)+"]/td[1]/strong").text)[0] in MINUTE_INDEX:
                    if len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i+1) + "]/td[3]/span")) == 0:
                        minute_title = driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr["+str(i)+"]/td[2]").text
                        minute_model = ingestion_models.EventMinutesItem(
                        minutes_item = ingestion_models.MinutesItem(minute_title)
                        )
                        event_minutes_items.append(minute_model)
            elif (len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[3]/span"))) != 0 :
                matter = driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[3]")
                matter_model = parse_single_matter(driver, matter)
                event_minutes_items.append(matter_model)
            i +=1
        except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException) : #except(A,B)
            i+=1
            continue

    agenda_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicAgendaFile").get_attribute("oldhref")
    minutes_link = driver.find_element(By.ID, "ContentPlaceHolder1_hlPublicMinutesFile").get_attribute("oldhref")

    driver.quit()

    return ingestion_models.EventIngestionModel(
        body = ingestion_models.Body(body_name, is_active=True),
        sessions=[
            ingestion_models.Session(
                video_uri=video_link,
                session_index=0,
                session_datetime=datetime.utcnow()
            )
        ],
        event_minutes_items=event_minutes_items,
        agenda_uri = "https://atlantacityga.iqm2.com/Citizens/" + agenda_link,
        minutes_uri = "https://atlantacityga.iqm2.com/Citizens/" + minutes_link
    )

def get_year(driver:webdriver, url: str, from_dt: datetime):
    driver.get(url)
    dates = driver.find_element(By.ID,"ContentPlaceHolder1_lblCalendarRange")
    link_temp = dates.find_element(By.XPATH, ("//*[text()=\'" + str(from_dt.year) + "\']")).get_attribute("href")
    link = ("https://atlantacityga.iqm2.com" +link_temp)
    return link

def get_date(driver:webdriver, url:str, from_dt: datetime, to_dt: datetime):
    driver.get(url)
    dates = driver.find_elements(By.CLASS_NAME,"RowTop")
    for current_date in dates:
        current_meeting_date = current_date.find_element(By.CLASS_NAME,"RowLink")
        current_meeting_time = datetime.strptime(current_meeting_date.text, "%b %d, %Y %I:%M %p")
        if from_dt <= current_meeting_time <= to_dt:
            link_temp = current_date.find_element(By.CSS_SELECTOR, '.WithoutSeparator a').get_attribute("onclick")
            link = ("\"https://atlantacityga.iqm2.com" +link_temp[23:-2])
            parse_event(link)
        else:
            continue


def get_events(from_dt: datetime, to_dt: datetime):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    web_url = "https://atlantacityga.iqm2.com/Citizens/Calendar.aspx?Frame=Yes"
    driver.get(web_url)
    if from_dt.year != datetime.date.today().year:  
        web_url = get_year(driver, web_url, from_dt)
    get_date(driver, web_url, from_dt, to_dt)

event = parse_event('https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3588&Format=Minutes')
# # event = parse_event('https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3587&Format=Minutes')
with open("april-26th-auto", "w") as open_f:
    open_f.write(event.to_json(indent=4))

