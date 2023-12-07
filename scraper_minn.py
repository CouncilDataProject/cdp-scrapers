from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from datetime import datetime
import requests as r
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import selenium
from selenium.webdriver.common.by import By
from cdp_backend.pipeline import ingestion_models
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from cdp_backend.database import constants as db_constants
import logging as log

def get_events(url, start_date, end_date):
    '''
    Get all the information for all events.
    Parameter:
        url: the API
    ----------------
    Returns:
    --------------
    '''
    # Converting dates to url format
    start_date_as_parameter = convert_date(start_date)
    end_date_as_parameter = convert_date(end_date)
    
    # Update the API
    # new_url = re.sub(r'toDate=(.*?)&', 'toDate=' + end_date_as_parameter + '&', \
    #                  re.sub(r'fromDate=(.*?)&', 'fromDate=' + start_date_as_parameter + '&', url))
    new_url = (
        f'https://lims.minneapolismn.gov/Calendar/GetCalenderList?fromDate={start_date_as_parameter}&toDate={end_date_as_parameter}&meetingType=0&committeeId=null&pageCount=1000&offsetStart=0&abbreviation=undefined&keywords='
    )
    
    # Request from API and filter all the valid committees
    committees = pd.DataFrame(r.get(new_url).json())
    valid_committee_types = ['Independent Committee', 'Standing Committee', 'City Council']
    valid_agenda_status = ['Committee Report Published', 'Publish', 'Marked Agenda Published']
    committees = committees[(committees.CommitteeType.isin(valid_committee_types)) & (committees.AgendaStatus.isin(valid_agenda_status))]
    
    # Generate all individual Marked Agenda urls
    # agenda_ids = committees.AgendaId
    marked_agenda_urls = {}
    for id, name in zip(committees.AgendaId, committees.CommitteeName):
        # marked_agenda_urls.append('https://lims.minneapolismn.gov/MarkedAgenda/' + str(id))
        marked_agenda_urls['https://lims.minneapolismn.gov/MarkedAgenda/' + str(id)] = name
    
    # return get_committee_type('https://lims.minneapolismn.gov/MarkedAgenda/2221', marked_agenda_urls)
    city_council = get_council_members()

    log.info('Start finding!')

    for url in marked_agenda_urls.keys():
        print(url)
        driver = webdriver.Chrome(executable_path=ChromeDriverManager().install())
        # url = "https://lims.minneapolismn.gov/MarkedAgenda/3323"
        driver.get(url)

        event_body = ingestion_models.Body(marked_agenda_urls[url], is_active=True)
        video_uri = None
        try:
            # video_link = driver.find_element(By.ID, 'VideoIcon_0_0')
            # video_link.click()
            # video_link = WebDriverWait(driver, 5).until(
            #     ec.visibility_of_all_elements_located((By.CSS_SELECTOR, 'a.ytp-youtube-button'))
            # ).get_attribute('href')
            video_link = 'https://www.youtube.com/watch?v=FGUUeajfnr0'
            
        except (selenium.common.exceptions.NoSuchElementException):
            video_uri = None
            print('No video found')
        
        log.info('video found!')
        
        committee_name = 'City Council'

        # Get Datetime:
        dt = get_event_date(driver)

        event_sessions = [
            ingestion_models.Session(
                video_uri=video_uri,
                session_index=0,
                session_datetime=dt.utcnow()
            )
        ]

        # Get voters
        member_roles = get_member_roles(driver, city_council, committee_name)

        # Inspecting each minute_item:
        li = driver.find_elements(by='css selector', value='li.customLineHeight')
        event_minutes_items = []
        month_convert = {
            'Jan': 'January',
            'Feb': 'February',
            'Mar': 'March',
            'Apr': 'April',
            'May': 'May',
            'Jun': 'June',
            'Jul': 'July',
            'Aug': 'August',
            'Sep': 'September',
            'Oct': 'October',
            'Nov': 'November',
            'Dec': 'December'
        }

        for list in li[:9]:
            try:
                if list.find_element(By.CSS_SELECTOR, 'a').get_attribute('class') == 'hrefnowrap':
                    link = list.find_element(By.CSS_SELECTOR, 'a.hrefnowrap')
                    link.click()
                    before = driver.window_handles[0]
                    after = driver.window_handles[1]
                    driver.switch_to.window(after)
                    element = WebDriverWait(driver, 2).until(
                        ec.visibility_of_element_located((By.CSS_SELECTOR, 'body'))
                    )
                    print('We are currently in the website: ' + driver.current_url)
                    togglets = element.find_elements(By.CSS_SELECTOR, '.togglet')

                    if len(togglets) > 1:
                        for i, togglet in enumerate(togglets):
                            togglets_new = WebDriverWait(driver, 5).until(
                                ec.visibility_of_all_elements_located((By.CSS_SELECTOR, '.togglet'))
                            )
                            togglet = togglets_new[i]
                            togglec = togglet.find_element(By.XPATH, "./following-sibling::div")
                            
                            m_decision = get_matter_decision(togglet)
                            if m_decision != 'Hearing Scheduled':
                                togglet.click()
                            
                            m_decision = convert_matter_decision(m_decision.text)
                            
                            minutes_item, m_name, support_file = get_minutes_item(driver, togglec)

                            m_title = togglet.find_element(By.CSS_SELECTOR, '.legisDetails-tog').text.split('\n')[1]
                            m_descr = m_title

                            m_status = None
                            m_sponsor = []
                            sponsor_name = None
                            m_type = None
                            if 'Effective Date:' in togglec.text:
                                rows = togglec.find_elements(By.CSS_SELECTOR, '.row')
                                for k, row in enumerate(rows):
                                    if 'Number' in row.text:
                                        m_type = get_mattertype(driver, row)
                                    elif 'Primary Author:' in row.text:
                                        sponsor_name = row.find_element(By.CSS_SELECTOR, 'span:nth-child(2)').text.split(' ')[-1]
                            
                            table = togglec.find_element(By.CSS_SELECTOR, '.col_full.nobottommargin table')
                            m_votes = []
                            rows = togglec.find_elements(By.CSS_SELECTOR, 'tbody tr')
                            rows = rows[:-1]
                            for j, row in enumerate(rows):
                                vote_date = parse_vote_date(driver, row, month_convert)
                                if (vote_date.year, vote_date.month, vote_date.day) == (dt.year, dt.month, dt.day):
                                    m_status = get_result_status(driver, row)
                                    
                                    vote_link = row.find_element(By.CSS_SELECTOR, 'td:nth-child(2) a')
                                    if vote_link.text == 'View Voting':
                                        vote_link.click()
                                        voting_details = WebDriverWait(driver, 3).until(
                                            ec.visibility_of_element_located((By.XPATH, f'//*[@id="model_{i}_{j}"]'))
                                        )
                                        
                                        voters = get_voters(driver, voting_details)
                                        for voter in voters:
                                            voter_name = get_voter_name(driver, voter)
                                            voter_decision = get_voter_decision(driver, voter)
                                            voter_is_active = check_is_active(voter_name, city_council)
                                            person_info = city_council[city_council['name'] == voter_name]
                                            voter_position, voter_picture, voter_phone, voter_elec_area, voter_seat_img, voter_email = get_voter_info(person_info)
                                            voter_role = member_roles[str(voter_name)]#.values[0]
                                            
                                            role_body = event_body

                                            person = ingestion_models.Person(
                                                name=voter_name,
                                                is_active = voter_is_active,
                                                seat=ingestion_models.Seat(
                                                    name=voter_position,
                                                    roles = ingestion_models.Role(title=voter_role, body=role_body),
                                                    electoral_area=voter_elec_area,
                                                    image_uri=voter_seat_img
                                                ),
                                                email=voter_email,
                                                phone=voter_phone,
                                                picture_uri=voter_picture
                                            )
                                            
                                            if sponsor_name != None:
                                                if sponsor_name in voter_name:
                                                    m_sponsor.append(person)
                                            
                                            m_votes = add_vote(m_votes, 
                                                        person,
                                                            voter_decision)
                                        
                                        print('adding into event_minutes_items!')
                                        event_minutes_items.append(
                                            ingestion_models.EventMinutesItem(
                                                minutes_item=ingestion_models.MinutesItem(m_name, description=m_descr),
                                                matter = ingestion_models.Matter(
                                                    name = m_name,
                                                    title = m_title,
                                                    matter_type=m_type,
                                                    sponsors=m_sponsor,
                                                    result_status=m_status
                                                ),
                                                decision=m_decision,
                                                votes = m_votes,
                                                supporting_files=support_file
                                            )
                                        )
                                        
                                        close_button = voting_details.find_element(By.XPATH, f'//*[@id="model_{str(i)}_{j}"]/div/div/div/div[1]/button')
                                        close_button.click()
                                        print('Go out!')
                                        break
                                
                            print("-" * 80)
                    # If toggles are opened, then do the following:
                    else:      
                        togglet = element.find_element(By.CSS_SELECTOR, '.togglet')
                        togglec = togglet.find_element(By.XPATH, "./following-sibling::div")
                        m_decision = get_matter_decision(togglet)
                        
                        m_decision = convert_matter_decision(m_decision.text)
                        
                        minutes_item, m_name, support_file = get_minutes_item(driver, togglec)

                        m_title = togglet.find_element(By.CSS_SELECTOR, '.legisDetails-tog').text.split('\n')[1]
                        m_descr = m_title
                        
                        m_type = None
                        m_sponsor = []
                        sponsor_name = None
                        if 'Effective Date:' in togglec.text:
                            rows = togglec.find_elements(By.CSS_SELECTOR, '.row')
                            for k, row in enumerate(rows):
                                if 'Number' in row.text:
                                    m_type = get_mattertype(driver, row)
                                elif 'Primary Author:' in row.text:
                                    # m_sponsor.append(row.find_element(By.CSS_SELECTOR, 'span:nth-child(2)').text)
                                    sponsor_name = row.find_element(By.CSS_SELECTOR, 'span:nth-child(2)').text.split(' ')[-1]

                        
                        m_status = None
                        
                        table = togglec.find_element(By.CSS_SELECTOR, '.col_full.nobottommargin table')
                        m_votes = []
                        rows = togglec.find_elements(By.CSS_SELECTOR, 'tbody tr')
                        rows = rows[:-1]
                        for j, row in enumerate(rows):
                            vote_date = parse_vote_date(driver, row, month_convert)
                            if (vote_date.year, vote_date.month, vote_date.day) == (dt.year, dt.month, dt.day):
                                
                                m_status = None
                                
                                vote_link = row.find_element(By.CSS_SELECTOR, 'td:nth-child(2) a')
                                if vote_link.text == 'View Voting':
                                    m_status = get_result_status(driver, row)
                                    vote_link.click()
                                    voting_details = WebDriverWait(driver, 5).until(
                                        ec.visibility_of_element_located((By.XPATH, f'//*[@id="model_0_{j}"]'))
                                    )
                                        
                                    voters = get_voters(driver, voting_details)
                                    for voter in voters:
                                        voter_name = get_voter_name(driver, voter)
                                        voter_decision = get_voter_decision(driver, voter)
                                        voter_is_active = check_is_active(voter_name, city_council)
                                        person_info = city_council[city_council['name'] == voter_name]
                                        voter_position, voter_picture, voter_phone, voter_elec_area, voter_seat_img, voter_email = get_voter_info(person_info)
                                        voter_role = member_roles[str(voter_name)]
                                        
                                        role_body = event_body
                                        
                                        person = ingestion_models.Person(
                                            name=voter_name,
                                            is_active = voter_is_active,
                                            seat=ingestion_models.Seat(
                                                name=voter_position,
                                                roles = ingestion_models.Role(title=voter_role, body=role_body),
                                                electoral_area=voter_elec_area,
                                                image_uri=voter_seat_img
                                            ),
                                            email=voter_email,
                                            phone=voter_phone,
                                            picture_uri=voter_picture
                                        )
                                        
                                        if sponsor_name != None:
                                            if sponsor_name in voter_name:
                                                m_sponsor.append(person)
                                        
                                        m_votes = add_vote(m_votes,
                                                        person,
                                                            voter_decision)

                                    print('adding into event_minutes_items!')
                                    event_minutes_items.append(
                                        ingestion_models.EventMinutesItem(
                                            minutes_item=ingestion_models.MinutesItem(m_name, description=m_descr),
                                            matter = ingestion_models.Matter(
                                                name = m_name,
                                                title = m_title,
                                                matter_type=m_type,
                                                sponsors=m_sponsor,
                                                result_status=m_status
                                            ),
                                            decision=m_decision,
                                            votes = m_votes,
                                            supporting_files=support_file
                                        )
                                    )
                                    
                                    close_button = voting_details.find_element(By.XPATH, f'//*[@id="model_0_{j}"]/div/div/div/div[1]/button')
                                    close_button.click()
                                    print('Go out!')
                                    break
                        print("-" * 80)   
                            
                    driver.close()
                    print('Closing the current tab')
                    driver.switch_to.window(before)
                    print('Switching to the other tab')
                    
                else:
                    try:
                        model = ingestion_models.EventMinutesItem(
                            minutes_item = ingestion_models.MinutesItem(
                                list.find_element(by='css selector', value='.custom-rcaview-action-review').text
                            ),
                            decision = list.find_element(by='css selector', value='.col-md-12 b').text.replace('Action Taken: ', '')
                        )
                        event_minutes_items.append(model)
                    except (selenium.common.exceptions.NoSuchElementException):
                        continue
            except (selenium.common.exceptions.NoSuchElementException):
                continue
        driver.quit()
        event = ingestion_models.EventIngestionModel(
            body=event_body,
            sessions=event_sessions,
            event_minutes_items=event_minutes_items,
            agenda_uri=url
        )

    
    return event


# def get_committee_type(url, urls):
#     return urls[url]


def convert_date(date):
    '''
    Convert the date scraped to datetime format.
    Parameter:
    ----------------
    date:
        the scraped string of the date
    Returns:
    --------------
    The updated date in datetime type.
    '''
    new_date = date.split('/')
    start_date_as_locale_str = datetime(int(new_date[2]), int(new_date[1]), int(new_date[0])).strftime("%b %d, %Y")
    return start_date_as_locale_str.replace(" ", "%20")

def get_council_members() -> pd.DataFrame:
    '''
    Get all council members' information.
    Parameter:
    ----------------
    Returns:
    --------------
    pd.Dataframe
        the dataframe of the council members' information.
    '''
    city_council = pd.DataFrame()
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install())
    council_url = 'https://www.minneapolismn.gov/government/city-council/'
    driver.get(council_url)
    cards = driver.find_elements(By.CSS_SELECTOR, '#image-text-link-50242 a.card-link')
    len(cards)
    for card in cards:
        driver.get(card.get_attribute('href'))
        position, name = driver.find_element(By.CSS_SELECTOR, '.masthead--title').text.split(' - ')
        role = driver.find_element(By.CSS_SELECTOR, 'a.contact span.title').text
        
        if role == 'Council Member':
            role = db_constants.RoleTitle.COUNCILMEMBER
        elif role == 'Council Vice-President':
            role = db_constants.RoleTitle.ALTERNATE
        elif role == 'Council President':
            role = db_constants.RoleTitle.COUNCILPRESIDENT
        else:
            raise TypeError('Basic Role not found')
        
        picture = driver.find_element(By.CSS_SELECTOR, 'a.contact img').get_attribute('src')
        elec_areas = None
        if position == 'Ward 5':
            elec_areas = driver.find_elements(By.CSS_SELECTOR, '.multicolumn-content li')
        else:
            elec_areas = driver.find_elements(By.CSS_SELECTOR, '.cell.medium-12.large-8 li')
        elec_area = []
        for area in elec_areas:
            elec_area.append(area.text)
        elec_area = ', '.join(elec_area)
        seat_img = driver.find_element(By.CSS_SELECTOR, 'section div.grid-container.fluid figure img').get_attribute('src')
        print('seat image: ' + seat_img)
        cell_num = 2
        email = None
        try:
            driver.find_element(By.CSS_SELECTOR, f'.multicolumn-content--columns.large-up-4.medium-up-2:nth-child(1) .cell:nth-child({cell_num}) button').click()
            email = WebDriverWait(driver, 2).until(
                ec.visibility_of_element_located((By.CSS_SELECTOR, f'.multicolumn-content--columns.large-up-4.medium-up-2:nth-child(1) .cell:nth-child({cell_num}) p p'))
            ).text
            cell_num += 1
        except (selenium.common.exceptions.NoSuchElementException):
            print('go on')
        phone_num = driver.find_element(By.CSS_SELECTOR, f'.multicolumn-content--columns.large-up-4.medium-up-2:nth-child(1) .cell:nth-child({cell_num}) p:nth-child(2)').text
        city_council = city_council.append({'name': name, 'position': position, 'role': role, 'picture': picture, 'phone': phone_num, 'electoral_area': elec_area, 'seat_img': seat_img, 'email': email}, ignore_index=True)
        driver.back()
    driver.quit()
    return city_council

def get_event_date(driver: selenium.webdriver.chrome.webdriver.WebDriver) -> datetime:
    '''
    Get the date and time for the single event.
    Parameters:
    --------------
    driver:
        The selenium webdriver of the single event
    
    Returns:
    --------------
    datetime
        the datetime of the current event
    '''
    dt = driver.find_element(by='css selector', value='.agendaHeader .col-md-12:nth-child(3)').text \
        .replace(',', '').replace('- ', '').split(' ')
    print(dt)
    month, day, year, time, ampm = dt
    hour, minute = time.split(':')
    hour, minute = int(hour), int(minute)
    # hour, minute
    if ampm == 'pm':
        hour += 12
    dt = datetime(int(year), datetime.strptime(month, "%B").month, int(day), hour, minute)
    return dt

def get_member_roles(driver: selenium.webdriver.chrome.webdriver.WebDriver, city_council: pd.core.frame.DataFrame, committee_name: str) -> dict:
    '''
    Updates the roles of each member.
    
    Parameter:
    ----------------
    driver:
        The selenium webdriver of the single event
    city_council:
        The dataframe of the members' information.
    committee_name:
        The body name of the event.
        
    Returns:
    --------------
    dict
        key: name of the member 
        value: the role title of the member
    '''
    member_roles = {}
    is_city_council = committee_name == 'City Council'
    for member in city_council['name']:
        member_roles[member] = city_council[city_council['name'] == member]['role'].values[0]
    members = driver.find_element(By.CSS_SELECTOR, '#markedAgendaSection .form-body .row:nth-child(2)')
    members = members.text.replace('Members Present: ', '').replace('Council Members ', '').split(', ')
    members[-1] = members[-1].replace('and ', '')
    members
    for member in members:
        member = member.split(' ')
        if len(member) > 2:
            if member[2] == '(Chair)':
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.CHAIR
            elif member[2] == '(Vice-Chair)':
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.VICE_CHAIR
            elif member[2] == '(Secretary)':
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.SUPERVISOR
            elif member[2] == '(President)':
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.COUNCILPRESIDENT
            elif member[2] == '(Vice-President)':
                member_roles[member[0]+' '+member[1]] = 'Council Vice-President' # db_constants.RoleTitle.ALTERNATE
            elif 'Quorum' in member[2]:
                if is_city_council:
                    member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.COUNCILMEMBER
                else:
                    member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.MEMBER
            else:
                raise TypeError('Role not found')
        else:
            if is_city_council:
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.COUNCILMEMBER
            else:
                member_roles[member[0]+' '+member[1]] = db_constants.RoleTitle.MEMBER
    return member_roles

def get_matter_decision(togglet: selenium.webdriver.remote.webelement.WebElement) -> selenium.webdriver.remote.webelement.WebElement:
    '''
    Get the matter decision.
    Parameter:
    ----------------
    togglet:
        The togglet web element
        
    Returns:
    --------------
    selenium.webdriver.remote.webelement.WebElement
        The web element containing the matter decision.
    '''
    m_decision = togglet.find_element(By.CSS_SELECTOR, 'a span.detail_Status')
    return m_decision

def convert_matter_decision(m_decision: str) -> str:
    '''
    Convert the matter decision string into CDP constants.
    Parameter:
    ----------------
    m_decision:
        The matter decision
        
    Returns:
    --------------
    str
        The matter decision in CDP constants format.
    '''
    if m_decision == 'Approved':
        m_decision = db_constants.EventMinutesItemDecision.PASSED
    else:
        m_decision = db_constants.EventMinutesItemDecision.FAILED
    return m_decision

def get_minutes_item(driver: selenium.webdriver.chrome.webdriver.WebDriver, togglec: selenium.webdriver.remote.webelement.WebElement) -> tuple[selenium.webdriver.remote.webelement.WebElement, str, str]:
    '''
    Gets the minute item element, the name of the matter,
    and its attached file.
    Parameter:
    ----------------
    togglec:
        The togglec web element
        
    Returns:
    --------------
    tuple
        selenium.webdriver.remote.webelement.WebElement: The minutes item 
        str: The minutes item name 
        str: The url of the attached file.
    '''
    minutes_item = togglec.find_element(By.CSS_SELECTOR, 'a:nth-child(1)')
    return [minutes_item, minutes_item.text.replace('This link open a new window\n', ''), minutes_item.get_attribute('href')]

def get_mattertype(driver: selenium.webdriver.chrome.webdriver.WebDriver, row: selenium.webdriver.remote.webelement.WebElement) -> str:
    '''
    Get the matter type.
    
    Parameter:
    ----------------
    row:
        The web element of a single row of the table
        
    Returns:
    --------------
    str
        The matter type string
    '''
    return row.find_element(By.CSS_SELECTOR, 'h5').text.split(' ')[0]

def parse_vote_date(driver: selenium.webdriver.chrome.webdriver.WebDriver,
                    row: selenium.webdriver.remote.webelement.WebElement,
                    month_convert: dict) -> datetime:
    '''
    Get the datetime form of the matter's voting date.
    
    Parameter:
    ----------------
    row:
        The web element of a single row of the table
    month_convert:
        The dict for converting month abbreviation.
        
    Returns:
    --------------
    datetime
        The datetime of the voting.
    '''
    vote_date = row.find_element(By.CSS_SELECTOR, 'td:nth-child(1)').text #.split(' ')
    vote_date = vote_date.replace(vote_date[:3], month_convert[vote_date[:3]])
    vote_date = datetime.strptime(vote_date, "%B %d, %Y")
    return vote_date

def get_result_status(driver: selenium.webdriver.chrome.webdriver.WebDriver,
                      row: selenium.webdriver.remote.webelement.WebElement) -> str:
    '''
    Converts and the matter's result status to the form
    of CDP constants.
    
    Parameter:
    ----------------
    row:
        The web element of a single row of the table
        
    Returns:
    --------------
    str
        The result_status of the matter
    '''
    m_status = None
    if row.find_element(By.CSS_SELECTOR, 'td:nth-child(2)').text.split(',')[0] == 'Adopted':
        m_status = db_constants.MatterStatusDecision.ADOPTED
    elif row.find_element(By.CSS_SELECTOR, 'td:nth-child(2)').text.split(',')[0] == 'Approved and Signed by Mayor':
        m_status = db_constants.MatterStatusDecision.IN_PROGRESS
    else:
        raise LookupError('New status type appears!')
    return m_status

def get_voters(driver: selenium.webdriver.chrome.webdriver.WebDriver,
               voting_details: selenium.webdriver.remote.webelement.WebElement) -> list:
    '''
    Get the voting detail elements for each voter.
    
    Parameter:
    ----------------
    row:
        The web element of a single row of the table
        
    Returns:
    --------------
    str
        The result_status of the matter
    '''
    return voting_details.find_elements(By.CSS_SELECTOR, '.vote-row')

def get_voter_name(driver: selenium.webdriver.chrome.webdriver.WebDriver,
                   voter: selenium.webdriver.remote.webelement.WebElement) -> str:
    '''
    Get the single voter's name.
    
    Parameter:
    ----------------
    voter:
        The web element of a single voter
        
    Returns:
    --------------
    str
        The voter's name.
    '''
    return voter.find_element(By.CSS_SELECTOR, '.vote-cell:nth-child(1)').text

def get_voter_decision(driver: selenium.webdriver.chrome.webdriver.WebDriver,
                       voter: selenium.webdriver.remote.webelement.WebElement) -> str:
    '''
    Get the voter's decision in the form of CDP constants.
    
    Parameter:
    ----------------
    voter:
        The web element of a single voter
        
    Returns:
    --------------
    str
        The voter's decision
    '''
    voter_decision = voter.find_element(By.CSS_SELECTOR, '.vote-cell:nth-child(2)').text
    if voter_decision == 'Aye':
        voter_decision = db_constants.VoteDecision.APPROVE
    elif voter_decision == 'Nay':
        voter_decision = db_constants.VoteDecision.REJECT
    elif voter_decision == 'Abstain':
        voter_decision = db_constants.VoteDecision.ABSTAIN_NON_VOTING
    else:
        raise TypeError('New type of vote decision found')
    return voter_decision

def check_is_active(voter_name: str, city_council: pd.DataFrame) -> bool:
    '''
    Returns the bool to check whether the voter is active.
    
    Parameter:
    ----------------
    voter_name:
        The name of the voter
    city_council:
        The dataframe containing all voters' information.
        
    Returns:
    --------------
    bool
        The status if the voter is active.
    '''
    return voter_name in city_council.name.tolist()

def get_voter_info(person_info: pd.DataFrame) -> tuple:
    '''
    Get the voter's position, picture uri, phone number,
    electoral area, seat image uri, and email address.
    
    Parameter:
    ----------------
    person_info:
        The all information of the single voter
        
    Returns:
    --------------
    tuple
        the voter's position, picture uri, phone number,
        electoral area, seat image uri, and email address
    '''
    voter_position = person_info['position'].values[0]
    voter_picture = person_info['picture'].values[0]
    voter_phone = person_info['phone'].values[0]
    voter_elec_area = person_info['electoral_area'].values[0]
    voter_seat_img = person_info['seat_img'].values[0]
    voter_email = person_info['email'].values[0]
    return (voter_position, voter_picture, voter_phone,
            voter_elec_area, voter_seat_img, voter_email)
    
def add_vote(m_votes: list,
            person: ingestion_models.Person,
            voter_decision: str) -> list:
    '''
    Add the vote of a person into the votes list.
    
    Parameter:
    ----------------
    m_votes:
        The voting list of the matter.
    person:
        The person ingestion model of a single voter.
    voter_decision:
        The voter's decision.
        
    Returns:
    --------------
    list
        the updated voting list
    '''
    m_votes.append(
        ingestion_models.Vote(
            person=person,
            decision = voter_decision
        )
    )
    return m_votes

def main():
    d = get_events('https://lims.minneapolismn.gov/Calendar/GetCalenderList?fromDate=May 1, 2021&toDate=Aug 1, 2022&meetingType=0&committeeId=null&pageCount=1000&offsetStart=0&abbreviation=undefined&keywords=', '31/01/2021', '26/07/2022')
    print(d)
    # print(d[:5])
    


if __name__ == "__main__":
    main()