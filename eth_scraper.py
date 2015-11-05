from __future__ import division
import os, sys, time
from bs4 import BeautifulSoup
from urllib2 import urlopen
import re 
import pandas as pd
import logging
import re
import pickle

tot_order = {} #Global total order dictionary. Could have been a class variable I guess
irregular_parse = False  #Global boolean to check if page is improperly formatted

#Define the root loggers
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler("scraper.log", encoding="utf-8"))

def scrape_item_list(node, cur_path, checkFormatting, unclassified):
    """
    Recursively scrape an item list to retrieve total order 
    """
    try:
        if node is not None:
            temp = node.find("div", class_ = "item-list")
            temp1 = node.find_all("div", class_ = "item-list", recursive = False)
            # Handle temp1
            pattern = re.compile("^\d+$")
            cur_path_check = re.match(pattern, cur_path) 
            global irregular_parse
            global tot_order
            tot_l = 0
            if temp is None:
                #In the last level
                #Check if it has any languages in it
                if node.a is not None:
                    lang_code = node.a.text.strip("[").strip("]")
                    if lang_code not in tot_order:
                        tot_order[lang_code] = cur_path
                        if checkFormatting:
                            # There was a language in the irregular parsed section
                            irregular_parse = True
            else:
                #There are subcategories
                li_list = temp.ul.find_all("li", recursive = False)
                for l, li in enumerate(li_list):
                    if ((cur_path_check is not None) and (irregular_parse)):
                        #Increment all subgroup counts by 1 as the first was irregularly parsed
                        scrape_item_list(li, cur_path + "." + str(l+2), False, unclassified)
                    elif (unclassified):
                        scrape_item_list(li, cur_path + str(l+1), False, unclassified)
                    else:
                        scrape_item_list(li, cur_path + "." + str(l+1), False, unclassified)
                tot_l = len(li_list)

            #Handle temp1
            if (len(temp1) != 0) and (temp1[0] != temp):
                li_list = temp1[0].ul.find_all("li", recursive = False)
                for l1, li in enumerate(li_list):
                    scrape_item_list(li, cur_path + "." + str(tot_l + l1), False, unclassified)
    except:
        logger.exception("Something went wrong")
        pass

def scrape():
    """
    Extracts a total ordering on language family information from ethnologue
    Returns: Dictionary mapping language code to ordering number
    """
    BASE_URL = "https://www.ethnologue.com/"
    LINK = "https://www.ethnologue.com/browse/families"

    try:
        req = urlopen(LINK)
        soup = BeautifulSoup(req)
    except:
        logger.exception("Check the url")
        sys.exit(1)

    #Get the language family table
    top_level_count = 0
    table = soup.find(lambda tag: tag.name == "table" and tag.has_attr("class") \
            and tag["class"] == ["views-view-grid", "cols-4"])
    links = table.find_all(lambda tag: tag.name == "a" and "subgroup" in tag.get("href"))
    uniq_links = set(links)
    for link in links:
        subgrp_url = link.get("href")
        top_level_count += 1
        #time.sleep(1) #Sleep for a second to avoid ip blocking
        try:
            unclassified = False
            if "unclassified" in subgrp_url:
                unclassified = True 

            subgrp_req = urlopen(BASE_URL+subgrp_url)
            subgrp_soup = BeautifulSoup(subgrp_req)
            global irregular_parse
            pre_content_box = subgrp_soup.find("div", class_ = "view view-family view-id-family view-display-id-attachment_1 indent1")
            logger.info("Starting pre-content_box scraping for page {}".format(subgrp_url))
            scrape_item_list(pre_content_box, str(top_level_count), True, unclassified)
            logger.info("Finished scraping the pre-content box for page {}".format(subgrp_url))
            if irregular_parse:
                logger.info("The page {} was improperly formatted".format(subgrp_url))
            
            content_box = subgrp_soup.find("div", class_="view-content indent1")
            if content_box is None:
                content_box = subgrp_soup.find("div", class_="view-content indent0")
            logger.info("Starting content_box scraping for page {}".format(subgrp_url))
            scrape_item_list(content_box, str(top_level_count), False, unclassified)
            logger.info("Finished content_box scraping page {}".format(subgrp_url))
            irregular_parse = False #set it back to false again
        except:
            logger.exception("Something went wrong with url {}".format(subgrp_url))

    #Pickle the total_order dictionary
    logger.info("Pickling the dictionary now")
    pickle.dump(tot_order, open("tot_order.pickle", "wb"))
    print "Finished"


if __name__ == '__main__':
    scrape()