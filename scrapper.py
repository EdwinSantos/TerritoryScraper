from bs4 import BeautifulSoup
import requests
import pandas
import re

streetName = input("Enter the street name\n")
streetName = streetName.replace(" ", "+")
url = 'https://www.canada411.ca/search/si/1/-/' + streetName + '+Brampton+ON/?pgLen=50'
htmlContent = requests.get(url)
content = BeautifulSoup(htmlContent.content, "html.parser")

Names = []
Numbers = []
Addresses = []

for Name in content.findAll('h2', attrs={"class": "c411ListedName"}):
    Names.append(Name.text)

for Number in content.findAll('span', attrs={"class": "c411Phone"}):
    Numbers.append(Number.text)

for Address in content.findAll('span', attrs={"class": "adr"}):
    Addresses.append(int(re.search("\w*(?= )", Address.text).group(0)))

df = pandas.DataFrame(data={"Addresses": Addresses, "Number": Numbers, "Name": Names})
df = df.sort_values(by='Addresses')
df.to_csv( streetName + ".csv", sep=',', index=False)
