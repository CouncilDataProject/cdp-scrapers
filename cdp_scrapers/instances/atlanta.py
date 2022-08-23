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

def get_single_person(driver:webdriver, member_name:str) -> ingestion_models.EventIngestionModel:
    seat_role = driver.find_element(By.CLASS_NAME, 'titlewidget-subtitle').text
    member_role = "Member"
    member_seat_name = "District"
    member_seat_area = "Citywide"
    if ('President' in seat_role):
        member_role = 'President'
        member_seat_name = 'President'
    elif ('Post' in seat_role): #need post number?
        name_list = seat_role.split(' ')
        member_seat_name = 'Post ' + name_list[1]
    else:
        area_list = seat_role.split(' ')
        member_seat_area = area_list[1]
    member_pic = driver.find_element(By.CSS_SELECTOR, '.image_widget img').get_attribute('src')
    temp_email = driver.find_element(By.XPATH, "// a[contains(text(),'Click Here')]").get_attribute('href').split(":")
    member_email = temp_email[1]
    try:
        member_details = driver.find_element(By.XPATH, "//*[contains(@id, 'widget_340_')]").text
    except (selenium.common.exceptions.NoSuchElementException):
        member_details = driver.find_element(By.XPATH, "//*[contains(@id, 'widget_437_')]").text
    detail_str = member_details.split('\n')
    phone_list = [s for s in detail_str if "P" in s]
    member_phone = phone_list[0].split(': ')[1]

    return ingestion_models.Person(
        name = member_name,
        is_active = True,
        email = member_email,
        phone = member_phone,
        picture_uri = member_pic,
        seat = ingestion_models.Seat(
            name = member_seat_name,
            electoral_area = member_seat_area,
            roles = ingestion_models.Role(
                title = member_role
            )
        )
    )

def get_person() -> dict:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get('https://citycouncil.atlantaga.gov/council-members')
    members = driver.find_elements(By.XPATH, '//*[@id="leftNav_2_0_12"]/ul/li')
    person_dict = {}
    for member in members:
        link = member.find_element(By.TAG_NAME, 'a').get_attribute("href")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        driver.get(link)
        member_name = driver.find_element(By.CLASS_NAME, 'titlewidget-title').text
        member_model = get_single_person(driver, member_name)
        driver.quit()
        person_dict[member_name] = member_model
    driver.quit()
    return person_dict


PERSONS = get_person()

def convert_mdecision_constant(decision:str) -> db_constants:
    d_constant = decision
    if ('FAVORABLE' in decision) or ('ADOPTED'in decision) or ('ACCEPTED' in decision) or ('accepted' in decision):
        d_constant = db_constants.MatterStatusDecision.ADOPTED
    elif('REFERRED' in decision) or ('RETURNED' in decision) or ('FILED'in decision) or ('Refer'):
        d_constant = db_constants.MatterStatusDecision.IN_PROGRESS
    return d_constant

def get_voting_result(driver:webdriver, sub_sections:Element, i:int) -> dict:
    voting_list = []
    for j in range(1, len(sub_sections)+1):
        sub_content =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]")
        sub_content_role = sub_content.find_element(By.CLASS_NAME, "Role").text
        if "AYES" in sub_content_role: 
            v_yes = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Yes_list = v_yes.split(", ")
            for n in Yes_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.APPROVE))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.APPROVE))
        if "NAYS" in sub_content_role:
            v_no = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            No_list = v_no.split(", ")
            for n in No_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.REJECT))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.REJECT))
        if "ABSENT" in sub_content_role:
            v_absent = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Absent_list = v_absent.split(", ")
            for n in Absent_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
        if "AWAY" in sub_content_role:
            v_away = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Away_list = v_away.split(", ")
            for n in Away_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
        if "ABSTAIN" in sub_content_role:
            v_abstain = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Abstain_list = v_abstain.split(", ")
            for n in Abstain_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.ABSTAIN_NON_VOTING))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.ABSTAIN_NON_VOTING))
        if "EXCUSED" in sub_content_role:
            v_excused = driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr[" + str(j) + "]/td[2]").text
            Excused_list = v_excused.split(", ")
            for n in Excused_list:
                if n in PERSONS:
                    voting_list.append(ingestion_models.Vote(person = PERSONS.get(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
                else:
                    voting_list.append(ingestion_models.Vote(get_new_person(n), decision = db_constants.VoteDecision.ABSENT_NON_VOTING))
    return voting_list

def get_new_person(name:str) -> ingestion_models.EventIngestionModel:
    return ingestion_models.Person(
    name = name,
    is_active = False
)

def get_matter_decision(driver:webdriver, i:int)-> Tuple[Element,Element]: #unsure about the type for two return items
    result =  driver.find_element(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table")
    decision = result.find_element(By.CLASS_NAME, "Result").text # vote result
    sub_sections = result.find_elements(By.XPATH, "//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i+1) + "]/td/table/tbody/tr")
    decision_constant = convert_mdecision_constant(decision)
    return sub_sections, decision_constant

def parse_single_matter(driver:webdriver, matter:Element) -> ingestion_models.EventIngestionModel:
    try:
        voting_list = []
        test = matter.find_element(By.CLASS_NAME, 'ItemVoteResult').text
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
            sponsor_raw = driver.find_element(By.XPATH, "//*[@id=\"tblLegiFileInfo\"]/tbody/tr[1]/td[2]").text 
            sponsor_list = sponsor_raw.split(', ')
            sponsors = []
            for s in sponsor_list:
                if 'District' in s:
                    current_temp = s.split(' ')[2:]
                    current = ' '.join(current_temp)
                    if current in PERSONS:
                        sponsors.append(PERSONS.get(current))
                    else:
                        sponsors.append(get_new_person(current))
                elif 'Post' in s:
                    current = s.split('Large ')[1]
                    if current in PERSONS:
                        sponsors.append(PERSONS.get(current))
                    else:
                        sponsors.append(get_new_person(current))
                elif 'President' in s:
                    current = s.split('President ')[1]
                    if current in PERSONS:
                        sponsors.append(PERSONS.get(current))
                    else:
                        sponsors.append(get_new_person(current))
            s_rows = (len(s_matter))
            for i in range(1, s_rows+1, 2):
                header =  driver.find_element(By.XPATH,"//*[@id=\"ContentPlaceHolder1_divHistory\"]/div/table/tbody/tr[" + str(i) + "]")
                date = header.find_element(By.CLASS_NAME, "Date").text
                s_word = driver.find_element(By.ID, "ContentPlaceHolder1_lblMeetingDate").text
                if parse(s_word) == parse(date[:-6]): # match the current meeting date
                    sub_sections, decision = get_matter_decision(driver, i) # get the decision of the matter
                    if ("[" in test):
                        voting_list = get_voting_result(driver, sub_sections, i)
            return ingestion_models.EventMinutesItem(
                minutes_item = ingestion_models.MinutesItem(matter_name),
                matter = ingestion_models.Matter(matter_name, 
                    matter_type = matter_type,
                    title = matter_title,
                    result_status = decision,
                    sponsors = sponsors
                ),
                decision = decision,
                votes = voting_list
                )
    except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException):
        pass

def parse_event(url:str) -> ingestion_models.EventIngestionModel:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)

    WebDriverWait(driver,10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr"))
    )

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
            elif (len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[3]/span"))) != 0:
                matter = driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[3]")
                matter_model = parse_single_matter(driver, matter)
                event_minutes_items.append(matter_model)
            elif (len(driver.find_elements(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[6]/span"))) != 0:
                matter = driver.find_element(By.XPATH, "//*[@id=\"MeetingDetail\"]/tbody/tr[" + str(i) + "]/td[6]")
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

def get_date(driver:webdriver, url:str, from_dt: datetime, to_dt: datetime)-> list:
    driver.get(url)
    dates = driver.find_elements(By.CLASS_NAME,"RowTop")
    events = []
    for current_date in dates:
        current_meeting_date = current_date.find_element(By.CLASS_NAME,"RowLink")
        current_meeting_time = datetime.strptime(current_meeting_date.text, "%b %d, %Y %I:%M %p")
        if from_dt <= current_meeting_time <= to_dt:
            link_temp = current_date.find_element(By.CSS_SELECTOR, '.WithoutSeparator a').get_attribute("onclick")
            link = ("https://atlantacityga.iqm2.com" +link_temp[23:-3])
            event = parse_event(link)
            events.append(event)
        else:
            continue
    driver.quit()
    return events

def get_events(from_dt: datetime, to_dt: datetime) -> list:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    web_url = "https://atlantacityga.iqm2.com/Citizens/Calendar.aspx?Frame=Yes"
    driver.get(web_url)
    if from_dt.year != datetime.today().year:  
        web_url = get_year(driver, web_url, from_dt)
    events = get_date(driver, web_url, from_dt, to_dt)
    return events



event = parse_event('https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3588&Format=Minutes')
web_url = "https://atlantacityga.iqm2.com/Citizens/Calendar.aspx?Frame=Yes"
events = get_events(datetime.fromisoformat('2022-04-18'), datetime.fromisoformat('2022-04-26'))
with open("april-18th-auto", "w") as open_f:
    open_f.write(events[2].to_json(indent=4))


# person sometime has middle name sometime dosen't
