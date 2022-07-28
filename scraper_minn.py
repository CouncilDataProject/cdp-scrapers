from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from datetime import datetime
import re
import requests as r
import pandas as pd


def get_events(url, start_date, end_date):
    # Converting dates to url format
    start_date_as_parameter = convert_date(start_date)
    end_date_as_parameter = convert_date(end_date)
    
    # Update the API
    new_url = re.sub(r'toDate=(.*?)&', 'toDate=' + end_date_as_parameter + '&', \
                     re.sub(r'fromDate=(.*?)&', 'fromDate=' + start_date_as_parameter + '&', url))
    
    # Request from API and filter all the valid committees
    committees = pd.DataFrame(r.get(new_url).json())
    valid_committee_types = ['Independent Committee', 'Standing Committee', 'City Council']
    valid_agenda_status = ['Committee Report Published', 'Publish', 'Marked Agenda Published']
    committees = committees[(committees.CommitteeType.isin(valid_committee_types)) & (committees.AgendaStatus.isin(valid_agenda_status))]
    
    # Generate all individual Marked Agenda urls
    agenda_ids = committees.AgendaId
    marked_agenda_urls = []
    for id in agenda_ids:
        marked_agenda_urls.append('https://lims.minneapolismn.gov/MarkedAgenda/' + str(id))
    
    return marked_agenda_urls


def convert_date(date):
    new_date = date.split('/')
    start_date_as_locale_str = datetime(int(new_date[2]), int(new_date[1]), int(new_date[0])).strftime("%b %d, %Y")
    return start_date_as_locale_str.replace(" ", "%20")


def main():
    d = get_events('https://lims.minneapolismn.gov/Calendar/GetCalenderList?fromDate=May 1, 2021&toDate=Aug 1, 2022&meetingType=0&committeeId=null&pageCount=1000&offsetStart=0&abbreviation=undefined&keywords=', '31/01/2021', '26/07/2022')
    print(len(d))
    print(d[:5])


if __name__ == "__main__":
    main()