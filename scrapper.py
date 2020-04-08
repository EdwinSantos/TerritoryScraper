from bs4 import BeautifulSoup
import requests
import pandas
import re
import os


def scrape_from_411(street_name):
    street_name = street_name.replace(" ", "+")
    url = 'https://www.canada411.ca/search/si/1/-/' + street_name + '+Brampton+ON/?pgLen=100'
    html_content = requests.get(url)
    content = BeautifulSoup(html_content.content, "html.parser")

    names = []
    phone_numbers = []
    street_names = []
    house_numbers = []

    for Name in content.findAll('h2', attrs={"class": "c411ListedName"}):
        names.append(Name.text)

    for PhoneNumber in content.findAll('span', attrs={"class": "c411Phone"}):
        phone_numbers.append(PhoneNumber.text)

    for Address in content.findAll('span', attrs={"class": "adr"}):
        house_numbers.append(int(re.search("\w*(?= )", Address.text).group(0)))
        street_names.append(re.search("\s(.*)", Address.text).group(0))

    df = pandas.DataFrame(data={"House Number": house_numbers, "Street Name": street_names,
                                "Phone Number": phone_numbers, "Name": names})
    df = df.sort_values(by='House Number')
    return df


def getInfoFromConsole():
    streetName = input("Enter the street name\n")
    df = scrape_from_411(streetName)
    df.to_csv(streetName + ".csv", sep=',', index=False)


def lookup_file(file_name):
    for full_file_name in os.listdir():
        if full_file_name.startswith(file_name):
            return full_file_name


def get_info_from_file():
    # Read the original territory and just keep the info that's important
    file_name = input("Enter the start of the file name in the format MyTerr if the full filename is MyTerritory.xls "
                      "\n You can enter the entire name if you wish but its just faster this way\n")
    full_file_name = lookup_file(file_name)

    original_territory = pandas.read_excel(full_file_name, skiprows=11)
    original_territory_address = original_territory.iloc[:, :3]
    original_territory_address.columns = ["House Number", "Street Name", "Symbol"]
    # Get rid of DNC, Witnesses ect.
    symbols_to_drop = original_territory_address[original_territory_address["Symbol"].isin(["JW", "DNC", "NE"])].index
    original_territory_address = original_territory_address.drop(symbols_to_drop, inplace=False)
    final_territory = pandas.DataFrame()
    # Send the individual streets to the scrapper
    unique_streets = original_territory_address["Street Name"].unique()
    for street in unique_streets:
        houses_on_street = original_territory_address.loc[original_territory_address["Street Name"] == street]
        joined_tables = pandas.merge(houses_on_street, scrape_from_411(street), how="left", on=["House Number", "House "
                                                                                                                "Number"])
        final_territory = final_territory.append(joined_tables)
    # output the results from the scrape to the territory
    final_territory = final_territory[final_territory['Phone Number'].notna()]
    final_territory = final_territory.drop(["Symbol", "Street Name_x"], 1)
    final_territory.to_csv(full_file_name + "WithPhoneNumbers.csv", sep=',', index=False)


def get_info_from_online_territory():
    # Havent setup to handle online territory
    print("This is still under construction")
    exit()


def main():
    inputFormat = input("Get phone numbers from \n 1. Territory on the web \n 2. Territory in file \n 3. Street\n eg. "
                        "if you want to use a territory you have saved as a file enter the number 2 on the line below"
                        " \n")
    if inputFormat == "1":
        get_info_from_online_territory()
    elif inputFormat == "2":
        get_info_from_file()
    elif inputFormat == "3":
        getInfoFromConsole()
    else:
        print("Please use one of the standard inputs")


if __name__ == "__main__": main()
