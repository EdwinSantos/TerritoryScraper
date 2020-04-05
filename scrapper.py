from bs4 import BeautifulSoup
import requests
import pandas
import re


def scrapeFrom411(streetName):
    streetName = streetName.replace(" ", "+")
    url = 'https://www.canada411.ca/search/si/1/-/' + streetName + '+Brampton+ON/?pgLen=50'
    htmlContent = requests.get(url)
    content = BeautifulSoup(htmlContent.content, "html.parser")

    names = []
    phoneNumbers = []
    streetNames = []
    houseNumbers = []

    for Name in content.findAll('h2', attrs={"class": "c411ListedName"}):
        names.append(Name.text)

    for PhoneNumber in content.findAll('span', attrs={"class": "c411Phone"}):
        phoneNumbers.append(PhoneNumber.text)

    for Address in content.findAll('span', attrs={"class": "adr"}):
        houseNumbers.append(int(re.search("\w*(?= )", Address.text).group(0)))
        streetNames.append(re.search("\s(.*)", Address.text).group(0))

    df = pandas.DataFrame(data={"House Number": houseNumbers, "Street Name": streetNames, "Phone Number": phoneNumbers,
                                "Name": names})
    df = df.sort_values(by='House Number')
    return df


def getInfoFromConsole():
    streetName = input("Enter the street name\n")
    df = scrapeFrom411(streetName)
    df.to_csv(streetName + ".csv", sep=',', index=False)


def getInfoFromFile():
    fileName = input("Enter the file name in the format MyTerritory.csv\n")
    originalDataFrame = pandas.read_excel(fileName, skiprows=11)
    address = originalDataFrame.iloc[:, :3]
    address.columns = ["House Number", "Street Name", "Symbol"]
    indexNames = address[address["Symbol"].isin(["JW", "DNC", "NE"])].index
    address = address.drop(indexNames, inplace=False)
    phonebooksResults = pandas.DataFrame()
    # Get unique values of streets
    uniqueStreets = address["Street Name"].unique()
    for street in uniqueStreets:
        housesOnStreet = address.loc[address["Street Name"] == street]
        tempDF = pandas.merge(housesOnStreet, scrapeFrom411(street), how="left", on=["House Number", "House Number"])
        phonebooksResults = phonebooksResults.append(tempDF)
    # output the results from the scrape to the territory
    phonebooksResults = phonebooksResults[phonebooksResults['Phone Number'].notna()]
    phonebooksResults.to_csv(fileName + "WithPhoneNumbers.csv", sep=',', index=False)


def getInfoFromOnlineTerritory():
    # Havent setup to handle online territory
    return 1


def main():
    inputFormat = input("Get phone numbers from \n 1. Territory on the web \n 2. Territory in file \n 3. Street\n")
    if inputFormat == "1":
        getInfoFromOnlineTerritory()
    elif inputFormat == "2":
        getInfoFromFile()
    elif inputFormat == "3":
        getInfoFromConsole()
    else:
        print("Please use one of the standard inputs")


if __name__ == "__main__": main()
