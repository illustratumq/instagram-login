import logging
import os
import random

import pyotp
import time
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from seleniumwire import webdriver as selwebdriver
from seleniumwire.handler import log as wire_log
from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.remote.webelement import WebElement
import pickle

log = logging.getLogger(__name__)
wire_log.setLevel(logging.WARNING)


@dataclass
class Button:
    login: tuple = 'xpath', '//*[@id="loginForm"]/div/div[1]/div/label/input'
    password: tuple = 'xpath', '//*[@id="loginForm"]/div/div[2]/div/label/input'
    entry: tuple = 'xpath', '//*[@id="loginForm"]/div/div[3]/button'
    accept_cookies: tuple = 'xpath', '//button[contains(text(), "Not Now")]'
    save_session: tuple = 'xpath', '//*[@id="react-root"]/section/main/div/div/div/div/button'
    new_media: str = 'xpath', '//button[contains(text(), "New post")]'
    select_file: tuple = 'xpath', "//*[contains(text(), 'Select from computer')]"
    input: tuple = 'tag name', 'input'
    next: tuple = 'xpath', '//button[contains(text(), "Next")]'
    caption: tuple = 'tag name', 'textarea'
    share: tuple = 'xpath', '//button[contains(text(), "Share")]'
    security: tuple = 'css selector', "[aria-label='Security Code']"
    confirm: tuple = 'xpath', "//*[contains(text(), 'Confirm')]"


class instagramLogin:

    login_url = 'https://www.instagram.com'
    cookies_form = '{}_cookies.pkl'

    def __init__(
            self,
            proxy: str = None,
            sleep: tuple = (5, 10),
            cookies_path: str = 'cookies'
    ):
        self.proxy = proxy
        self.sleep = sleep
        self.cookies_path = cookies_path
        self.browser = None
        self.button = Button()

    def set_browser(self):
        web = selwebdriver if isinstance(self.proxy, str) else webdriver
        self.browser = web.Chrome(executable_path='chromedriver.exe', **self.options())

    def options(self) -> dict:
        options = webdriver.ChromeOptions()
        # options.add_argument('--no-sandbox')
        options.add_argument("--lang=eng")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        result = dict(options=options)

        if isinstance(self.proxy, str):
            host, port, username, password, type_ = self.proxy.split(':')
            proxy = {
                'proxy': {
                    'https': f'{type_}://{username}:{password}@{host}:{port}'
                }
            }
            result.update(seleniumwire_options={}.update(proxy))
        return result

    def random_sleep(self):
        time.sleep(random.randint(*self.sleep))

    def is_exist(self, *args) -> bool:
        try:
            self.browser.find_element(*args)
            exist = True
        except NoSuchElementException:
            exist = False
        return exist

    def click(self, *args, browser: webdriver.Chrome, check_exist: bool = False):
        if check_exist:
            if not self.is_exist(*args):
                return
        browser.execute_script('arguments[0].click();', browser.find_element(*args))
        self.random_sleep()

    def confirmations(self, browser: webdriver.Chrome):
        self.click(*self.button.accept_cookies, browser=browser, check_exist=True)

    def save_cookies(self, browser: webdriver.Chrome, login: str):
        log.info(f'Save cookies for {login}')
        with open(Path(self.cookies_path, self.cookies_form.format(login)), mode='wb') as file:
            pickle.dump(browser.get_cookies(), file)
        self.random_sleep()

    def get_cookies(self, browser: webdriver.Chrome, login: str) -> webdriver.Chrome:
        log.info(f'Load cookies for {login}')
        with open(Path(self.cookies_path, self.cookies_form.format(login)), 'rb') as file:
            cookies = pickle.load(file)
            browser.delete_all_cookies()
            for cookie in cookies:
                browser.add_cookie(cookie)
            browser.refresh()
        self.random_sleep()
        self.confirmations(browser)
        return browser

    def is_cookies_exist(self, login: str):
        return self.cookies_form.format(login) in os.listdir(self.cookies_path)

    @staticmethod
    def close(browser: webdriver.Chrome):
        browser.close()
        browser.quit()

    def click_by_coordinates(self, browser: webdriver.Chrome, x: float, y: float):
        action = ActionChains(browser)
        action.move_by_offset(x, y)
        action.click()
        action.perform()
        self.random_sleep()

    @staticmethod
    def get_element_by_name(browser: webdriver.Chrome, name: str, tag: str) -> WebElement | None:
        buttons = browser.find_elements('tag name', tag)
        for b in buttons:
            try:
                if name in b.accessible_name:
                    return b
            except WebDriverException:
                pass

    @staticmethod
    def get_button_coordinates(browser: webdriver.Chrome, name: str) -> dict | None:
        buttons = browser.find_elements('tag name', 'button')
        for b in buttons:
            try:
                if b.accessible_name == name:
                    return b.location
            except WebDriverException:
                pass

    @staticmethod
    def get_button(browser: webdriver.Chrome, name: str) -> dict | None:
        buttons = browser.find_elements('tag name', 'button')
        for b in buttons:
            try:
                if b.accessible_name == name:
                    return b
            except WebDriverException:
                pass

    def login(self, login: str, password: str, key: str = None) -> webdriver.Chrome:
        """
        :param login: Instagram account login
        :param password: Instagram account password
        :param key: Instagram account 2fa key
        :return: Current browser state
        """
        log.info(f'Login {login}')
        self.set_browser()
        browser = self.browser
        browser.get(self.login_url)
        time.sleep(5)
        cookies = self.is_cookies_exist(login)
        if cookies:
            browser = self.get_cookies(browser, login)
            time.sleep(10)
            loc = self.get_button_coordinates(browser, 'New post')
            if loc:
                return browser
        browser.find_element(*self.button.login).send_keys(login)
        time.sleep(3)
        browser.find_element(*self.button.password).send_keys(password)
        self.random_sleep()
        browser.find_element(*self.button.entry).send_keys(Keys.ENTER)
        time.sleep(10)
        if key:
            button = browser.find_element(*self.button.security)
            if button is not None:
                button.send_keys(pyotp.TOTP(key.replace(' ', '')).now())
                self.click(*self.button.confirm, browser=browser)
                self.random_sleep()
                self.save_cookies(browser, login)
        self.confirmations(browser)
        if not cookies:
            self.save_cookies(browser, login)
        log.info(f'Successfully login for {login}')
        return browser


instagramLogin().login('admin', 'admin')