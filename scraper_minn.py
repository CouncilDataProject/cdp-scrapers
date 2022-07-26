from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import re

PATH = "C:\Program Files (x86)\chromedriver.exe"

def get_all_urls(url, startdate='', enddate=''):
    # driver = webdriver.Chrome(executable_path=ChromeDriverManager().install())
    divided = re.split('\?', url)
    first_part = divided[0]
    second_part = divided[1]
    divided_2 = re.split('&', second_part)
    
    sd = 'fd=' + startdate.replace('/', '%2F')
    ed = 'ed=' + enddate.replace('/', '%2F')
    
    divided_2[0] = sd
    divided_2[1] = ed
    
    print(divided_2)
    # driver.get(url)
    # driver.find_element(by='css selector', value='#resolutionsAdoptedItems tbody tr:nth-child(4) :nth-child(5) a').text


def main():
    url = "https://lims.minneapolismn.gov/sessionstatistics/resolutionsadopted?fd=01%2F01%2F2022&ed=07%2F22%2F2022&pid=&page=2"
    get_all_urls(url=url, startdate='01/02/2022', enddate='07/23/2022')


if __name__ == "__main__":
    main()