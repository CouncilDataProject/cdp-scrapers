from bs4 import BeautifulSoup
import requests
from cdp_backend.pipeline import ingestion_models
from datetime import datetime, timedelta
from typing import Optional, List

URL = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=549"
video_URL = "https://houstontx.new.swagit.com/videos/177384"
page = requests.get(URL)
event = BeautifulSoup(page.content, "html.parser")

form1 = event.find('form', id = 'Form1')
# contain body name & date
bodyTable = form1.find_all('table')[1].find('table')


#Big Functions
main_URL = "https://houstontx.new.swagit.com/views/408"
main_page = requests.get(main_URL)
main = BeautifulSoup(main_page.content, "html.parser")

# get date from main page
#only find a specific year. different year by div id = 'city-council-2022', later do get_diff_year

# 1)loop through all date, 2)change each into datetime format, 3)if match, get the 3rd td
# 4)get the href in first a
def get_date_main(time: datetime):
    #all events in a specific year
    main_year = main.find('div', id = 'city-council-2022').find('table', id = 'video-table').find('tbody').find_all('tr')
    time = datetime.strptime(time, '%Y-%m-%d').date() #may need to delete when actually pass datetime
    for year in main_year:
        cells = year.find_all('td')
        date = cells[1].text.replace(',', '').strip()
        date = datetime.strptime(date, '%b %d %Y').date()
        if (date == time):
            link = cells[3].find('a')['href']
            link = 'https://houstontx.new.swagit.com/' + link #may have to return only link and make
                                                    #agenda and video url in other function
            #agenda url
            agenda = link + '/agenda'
            #video url
            video = link + '/embed'
            print(agenda)
        #print(time)
    #return date

# parse one event at a specific date
def get_event(
    self, 
    event_time: datetime
) -> ingestion_models.EventIngestionModel:
# convert main page string date to datetime: datetime.strptime('Jul 06 2022', '%b %d %Y').date()
# loop through the whole list in the specific year, find the event that has date match the passed
# in date, and get the agenda url
    # the video url is just the href url + "/embed", agenda is url + "/agenda"
    event = self.get_agenda()
    # things to do after getting the agenda url
    ingestion_models.EventIngestionModel(
        body = Body(name = self.get_bodyName),
        sessions = 0
    )

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
def get_bodyName(self, event: BeautifulSoup):
    if 'CITY COUNCIL' in bodyTable.text:
        return 'City Council'
    else:
        return bodyTable.find_all('span')[3].text



#def print_date(date: datetime):
    print(date == '2022-03-22')
# get session video url
print(get_date_main('2022-07-26'))
#print(datetime.strptime('2022-03-22', '%Y-%m-%d').date())
#datetime.strptime('Mar 22 2022', '%b %d %Y').date() == 