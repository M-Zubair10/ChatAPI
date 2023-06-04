import logging
import os
import re
import time
from threading import Event

import selenium.common.exceptions as Exceptions
# from seleniumbase import Driver
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from .tools import multiWait


class Poe:
    """ChatGPT_Client class to interact with ChatGPT"""

    universal_link_xq = '//a[text()="Talk to Sage"]'
    continue_with_google_xq = '//button[text()="Continue with Google"]'
    email_xq = '//*[@type="email"]'
    password_xq = '//*[@aria-label="Enter your password"]'
    retry_password_xq = '//*[contains(text(), "Wrong password")]'
    next_xq = '//*[text()="Next"]'

    button_tq = 'button'
    # next_xq     = '//button[//div[text()='Next']]'
    done_xq = '//button[//div[text()="Done"]]'

    response_xq = '//*[@class="ChatMessagesView_messagePair__CsQMW"]'
    chatbox_xq = '//*[@class="GrowingTextArea_textArea__eadlu"]'
    reset_xq = '//*[@class="Button_buttonBase__0QP_m Button_flat__1hj0f ChatBreakButton_button__EihE0 ChatMessage' \
               'InputFooter_chatBreakButton__hqJ3v"]'
    logged_in_xq = reset_xq

    def __init__(
            self,
            username: str,
            password: str,
            headless: bool = True,
            timeout: int = 120,
    ):
        self.username = username
        self.password = password
        self.engines = ['Claude-instant', 'ChatGPT', 'Sage']
        self.url_prefix = 'https://poe.com'
        user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "profile"))
        os.makedirs(user_data_dir, exist_ok=True)

        options = Options()
        options.add_argument('--start-maximized')
        if headless:
            options.add_argument('--headless=new')
        driver_executable_path = ChromeDriverManager().install()
        version_main = int(re.findall('[0-9]+\.', driver_executable_path)[0][:-1])

        logging.info('Initializing browser')
        self.driver = uc.Chrome(use_subprocess=True, options=options, user_data_dir=user_data_dir,
                                driver_executable_path=driver_executable_path, version_main=version_main)
        self.wait = WebDriverWait(self.driver, timeout)
        self.is_running = Event()
        self.is_running.set()

        logging.info('Opening poe')
        self.driver.get(f"{self.url_prefix}/Sage")

        assert self.login(), "Cannot login to poe"
        logging.info('Poe is ready to interact')

    def quit(self):
        """
        Safely exit chromedriver
        :return: None
        """
        self.driver.quit()
        self.is_running.clear()

    def universal_link_handler(self):
        """
        Sometimes redirected to universal link page, just handle it
        :return: false
        """
        try:
            element = self.driver.find_element(By.XPATH, self.universal_link_xq)
        except Exceptions.NoSuchElementException:
            return False
        else:
            self.driver.execute_script("arguments[0].click()", element)
            time.sleep(5)
        return False

    def click_js(self, element=None, loc=None):
        """
        Click element using javascript executor
        :param element: selenium.webelement
        :param loc: tuple(by, value)
        :return: None
        """
        if loc is not None:
            element = self.driver.find_element(*loc)
        self.driver.execute_script("arguments[0].click()", element)

    def sign_in_google(self):
        """
        Sign in to account using google account
        :raise Exception: Wrong password
        :return: bool
        """
        self.click_js(loc=(By.XPATH, self.continue_with_google_xq))
        self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "Google will share")]')))

        self.driver.find_element(By.XPATH, self.email_xq).send_keys(self.username)
        self.click_js(loc=(By.XPATH, self.next_xq))

        self.wait.until(EC.presence_of_element_located((By.XPATH, self.password_xq)))
        self.driver.find_element(By.XPATH, self.password_xq).send_keys(self.password)
        self.click_js(loc=(By.XPATH, self.next_xq))

        is_logged_in = multiWait(self.driver, [(By.XPATH, self.retry_password_xq), (By.XPATH, self.logged_in_xq)], 120)
        if is_logged_in:
            return True
        raise Exception('Wrong password!')

    def login(self):
        """
        Performs the login process with the provided username and password.

        This function operates on the login page.
        It finds and clicks the login button,
        fills in the email and password text boxes

        Returns:
            None
        """
        auth_id = multiWait(self.driver,
                            [
                                self.universal_link_handler,
                                (By.XPATH, self.continue_with_google_xq),
                                (By.XPATH, self.logged_in_xq)
                            ],
                            max_polls=120)
        if auth_id == 1:
            self.sign_in_google()
        return True

    def interact(self, question: str, engine: str = 'sage'):
        """
        Sends a question and retrieves the answer from the GPT system.

        This function interacts with the Poe.
        It takes the question as input and sends it to the system.
        The question may contain multiple lines separated by '\n'.
        In this case, the function simulates pressing SHIFT+ENTER for each line.

        After sending the question, the function waits for the answer.
        Once the response is ready, the response is returned.

        Args:
            question (str): The interaction text.
            engine (str): choose poe engine, chatgpt or sage or claude-instant

        Returns:
            str: The generated answer.
        """
        assert self.show_engine_page(engine), f"Unknown engine {engine}\n Choose from {self.engines}"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, self.chatbox_xq)))

        text_area = self.driver.find_element(By.XPATH, self.chatbox_xq)
        for each_line in question.split('\n'):
            text_area.send_keys(each_line)
            text_area.send_keys(Keys.SHIFT + Keys.ENTER)
        text_area.send_keys(Keys.RETURN)
        logging.info('Message sent, waiting for response')

        # Get answer, check persistency for 3 seconds, try again
        answer_elm = self.driver.find_elements(By.XPATH, self.response_xq)[-1]
        answer = self.driver.execute_script("return arguments[0].textContent", answer_elm)
        time.sleep(3)
        new_answer_elm = self.driver.find_elements(By.XPATH, self.response_xq)[-1]
        new_answer = self.driver.execute_script("return arguments[0].textContent", new_answer_elm)
        while len(answer) != len(new_answer):
            answer_elm = self.driver.find_elements(By.XPATH, self.response_xq)[-1]
            answer = self.driver.execute_script("return arguments[0].textContent", answer_elm)
            time.sleep(3)
            new_answer_elm = self.driver.find_elements(By.XPATH, self.response_xq)[-1]
            new_answer = self.driver.execute_script("return arguments[0].textContent", new_answer_elm)

        # Post-process answers
        logging.info('Answer is ready')
        question = [question.replace(x, '\n') for x in re.findall('\n*\n', question)][0]
        answer = answer.replace(question, '')
        if 'ShareLikeDislikeTell' in answer:
            answer = answer[:answer.find('ShareLikeDislikeTell')]
        return answer

    def reset_thread(self):
        """Function to close the current thread and start new one"""
        self.click_js(loc=(By.XPATH, self.reset_xq))
        logging.info('Conversation is cleared')

    def show_engine_page(self, engine):
        """
        Show the required engine page
        :param engine: chatgpt or claude-instant or sage
        :return: bool
        """
        engines = [x.lower() for x in self.engines]
        engine = engine.lower()

        if engine not in engines:
            return False
        elif engine in self.driver.current_url.lower():
            return True

        url_suffix = self.engines[engines.index(engine)]
        self.driver.get(f"{self.url_prefix}/{url_suffix}")
        return True
