from bs4 import BeautifulSoup
import requests
from cdp_backend.pipeline import ingestion_models
from datetime import datetime, timedelta
from typing import Optional, List

#For individual function test
URL = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=549"
video_URL = "https://houstontx.new.swagit.com/videos/177384"
page = requests.get(URL)
event = BeautifulSoup(page.content, "html.parser")
form1 = event.find('form', id = 'Form1')
#


#Big Functions
main_URL = "https://houstontx.new.swagit.com/views/408"
main_page = requests.get(main_URL)
main = BeautifulSoup(main_page.content, "html.parser")

# get date from main page
#only find a specific year. different year by div id = 'city-council-2022', later do get_diff_year

# 1)loop through all date, 2)change each into datetime format, 3)if match, get the 3rd td
# 4)get the href in first a
# return the link, make agenda and video url in other function
# need to change format
def get_date_mainlink(time: datetime) -> str:
    #all events in a specific year
    main_year = main.find('div', id = 'city-council-2022').find('table', id = 'video-table').find('tbody').find_all('tr')
    time = datetime.strptime(time, '%Y-%m-%d').date() #may need to delete when actually pass datetime
    for year in main_year:
        cells = year.find_all('td')
        date = cells[1].text.replace(',', '').strip()
        date = datetime.strptime(date, '%b %d %Y').date()
        if (date == time):
            link = cells[3].find('a')['href']
            link = 'https://houstontx.new.swagit.com/' + link
    return link

#agenda url: agenda = link + '/agenda'
#video url: video = link + '/embed'

def get_agenda(event_time: datetime):
    agenda_link = get_date_mainlink(event_time) + '/agenda'
    page = requests.get(agenda_link)
    event = BeautifulSoup(page.content, "html.parser")
    form1 = event.find('form', id = 'Form1')
    return form1
#what is the type for form1?????????beautifulsoup????????

# parse one event at a specific date
def get_event(event_time: datetime) -> ingestion_models.EventIngestionModel:
    event = get_agenda(event_time)
    # things to do after getting the agenda url
    ingestion_models.EventIngestionModel(
        #body = ingestion_models.Body(name = get_bodyName(event)),
        body = ingestion_models.Body('City Council'),
        sessions = 0
    )
#what is the output for testing purpose???????????????????????????????????

# get all events within time range
def get_events(
    self,
    begin: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> list:
    for day in range((end - begin).days): 
        self.get_event(begin + timedelta(days=day))


#Get Functions
# get body name
def get_bodyName(event: BeautifulSoup):
    # contain body name & date
    bodyTable = event.find_all('table')[1].find('table')
    if 'CITY COUNCIL' in bodyTable.text:
        return 'City Council'
    else:
        return bodyTable.find_all('span')[3].text



print(get_event('2022-07-26'))