import requests as r

response = r.get("https://lims.minneapolismn.gov/Calendar/GetCalenderList?fromDate=Jun 26, 2022&toDate=Aug 1, 2022&meetingType=0&committeeId=null&pageCount=1000&offsetStart=0&abbreviation=undefined&keywords=")
committees = response.json()
print(committees[1])
