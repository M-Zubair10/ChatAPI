import logging
import random
import time

from selenium.common import TimeoutException, NoSuchWindowException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logger = logging.getLogger(__name__)


def get_func_name(func):
    try:
        fn_name = func.__name__
    except AttributeError:
        try:
            fn_name = func.__class__.__name__
        except AttributeError:
            fn_name = 'func'
    return fn_name


def _multiWait(driver, locators, max_polls, output_type):
    """ multiWait in given timeout """

    logger.info('===== WebDriver-MultiWait =====')
    logger.debug(f'[MultiWait] Locators: {locators}')
    logger.debug(f"[MultiWait] Max-Polls: {max_polls}")
    wait = WebDriverWait(driver, 1)
    cp = 0
    while cp < max_polls:
        cp += 1
        for i, loc in enumerate(locators):
            if isinstance(loc, dict):
                func = loc.get('func')
                if func is not None:
                    fargs = loc.get('args')
                    if fargs is None:
                        fargs = ()
                    fkwds = loc.get('kwargs')
                    if fkwds is None:
                        fkwds = {}
                    if func(*fargs, **fkwds):
                        logger.debug(f'[MultiWait] func: {get_func_name(loc)} returned true')
                        return i
                    time.sleep(1)
                else:
                    ec = loc.get('ec')
                    if ec is None:
                        ec = EC.presence_of_element_located(loc.get('locator'))
                    methods = loc.get('methods')
                    try:
                        element = wait.until(ec)
                        logger.debug(f"[MultiWait] Element found at {loc.get('locator')}")
                        if methods is not None:
                            logger.debug(f"[MultiWait] {loc.get('locator')} - Methods: {methods}")
                            if not all([eval(f"element.{m}()", {'element': element}) for m in methods]):
                                raise TimeoutException
                        logger.debug(f"[MultiWait] All methods exist on {loc.get('locator')}")
                        return i if output_type == 'id' else element
                    except TimeoutException:
                        pass
            else:
                if callable(loc):
                    if loc():
                        logger.debug(f'[MultiWait] func: {get_func_name(loc)} returned true')
                        return i
                    time.sleep(1)
                else:
                    try:
                        element = wait.until(EC.presence_of_element_located(loc))
                        logger.debug(f'[MultiWait] Element found at {loc}')
                        return i if output_type == 'id' else element
                    except TimeoutException:
                        pass

        logger.debug(f"[MultiWait] Current-Polls: {cp}")


def multiWait(
        driver,
        locators,
        max_polls=120,
        output_type='id',
        refresh_url_every_n_sec=None):
    """
    Wait until any element found in the DOM.

    :param driver: a WebDriver instance
    :type locators: list[func, tuples] or list[dict[func, loc]]
    :param locators: a list of locators or locator with its method like is_displayed, click etc
    :param max_polls: max number of time check given locator
    :param output_type: 'id' to get locator id or 'element' to get the resulting element
    :param refresh_url_every_n_sec: refresh the url every n seconds, if provided
    :return: output as specified by the output parameter
    :raises: TimeoutException if none of the elements are present in the DOM
    """

    if refresh_url_every_n_sec is not None:
        iters = int(max_polls / refresh_url_every_n_sec)
        max_polls = refresh_url_every_n_sec

    resp = _multiWait(driver, locators, max_polls, output_type)
    if refresh_url_every_n_sec is not None:
        for iter in range(iters - 1):
            if resp is None:
                driver.refresh()
            else:
                return resp
        resp = _multiWait(driver, locators, max_polls, output_type)

    if resp is None:
        raise TimeoutException("None of the given element is present in the DOM!")
    return resp


def safe_find_element(driver, by, query):
    try:
        return driver.find_element(by, query)
    except:
        return None


def cloudflare(driver, is_running, persistent=True):
    def _solve_cloudflare():
        cff = safe_find_element(driver, By.XPATH, '//*[@title="Widget containing a Cloudflare security challenge"]')
        verify_btn = safe_find_element(driver, By.XPATH, '//*[contains(@value, "Verify")]')
        if cff is not None:
            logger.debug('[Cloudflare] Turnstile frame found')
            driver.switch_to.frame(cff)
            for i in range(25):
                verify_element = driver.find_element(By.XPATH, '//*[@id="verifying-text"]')
                if 'hidden' in verify_element.get_attribute('style'):
                    break
                time.sleep(1)

            time.sleep(random.randint(1000, 3000) / 1000)
            checkbox = driver.find_element(By.XPATH, '//*[@type="checkbox"]')
            ActionChains(driver, duration=random.randint(500, 1000)).move_to_element(checkbox).click().perform()
            driver.switch_to.default_content()
            logger.debug('[Cloudflare] Turnstile frame clicked')
        elif verify_btn is not None:
            logger.debug('[Cloudflare] Verify-button found')
            time.sleep(random.randint(1000, 3000) / 1000)
            ActionChains(driver, duration=random.randint(500, 1000)).move_to_element(verify_btn).click().perform()
            logger.debug('[Cloudflare] Verify-button clicked')

    logger.debug(f"[Cloudflare] Solving with persistent flag: {persistent}")
    while is_running.is_set():
        persistency = 0
        while persistency < 3:
            try:
                if 'Just a moment' not in driver.title:
                    time.sleep(1)
                    persistency += 1
                    logger.debug(f'[Cloudflare] Title persistency {persistency}')
                else:
                    break
            except NoSuchWindowException:
                break
        if persistency == 3 and not persistent:
            break

        try:
            _solve_cloudflare()
        except NoSuchElementException:
            pass
        except Exception as e:
            logger.exception(e, exc_info=True)
        finally:
            driver.switch_to.default_content()

        time.sleep(1)
    logger.debug('[Cloudflare] Exit')
    return True
