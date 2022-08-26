from asyncio import constants
from asyncio.windows_events import NULL
from lib2to3.pgen2.driver import Driver
from tkinter import Frame
from typing import Sized, Tuple
import webbrowser
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

# global variables
MINUTE_INDEX = []
PERSONS: dict[str, ingestion_models.Person] 


def get_single_person(
    driver: ChromeDriverManager, member_name: str
) -> ingestion_models.Person:
    """
    Get all the information fot one person
    Includes: role, seat, picture, phone, email

    Parameter:
    ----------------
    driver: 
        webdriver calling the people's dictionary page 
    member_name: 
        person's name 

    Returns:
    --------------
    ingestion_models
        the ingestion model for the person's part
    """
    seat_role = driver.find_element(By.CLASS_NAME, "titlewidget-subtitle").text
    member_role = "Member"
    member_seat_name = "District"
    member_seat_area = "Citywide"
    if "President" in seat_role:
        member_role = "President"
        member_seat_name = "President"
    elif "Post" in seat_role:  # need post number?
        name_list = seat_role.split(" ")
        member_seat_name = "Post " + name_list[1]
    else:
        area_list = seat_role.split(" ")
        member_seat_area = area_list[1]
    member_pic = driver.find_element(
        By.CSS_SELECTOR, ".image_widget img"
    ).get_attribute("src")
    temp_email = (
        driver.find_element(By.XPATH, "// a[contains(text(),'Click Here')]")
        .get_attribute("href")
        .split(":")
    )
    member_email = temp_email[1]
    try:
        member_details = driver.find_element(
            By.XPATH, "//*[contains(@id, 'widget_340_')]"
        ).text
    except (selenium.common.exceptions.NoSuchElementException):
        member_details = driver.find_element(
            By.XPATH, "//*[contains(@id, 'widget_437_')]"
        ).text
    detail_str = member_details.split("\n")
    phone_list = [s for s in detail_str if "P" in s]
    member_phone = phone_list[0].split(": ")[1]

    return ingestion_models.Person(
        name=member_name,
        is_active=True,
        email=member_email,
        phone=member_phone,
        picture_uri=member_pic,
        seat=ingestion_models.Seat(
            name=member_seat_name,
            electoral_area=member_seat_area,
            roles=[ingestion_models.Role(title=member_role)],
        ),
    )


def get_person() -> dict:
    """
    Put the informtion get by get_single_person() to dictionary 

    Returns:
    --------------
    dictionary
        key: person's name
        value: person's ingestion model
    """
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://citycouncil.atlantaga.gov/council-members")
    members = driver.find_elements(By.XPATH, '//*[@id="leftNav_2_0_12"]/ul/li')
    person_dict = {}
    for member in members:
        link = member.find_element(By.TAG_NAME, "a").get_attribute("href")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        driver.get(link)
        member_name = driver.find_element(By.CLASS_NAME, "titlewidget-title").text
        if "President" in member_name:
            member_name = member_name.split("President ")[1]
        else:
            current_name = re.match(
                r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", member_name
            )
            member_name = f"{current_name.group(1)} {current_name.group(5)}"
        member_model = get_single_person(driver, member_name)
        driver.quit()
        person_dict[member_name] = member_model
    driver.quit()
    return person_dict


def get_new_person(name: str) -> ingestion_models.Person:
    """
    Creates the person ingestion model for the people that are not recored 

    Parameter:
    ----------------
    name:str
        the name of the person 

    Returns:
    --------------
    ingestion model
        the person ingestion model for the newly appeared person 
    """
    return ingestion_models.Person(name=name, is_active=False)


def convert_mdecision_constant(decision: str) -> constants:
    """
    Converts the matter decisions to the exsiting constants 

    Parameter:
    ----------------
    decision: str 
        decision of the matter

    Returns:
    --------------
    db_constants
        matter decision constants 
    """
    d_constant = decision
    if ("FAVORABLE" in decision) or ("ADOPTED" in decision) or ("ACCEPTED" in decision):
        d_constant = db_constants.MatterStatusDecision.ADOPTED
    elif (
        ("REFERRED" in decision)
        or ("RETURNED" in decision)
        or ("FILED" in decision)
        or ("Refer")
        or ("/" in decision)
    ):
        d_constant = db_constants.MatterStatusDecision.IN_PROGRESS
    else:
        raise ValueError("New Type")
    return d_constant


def get_voting_result(driver: ChromeDriverManager, sub_sections: Element, i: int) -> list:
    """
    Scrapes and converts the voting decisions to the exsiting constants 

    Parameter:
    ----------------
    driver:webdriver
        webdriver of the matter page 
    sub_sections: element 
        the block under the matter for the current date
    i: int
        tr[i] is the matter we are looking at

    Returns:
    --------------
    list
        contains the Vote ingestion model for each person
    """
    voting_list = []
    for j in range(1, len(sub_sections) + 1):
        sub_content = driver.find_element(
            By.XPATH,
            '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
            + str(i + 1)
            + "]/td/table/tbody/tr["
            + str(j)
            + "]",
        )
        sub_content_role = sub_content.find_element(By.CLASS_NAME, "Role").text
        if "AYES" in sub_content_role:
            v_yes = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            Yes_list = v_yes.split(", ")
            for p in Yes_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.APPROVE,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n),
                            decision=db_constants.VoteDecision.APPROVE,
                        )
                    )
        if "NAYS" in sub_content_role:
            v_no = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            No_list = v_no.split(", ")
            for p in No_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.REJECT,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n), 
                            decision=db_constants.VoteDecision.REJECT
                        )
                    )
        if "ABSENT" in sub_content_role:
            v_absent = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            Absent_list = v_absent.split(", ")
            for p in Absent_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
        if "AWAY" in sub_content_role:
            v_away = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            Away_list = v_away.split(", ")
            for p in Away_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
        if "ABSTAIN" in sub_content_role:
            v_abstain = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            Abstain_list = v_abstain.split(", ")
            for p in Abstain_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.ABSTAIN_NON_VOTING,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n),
                            decision=db_constants.VoteDecision.ABSTAIN_NON_VOTING,
                        )
                    )
        if "EXCUSED" in sub_content_role:
            v_excused = driver.find_element(
                By.XPATH,
                '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                + str(i + 1)
                + "]/td/table/tbody/tr["
                + str(j)
                + "]/td[2]",
            ).text
            Excused_list = v_excused.split(", ")
            for p in Excused_list:
                if "President" in p:
                    n = p.split("President ")[1]
                else:
                    n_temp = re.match(
                        r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)", p
                    )
                    n = f"{n_temp.group(1)} {n_temp.group(5)}"
                if n in PERSONS:
                    voting_list.append(
                        ingestion_models.Vote(
                            person=PERSONS.get(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
                else:
                    voting_list.append(
                        ingestion_models.Vote(
                            person = get_new_person(n),
                            decision=db_constants.VoteDecision.ABSENT_NON_VOTING,
                        )
                    )
    return voting_list


def get_matter_decision(driver: ChromeDriverManager, i: int) -> Tuple[Element, str]:
    """
    Find the matter decisions

    Parameter:
    ----------------
    driver:webdriver
        webdriver of the matter page 
    i: int
        tracker used to loop the rows in the matter page

    Returns:
    --------------
    sub_sections: element 
        the block under the matter for the current date
    decision_constant: element
        the matter decision constant
    """
    result = driver.find_element(
        By.XPATH,
        '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
        + str(i + 1)
        + "]/td/table",
    )
    decision = result.find_element(By.CLASS_NAME, "Result").text
    sub_sections = result.find_elements(
        By.XPATH,
        '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
        + str(i + 1)
        + "]/td/table/tbody/tr",
    )
    decision_constant = convert_mdecision_constant(decision)
    return sub_sections, decision_constant


def parse_single_matter(
    driver: ChromeDriverManager, matter: ChromeDriverManager
) -> ingestion_models.EventMinutesItem:
    """
    Get the minute items that contains a matter

    Parameter:
    ----------------
    driver:webdriver
        webdriver of the matter page 
    matter:element
        the matter we are looking at

    Returns:
    --------------
    ingestion model
        minutes ingestion model with the matters information
    """
    try:
        voting_list = []
        test = matter.find_element(By.CLASS_NAME, "ItemVoteResult").text
        item = matter.find_element(By.CLASS_NAME, "AgendaOutlineLink").text
        if len(item) != 0:
            matter_name = item[0:9]  # name of the matter eg. "22-C-5024", "22-R-3404"
            matter_title = item[
                12:
            ]  # the paragraph the describes the matter eg. "A COMMUNICATION FROM ..."
            matter_type = " ".join(
                re.split("BY |FROM", matter_title)[0].split(" ")[1:-1]
            )  # the type of the matter eg. "COMMUNICATION", "SUBSTITUTE ORDINANCE"
            link = driver.find_element("link text", item)
            link.click()
            # get to the specific page for each matter
            s_matter = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr',
                    )
                )
            )
            sponsor_raw = driver.find_element(
                By.XPATH, '//*[@id="tblLegiFileInfo"]/tbody/tr[1]/td[2]'
            ).text
            sponsor_list = sponsor_raw.split(", ")
            if len(sponsor_list) != 0:
                sponsors = []
                for s in sponsor_list:
                    if "District" in s:
                        current_temp = s.split(" ")[2:]
                        current_temp2 = " ".join(current_temp)
                        current_name = re.match(
                            r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)",
                            current_temp2,
                        )
                        current = f"{current_name.group(1)} {current_name.group(5)}"
                        if current in PERSONS:
                            sponsors.append(PERSONS.get(current))
                        else:
                            sponsors.append(get_new_person(current))
                    elif "Post" in s:
                        current_temp = s.split("Large ")[1]
                        current_name = re.match(
                            r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)",
                            current_temp,
                        )
                        current = f"{current_name.group(1)} {current_name.group(5)}"
                        if current in PERSONS:
                            sponsors.append(PERSONS.get(current))
                        else:
                            sponsors.append(get_new_person(current))
                    elif "President" in s:
                        current_temp = s.split("President ")[1]
                        current_name = re.match(
                            r"([a-zA-Z]+)((\ {0,1}[a-zA-Z]+\.{0,1}\ )|(\ ))([a-zA-Z]+)",
                            current_temp,
                        )
                        current = f"{current_name.group(1)} {current_name.group(5)}"
                        if current in PERSONS:
                            sponsors.append(PERSONS.get(current))
                        else:
                            sponsors.append(get_new_person(current))
                s_rows = len(s_matter)
                for i in range(1, s_rows + 1, 2):
                    header = driver.find_element(
                        By.XPATH,
                        '//*[@id="ContentPlaceHolder1_divHistory"]/div/table/tbody/tr['
                        + str(i)
                        + "]",
                    )
                    date = header.find_element(By.CLASS_NAME, "Date").text
                    s_word = driver.find_element(
                        By.ID, "ContentPlaceHolder1_lblMeetingDate"
                    ).text
                    if parse(s_word) == parse(date[:-6]):  # match the current meeting date
                        sub_sections, decision = get_matter_decision(
                            driver, i
                        )  # get the decision of the matter
                        if "[" in test:
                            voting_list = get_voting_result(driver, sub_sections, i)
                return ingestion_models.EventMinutesItem(
                    minutes_item=ingestion_models.MinutesItem(matter_name),
                    matter=ingestion_models.Matter(
                        matter_name,
                        matter_type=matter_type,
                        title=matter_title,
                        result_status=decision,
                        sponsors=sponsors,
                    ),
                    decision=decision,
                    votes=voting_list,
                )
        else:
            return ingestion_models.EventMinutesItem(
                minutes_item=ingestion_models.MinutesItem(matter_name),
                matter=ingestion_models.Matter(
                    matter_name,
                    matter_type=matter_type,
                    title=matter_title,
                    result_status=decision
                ),
                decision=decision,
                votes=voting_list,
            )
    except (
        selenium.common.exceptions.NoSuchElementException,
        selenium.common.exceptions.TimeoutException,
    ):
        pass


def parse_event(url: str) -> ingestion_models.EventIngestionModel:
    """
    Scrapes all the information for a meeting

    Parameter:
    ----------------
    url:str
        the url of the meeting that we want to scrape

    Returns:
    --------------
    ingestion model
        the ingestion model for the meeting
    """
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, '//*[@id="MeetingDetail"]/tbody/tr')
        )
    )

    body_name = driver.find_element(
        By.ID, "ContentPlaceHolder1_lblMeetingGroup"
    ).text  # body name
    video_link = driver.find_element(By.ID, "MediaPlayer1_html5_api").get_attribute(
        "src"
    )  # video link (mp4)

    event_minutes_items = []
    i = 1

    while (
        len(
            driver.find_elements(
                By.XPATH, '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]"
            )
        )
        != 0
    ):
        try:
            if (
                (
                    len(
                        driver.find_elements(
                            By.XPATH,
                            '//*[@id="MeetingDetail"]/tbody/tr['
                            + str(i)
                            + "]/td[1]/strong",
                        )
                    )
                )
                != 0
                and (
                    len(
                        driver.find_element(
                            By.XPATH,
                            '//*[@id="MeetingDetail"]/tbody/tr['
                            + str(i)
                            + "]/td[1]/strong",
                        ).text
                    )
                )
                != 0
            ):
                if (
                    driver.find_element(
                        By.XPATH,
                        '//*[@id="MeetingDetail"]/tbody/tr['
                        + str(i)
                        + "]/td[1]/strong",
                    ).text
                )[0] in MINUTE_INDEX:
                    if (
                        len(
                            driver.find_elements(
                                By.XPATH,
                                '//*[@id="MeetingDetail"]/tbody/tr['
                                + str(i + 1)
                                + "]/td[3]/span",
                            )
                        )
                        == 0
                    ):
                        minute_title = driver.find_element(
                            By.XPATH,
                            '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]/td[2]",
                        ).text
                        minute_model = ingestion_models.EventMinutesItem(
                            minutes_item=ingestion_models.MinutesItem(minute_title)
                        )
                        event_minutes_items.append(minute_model)
            elif (
                len(
                    driver.find_elements(
                        By.XPATH,
                        '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]/td[3]/span",
                    )
                )
            ) != 0:
                matter = driver.find_element(
                    By.XPATH, '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]/td[3]"
                )
                matter_model = parse_single_matter(driver, matter)
                event_minutes_items.append(matter_model)
            elif (
                len(
                    driver.find_elements(
                        By.XPATH,
                        '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]/td[6]/span",
                    )
                )
            ) != 0:
                matter = driver.find_element(
                    By.XPATH, '//*[@id="MeetingDetail"]/tbody/tr[' + str(i) + "]/td[6]"
                )
                matter_model = parse_single_matter(driver, matter)
                event_minutes_items.append(matter_model)
            i += 1
        except (
            selenium.common.exceptions.NoSuchElementException,
            selenium.common.exceptions.TimeoutException,
        ):  # except(A,B)
            i += 1
            continue

    agenda_link = driver.find_element(
        By.ID, "ContentPlaceHolder1_hlPublicAgendaFile"
    ).get_attribute("oldhref")
    minutes_link = driver.find_element(
        By.ID, "ContentPlaceHolder1_hlPublicMinutesFile"
    ).get_attribute("oldhref")

    driver.quit()

    return ingestion_models.EventIngestionModel(
        body=ingestion_models.Body(body_name, is_active=True),
        sessions=[
            ingestion_models.Session(
                video_uri=video_link,
                session_index=0,
                session_datetime=datetime.utcnow(),
            )
        ],
        event_minutes_items=event_minutes_items,
        agenda_uri="https://atlantacityga.iqm2.com/Citizens/" + agenda_link,
        minutes_uri="https://atlantacityga.iqm2.com/Citizens/" + minutes_link,
    )


def get_year(driver: ChromeDriverManager, url: str, from_dt: datetime) -> str:
    """
    Navigate to the year that we are looking for

    Parameter:
    ----------------
    driver:webdriver 
        empty webdriver
    url:str
        the url of the calender page

    Returns:
    --------------
    link:str
        the link to the calender of the year that we are looking for 
    """
    driver.get(url)
    dates = driver.find_element(By.ID, "ContentPlaceHolder1_lblCalendarRange")
    link_temp = dates.find_element(
        By.XPATH, ("//*[text()='" + str(from_dt.year) + "']")
    ).get_attribute("href")
    link = "https://atlantacityga.iqm2.com" + link_temp
    return link


def get_date(driver: ChromeDriverManager, url: str, from_dt: datetime, to_dt: datetime) -> list:
    """
    Get a list of ingestion models for the meetings hold during the selected time range

    Parameter:
    ----------------
    driver:webdriver 
        empty webdriver
    url:str
        the url of the calender page
    from_dt:
        the begin date 
    to_date:
        the end date 

    Returns:
    --------------
    list
        all the ingestion models for the selected date range
    """
    driver.get(url)
    dates = driver.find_elements(By.CLASS_NAME, "RowTop")
    events = []
    for current_date in dates:
        current_meeting_date = current_date.find_element(By.CLASS_NAME, "RowLink")
        current_meeting_time = datetime.strptime(
            current_meeting_date.text, "%b %d, %Y %I:%M %p"
        )
        if from_dt <= current_meeting_time <= to_dt:
            link_temp = current_date.find_element(
                By.CSS_SELECTOR, ".WithoutSeparator a"
            ).get_attribute("onclick")
            link = "https://atlantacityga.iqm2.com" + link_temp[23:-3]
            event = parse_event(link)
            events.append(event)
        else:
            continue
    driver.quit()
    return events


def get_events(from_dt: datetime, to_dt: datetime) -> list:
    """
    gets the right calender link
    feed it to the function that get a list of ingestion models 

    Parameter:
    ----------------
    from_dt:
        the begin date 
    to_date:
        the end date 

    Returns:
    --------------
    list
        all the ingestion models for the selected date range
    """
    global MINUTE_INDEX
    MINUTE_INDEX = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
    global PERSONS
    PERSONS = get_person()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    web_url = "https://atlantacityga.iqm2.com/Citizens/Calendar.aspx?Frame=Yes"
    driver.get(web_url)
    if from_dt.year != datetime.today().year:
        web_url = get_year(driver, web_url, from_dt)
    events = get_date(driver, web_url, from_dt, to_dt)
    return events
