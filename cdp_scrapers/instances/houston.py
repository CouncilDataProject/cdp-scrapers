from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from cdp_backend.pipeline import ingestion_models
from datetime import datetime, timedelta
from typing import List, Union

# import bs4
# from typing import Tuple, Optional


# def get_role(name: str) -> Tuple[List[str], bool]:
#     """
#     Get the role name for one person
#     title: eg.PUBLIC SAFETY & HOMELAND SECURITY (PSHS)
#     role_name: chair, vice chair, member, etc

#     Parameters:
#     ----------------
#     name: str
#         The name of one person who participates in voting

#     Returns:
#     ----------------
#     (str, boolean)
#         str: role name
#         boolean: whether the person is in the current council
#     """
#     name = name.split(" ")[-1].strip()
#     role_url = "http://www.houstontx.gov/council/committees/"
#     role_page = BeautifulSoup(requests.get(role_url).content, "html.parser")
#     roles = ["City Council: Member"]
#     status = False
#     role_list = role_page.find("div", class_="8u 12u(mobile)")
#     role_titles = role_list.find_all("p")
#     for role_title in role_titles:
#         titles = role_title.find_all("strong")
#         for title in titles:
#             if title is not None and title.text != "":
#                 role_members = title.find_next("ul").find_all("li")
#                 for role_member in role_members:
#                     if "Agenda" not in role_member.text:
#                         role_and_member = role_member.text.split(":")
#                         role_name = role_and_member[0].strip()
#                         if len(role_and_member) > 2:
#                             member_names = role_and_member[2].split(",")
#                         else:
#                             member_names = role_and_member[1].split(",")
#                         for member_name in member_names:
#                             if name in member_name.strip():
#                                 roles.append(title.text + ": " + role_name)
#                                 status = True

#     return (roles, status)


# def get_seat(name: str, event: Tag) -> str:
#     """
#     Get the seat for one person
#     Not calling this currently as there's no voting info

#     Parameters:
#     ----------------
#     name: str
#         The name of the person who votes
#     event: Tag
#         All elements in the page that we want to scrape

#     Returns:
#     ----------------
#     str:
#         The seat information for one person
#     """
#     peopleTable = event.find_all("table")[1].find_all("table")[1].table.table
#     membersTable = peopleTable.find_all("tr")[1]
#     districtTable = membersTable.find("table").find("tr").find_all("td")
#     seat = ""
#     # left and right district
#     for td in districtTable:
#         text = td.find("span").find_all("br")
#         for br in text:
#             content = br.previousSibling
#             if type(content) is bs4.element.NavigableString:
#                 if content.text.strip() == name:
#                     seat = content.nextSibling.nextSibling.strip()
#     # lower district
#     underDistrict = membersTable.find("p").find("span").find("br")
#     underDName = underDistrict.previousSibling
#     if underDName.text.strip() == name:
#         seat = underDName.nextSibling.nextSibling.strip()
#     # left and right position
#     positionTable = membersTable.find_all("table")[1].find("tr").find_all("td")
#     for td in positionTable:
#         textP = td.find("span").find_all("br")
#         for br in textP:
#             contentP = br.previousSibling
#             if type(contentP) is bs4.element.NavigableString:
#                 if contentP.text.strip() == name:
#                     seat = contentP.nextSibling.nextSibling.strip()
#     # lower position
#     underPosition = membersTable.find_all("span")[-1].find("br")
#     underPName = underPosition.previousSibling
#     if underPName.text.strip() == name:
#         seat = underPName.nextSibling.nextSibling.strip()
#     return seat


# def get_person(name: str, event: Tag) -> ingestion_models.Person:
#     """
#     Get the seat and role for one person

#     Parameters:
#     -----------------
#     name:str
#         The name of one person

#     Returns:
#     -----------------
#     ingestion_models.Person:
#         Seat and role information for one person
#     """
#     return ingestion_models.Person(
#         name=name,
#         is_active=get_role(name)[1],
#         seat=ingestion_models.Seat(
#             name = get_seat(name, event),
#             roles = ingestion_models.Role(title=get_role(name)[0])
#         ),
#     )


# missing: get_votes()


def get_body_name(event: Union[Tag, NavigableString, None]) -> str:
    """
    Get the body name for an event

    Parameter:
    ----------------
    event: Tag
        All elements in the page that we want to scrape

    Returns:
    ----------------
    str
        The body name
    """
    if event is None:
        raise ValueError("Incorrect variable type none")
    if event is NavigableString:
        raise ValueError("Incorrect variable type string")
    bodyTable = event.find_all("table")[1].find("table")
    if "CITY COUNCIL" in bodyTable.text:
        return "City Council"
    else:
        return bodyTable.find_all("span")[3].text


def get_matter_name(link: str) -> str:
    """
    Get the matter numbers for one matter

    Parameters:
    ---------------
    link:str
        The link to each matter item

    Returns:
    ---------------
    str:
        The matter numbers for one matter
    """
    matter_page = requests.get(link)
    matter = BeautifulSoup(matter_page.content, "html.parser")
    if matter is None:
        raise ValueError("Incorrect variable type none")
    if matter is NavigableString:
        raise ValueError("Incorrect variable type string")
    if matter is int:
        raise ValueError("Incorrect variable type int")
    matter_name = (
        matter.find("table")
        .find("table")
        .find("table")
        .find_all("td")[1]
        .find("div")
        .find("div")
        .find("br")
        .previousSibling
    )
    return matter_name


def get_matter_title(link: str) -> str:
    """
    Get title for one matter, which is the summary for one matter

    Parameters:
    --------------
    link:str
        The link to each matter item

    Returns:
    --------------
    str: Title for one matter, which is the summary for one matter
    """
    matter_page = requests.get(link)
    matter = BeautifulSoup(matter_page.content, "html.parser")
    if matter is None:
        raise ValueError("Incorrect variable type none")
    if matter is NavigableString:
        raise ValueError("Incorrect variable type string")
    matter_title = (
        matter.find("table").find_all("table")[2].text.replace("Summary:", "").strip()
    )
    return matter_title


def get_eventMinutesItem(
    event: Union[Tag, NavigableString, None],
) -> List[ingestion_models.EventMinutesItem]:
    """
    Loop through the whole agenda and get both the minutes item and matter.

    The first block of code:
    * get minutes item on the first day of the meeting
    The second block of code:
    * get minutes item before the matter items in the second day of meeting.
    The third block of code:
    * get all matter items
    The fourth block of code:
    * get minutes items after the matter items

    Parameter:
    --------------
    event: Tag
        The web page of agenda that we are parsing

    Returns:
    --------------
    list[ingestion_models.EventMinutesItem]
        A list of EventMinutesItem
    """
    event_minutes_items = []
    # get minutes on the first day
    if event is None:
        raise ValueError("Incorrect variable type none")
    if event is NavigableString:
        raise ValueError("Incorrect variable type string")
    firstday_minutes = event.find_all("td", id="column1", class_="style1")
    for firstday_minute in firstday_minutes:
        event_minutes_items.append(
            ingestion_models.EventMinutesItem(
                minutes_item=ingestion_models.MinutesItem(firstday_minute.text.strip())
            )
        )

    # get minutes before matter
    all_tables = event.find_all("table")[1].find_all("table")
    for all_table in all_tables:
        if (
            "DESCRIPTIONS OR CAPTIONS OF AGENDA ITEMS WILL BE READ BY THE"
            in all_table.text
        ):
            all_prematter_tables = all_table.find_all_next("table")
            for all_prematter_table in all_prematter_tables:
                if "CONSENT AGENDA NUMBERS" in all_prematter_table.text:
                    break
                else:
                    minutes_names = all_prematter_table.find_all("td", id="column2")
                    for minutes_name in minutes_names:
                        if (
                            minutes_name is not None
                            and minutes_name.text != ""
                            and "." not in minutes_name.text
                        ):
                            event_minutes_items.append(
                                ingestion_models.EventMinutesItem(
                                    minutes_item=ingestion_models.MinutesItem(
                                        minutes_name.text.strip()
                                    )
                                )
                            )

    # get matter
    allTable = event.find_all("table")[1].find_all("table")
    for table in allTable:
        for td in table.find_all("td", id="column2"):
            if "CONSENT AGENDA NUMBERS" in td.text:
                all_Link = table.find_all_next("table")
                for table_link in all_Link:
                    if table_link.text == "END OF CONSENT AGENDA":
                        break
                    else:
                        all_links = table_link.find_all("a", href=True)
                        for links in all_links:  # links: one matter
                            if links is not None and links.text != "VIDEO":
                                link = (
                                    "https://houston.novusagenda.com/agendapublic//"
                                    + links["href"]
                                )
                                if "**PULLED" not in get_matter_title(link):
                                    matter_types = links.find_all_previous(
                                        "td", id="column2", class_="style1"
                                    )
                                    one_matter_type = ""
                                    for matter_type in matter_types:
                                        if "-" in matter_type.text:
                                            one_matter_type = matter_type.text.split(
                                                "-"
                                            )[0].strip()
                                            break
                                    event_minutes_items.append(
                                        ingestion_models.EventMinutesItem(
                                            minutes_item=ingestion_models.MinutesItem(
                                                get_matter_name(link)
                                            ),
                                            matter=ingestion_models.Matter(
                                                name=get_matter_name(link),
                                                matter_type=one_matter_type,
                                                title=get_matter_title(link),
                                            ),
                                        )
                                    )
                else:
                    continue
                break
        else:
            continue
        break

    # get minutes after matter
    allTable = event.find_all("table")[1].find_all("table")
    for table in allTable:
        for td in table.find_all("td", id="column2"):
            if "END OF CONSENT AGENDA" in td.text:
                all_afterm_minutes = table_link.find_all_next("a", href=True)
                for minutes in all_afterm_minutes:
                    if minutes is not None and minutes.text != "VIDEO":
                        minutes_link = (
                            "https://houston.novusagenda.com/agendapublic//"
                            + minutes["href"]
                        )
                        minute_types = minutes.find_all_previous(
                            "td", id="column2", class_="style1"
                        )
                        one_minute_type = ""
                        for minute_type in minute_types:
                            if minute_type is not None and minute_type.text != "":
                                one_minute_type = minute_type.text.split("-")[0].strip()
                                break
                        if "MATTERS HELD" not in one_minute_type:
                            event_minutes_items.append(
                                ingestion_models.EventMinutesItem(
                                    minutes_item=ingestion_models.MinutesItem(
                                        get_matter_name(minutes_link)
                                    )
                                )
                            )
    return event_minutes_items


# Big Functions
main_URL = "https://houstontx.new.swagit.com/views/408"
main_page = requests.get(main_URL)
main = BeautifulSoup(main_page.content, "html.parser")


def get_diff_yearid(time: datetime) -> str:
    """
    Get the events in different years as the events for different
    years are stored in different tabs. Can get multiple events
    across years.

    Parameters:
    ---------------
    time: datetime
        The date of the event we are trying to parse

    Returns:
    ---------------
    str
        The year id that can locate the year tab where the event is stored
    """
    year = str(time.year)
    year_id = "city-council-" + year
    return year_id


def get_date_mainlink(time: datetime) -> str:
    """
    Find the main link for one event. Only find link in a specific year
    * 1)loop through all date
    * 2)change each into datetime format
    * 3)if match, get the 3rd td
    * 4)get the href in first a

    Parameters:
    --------------
    time: datetime
        The date of one event

    Returns:
    --------------
    str
        The main link, make agenda and video url in other function
    """
    # all events in a specific year
    main_year = (
        main.find("div", id=get_diff_yearid(time))
        .find("table", id="video-table")
        .find("tbody")
        .find_all("tr")
    )
    link = ""
    for year in main_year:
        cells = year.find_all("td")
        date = cells[1].text.replace(",", "").strip()
        date = datetime.strptime(date, "%b %d %Y").date()
        if date == time:
            link_post = cells[3].find("a")["href"]
            link = "https://houstontx.new.swagit.com/" + link_post
    return link


def check_in_range(time: datetime) -> bool:
    """
    Check if the date is in the time range we want

    Parameters:
    --------------
    time: datetime
        The date of one event

    Returns:
    --------------
    bool
        True if the event is in the time range we want; false otherwise
    """
    main_year = (
        main.find("div", id=get_diff_yearid(time))
        .find("table", id="video-table")
        .find("tbody")
        .find_all("tr")
    )
    in_range = False
    for year in main_year:
        cells = year.find_all("td")
        date = cells[1].text.replace(",", "").strip()
        date = datetime.strptime(date, "%b %d %Y").date()
        if date == time:
            in_range = True
    return in_range


def get_agenda(event_time: datetime) -> Union[Tag, NavigableString, None]:
    """
    Get event agenda for a specific date

    Parameters:
    ----------------
    event_time: datetime
        The date we want to get agenda

    Returns:
    ----------------
    Tag
        The agenda web page we want parse
    """
    link = get_date_mainlink(event_time)
    agenda_link = link + "/agenda"
    page = requests.get(agenda_link)
    event = BeautifulSoup(page.content, "html.parser")
    form1 = event.find("form", id="Form1")
    return form1


def get_event(event_time: datetime) -> ingestion_models.EventIngestionModel:
    """
    Parse one event at a specific date. City council meeting information for
    a specific date

    Parameters:
    --------------
    event_time: datetime
        Meeting date

    Returns:
    --------------
    ingestion_models.EventIngestionModel
        EventIngestionModel for one meeting date
    """
    agenda = get_agenda(event_time)
    event = ingestion_models.EventIngestionModel(
        body=ingestion_models.Body(name=get_body_name(agenda), is_active=True),
        sessions=[
            ingestion_models.Session(
                session_datetime=event_time,
                video_uri=get_date_mainlink(event_time) + "/embed",
                session_index=0,
            )
        ],
        event_minutes_items=get_eventMinutesItem(agenda),
        agenda_uri=get_date_mainlink(event_time) + "/agenda",
    )
    return event


def get_events(
    from_dt: datetime, to_dt: datetime
) -> List[ingestion_models.EventIngestionModel]:
    """
    Get all city council meetings information within a specific time range

    Parameters:
    --------------
    from_dt: datetime
        The start date of the time range
    to_dt: datetime
        The end date of the time range

    Returns:
    --------------
    list[ingestion_models.EventIngestionModel]
        A list of EventIngestionModel that contains all city council
        meetings information within a specific time range
    """
    events = []
    for day in range((to_dt - from_dt).days + 1):
        date = from_dt + timedelta(days=day)
        if check_in_range(date):
            event = get_event(date)
            events.append(event)
    return events


# python standard function name
# flake8 lint
# mypy

print(get_events(datetime(2022, 2, 1).date(), datetime(2022, 2, 1).date()))
# print(datetime(2022, 2, 1))
