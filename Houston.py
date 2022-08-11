from bs4 import BeautifulSoup, Tag
import requests
import bs4
from cdp_backend.pipeline import ingestion_models
from datetime import datetime, timedelta
from typing import Optional, List

#For individual function test
URL = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=383" #same till 2017
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

#for each department(ul), search whether the name is in the department text, if is, append to role
#list.
def get_role(name: str):
    name = name.split(' ')[-1].strip()
    role_url = 'http://www.houstontx.gov/council/committees/'
    role_page = BeautifulSoup(requests.get(role_url).content, "html.parser")
    roles = ['City Council: Member']
    status = False
    role_list = role_page.find('div', class_ = '8u 12u(mobile)')
    role_titles = role_list.find_all('p')
    for role_title in role_titles:
        titles = role_title.find_all('strong')
        for title in titles:
            if title is not None and title.text != '': #title: eg.PUBLIC SAFETY & HOMELAND SECURITY (PSHS)
                role_members = title.find_next('ul').find_all('li')
                for role_member in role_members:
                    if 'Agenda' not in role_member.text:
                        role_and_member = role_member.text.split(':')
                        role_name = role_and_member[0].strip() #role_name: chair, vice chair, member, etc
                        if len(role_and_member) > 2:
                            member_names = role_and_member[2].split(',')
                        else:
                            member_names = role_and_member[1].split(',')
                        for member_name in member_names:
                            if name in member_name.strip():
                                roles.append(title.text + ': ' + role_name)
                                status = True

    return (roles, status)

#print(get_role('Letitia Plummer'))

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

def get_person(name:str):
    return ingestion_models.Person(
        name = name,
        is_active = get_role(name)[1],
        seat = ingestion_models.Seat(
            name = get_seat(name),
            roles = ingestion_models.Role(
                title = get_role(name)[0]
            )
        )
    )

#print(get_person('Amy Peck'))

#missing: get_votes()

def get_matter_name(link):
    matter_page = requests.get(link)
    matter = BeautifulSoup(matter_page.content, "html.parser")
    matter_name = matter.find('table').find('table').find('table').find_all('td')[1].find('div').find('div').find('br').previousSibling
    return matter_name

def get_matter_title(link):
    matter_page = requests.get(link)
    matter = BeautifulSoup(matter_page.content, "html.parser")
    matter_title = matter.find('table').find_all('table')[2].text.replace('Summary:', '').strip()
    return matter_title

#def get_matter_type(): #event:Tag
 #   agenda_titles = form1.find_all('td', id = 'column2', class_ = 'style1')
  #  for agenda_title in agenda_titles:
   #     print(agenda_title.text)


#print(get_matter_type())

#Aug 3: can get every matter's link, need to parse every matter page to get matter info √
#need to ignor video link like http://houstontx.swagit.com/mini/11282017-1376/#12 √
#if contain PULLED don't include √
# MAY DELETE EVENTUALLY!!!!!!!!!!!!!!!!!
# def get_matter():#event: Tag 
#     allTable = event.find_all('table')[1].find_all('table')
#     matter = []
#     for table in allTable:  
#         for td in table.find_all('td', id = 'column2'):
#             if 'CONSENT AGENDA NUMBERS' in td.text:
#                 all_Link = table.find_all_next('table')
#                 for table_link in all_Link:
#                     #for td in table_link:
#                         if table_link.text == 'END OF CONSENT AGENDA':
#                             break
#                         else:
#                             all_links = table_link.find_all('a', href=True)
#                             for links in all_links: #links: one matter
#                                 if links is not None and links.text != 'VIDEO':
#                                     link = 'https://houston.novusagenda.com/agendapublic//' + links['href']
#                                     if '**PULLED' not in get_matter_title(link):
#                                         matter_types = links.find_all_previous('td', id = 'column2', class_ = 'style1')
#                                         one_matter_type = ''
#                                         for matter_type in matter_types:
#                                             if '-' in matter_type.text:
#                                                 one_matter_type = matter_type.text.split('-')[0].strip()
#                                                 break
#                                         matter.append(
#                                             ingestion_models.EventMinutesItem(
#                                                 minutes_item = ingestion_models.MinutesItem(get_matter_name(link)),
#                                                 matter = ingestion_models.Matter(
#                                                             name = get_matter_name(link),
#                                                             matter_type = one_matter_type,
#                                                             title = get_matter_title(link)
#                                                             )
#                                             )
#                                         )
#                     #else:
#                        # continue
#                     #break
#                 else:
#                     continue
#                 break
#         else:
#             continue
#         break
#     return matter

#def get_minutesItem() starting from matters held, check if the nextsibling is a link, if is then ignore
#check if the link has title matters held, if is, not include

#is_matter = False  if under consent agenda, is_matter = True
def get_eventMinutesItem(event: Tag): #event: Tag
    event_minutes_items = []
    # get minutes on the first day, done, don't delete!
    firstday_minutes = event.find_all('td', id = 'column1', class_ = 'style1') #change form1 to event
    for firstday_minute in firstday_minutes:
        #print(firstday_minute.text.strip())
       event_minutes_items.append(ingestion_models.EventMinutesItem(
           minutes_item = ingestion_models.MinutesItem(firstday_minute.text.strip())
       ))
    
    # get minutes before matter, done, don't delete!
    all_tables = event.find_all('table')[1].find_all('table')
    for all_table in all_tables:
       if 'DESCRIPTIONS OR CAPTIONS OF AGENDA ITEMS WILL BE READ BY THE' in all_table.text:
           all_prematter_tables = all_table.find_all_next('table')
           for all_prematter_table in all_prematter_tables:
               if 'CONSENT AGENDA NUMBERS' in all_prematter_table.text:
                   break
               else:
                   minutes_names = all_prematter_table.find_all('td', id = 'column2')
                   for minutes_name in minutes_names:
                       if minutes_name is not None and minutes_name.text != '' and '.' not in minutes_name.text:
                           #print(minutes_name.text.strip())  #
                           event_minutes_items.append(ingestion_models.EventMinutesItem(
                               minutes_item = ingestion_models.MinutesItem(minutes_name.text.strip())
                           ))
    
    #get matter
    allTable = event.find_all('table')[1].find_all('table')
    for table in allTable:  
        for td in table.find_all('td', id = 'column2'):
            if 'CONSENT AGENDA NUMBERS' in td.text:
                all_Link = table.find_all_next('table')
                for table_link in all_Link:
                        if table_link.text == 'END OF CONSENT AGENDA':
                            break
                        else:
                            all_links = table_link.find_all('a', href=True)
                            for links in all_links: #links: one matter
                                if links is not None and links.text != 'VIDEO':
                                    link = 'https://houston.novusagenda.com/agendapublic//' + links['href']
                                    if '**PULLED' not in get_matter_title(link):
                                        matter_types = links.find_all_previous('td', id = 'column2', class_ = 'style1')
                                        one_matter_type = ''
                                        for matter_type in matter_types:
                                            if '-' in matter_type.text:
                                                one_matter_type = matter_type.text.split('-')[0].strip()
                                                break
                                        #print(get_matter_name(link))  #
                                        event_minutes_items.append(
                                            ingestion_models.EventMinutesItem(
                                                minutes_item = ingestion_models.MinutesItem(get_matter_name(link)),
                                                matter = ingestion_models.Matter(
                                                            name = get_matter_name(link),
                                                            matter_type = one_matter_type,
                                                            title = get_matter_title(link)
                                                            )
                                            )
                                        )
                    #else:
                       # continue
                    #break
                else:
                    continue
                break
        else:
            continue
        break

    # get minutes after matter
    allTable = event.find_all('table')[1].find_all('table')
    for table in allTable:  
        for td in table.find_all('td', id = 'column2'):
            if 'END OF CONSENT AGENDA' in td.text:
                all_afterm_minutes = table_link.find_all_next('a', href=True)
                for minutes in all_afterm_minutes: #links: one minute
                    if minutes is not None and minutes.text != 'VIDEO':
                        minutes_link = 'https://houston.novusagenda.com/agendapublic//' + minutes['href']
                        minute_types = minutes.find_all_previous('td', id = 'column2', class_ = 'style1')
                        one_minute_type = ''
                        for minute_type in minute_types:
                            if minute_type is not None and minute_type.text != '':
                                one_minute_type = minute_type.text.split('-')[0].strip()
                                break
                        if 'MATTERS HELD' not in one_minute_type:
                            #print(get_matter_name(minutes_link))
                            event_minutes_items.append(ingestion_models.EventMinutesItem(
                               minutes_item = ingestion_models.MinutesItem(get_matter_name(minutes_link))
                            ))
    return event_minutes_items

#print(get_eventMinutesItem())








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
def get_event(event_time) -> ingestion_models.EventIngestionModel:
    event_time = datetime.strptime(event_time, '%Y-%m-%d').date() #
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
        event_minutes_items = get_eventMinutesItem(agenda),
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
#print(get_events('2019-10-29', '2019-10-29'))

one_event_minutes_item = get_event('2019-10-29')
# need event ingestion model to do to_json
with open("test-cdp-event-minutesitem.json", "w") as open_f:
    open_f.write(one_event_minutes_item.to_json(indent=4))


#Aug2:
#role: scrape from other page for 2022, other years just do default members(taken pic)
#ignore matters held and pulled
#3. what to do with votes?   wait till get more info
#4. 2019 has minutes name? email the city council for more info

#Question:
#1. if people not in the current member list, is_active = False?
#2. can't make next Fri meeting
#3. must the eventminutes item in order? now return a list of matter, can i just return a list of
#eventsminutesitem in get_matter?