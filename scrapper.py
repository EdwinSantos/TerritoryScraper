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


def correct_street_name(street_name):
    # Fix street type because white pages is trash
    street_type = re.search("\s*([\S]+)$", street_name).group(0).lstrip().lower()
    street_name_sans_type = re.sub("\s*([\S]+)$", "", street_name)
    if street_type in street_dict:
        street_type = street_dict[street_type]
    street_name = street_name_sans_type + " " + street_type
    street_name = street_name.replace(" ", "+")
    return street_name


def scrape_from_WhitePagesCanada(street_name, houses_on_street, city_name):
    print("Looking up people on" + street_name)
    whole_street = not houses_on_street
    street_name = correct_street_name(street_name)
    # Scrape from this URL
    original_url = "https://www.whitepagescanada.ca/dir/address_search.php?txtaddress=" + street_name + "&city=" + \
                   city_name + "&prov=ON&page="
    collected_all_pages = False
    page_counter = 1
    person_url = list()
    # Collect all the URL's for people on that street
    while collected_all_pages is False:
        print("Scanning Page " + str(page_counter))
        first_div = True
        url = original_url + str(page_counter)
        print(url)
        html_content = requests.get(url)
        content = BeautifulSoup(html_content.content, "html.parser")
        # Check if I reached the last page
        for page in content.findAll('div', attrs={"class": "eleven columns"}):
            if "No record found.Please try searching different keyword." in page.text:
                print("Reached last page")
                collected_all_pages = True
                break
        for person in content.findAll('a', attrs={"style": "color:#333; font-size:16px; text-decoration:none"}):
            house_number, street_name, unit_number = split_address(person.text)
            if (house_number in houses_on_street) or whole_street:
                person_url.append(person.get("href"))
        page_counter = page_counter + 1
    people = list()
    print("Collecting all of the personal information")
    for url in person_url:
        print(url)
        html_content = requests.get(url)
        content = BeautifulSoup(html_content.content, "html.parser")
        telephone = content.find('span', attrs={"itemprop": "telephone"})
        address = content.find('span', attrs={"itemprop": "streetAddress"})
        name = content.find('span', attrs={"itemprop": "name"})
        house_number, street_name, unit_number = split_address(address.text)
        people.append([house_number, unit_number, street_name, telephone.text, name.text])

    scrape_results = pandas.DataFrame.from_records(people, columns=["House Number", "Unit Number", "Address",
                                                                    "Phone Number", "Name"])
    return scrape_results


def scrape_from_411(street_name, houses_on_street, city_name):
    print("Looking up " + street_name + " on 411")
    whole_street = not houses_on_street
    street_name = street_name.replace(" ", "+")
    url = 'https://www.canada411.ca/search/si/1/-/' + street_name + '+Brampton+ON/?pgLen=100'
    print(url)
    html_content = requests.get(url)
    content = BeautifulSoup(html_content.content, "html.parser")

    people = list()

    for FullPerson in content.findAll('div', attrs={"class": "c411Listing jsResultsList"}):
        phone_number = FullPerson.find('span', attrs={"class": "c411Phone"}).text
        name = FullPerson.find('h2', attrs={"class": "c411ListedName"}).string
        full_address = FullPerson.find('span', attrs={"class": "adr"}).text
        short_address = full_address.partition(" Brampton")[0]
        house_number, street_name, unit_number = split_address(short_address)
        if (house_number in houses_on_street) or whole_street:
            people.append([house_number, unit_number, street_name, phone_number, name])
    scrape_results = pandas.DataFrame.from_records(people, columns=["House Number", "Unit Number", "Address",
                                                                    "Phone Number", "Name"])
    return scrape_results


def split_address(address):
    unit_number = re.search("^(.+?)-", address)
    if unit_number is not None:
        address = address.replace(unit_number.group(0), "")
        unit_number = unit_number.group(0)[:-1]
    house_number = int(re.search("\d+", address).group(0))
    street_name = re.search("\s(.*)", address).group(0)
    return house_number, street_name, unit_number


def getInfoFromConsole():
    city_name = input("Enter the city name \n")
    street_name = input("Enter the street name\n")
    scrape_from_411_results = scrape_from_411(street_name, [], city_name)
    scrape_from_whitepagescanada_results = scrape_from_WhitePagesCanada(street_name, [], city_name)
    scraped_tables = pandas.concat([scrape_from_411_results, scrape_from_whitepagescanada_results])
    scraped_tables = scraped_tables.drop_duplicates(subset=["House Number", "Phone Number"])
    final_df = scraped_tables.sort_values(["House Number", "Unit Number"], ascending=[True, True])
    # Scrape from both and send the results to another method to do the merging
    final_df.to_csv(street_name + ".csv", sep=',', index=False)


def lookup_file(file_name):
    for full_file_name in os.listdir():
        if full_file_name.startswith(file_name):
            return full_file_name


def get_info_from_file():
    city_name = input("Enter the city name \n")
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
        all_entries_on_street = original_territory_address.loc[original_territory_address["Street Name"] == street]
        houses_on_street = all_entries_on_street["House Number"].tolist()

        df_canada_white_pages = scrape_from_WhitePagesCanada(street, houses_on_street, city_name)
        df_411 = scrape_from_411(street, houses_on_street, city_name)

        scraped_tables = pandas.concat([df_canada_white_pages, df_411])
        scraped_tables = scraped_tables.drop_duplicates(subset=["House Number", "Phone Number"])
        print("Removed the duplicates")
        scraped_tables_sorted = scraped_tables.sort_values(["House Number", "Unit Number"], ascending=[True, True])
        final_territory = final_territory.append(scraped_tables_sorted)
    # output the results from the scrape to the territory
    final_territory = final_territory[final_territory['Phone Number'].notna()]
    final_territory.to_csv(full_file_name + "WithPhoneNumbers.csv", sep=',', index=False)


def get_info_from_online_territory():
    # Havent setup to handle online territory yet
    print("This is still under construction")
    exit()


def main():
    input_type = input("Get phone numbers from \n 1. Territory on the web \n 2. Territory in file \n 3. Street\n eg. "
                       "if you want to use a territory you have saved as a file enter the number 2 on the line below"
                       " \n")
    if input_type == "1":
        get_info_from_online_territory()
    elif input_type == "2":
        get_info_from_file()
    elif input_type == "3":
        getInfoFromConsole()
    else:
        print("Please use one of the standard inputs")
        main()


if __name__ == "__main__": main()
