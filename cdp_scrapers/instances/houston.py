import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from cdp_backend.pipeline import ingestion_models
from cdp_backend.pipeline.ingestion_models import EventIngestionModel

from cdp_scrapers.scraper_utils import IngestionModelScraper

log = logging.getLogger(__name__)


class HoustonScraper(IngestionModelScraper):
    def __init__(self):
        super().__init__(timezone="America/Chicago")

    def remove_extra_type(self, element: Union[Tag, NavigableString, None]) -> Tag:
        """
        Remove types that are not useful.

        Parameters
        ----------
        element: Union[Tag, NavigableString, None]
            The element in the page that we want to scrape

        Returns
        -------
        Tag
            Same elements as received, assuming the elements are not null
        """
        if isinstance(element, NavigableString) or element is None:
            raise ValueError(f"Wrong Type {type(element)}")
        return element

    def get_body_name(self, event: Union[Tag, NavigableString, None]) -> str:
        """
        Get the body name for an event.

        Parameters
        ----------
        event: Union[Tag, NavigableString, None]
            All elements in the page that we want to scrape

        Returns
        -------
        str
            The body name
        """
        log.info("start get body name")
        event = self.remove_extra_type(event)
        body_table = event.find_all("table")[1].find("table")
        if "CITY COUNCIL" in body_table.text:
            return "City Council"
        else:
            return body_table.find_all("span")[3].text.title()

    def get_event_minutes_item(
        self,
        event: Union[Tag, NavigableString, None],
    ) -> List[ingestion_models.EventMinutesItem]:
        """
        Parse the page and gather the event minute items.

        Parameters
        ----------
        event: Union[Tag, NavigableString, None]
            All elements in the page that we want to scrape

        Returns
        -------
        List[ingestion_models.EventMinutesItem]
            All the event minute items gathered from the event on the page
        """
        log.info("start get items")
        event_minutes_items = []
        all_items = self.remove_extra_type(event).find_all("td", {"class": "style4"})
        for item in all_items:
            name = ""

            for i in item.stripped_strings:
                name = name + " " + repr(i).replace("'", "")

            for a in item.find_all("a", href=True):
                href = "https://houston.novusagenda.com/agendapublic/" + a["href"]

            if name is not None and name != "":
                event_minutes_items.append(
                    ingestion_models.EventMinutesItem(
                        minutes_item=ingestion_models.MinutesItem(name.strip()),
                        supporting_files=href,
                    )
                )

        return event_minutes_items

    def get_diff_yearid(self, event_date: datetime) -> str:
        """
        Get the events in different years as the events for different
        years are stored in different tabs. Can get multiple events
        across years.

        Parameters
        ----------
        event_date: datetime
            The date of the event we are trying to parse

        Returns
        -------
        str
            The year id that can locate the year tab where the event is stored
        """
        year = str(event_date.year)
        year_id = "city-council-" + year
        return year_id

    def get_date_mainlink(self, element: Tag) -> str:
        """
        Find the main link for one event.

        Parameters
        ----------
        element: Tag
            The element of one event

        Returns
        -------
        str
            The main link for this event
        """
        link_post = element.find("a")["href"]
        link = f"https://houstontx.new.swagit.com/{link_post}"
        return link

    def get_agenda(self, element: Tag) -> Union[Tag, NavigableString, None]:
        """
        Get event agenda for a specific details page.

        Parameters
        ----------
        element: Tag
            The element from which we want to get agenda

        Returns
        -------
        Tag
            The agenda web page we want parse
        """
        link = self.get_date_mainlink(element)
        agenda_link = link + "/agenda"
        page = requests.get(agenda_link)
        event = BeautifulSoup(page.content, "html.parser")
        form1 = event.find("form", id="Form1")
        return form1

    def get_event(
        self, date: str, element: Tag
    ) -> ingestion_models.EventIngestionModel:
        """
        Parse one event at a specific date. City council meeting information for
        a specific date.

        Parameters
        ----------
        date: str
            the date of this meeting
        element: Tag
            the meeting Tag element

        Returns
        -------
        ingestion_models.EventIngestionModel
            EventIngestionModel for one meeting date
        """
        log.info("start get one event")
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
            event_minutes_items=self.get_event_minutes_item(agenda),
            agenda_uri=main_uri + "/agenda",
        )
        return event

    def get_all_elements_in_range(
        self, time_from: datetime, time_to: datetime
    ) -> Dict[str, Tag]:
        """
        Get all the meetings in a range of dates.

        Parameters
        ----------
        time_from: datetime
            Earliest meeting date to look at
        time_to: datetime
            Latest meeting date to look at

        Returns
        -------
        Dict[str, Tag]
            Dictionary of mapping between the date of the meeting and the element for
            the meeting in that date
        """
        if time_from.year != time_to.year:
            raise ValueError(
                "time_from and time_to are in different years, which is not supported"
            )
        date_years = {}
        main_url = "https://houstontx.new.swagit.com/views/408"
        main_page = requests.get(main_url)
        main = BeautifulSoup(main_page.content, "html.parser")
        main_div = self.remove_extra_type(
            main.find("div", id=self.get_diff_yearid(time_from))
        )
        main_table = self.remove_extra_type(main_div.find("table", id="video-table"))
        main_tbody = self.remove_extra_type(main_table.find("tbody"))
        main_year_elem = main_tbody.find_all("tr")
        for year_elem in main_year_elem:
            cells = year_elem.find_all("td")
            date = cells[1].text.replace(",", "").strip()
            date = datetime.strptime(date, "%b %d %Y").date()
            if date >= time_from.date() and date <= time_to.date():
                # date_year = [date, year_elem]
                # date_years.append(date_year)
                date_years[date] = year_elem
        return date_years

    def get_events(
        self, from_dt: datetime, to_dt: datetime
    ) -> List[ingestion_models.EventIngestionModel]:
        """
        Get all city council meetings information within a specific time range.

        Parameters
        ----------
        from_dt: datetime
            The start date of the time range
        to_dt: datetime
            The end date of the time range

        Returns
        -------
        list[ingestion_models.EventIngestionModel]
            A list of EventIngestionModel that contains all city council
            meetings information within a specific time range
        """
        events = []
        d = self.get_all_elements_in_range(from_dt, to_dt)
        for date, _element in d.items():
            events.append(self.get_event(date, d[date]))
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
    kwargs: Any
        Any extra keyword arguments to pass to the get_events function.

    Returns
    -------
    events: List[EventIngestionModel]

    See Also
    --------
    cdp_scrapers.instances.__init__.py
    """
    scraper = HoustonScraper()
    return scraper.get_events(begin=from_dt, end=to_dt, **kwargs)
