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
#only find a specific year. different year by div id = 'city-council-2022', later
main_year = main.find('table', id = 'video-table')
#def get_date_main(self):
    # convert string date to datetime: datetime.strptime('Jul 06 2022', '%b %d %Y').date()
    

# parse one event at a specific date
def get_event(
    self, 
    event_time: datetime
) -> ingestion_models.EventIngestionModel:
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



# get session video url
print(main_year.find_all('tr'))