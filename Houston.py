from bs4 import BeautifulSoup, Tag
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

#Individual Get Functions
# get body name, done
def get_bodyName(event: Tag):
    # contain body name & date
    bodyTable = event.find_all('table')[1].find('table')
    if 'CITY COUNCIL' in bodyTable.text:
        return 'City Council'
    else:
        return bodyTable.find_all('span')[3].text





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
def get_date_mainlink(time) -> str:
    #all events in a specific year
    main_year = main.find('div', id = 'city-council-2022').find('table', id = 'video-table').find('tbody').find_all('tr')
    #time = datetime.strptime(time, '%Y-%m-%d').date() #may need to delete when actually pass datetime
    link = 'https://houstontx.new.swagit.com/'
    for year in main_year:
        cells = year.find_all('td')
        date = cells[1].text.replace(',', '').strip()
        date = datetime.strptime(date, '%b %d %Y').date()
        if (date == time):
            link_post = cells[3].find('a')['href']
            link = link + link_post
    return link

#agenda url: agenda = link + '/agenda'
#video url: video = link + '/embed'

# get agenda for a specific date, done
def get_agenda(event_time: datetime):
    link = get_date_mainlink(event_time)
    agenda_link = link + "/agenda"
    page = requests.get(agenda_link)
    event = BeautifulSoup(page.content, "html.parser") #type: BeautifulSoup
    form1 = event.find('form', id = 'Form1') #type: Tag
    return form1

# parse one event at a specific date, done
def get_event(event_time: datetime) -> ingestion_models.EventIngestionModel:
    agenda = get_agenda(event_time)
    # just basic body and sessions for now, add more after get_events done
    event = ingestion_models.EventIngestionModel(
        body = ingestion_models.Body(name = get_bodyName(agenda), is_active=True),
        sessions = [
            ingestion_models.Session(
                session_datetime = event_time,
                video_uri = get_date_mainlink(event_time) + '/embed',
                session_index = 0
        )
        ]
    )
    return event

# get all events within time range
#now need to deal with cases with no events on that date
def get_events(begin, end) -> list:
    events = []
    begin = datetime.strptime(begin, '%Y-%m-%d').date()
    end = datetime.strptime(end, '%Y-%m-%d').date()
    for day in range((end - begin).days + 1): 
        date = begin + timedelta(days=day)
        event = get_event(date)
        events.append(event)
    return events


#print(get_date_mainlink('2022-07-26'))
print(get_events('2022-05-10', '2022-05-10'))