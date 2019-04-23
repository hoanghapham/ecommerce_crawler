import pandas as pd
import numpy as np
import requests
import os
import time
import datetime
import random

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Replace account's username & password here
username = os.environ['vipon_username']
password = os.environ['vipon_password']

class ViponCrawler:
    
    def __init__(self, username, password):
        
        print('Initating...', end='\n')
        display = Display(size=(800,600), visible=False)
        display.start()
        
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 20)
        self.deals_url = 'https://www.vipon.com/promotion/index?type=instant'
        self.code_base_url = 'https://www.vipon.com/code/get-code?id={}'
        self.username = username
        self.password = password
        
    def login(self):
        
        print('Logging in...', end='\n')
        self.driver.get('https://www.vipon.com/login?ref=menu_login_mobile')

        form_email = self.driver.find_element_by_css_selector('input[id="loginform-email"]')
        form_email.send_keys(self.username)
        form_password = self.driver.find_element_by_css_selector('input[id="loginform-password"]')
        form_password.send_keys(self.password)
        submit_button = self.driver.find_element_by_css_selector('button[type="submit"]')
        submit_button.click()
        
    def get_link_count(self):
        deals_soup = BeautifulSoup(self.driver.page_source, 'lxml')
        elm_count = len(deals_soup.select('div .layer'))
        return elm_count
    
    def get_links(self, max_link_count=200):
        
        print('Getting links...', end='\n')
        self.driver.get(self.deals_url)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div .layer')), 'Timeout.')

        last_link_count = 0

        while last_link_count < max_link_count:

            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')

            try:
                self.wait.until(lambda driver: last_link_count < self.get_link_count(), "Timeout")
            except TimeoutException:
                print('Cannot get more links')
                pass

            last_link_count = self.get_link_count()
    
        deals_soup = BeautifulSoup(self.driver.page_source, 'lxml')
        prod_elms = deals_soup.select('div .layer')
        prod_urls = [x.get('onclick').split('\'')[1] for x in prod_elms]
        print('Links get: {}'.format(len(prod_urls)))
        
        self.prod_urls = prod_urls
        
    def parse_info(self, get_code=False):

        self.data_dict = {
            'product_id': []
            , 'title': []
            , 'category': []
            , 'like': []
            , 'dislike': []
            , 'discount': []
            , 'code': []
            , 'expiry_time': []
            , 'list_price': []
            , 'sales_price': []
            , 'amazon_url': []
        }

        for counter, url in enumerate(self.prod_urls):
            
            print('Checking link {} of {}'.format(counter + 1, len(self.prod_urls)), end = '\r')
            
            self.driver.get(url)
            prod_soup = BeautifulSoup(self.driver.page_source, 'lxml')

            # Basic information
            product_id = pd.to_numeric(url.split('/')[-1])

            title = prod_soup.select('p[class=product-title]')[0] \
                                .getText(strip=True, separator = ',')

            category, dislike, like = prod_soup.select('div .product-category')[0] \
                                            .getText(strip=True, separator=';').split(';')

            discount = prod_soup.select('p[class=product-discount]')[0] \
                                .getText(strip=True, separator = ',')

            expiry_time = prod_soup.select('span[id=productExpiry]')[0] \
                                    .select('b')[0].getText()

            list_price, sales_price = prod_soup.select('p[class=product-price]')[0] \
                                                .getText(strip=True, separator = ',').split(',')

            amazon_url = prod_soup.select('a[onclick="bing_open_in_amazon();"]')[0] \
                                    .get('href')
            
            self.data_dict['product_id'].append(product_id)
            self.data_dict['title'].append(title)
            self.data_dict['category'].append(category)
            self.data_dict['like'].append(pd.to_numeric(like))
            self.data_dict['dislike'].append(pd.to_numeric(dislike))
            self.data_dict['discount'].append(discount)
            self.data_dict['expiry_time'].append(expiry_time)
            self.data_dict['list_price'].append(list_price)
            self.data_dict['sales_price'].append(sales_price)
            self.data_dict['amazon_url'].append(amazon_url)
            
            time.sleep(random.randint(2, 10))
            
            # Get code
            if get_code == True:
                self.login()
                code_url = self.code_base_url.format(product_id)
                self.driver.get(code_url)
                code_soup = BeautifulSoup(self.driver.page_source, 'lxml')
                try:
                    code = code_soup.select('div .code-container')[0] \
                            .getText(separator=',', strip=True) \
                            .split(',')[-1]
                except IndexError:
                    code = np.nan
            else:
                code = np.nan
                
            self.data_dict['code'].append(code)
            
            time.sleep(random.randint(2, 10))
            
        self.deals_info = pd.DataFrame(self.data_dict)
        self.deals_info['crawl_date'] = datetime.date.today()
        print('Finished.', end='\n')

if __name__ == '__main__':
    crawler = ViponCrawler(username, password)
    crawler.get_links(max_link_count=20)
    crawler.parse_info(get_code=False)

    crawler.deals_info.to_csv(
        'deals_info_{}.csv'.format(datetime.date.strftime(datetime.date.today(), '%Y%m%d'))
        , index=False
    )
