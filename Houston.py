from bs4 import BeautifulSoup, Tag
import requests
import bs4
from cdp_backend.pipeline import ingestion_models
from datetime import datetime, timedelta
from typing import Optional, List

#For individual function test
URL = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=549" #same till 2017
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


#def get_role() ->

def get_seat(name: str):  #add event: Tag
    peopleTable = form1.find_all('table')[1].find_all('table')[1].table.table #event.find_all('table')[1].find_all('table')[1].table.table
    membersTable = peopleTable.find_all('tr')[1]
    districtTable = membersTable.find('table').find('tr').find_all('td')
    seat = ''
    #left and right district
    for td in districtTable:
        text = td.find('span').find_all('br')
        for br in text:
            content = br.previousSibling
            if type(content) is bs4.element.NavigableString:
                if content.text.strip() == name:
                    seat = content.nextSibling.nextSibling.strip()
    #lower district
    underDistrict = membersTable.find('p').find('span').find('br')
    underDName = underDistrict.previousSibling
    if underDName.text.strip() == name:
        seat = underDName.nextSibling.nextSibling.strip()
    #left and right position
    positionTable = membersTable.find_all('table')[1].find('tr').find_all('td')
    for td in positionTable:
        textP = td.find('span').find_all('br')
        for br in textP:
            contentP = br.previousSibling
            if type(contentP) is bs4.element.NavigableString:
                if contentP.text.strip() == name:
                    seat = contentP.nextSibling.nextSibling.strip()
    #lower position
    underPosition = membersTable.find_all('span')[-1].find('br')
    underPName = underPosition.previousSibling
    if underPName.text.strip() == name:
        seat = underPName.nextSibling.nextSibling.strip()
    return seat

#def get_person ->
#missing: get_votes()

#def get_matter_link(link:str):
    

#Aug 3: can get every matter's link, need to parse every matter page to get matter info
def get_matter():#if contain PULLED don't include
    allTable = event.find_all('table')[1].find_all('table')
    for table in allTable:
        for td in table.find_all('td', id = 'column2'):
            if 'CONSENT AGENDA NUMBERS' in td.text:
                all_Link = table.find_all_next('table')
                for table_link in all_Link:
                    #for td in table_link:
                        if table_link.text == 'END OF CONSENT AGENDA':
                            break
                        else:
                            all_links = table_link.find_all('a', href=True)
                            for links in all_links:
                                if links is not None:
                                    link = 'https://houston.novusagenda.com/agendapublic//' + links['href']
                                    matter = get_matter_link(link)
                                    #print(link)
                    #else:
                       # continue
                    #break
                else:
                    continue
                break
        else:
            continue
        break



print(get_matter())
#def get_minutesItem()

#def get_eventMinutesItem()



#Big Functions
main_URL = "https://houstontx.new.swagit.com/views/408"
main_page = requests.get(main_URL)
main = BeautifulSoup(main_page.content, "html.parser")


# get different year
def get_diff_yearid(time):
    #time = datetime.strptime(time, '%Y-%m-%d').date()
    year = str(time.year)
    year_id = 'city-council-' + year
    return year_id

# get date from main page
#only find a specific year. different year by div id = 'city-council-2022', later do get_diff_year
# 1)loop through all date, 2)change each into datetime format, 3)if match, get the 3rd td
# 4)get the href in first a
# return the link, make agenda and video url in other function
# need to change format
def get_date_mainlink(time) -> str:
    #all events in a specific year
    main_year = main.find('div', id = get_diff_yearid(time)).find('table', id = 'video-table').find('tbody').find_all('tr')
    #time = datetime.strptime(time, '%Y-%m-%d').date() #may need to delete when actually pass datetime
    link = ''
    for year in main_year:
        cells = year.find_all('td')
        date = cells[1].text.replace(',', '').strip()
        date = datetime.strptime(date, '%b %d %Y').date()
        if (date == time):
            link_post = cells[3].find('a')['href']
            link = 'https://houstontx.new.swagit.com/' + link_post
    return link

# check if the date is in the time range we want
def check_in_range(time):
    main_year = main.find('div', id = get_diff_yearid(time)).find('table', id = 'video-table').find('tbody').find_all('tr')
    #time = datetime.strptime(time, '%Y-%m-%d').date() #may need to delete when actually pass datetime
    in_range = False
    for year in main_year:
        cells = year.find_all('td')
        date = cells[1].text.replace(',', '').strip()
        date = datetime.strptime(date, '%b %d %Y').date()
        if (date == time):
            in_range = True
    return in_range

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
        )],
        agenda_uri = get_date_mainlink(event_time) + '/agenda',
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
        if check_in_range(date) == True:
            event = get_event(date)
            events.append(event)
    return events


#print(get_events('2020-12-15', '2021-01-12'))
#print(get_events('2022-07-26', '2022-07-26'))


#Question:
#1. seat: position, district    
#role: scrape from other page for 2022, other years just do default members(taken pic)
#2. matter: all consent agenda link  minute: link not under consent and presentation stuff
#ignore matters held and pulled
#3. what to do with votes?   wait till get more info
#4. 2019 has minutes name? email the city council for more info