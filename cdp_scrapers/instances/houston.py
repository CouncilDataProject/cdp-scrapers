from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from cdp_backend.pipeline import ingestion_models
from cdp_backend.pipeline.ingestion_models import (
    Body,
    EventIngestionModel,
    EventMinutesItem,
    Matter,
    MinutesItem,
    Person,
    Session,
    SupportingFile,
    Vote,
)


from datetime import datetime
from typing import List, Union, Optional, Any
import logging

from cdp_scrapers.scraper_utils import IngestionModelScraper

log = logging.getLogger(__name__)


class HoustonScraper(IngestionModelScraper):
    def __init__(self):
        super().__init__(timezone="America/Chicago")

    def remove_extra_type(self, element: Union[Tag, NavigableString, None]) -> Tag:
        """
        Remove types that are not useful

        Parameter:
        ----------------
        event: Union[Tag, NavigableString, None]
            All elements in the page that we want to scrape

        Returns:
        ----------------
        Tag
            Same elements as received, assuming the elements are not null
        """
        if isinstance(element, NavigableString) or element is None:
            raise ValueError(f"Wrong Type {type(element)}")
        return element

    def get_body_name(self, event: Union[Tag, NavigableString, None]) -> str:
        """
        Get the body name for an event

        Parameter:
        ----------------
        event: Union[Tag, NavigableString, None]
            All elements in the page that we want to scrape

        Returns:
        ----------------
        str
            The body name
        """
        log.info("start get body name")
        event = self.remove_extra_type(event)
        bodyTable = event.find_all("table")[1].find("table")
        if "CITY COUNCIL" in bodyTable.text:
            return "City Council"
        else:
            return bodyTable.find_all("span")[3].text.title()

    def get_event_Minutes_Item(
        self, event: Union[Tag, NavigableString, None],
    ) -> List[ingestion_models.EventMinutesItem]:
        """
        Parse the page and gather the event minute items

        Parameter:
        ----------------
        event: Union[Tag, NavigableString, None]
            All elements in the page that we want to scrape

        Returns:
        ----------------
        List[ingestion_models.EventMinutesItem]
            All the event minute items gathered from the event on the page
        """
        log.info("start get items")
        event_minutes_items = []
        all_items = self.remove_extra_type(event).find_all("td", {"class": "style4"})
        for item in all_items:
            name = ''

            for i in item.stripped_strings:
                name = name + " " + repr(i).replace('\'', '')

            if name is not None and name != "":
                event_minutes_items.append(
                    ingestion_models.EventMinutesItem(
                        minutes_item=ingestion_models.MinutesItem(
                            name.strip()
                        )
                    )
                )

        return event_minutes_items

    # Big Functions
    def get_diff_yearid(self, time: datetime) -> str:
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

    def get_date_mainlink(self, element: BeautifulSoup) -> str:
        """
        Find the main link for one event.

        Parameters:
        --------------
        time: datetime
            The date of one event

        Returns:
        --------------
        str
            The main link, make agenda and video url in other function
        """
        link_post = element.find("a")["href"]
        link = f"https://houstontx.new.swagit.com/{link_post}"
        return link

    def get_agenda(self, element: BeautifulSoup) -> Union[Tag, NavigableString, None]:
        """
        Get event agenda for a specific details page

        Parameters:
        ----------------
        event_time: datetime
            The date we want to get agenda

        Returns:
        ----------------
        Tag
            The agenda web page we want parse
        """
        link = self.get_date_mainlink(element)
        agenda_link = link + "/agenda"
        page = requests.get(agenda_link)
        event = BeautifulSoup(page.content, "html.parser")
        form1 = event.find("form", id="Form1")
        return form1

    def get_event(self, element_list) -> ingestion_models.EventIngestionModel:
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
        log.info("start get one event")
        date, element = element_list
        main_uri = self.get_date_mainlink(element)
        agenda = self.get_agenda(element)
        event = ingestion_models.EventIngestionModel(
            body=ingestion_models.Body(name=self.get_body_name(agenda), is_active=True),
            sessions=[
                ingestion_models.Session(
                    session_datetime=date,
                    video_uri=main_uri + "/embed",
                    session_index=0,
                )
            ],
            event_minutes_items=self.get_event_Minutes_Item(agenda),
            agenda_uri=main_uri + "/agenda",
        )
        return event

    def get_all_elements_in_range(self, time_from: datetime, time_to: datetime) -> List[BeautifulSoup]:
        """
        Get all the meetings in a range of dates

        Parameters:
        --------------
        time_from: datetime
            Earliest meeting date to look at
        time_to: datetime
            Latest meeting date to look at

        Returns:
        --------------
        List[BeautifulSoup]
            Elements that contain different meetings
        """
        if time_from.year != time_to.year:
            raise ValueError(f"time_from and time_to are in different years, which is not")
        elements = []
        main_URL = "https://houstontx.new.swagit.com/views/408"
        main_page = requests.get(main_URL)
        main = BeautifulSoup(main_page.content, "html.parser")
        main_div = self.remove_extra_type(main.find("div", id=self.get_diff_yearid(time_from)))
        main_table = self.remove_extra_type(main_div.find("table", id="video-table"))
        main_tbody = self.remove_extra_type(main_table.find("tbody"))
        main_year = main_tbody.find_all("tr")
        for year in main_year:
            cells = year.find_all("td")
            date = cells[1].text.replace(",", "").strip()
            date = datetime.strptime(date, "%b %d %Y").date()
            if date >= time_from.date() and date <= time_to.date():
                element = [date, year]
                elements.append(element)
        return elements

    def get_events(
        self,
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
        elements = self.get_all_elements_in_range(from_dt, to_dt)
        for element in elements:
            events.append(self.get_event(element))
        return events


def get_houston_events(
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    **kwargs: Any,
) -> List[EventIngestionModel]:
    """
    Public API for use in instances.__init__ so that this func can be attached
    as an attribute to cdp_scrapers.instances module.
    Thus the outside world like cdp-backend can get at this by asking for
    "get_portland_events".

    Parameters
    ----------
    from_dt: datetime, optional
        The timespan beginning datetime to query for events after.
        Default is 2 days from UTC now
    to_dt: datetime, optional
        The timespan end datetime to query for events before.
        Default is UTC now

    Returns
    -------
    events: List[EventIngestionModel]

    See Also
    --------
    cdp_scrapers.instances.__init__.py
    """
    scraper = HoustonScraper()
    return scraper.get_events(begin=from_dt, end=to_dt, **kwargs)

