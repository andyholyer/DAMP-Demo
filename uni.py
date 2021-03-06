#!/usr/bin/env python
# This library is called from scraper.py. Crucially it contains the (boringly 
# named) method "process"

# BeautifulSoup is a library which lets us scrape HTML (and other) documents
from bs4 import BeautifulSoup
# The Regular Expression library
import re
# The Python interface to the Google Maps libraries
import googlemaps
# Requests is a library to fetch documents using http, like a web browser, but 
# under program control
import requests
# I may not still use the pretty printing library but I read it in anyway
import pprint
# Library to control the language and location where the program is being run
import locale

# Tell Python to use UK English (principally for currency formats etc.)
locale.setlocale(locale.LC_ALL, 'en_GB')

# Not used much at the moment, but config.py stores unsernames and passwords 
# slightly more securely than having them littered all through the source code
# What it does contain which we use is my Googlemaps key
import config

# This is a Regular Expression to mathc a UK post code. We compile it because 
# that way it'll run a bit faster, which since it'll be used for all 170+ 
# universities will speed things up a lot
postcode = re.compile('\b([A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2})\b')

# Connect to Googlemaps using my key. 
# Please get your own key by going here: 
# https://developers.google.com/maps/documentation/javascript/get-api-key
# It's free to get a key, with a limit of a few thousand fetches per day. You 
# would need to pay for an account if you were going to use Google Maps 
# commercially.
gmaps = googlemaps.Client( key = config.g_key)

# This is the base URL we are scraping. Would be better to have it in config.py
list_url = 'https://www.thecompleteuniversityguide.co.uk'

# This is a RegExp to trap price range from the University pages. Again, we 
# compile it for speed
pricerange = re.compile('from.*([0-9,]+).*to.*([0-9,]+).*per (year|month|week)', re.DOTALL)

# This is the main function which is used outside of this module. 
# My original comment read...
# Do stuff with the University link
# ...and i think that sums it up quite well. 
# It's passed the (relative) URL of an individual University's page on The Complete University 
# Guide, and fetches that page to look for the postcode, which it then converts to latitude and 
# longitude, and then goes to the "Living Here" page to scrape the range of prices of 
# accomodation. Phew!
def process(url):
    
    # Make up the full URL by concatenating the complete Uni Guide's URL with the relative one
    uni_url = list_url + url
    
    # 'loc' is a routine whic his defined just a few lines lower down from here. It fetches the 
    # page and then finds the name of the university and gets its address, whic it then convers 
    # into latitude and logitude
    loc_title = loc(uni_url)
    
    pprint.pprint(loc_title) # This is a debugging statement which I leave in to make sure I know 
                             # what the scraper is doing while it's running. If it;s deleted the 
                             # whole thing runs much, much faster 
    
    # 'costs' is another routine defined below. It goes to the apprpriate page and extracts the 
    # correct costs of accomodation
    cost_dict = costs(uni_url)
    
    pprint.pprint(cost_dict) # Another debugging statemet, left in.

#   For now, we only want the highest of the possible values in the cost dictionary returned
    dearest = 0
    # Not all universities tell us the cost of accommodation: if they haven't, just skip this bit 
    # and record a "0" under the cost. I originally skipped these entries completely, but some 
    # major universities (including Oxford and Cambridge) leave this off their page (in the case 
    # of Oxbridge I guess because every college charges a different amount and it's just too 
    # complicated), and if Oxford and Cambridge are missing from the map it just looks odd
    if cost_dict:
        # Typically there are four results returned: catered (low), catered (high), self 
        # catering(low) and self catering (high). I'm hoing nobody gets the numbers in the wrong 
        # order so I just go through looking for the highest at all.
        # In software engineering terms it would be better to keep all of this data as late as 
        # possible, and only take the highest one out at the last possible moment, such as in the 
        # front end - but that's not what I did and it's a bit late now. Maybe after a refactor.
        for c in cost_dict:
            if c['high'] > dearest:
                dearest = c['high']
                
    # It's possible we can't find either the name of the University or its location, in which case 
    # all bets are off, and we return nothing. Otherwise, return a record, which will become 
    # familiar as we go further through the system...                
    if loc_title:
        # Return the structure for this University
        # This is a Python dictionary - se how similar it is to JSON...
        return {
            'label':    loc_title['label'],
            'lat':      loc_title['loc']['lat'],
            'lng':      loc_title['loc']['lng'],
            'cost':     dearest,
            'url':      uni_url
        }

# This function handles scraping the location-related features of the University
# Coding style hint: The comment following the declaration is what I'd typically put in
# production code - in fact it was the first thing I wrote, then I filled in the 
# actual program code.
def loc(url):
    #    What we want to do is the following:
    #    From each university, find out its lattitude and logitude
    #    We do this by Scraping the Postcode from 
    #    https://www.thecompleteuniversityguide.co.uk/portsmouth/
    #    and then by using the googlemaps library
    #    to get the cooordinates from the postcode.
    
    # In scraper.py we've seen this sort of thing stretched out further, but this is 
    # the "compact" way of doing it. 
    # What we're doing is this:
    # * requests.get(url) fetches the page from the website
    # * ().text returns the text - tha tis, the HTML source of that
    # The call to BeautifulSoup applies the HTML parser to this text, and returns a
    # BeautifulSoup object whichwe're going to do something with, in a minute...
    uni_page = BeautifulSoup(requests.get(url).text, "html.parser")
    
    # You know I compiled a regular expression for postcodes up above? Well, I couldn't work out
    # how to include this in the BS syntax, so I have to compile it again. Pity.
    # This searches for the first occasion of a Postcode in the text.
    addr = uni_page.find(string=re.compile('([A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2})'))
#    print addr
    
    # Not all Complete Uni Guide pages have the address - it looks to me that each university 
    # writes the page by hand, so you do get odd omissions on particular ones.
    # So I'm checking that we actually did match a postcode just now
    if (not addr):
        return (None)
    
    # Still here? We must have matched something in the address then...
    
    # While we're here, grab the label
    
    # This RegExp is a bit dodgy, it wants a letter, followed by anything which is not a comma at 
    # the start of the field. But it works, so I'm leaving it as is
    label = re.search('(\w[^,]+)', addr).group(1)
    
    # Now use Google to find the latitude and longitude...
    # The Geocoding routine will take anything which sort of makes an address, and returns 
    # this JSON, out of which we want lat and lng (this is the return from an example in the docs)
    #{
    #  "results" : [
    #   {
    #     "address_components" : [
    #        {
    #           "long_name" : "Winnetka",
    #           "short_name" : "Winnetka",
    #           "types" : [ "locality", "political" ]
    #        },
    #        {
    #           "long_name" : "New Trier",
    #           "short_name" : "New Trier",
    #           "types" : [ "administrative_area_level_3", "political" ]
    #        },
    #        {
    #           "long_name" : "Cook County",
    #           "short_name" : "Cook County",
    #           "types" : [ "administrative_area_level_2", "political" ]
    #        },
    #        {
    #           "long_name" : "Illinois",
    #           "short_name" : "IL",
    #           "types" : [ "administrative_area_level_1", "political" ]
    #        },
    #        {
    #           "long_name" : "United States",
    #           "short_name" : "US",
    #           "types" : [ "country", "political" ]
    #        }
    #     ],
    #     "formatted_address" : "Winnetka, IL, USA",
    #     "geometry" : {
    #        "bounds" : {
    #           "northeast" : {
    #              "lat" : 42.1282269,
    #              "lng" : -87.7108162
    #           },
    #           "southwest" : {
    #              "lat" : 42.0886089,
    #              "lng" : -87.7708629
    #           }
    #        },
    #        "location" : {
    #           "lat" : 42.10808340000001,
    #           "lng" : -87.735895
    #        },
    #        "location_type" : "APPROXIMATE",
    #        "viewport" : {
    #           "northeast" : {
    #              "lat" : 42.1282269,
    #              "lng" : -87.7108162
    #           },
    #           "southwest" : {
    #              "lat" : 42.0886089,
    #              "lng" : -87.7708629
    #           }
    #        }
    #     },
    #     "place_id" : "ChIJW8Va5TnED4gRY91Ng47qy3Q",
    #     "types" : [ "locality", "political" ]
    #     }
    #   ],
    #   "status" : "OK"
    # }
    # ... so you see there's lots of info returned
    geocode = gmaps.geocode(addr)
    
    # We only want a little bit of the information, the lat and lng values...
    loc = geocode[0]['geometry']['location']
    
    # This next line is just for debugging....
#   pprint.pprint(loc)
    # And now we return the name of the University, and its latitude and longitude
    # I'm ignoring cases where Universites have several campuses, (that would be good to 
    # capture in a later version)
    return { 
                'label': label,
                'loc': loc
           }

# This routine scrapes the "Living Here" page (fetch it in a browser to see what we're working 
# with), and fetches out the accommodation costs 
def costs(url):
    # Now we need to fetch the .../local page - which should have the costs
    # Then extract the amount from it using regexp
    
    local_url = url + 'local'

    # This fetches the page from the websitem and extracts the HTML text
    local_html = requests.get(local_url).text

    # Parse it using BeautifulSoup, and return the BS object
    local_dom = BeautifulSoup(local_html, "html.parser")

    # It would be nice if I could compile this RegExp once, but not to be...
    # But I use it below...
    # Note that '\xa3' is a 'pound' sign..
    cost_re = re.compile('from \xa3([\d,]+).*to \xa3([\d,]+).*per (week|month|year)', re.DOTALL)
    # So I have to do it like this...
    # Looks for all the lines which say "From (pounds)100 to (pounds)290 per week" etc.
    cost = local_dom.find_all(string=re.compile('from \xa3([\d,]+).*to \xa3([\d,]+).*per (week|month|year)', re.DOTALL))
    
    # Not all institutions list the accomodation costs in which case return a blank response... 
    if (not cost):
        return [{'low': 0, 'high': 0, 'per': 'month'}]
    
    # Another debugging statement...
  #  pprint.pprint(cost)
    
    # Make an emply array to keep the results...
    list = []
    # 'cost' is an array of results (maybe with only one entry) so we need to iterate through it
    for c in cost:
        
        # Using the regexp I compiled above, match the row, and return the groups which are in the 
        # Regexp in (brackets). There are three groups in the regexp, so we do three
        # variable assignments in one statement. Neat, huh?
        (low, high, per) = cost_re.search(c).groups()
        # Convert 'low' and 'high' from strings to floating point numbers using the UK locale
        # That is, in the UK we write 1,370.74 whereas in France (say) they write 1 370,74
        # By using the library funtion here we're reasonably assured of getting it right in all 
        # circumstances, which is probably not the case were I to hand-roll the function
        low = locale.atof(low)
        high = locale.atof(high)
        
        # On reflection, I'm probably doing some institutions a disservice since I'm assuming 
        # students pay for 52 weeks of the year, when I bet most of them only pay for about 30, 
        # and for 12 months per year, when I'm sure most places only charge for 9.
        # However this is the point when it gets complicated, so I'm gonig to leave it as is
        # since this is only a demonstrator
        
        # Some institutions display costs per week...
        if (per == 'week'):
            low = round(low*52/12, 2)
            high = round(high*52/12, 2)
            per = 'month'
        # And some do it per year...
        elif (per == 'year'):
            low = round(low/12, 2)
            high = round(high/12, 2)
            per = 'month'
        
        # We've now corrected the values, so push them onto the end of our temporary list
        # (and loop back to line 263)
        list.append({"low": low, "high" : high, "per": per})
    
    
    # And then return the completed list
    return list
