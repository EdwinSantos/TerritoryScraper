from bs4 import BeautifulSoup
import requests
import pandas
import re
import os

# Had to add a dictionary to change street types because white pages canada search is hot garbage
street_dict = {
    "avenue": "ave",
    "boulevard": "blvd",
    "circle": "cir",
    "court": "crt",
    "drive": "dr",
    "mountain": "mtn",
    "park": "pk",
    "parkway": "pky",
    "place": "pl",
    "road": "rd",
    "route": "rte",
    "square": "sq",
    "street": "st",
}


def scrape_from_WhitePagesCanada(street_name):
    print("Looking up people on" + street_name)

    # Fix street type because white pages is trash
    street_type = re.search("\s*([\S]+)$", street_name).group(0).lstrip().lower()
    street_name_sans_type = re.sub("\s*([\S]+)$", "", street_name)
    if street_type in street_dict:
        street_type = street_dict[street_type]
    street_name = street_name_sans_type + " " + street_type
    street_name = street_name.replace(" ", "+")

    # Scrape from this URL
    original_url = "https://www.whitepagescanada.ca/dir/address_search.php?txtaddress=" + street_name + "&city=Brampton&prov=ON&page="
    collected_all_pages = False
    counter = 1
    person_url = list()
    # Collect all the URL's for people on that street
    print("Finding all the people who live on " + street_name)
    while collected_all_pages is not True:
        print("Scanning Page " + str(counter))
        first_div = True
        url = original_url + str(counter)
        print(url)
        html_content = requests.get(url)
        content = BeautifulSoup(html_content.content, "html.parser")
        # Check if I reached the last page
        for page in content.findAll('div', attrs={"class": "eleven columns"}):
            if first_div:
                first_div = False
                continue
            if "No record found" in page.text:
                collected_all_pages = True
                break
        for person in content.findAll('a', attrs={"class": "rsslink-m"}):
            person_url.append(person.get("href"))
        counter = counter + 1
    people = list()
    print("Collecting all of the personal information")
    for url in person_url:
        print(url)
        html_content = requests.get(url)
        content = BeautifulSoup(html_content.content, "html.parser")
        telephone = content.find('span', attrs={"itemprop": "telephone"})
        address = content.find('span', attrs={"itemprop": "streetAddress"})
        name = content.find('span', attrs={"itemprop": "name"})
        house_number = int(re.search("\w*(?= )", address.text).group(0))
        street_name = re.search("\s(.*)", address.text).group(0)
        people.append([house_number, street_name, telephone.text, name.text])

    scrape_results = pandas.DataFrame.from_records(people, columns=["House Number", "Address", "Phone Number", "Name"])
    return scrape_results


# Clean up to use the standard data formatting used by WhitePages
def scrape_from_411(street_name):
    print("Looking up " + street_name + " on 411")
    street_name = street_name.replace(" ", "+")
    url = 'https://www.canada411.ca/search/si/1/-/' + street_name + '+Brampton+ON/?pgLen=100'
    print(url)
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

    df = pandas.DataFrame(data={"House Number": house_numbers, "Address": street_names,
                                "Phone Number": phone_numbers, "Name": names})
    return df


def getInfoFromConsole():
    streetName = input("Enter the street name\n")
    scrape_from_411_results = scrape_from_411(streetName)
    scrape_from_whitepagescanada_results = scrape_from_WhitePagesCanada(streetName)
    scraped_tables = pandas.concat([scrape_from_411_results, scrape_from_whitepagescanada_results])
    print("Concatinated Tables")
    print(scraped_tables)
    scraped_tables = scraped_tables.drop_duplicates(subset=["House Number", "Phone Number"])
    final_df = scraped_tables.sort_values("House Number")
    # Scrape from both and send the results to another method to do the merging
    final_df.to_csv(streetName + ".csv", sep=',', index=False)


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
        df_canada_white_pages = scrape_from_WhitePagesCanada(street)
        df_411 = scrape_from_411(street)
        scraped_tables = pandas.concat([df_canada_white_pages, df_411])
        print("Concatinated Tables")
        print(scraped_tables)
        scraped_tables = scraped_tables.drop_duplicates(subset=["House Number", "Phone Number"])
        print("Removed the duplicates")
        print(scraped_tables)
        joined_tables = pandas.merge(houses_on_street, scraped_tables, how="left", on=["House Number", "House Number"])
        joined_tables_sorted = joined_tables.sort_values("House Number")
        final_territory = final_territory.append(joined_tables_sorted)
    # output the results from the scrape to the territory
    final_territory = final_territory[final_territory['Phone Number'].notna()]
    final_territory = final_territory.drop(["Symbol", "Address"], 1)
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
    elif inputFormat == "0":
        # Debug mode
        scrape_from_WhitePagesCanada("Montjoy")
    else:
        print("Please use one of the standard inputs")


if __name__ == "__main__": main()
