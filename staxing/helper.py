"""OpenStax Python helper for common actions."""

import calendar
import datetime
import inspect
import os
import re

from autochomsky import chomsky
from builtins import FileNotFoundError
from itertools import repeat
from random import randint
from requests import HTTPError
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome import service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as expect
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from urllib.parse import urlparse, ParseResult

try:
    from staxing.assignment import Assignment
except ImportError:
    from assignment import Assignment
try:
    from staxing.page_load import SeleniumWait as Page
except ImportError:
    from page_load import SeleniumWait as Page

__version__ = '0.0.32'


class Helper(object):
    """Primary parent control class."""

    CONDENSED_WIDTH = 767  # pixels wide
    DEFAULT_WAIT_TIME = 15  # seconds
    CAPABILITIES = {
        'android': DesiredCapabilities.ANDROID,
        'chrome': DesiredCapabilities.CHROME,
        'firefox': DesiredCapabilities.FIREFOX,
        'htmlunit': DesiredCapabilities.HTMLUNIT,
        'htmlunitwithjs': DesiredCapabilities.HTMLUNITWITHJS,
        'internetexplorer': DesiredCapabilities.INTERNETEXPLORER,
        'ipad': DesiredCapabilities.IPAD,
        'iphone': DesiredCapabilities.IPHONE,
        'microsoftedge': DesiredCapabilities.EDGE,
        'opera': DesiredCapabilities.OPERA,
        'phantomjs': DesiredCapabilities.PHANTOMJS,
        'safari': DesiredCapabilities.SAFARI,
    }

    def __init__(self,
                 driver_type='chrome',
                 capabilities=None,
                 pasta_user=None,
                 wait_time=DEFAULT_WAIT_TIME,
                 opera_driver='',
                 existing_driver=None,
                 **kwargs):
        """Class constructor."""
        if driver_type == 'saucelabs' and pasta_user is None:
            raise TypeError('A Sauce Labs user is required for remote testing')
        self.pasta = pasta_user
        self.opera_driver = opera_driver
        if existing_driver:
            self.driver = existing_driver
        else:
            driver = driver_type if not pasta_user else 'saucelabs'
            self.driver = self.run_on(driver_type=driver,
                                      pasta_user=self.pasta,
                                      capabilities=capabilities)
            self.driver.implicitly_wait(wait_time)
        self.wait = WebDriverWait(self.driver, wait_time)
        self.wait_time = wait_time
        self.page = Page(self.driver, self.wait_time)
        super(Helper, self).__init__(**kwargs)

    def __enter__(self):
        """Entry point."""
        return self

    def __del__(self):
        """Class destructor."""
        self.delete()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Class exitor."""
        self.delete()

    def delete(self):
        """Webdriver destructor."""
        self.wait = None
        try:
            self.driver.quit()
        except:
            pass

    @classmethod
    def default_capabilities(cls, browser='chrome'):
        """Return the default browser capabilities."""
        browser = browser.lower()
        browser = ''.join(browser.split())
        return Helper.CAPABILITIES[browser].copy()

    def run_on(self, driver_type, pasta_user=None, capabilities={}):
        """Webdriver activation.

        driver_type (string): web browser type
        pasta_user (PastaSauce): optional API access for saucelabs
        capabilities (dict): browser settings; copy object to avoid overwrite
            Defaults:
                DesiredCapabilities.ANDROID.copy()
                DesiredCapabilities.CHROME.copy()
                DesiredCapabilities.EDGE.copy()
                DesiredCapabilities.FIREFOX.copy()
                DesiredCapabilities.HTMLUNIT.copy()
                DesiredCapabilities.HTMLUNITWITHJS.copy()
                DesiredCapabilities.INTERNETEXPLORER.copy()
                DesiredCapabilities.IPAD.copy()
                DesiredCapabilities.IPHONE.copy()
                DesiredCapabilities.ORERA.copy()
                DesiredCapabilities.PHANTOMJS.copy()
                DesiredCapabilities.SAFARI.copy()
            Keys:
                platform
                browserName
                version
                javascriptEnabled
        wait (int): standard time, in seconds, to wait for Selenium commands
        opera_driver (string): Chromium location
        """
        if pasta_user:
            driver = 'saucelabs'
        elif driver_type:
            driver = driver_type
        else:
            driver = 'chrome'
        try:
            return {
                'firefox': lambda: webdriver.Firefox(),
                'chrome': lambda: webdriver.Chrome(),
                'ie': lambda: webdriver.Ie(),
                'opera': lambda: self.start_opera(self.opera_driver),
                'phantomjs': lambda: webdriver.PhantomJS(),
                # 'safari': lambda: webdriver.Safari(),
                'saucelabs': lambda: webdriver.Remote(
                    command_executor=(
                        'http://%s:%s@ondemand.saucelabs.com:80/wd/hub' %
                        (pasta_user.get_user(), pasta_user.get_access_key())),
                    desired_capabilities=capabilities
                ),
            }[driver]()
        except WebDriverException as err:
            raise FileNotFoundError(err)
        except Exception as err:
            raise err

    def start_opera(self, location):
        """Opera initiator."""
        webdriver_service = service.Service(location)
        webdriver_service.start()
        return webdriver.Remote(
            webdriver_service.service_url,
            DesiredCapabilities.OPERA.copy()
        )

    def change_wait_time(self, new_wait):
        """Change the max action wait time."""
        if new_wait <= 0:
            raise ValueError('Wait time must be 1 or higher.')
        self.driver.implicitly_wait(new_wait)
        self.wait = WebDriverWait(self.driver, new_wait)
        self.wait_time = new_wait

    def date_string(self, day_delta=0, str_format='%m/%d/%Y'):
        """System date format for Tutor."""
        return (datetime.date.today() + datetime.timedelta(days=day_delta)). \
            strftime(str_format)

    def get(self, url):
        """Return the current URL."""
        self.driver.get(url)
        self.page.wait_for_page_load()

    def get_window_size(self, dimension=None):
        """Return the current window dimensions."""
        get_size = self.driver.get_window_size()
        if dimension is None:
            return get_size
        if dimension not in get_size:
            raise IndexError('Unknown dimension: %s' % dimension)
        return get_size[dimension]

    def set_window_size(self, width=0, height=0, maximize=False):
        """Attempt to change the browser window size."""
        if maximize:
            self.driver.maximize_window()
        elif width >= 1 and height >= 1:
            self.driver.set_window_size(width, height)
            sleep(1.0)
        return self.get_window_size()

    def set_window_position(self, x_=0, y_=0):
        """Move the browser window anchor."""
        if x_ >= 0 and y_ >= 0:
            self.driver.set_window_position(x_, y_)
            sleep(1.0)

    def sleep(self, seconds=1):
        """Stop execution for the specified time in seconds."""
        sleep(seconds)

    def find(self, by, value):
        """Find element."""
        return self.driver.find_element(by=by, value=value)

    def find_all(self, by, value):
        """Find elements."""
        return self.driver.find_elements(by=by, value=value)


class WebDriverTypeException(WebDriverException):
    """Exception for unknown WebDriver types."""

    def __init__(self, msg, err):
        """Exception initializer."""
        self.msg = msg
        self.__traceback__ = err

    def __repr__(self):
        """Return __str__ print."""
        return self.__str__()

    def __str__(self):
        """String representation of the exception."""
        try:
            return str(self.msg).join(str(self.__traceback__))
        except Exception as e:
            return str(type(e)).join(str(e))


class User(Helper):
    """User parent class."""

    CONDENSED_WIDTH = Helper.CONDENSED_WIDTH
    DEFAULT_WAIT_TIME = Helper.DEFAULT_WAIT_TIME

    def __init__(self,
                 username,
                 password,
                 site='https://tutor-qa.openstax.org',
                 email=None,
                 email_username=None,
                 email_password=None,
                 driver_type='chrome',
                 capabilities=None,
                 pasta_user=None,
                 wait_time=DEFAULT_WAIT_TIME,
                 opera_driver='',
                 existing_driver=None,
                 **kwargs):
        """
        Base user constructor.

        username (string): website username
        password (string): website password
        site (string): website URL
        driver_type (string): web browser type
        pasta_user (PastaSauce): optional API access for saucelabs
        capabilities (dict): browser settings; copy object to avoid overwrite
            Defaults:
                DesiredCapabilities.ANDROID.copy()
                DesiredCapabilities.CHROME.copy()
                DesiredCapabilities.EDGE.copy()
                DesiredCapabilities.FIREFOX.copy()
                DesiredCapabilities.HTMLUNIT.copy()
                DesiredCapabilities.HTMLUNITWITHJS.copy()
                DesiredCapabilities.INTERNETEXPLORER.copy()
                DesiredCapabilities.IPAD.copy()
                DesiredCapabilities.IPHONE.copy()
                DesiredCapabilities.ORERA.copy()
                DesiredCapabilities.PHANTOMJS.copy()
                DesiredCapabilities.SAFARI.copy()
            Keys:
                platform
                browserName
                version
                javascriptEnabled
        wait (int): standard time, in seconds, to wait for Selenium commands
        opera_driver (string): Chromium location
        """
        self.username = username
        self.password = password
        parse = list(
            urlparse(
                site if urlparse(site).scheme
                else '%s%s' % ('//', site)
            )
        )
        parse[0] = b'https'
        for index, value in enumerate(parse):
            parse[index] = value.decode('utf-8') if isinstance(value, bytes) \
                else value
        parse = ParseResult(*parse)
        self.url = parse.geturl()
        self.email = email
        self.email_username = email_username
        self.email_password = email_password
        self.assign = Assignment()
        super(User, self).__init__(driver_type=driver_type,
                                   capabilities=capabilities,
                                   pasta_user=pasta_user,
                                   wait_time=wait_time,
                                   opera_driver=opera_driver,
                                   existing_driver=existing_driver,
                                   **kwargs)

    def accept_contract(self):
        """
        Contract acceptance for Terms of Service and the Privacy Policy.
        """
        checkbox_id = 'agreement_i_agree' if 'accounts' in \
            self.current_url() else 'i_agree'
        try:
            target = self.find(By.ID, checkbox_id)
            Assignment.scroll_to(self.driver, target)
            target.click()
            target = self.find(By.ID, 'agreement_submit')
            Assignment.scroll_to(self.driver, target)
            target.click()
        except Exception as e:
            raise e

    def login(self, url=None, username=None, password=None):
        """
        Tutor login control.

        If parameters are not passed, login using the class values.
        Branching to deal with standard or compact screen widths

        username (string): website username
        password (string): website password
        url (string): website URL
        """
        username = self.username if not username else username
        password = self.password if not password else password
        url_address = self.url if not url else url
        # open the URL
        self.get(url_address)
        self.page.wait_for_page_load()
        if 'tutor' in url_address:
            # check to see if the screen width is normal or condensed
            if self.get_window_size('width') <= self.CONDENSED_WIDTH:
                # get small-window menu toggle
                is_collapsed = self.find(By.CSS_SELECTOR,
                                         'button.navbar-toggle')
                # check if the menu is collapsed and, if yes, open it
                try:
                    WebDriverWait(self.driver, 2).until(
                        expect.visibility_of_element_located(
                            By.XPATH,
                            '//a[contains(@href,"/accounts/login")]'
                        )
                    )
                except:  # closed menu,
                    is_collapsed.click()
            self.wait.until(
                expect.visibility_of_element_located(
                    (By.LINK_TEXT, 'Log in')
                )
            ).click()
            self.page.wait_for_page_load()
        elif 'exercises' in url_address:
            self.find(By.LINK_TEXT, 'Sign in').click()
            self.page.wait_for_page_load()
        src = self.driver.page_source
        text_located = re.search(r'openstax', src.lower())
        self.sleep(1)
        if not text_located:
            raise self.LoginError(
                'Non-OpenStax URL: %s' % self.driver.current_url
            )
        # enter the username and password
        self.find(By.ID, 'login_username_or_email').send_keys(username)
        self.find(By.XPATH, '//input[@value="Next"]').click()
        self.find(By.ID, 'login_password').send_keys(password)
        self.find(By.XPATH, '//input[@value="Login"]').click()
        self.page.wait_for_page_load()
        # check if a password change is required
        if 'reset your password' in self.driver.page_source.lower():
            try:
                self.find(By.ID, 'reset_password_password') \
                    .send_keys(self.password)
                self.find(By.ID, 'reset_password_password_confirmation') \
                    .send_keys(self.password)
                self.find(By.XPATH, '//input[@value="Reset Password"]').click()
                self.sleep(1)
                self.find(By.XPATH, '//input[@value="Continue"]').click()
            except Exception as e:
                raise e
        self.page.wait_for_page_load()
        source = self.driver.page_source.lower()
        print('Reached Terms/Privacy')
        while 'terms of use' in source or 'privacy policy' in source:
            self.accept_contract()
            self.page.wait_for_page_load()
            source = self.driver.page_source.lower()
        return self

    def logout(self):
        """Logout control."""
        url_address = self.current_url()
        if 'tutor' in url_address:
            self.tutor_logout()
        elif 'accounts' in url_address:
            self.accounts_logout()
        elif 'exercises' in url_address:
            self.exercises_logout()
        else:
            raise HTTPError('Not an OpenStax URL')

    def current_url(self):
        """Return the current browser URL."""
        return self.driver.current_url

    def goto_course_list(self):
        """Go to the course picker."""
        try:
            self.wait.until(
                expect.presence_of_element_located(
                    (By.ID, 'ox-react-root-container')
                )
            )
            if 'tutor' in self.current_url():
                self.find(By.XPATH, '//a[contains(@href,"dashboard")]') \
                    .click()
                self.page.wait_for_page_load()
            else:
                raise HTTPError('Not currently on an OpenStax Tutor webpage:' +
                                '%s' % self.current_url())
        except Exception as ex:
            raise ex

    def get_course_list(self, closed=False):
        """Return a list of available courses."""
        courses = self.find_all(
            By.CSS_SELECTOR,
            'div.course-listing-current-section' + ' ' +
            'div.course-listing-item'
        )
        for a, x in enumerate(courses):
            print('%s : "%s"' % (a, x.get_attribute('data-title')))
        return courses

    def open_user_menu(self):
        """
        Hamburger (user) menu opener.

        ToDo: branching to handle if a toggle is already open
        """
        if self.get_window_size('width') <= self.CONDENSED_WIDTH:
            # compressed window display on Tutor
            self.wait.until(
                expect.visibility_of_element_located(
                    (By.CLASS_NAME, 'navbar-toggle')
                )
            ).click()
        self.wait.until(
            expect.visibility_of_element_located(
                (By.CLASS_NAME, 'dropdown-toggle')
            )
        ).click()

    def tutor_logout(self):
        """Tutor logout helper."""
        self.open_user_menu()
        self.wait.until(
            expect.visibility_of_element_located(
                (By.XPATH, '//input[@aria-label="Log Out"]')
            )
        ).click()
        self.page.wait_for_page_load()

    def accounts_logout(self):
        """OS Accounts logout helper."""
        self.find(By.LINK_TEXT, 'Log out').click()
        self.page.wait_for_page_load()

    def execises_logout(self):
        """Exercises logout helper."""
        wait = WebDriverWait(self.driver, 3)
        try:
            wait.until(
                expect.element_to_be_clickable(
                    (By.ID, 'navbar-dropdown')
                )
            ).click()
            wait.until(
                expect.element_to_be_clickable(
                    (By.XPATH, '//input[@aria-label="Log Out"]')
                )
            ).click()
            self.page.wait_for_page_load()
        except NoSuchElementException:
            # Different page, but uses the same logic and link text
            self.accounts_logout()

    def select_course(self, title=None, appearance=None):
        """Select course."""
        print('Select course "%s" / "%s"' % (title, appearance))
        print('Currently at: %s' % self.current_url())
        if 'dashboard' not in self.current_url():
            # If not at the dashboard, try to load it
            print('Go to course list')
            self.goto_course_list()
            self.page.wait_for_page_load()
        if 'dashboard' not in self.current_url():
            # Only has one course and the user is at the dashboard so return
            print('Single course; select course complete')
            return
        if title:
            uses_option = 'title'
            course = title
        elif appearance:
            uses_option = 'appearance'
            course = appearance
        else:
            raise self.LoginError('Unknown course selection "%s"' %
                                  title if title else appearance)
        print('//div[@data-%s="%s"]//a' % (uses_option, course))
        select = self.wait.until(
            expect.element_to_be_clickable(
                (
                    By.XPATH, '//div[@data-%s="%s"]//a' %
                    (uses_option, course)
                )
            )
        )
        print('Course: %s - %s' % (title if title else appearance,
                                   select.get_attribute('href')))
        select.click()
        self.page.wait_for_page_load()
        print('Select course complete')
        return self

    def view_reference_book(self):
        """Access the reference book."""
        try:
            self.find(
                By.XPATH, '//div/a[contains(@class,"view-reference-guide")]'
            ).click()
            return
        except:
            pass
        self.open_user_menu()
        self.find(
            By.XPATH, '//li/a[contains(@class,"view-reference-guide")]'
        ).click()


class LoginError(Exception):
    """Login error exception."""

    def __init__(self, value):
        """Exception initializer."""
        self.value = value

    def __str__(self):
        """Return string of the exception text."""
        return repr(self.value)


class Teacher(User):
    """User extention for teachers."""

    CONDENSED_WIDTH = User.CONDENSED_WIDTH
    DEFAULT_WAIT_TIME = User.DEFAULT_WAIT_TIME

    def __init__(self,
                 use_env_vars=False,
                 existing_driver=None,
                 **kwargs):
        """Teacher initialization with User pass-through."""
        if use_env_vars:
            if not kwargs:
                kwargs = {}
            kwargs['username'] = os.getenv('TEACHER_USER')
            kwargs['password'] = os.getenv('TEACHER_PASSWORD')
            kwargs['site'] = os.getenv('SERVER_URL')
            kwargs['email'] = os.getenv('TEST_EMAIL_ACCOUNT')
            kwargs['email_username'] = os.getenv('TEST_EMAIL_USER')
            kwargs['email_password'] = os.getenv('TEST_EMAIL_PASSWORD')
        super(Teacher, self).__init__(existing_driver=existing_driver,
                                      **kwargs)

    def switch_user(self, username):
        """Switch username during chained actions."""
        self.username = username
        return self

    def add_assignment(self, assignment, args):
        """Add an assignment."""
        self.assign.add[assignment](
            driver=self.driver,
            name=args['title'],
            description=args['description'] if 'description' in args else '',
            periods=args['periods'],
            state=args['status'],
            url=args['url'] if 'url' in args else None,
            reading_list=args['reading_list'] if 'reading_list' in args else
            None,
            problems=args['problems'] if 'problems' in args else None,
            feedback=args['feedback'] if 'feedback' in args else None
        )

    def change_assignment(self, assignment, args):
        """Alter an existing assignment."""
        self.assign.edit[assignment](
            driver=self.driver,
            name=args['title'],
            description=args['description'],
            periods=args['periods'],
            state=args['status'],
            url=args['url'] if 'url' in args else None,
            reading_list=args['reading_list'] if 'reading_list' in args else
            None,
            problems=args['problems'] if 'problems' in args else None,
            feedback=args['feedback'] if 'feedback' in args else None,
        )

    def delete_assignment(self, assignment, args):
        """Delete an existing assignment (if available)."""
        self.assign.remove[assignment](
            driver=self.driver,
            name=args['title'],
            description=args['description'] if 'description' in args else None,
            periods=args['periods'] if 'periods' in args else None,
            state=args['status'] if 'status' in args else None,
            url=args['url'] if 'url' in args else None,
            reading_list=args['reading_list'] if 'reading_list' in args else
            None,
            problems=args['problems'] if 'problems' in args else None,
            feedback=args['feedback'] if 'feedback' in args else None,
        )

    def goto_menu_item(self, item):
        """Go to a specific user menu item."""
        print('Enter: goto_menu_item')
        if 'courses' in self.current_url():
            print('Open user menu')
            self.open_user_menu()
            print('Select menu item %s' % item)
            self.wait.until(
                expect.element_to_be_clickable((By.LINK_TEXT, item))
            ).click()
            self.page.wait_for_page_load()
        print('Exit: goto_menu_item')

    def goto_calendar(self):
        """Return the teacher to the calendar dashboard."""
        print('Enter: goto_calendar')
        try:
            print('Try to return to the calendar')
            self.find(By.CSS_SELECTOR, 'ul.navbar-nav a.navbar-brand').click()
            print('Succeeded')
            self.page.wait_for_page_load()
        except:
            print('Failed, Try to return to the calendar using the Brand')
            try:
                self.find(
                    By.CSS_SELECTOR,
                    'div.navbar-header a.navbar-brand'
                ).click()
                print('Succeeded')
                self.page.wait_for_page_load()
            except:
                print('Failed')
                pass
        print('Exit: goto_calendar')

    def goto_performance_forecast(self):
        """Access the performance forecast page."""
        print('Enter: goto_performance_forecast')
        self.goto_menu_item('Performance Forecast')
        timer = 0
        while timer < 10:
            try:
                print('Wait for forecast load try %s of 10' % (timer + 1))
                self.wait.until(
                    expect.visibility_of_element_located(
                        (By.CLASS_NAME, 'guide-container')
                    )
                )
                timer = 10
            except:
                timer = timer + 1
        print('Exit: goto_performance_forecast')

    def goto_student_scores(self):
        """Access the student scores page."""
        print('Enter: goto_student_scores')
        self.goto_menu_item('Student Scores')
        print('Exit: goto_student_scores')

    def goto_course_roster(self):
        """Access the course roster page."""
        print('Enter: goto_course_roster')
        self.goto_menu_item('Course Settings and Roster')
        print('Exit: goto_course_roster')

    def goto_course_settings(self):
        """Access the course settings page."""
        self.goto_course_roster()

    def add_course_section(self, section_name):
        """Add a section to the course."""
        print('Enter: add_course_section')
        if 'settings' not in self.current_url():
            self.goto_course_roster()
        self.find(By.XPATH, '//button[i[contains(@class,"fa-plus")]]').click()
        self.wait.until(
            expect.visibility_of_element_located(
                (By.XPATH,
                 '//div[contains(@class,"teacher-edit-period-form")]' +
                 '//input[@type="text"]')
            )
        ).send_keys(section_name)
        self.wait.until(
            expect.element_to_be_clickable(
                (By.XPATH, '//button[contains(@class,"-edit-period-confirm")]')
            )
        ).click()
        print('Exit: add_course_section')

    def get_enrollment_code(self, section_name):
        """Return the enrollment code for a class section."""
        print('Enter: get_enrollment_code')
        if 'settings' not in self.driver.current_url:
            self.goto_course_roster()
        self.find(By.XPATH, '//a[text()="%s"]' % section_name).click()
        self.wait.until(
            expect.element_to_be_clickable(
                (By.CLASS_NAME, 'show-enrollment-code')
            )
        ).click()
        sleep(1)
        code = self.wait.until(
            expect.presence_of_element_located(
                (By.CLASS_NAME, 'code')
            )
        )
        print('Exit: get_enrollment_code')
        return '%s' % code.text.strip()

    def get_book_sections(self):
        """Return a list of book sections."""
        print('Retrieve the book section list')
        self.goto_calendar()
        self.page.wait_for_page_load()
        self.assign.open_assignment_menu(self.driver)
        self.wait.until(
            expect.element_to_be_clickable(
                (By.LINK_TEXT, 'Add Reading')
            )
        ).click()
        self.page.wait_for_page_load()
        selector = self.find(By.ID, 'reading-select')
        Assignment.scroll_to(self.driver, selector)
        sleep(1.0)
        selector.click()
        self.page.wait_for_page_load()
        for chapter in self.find_all(By.CSS_SELECTOR,
                                     'div.chapter-heading > a'):
            if chapter.get_attribute('aria-expanded') != 'true':
                Assignment.scroll_to(self.driver, chapter)
                sleep(0.25)
                chapter.click()
        sections = self.find_all(
            By.CSS_SELECTOR, 'div.section span.chapter-section')
        section_list = []
        section_string = ''
        for section in sections:
            section_list.append(section.text)
            section_string += ' %s' % section.text
        print('Section options: %s' % section_string)
        self.goto_calendar()
        return section_list

    def get_month_number(self, month):
        """Take a string month and return its numberic."""
        months = {v: k for k, v in enumerate(calendar.month_name)}
        return months[month]

    def get_month_year(self):
        """Break a date string into a month year tuple."""
        calendar_heading = self.find(By.CSS_SELECTOR,
                                     'div.calendar-header-label')
        Assignment.scroll_to(self.driver, calendar_heading)
        calendar_date = calendar_heading.text
        month, year = calendar_date.split(' ')
        return self.get_month_number(month), int(year)

    def rotate_calendar(self, target):
        """Rotate the teacher calendar to a specific month and year."""
        cal_month, cal_year = self.get_month_year()
        target_date = datetime.datetime.strptime(target, '%m/%d/%Y').date()
        if cal_year == target_date.year and \
                cal_month == target_date.month:
            return
        cal_month, cal_year = self.get_month_year()
        while cal_year < target_date.year:
            self.find(By.CLASS_NAME, 'fa-caret-right').click()
            sleep(0.2)
            cal_month, cal_year = self.get_month_year()
        while cal_month < target_date.month:
            self.find(By.CLASS_NAME, 'fa-caret-right').click()
            sleep(0.2)
            cal_month, cal_year = self.get_month_year()
        while cal_year > target_date.year:
            self.find(By.CLASS_NAME, 'fa-caret-left').click()
            sleep(0.2)
            cal_month, cal_year = self.get_month_year()
        while cal_month > target_date.month:
            self.find(By.CLASS_NAME, 'fa-caret-left').click()
            sleep(0.2)
            cal_month, cal_year = self.get_month_year()


class Student(User):
    """User extention for students."""

    CONDENSED_WIDTH = User.CONDENSED_WIDTH
    DEFAULT_WAIT_TIME = User.DEFAULT_WAIT_TIME

    def __init__(self,
                 use_env_vars=False,
                 existing_driver=None,
                 **kwargs):
        """Student initialization with User pass-through."""
        if use_env_vars:
            if not kwargs:
                kwargs = {}
            kwargs['username'] = os.getenv('STUDENT_USER')
            kwargs['password'] = os.getenv('STUDENT_PASSWORD')
            kwargs['site'] = os.getenv('SERVER_URL')
            kwargs['email'] = os.getenv('TEST_EMAIL_ACCOUNT')
            kwargs['email_username'] = os.getenv('TEST_EMAIL_USER')
            kwargs['email_password'] = os.getenv('TEST_EMAIL_PASSWORD')
        super(Student, self).__init__(existing_driver=existing_driver,
                                      **kwargs)

    def goto_menu_item(self, item):
        """Go to a specific user menu item."""
        print('Enter: goto_menu_item')
        if 'courses' in self.driver.current_url:
            self.open_user_menu()
            self.wait.until(
                expect.element_to_be_clickable((By.LINK_TEXT, item))
            ).click()
            self.page.wait_for_page_load()
        print('Exit: goto_menu_item')

    def goto_dashboard(self):
        """Go to current work."""
        self.goto_menu_item('Dashboard')

    def work_assignment(self):
        """Work an assignment."""
        if '/courses/' not in self.current_url():
            self.find(By.XPATH, '//a[contains(@class,"na")]')
        self.wait.until(
            expect.element_to_be_clickable((By.LINK_TEXT, 'All Past Work'))
        )
        raise NotImplementedError(inspect.currentframe().f_code.co_name)

    def goto_past_work(self):
        """View work for previous weeks."""
        self.goto_dashboard()
        self.wait.until(
            expect.element_to_be_clickable((By.LINK_TEXT, 'All Past Work'))
        ).click()
        self.page.wait_for_page_load()

    def goto_performance_forecast(self):
        """View the student performance forecast."""
        self.goto_menu_item('Performance Forecast')

    def practice(self, practice_set='weakest'):
        """Complete a set of up to 5 practice problems."""
        options = []
        self.goto_dashboard()
        # Wait for the student performance meters to load
        try:
            print('Loading Performance Forecast')
            WebDriverWait(self.driver, 60).until(
                expect.staleness_of(
                    (By.CLASS_NAME, 'is-loading')
                )
            )
        except:
            pass
        finally:
            self.sleep(2)
        # Select a section or the weakest topic to practice
        options.append(
            self.wait.until(
                expect.visibility_of_element_located(
                    (By.CLASS_NAME, 'practice')
                )
            )
        )
        if practice_set == 'weakest':
            options[0].click()
            self.page.wait_for_page_load()
        else:
            try:
                sections = self.find_all(
                    By.XPATH,
                    '//button[contains(@aria-describedby,' +
                    '"progress-bar-tooltip-")]'
                )
                if not isinstance(sections, list):
                    sections = [sections]
                for section in sections:
                    options.append(section)
            except:
                pass
            finally:
                options[randint(0, len(options) - 1)].click()
                self.page.wait_for_page_load()
        # How many questions are there? (default = 5)
        breadbox = self.wait.until(
            expect.presence_of_element_located(
                (By.CLASS_NAME, 'task-breadcrumbs')
            )
        )
        crumbs = breadbox.find_elements(By.TAG_NAME, 'span')
        # Answer each assessment
        for _ in repeat(None, len(crumbs) - 1):
            self.answer_assessment()
        # Finish the practice
        self.wait.until(
            expect.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(),"Dashboard") and' +
                 ' contains(@class,"btn")]')
            )
        ).click()
        self.page.wait_for_page_load()

    def answer_assessment(self):
        """Answer a Tutor assessment."""
        self.wait.until(
            expect.presence_of_element_located(
                (By.CLASS_NAME, 'openstax-question')
            )
        )
        text = chomsky(1, 500)
        wt = self.wait_time
        try:
            self.change_wait_time(3)
            text_block = self.find(By.XPATH, '//textarea')
            self.change_wait_time(wt)
            print('Enter free response')
            Assignment.send_keys(self.driver, text_block, text)
            self.find(By.CLASS_NAME, 'continue').click()
        except Exception:
            self.change_wait_time(wt)
            print('Skip free response')
        finally:
            self.page.wait_for_page_load()
        answers = self.find_all(By.CLASS_NAME, 'answer-letter')
        self.sleep(0.8)
        rand = randint(0, len(answers) - 1)
        answer = chr(ord('a') + rand)
        print('Selecting %s' % answer)
        Assignment.scroll_to(self.driver, answers[0])
        if answer == 'a':
            self.driver.execute_script('window.scrollBy(0, -160);')
        elif answer == 'd':
            self.driver.execute_script('window.scrollBy(0, 160);')
        answers[rand].click()
        self.sleep(1.0)
        self.wait.until(
            expect.element_to_be_clickable(
                (By.XPATH, '//button[span[text()="Submit"]]')
            )
        ).click()
        self.wait.until(
            expect.element_to_be_clickable(
                (By.CLASS_NAME, 'continue')
            )
        ).click()
        self.page.wait_for_page_load()


class Admin(User):
    """User extention for administrators."""

    CONDENSED_WIDTH = User.CONDENSED_WIDTH
    DEFAULT_WAIT_TIME = User.DEFAULT_WAIT_TIME

    def __init__(self, use_env_vars=False, existing_driver=None, **kwargs):
        """Administrator initialization with User pass-through."""
        if use_env_vars:
            if not kwargs:
                kwargs = {}
            kwargs['username'] = os.getenv('ADMIN_USER')
            kwargs['password'] = os.getenv('ADMIN_PASSWORD')
            kwargs['site'] = os.getenv('SERVER_URL')
            kwargs['email'] = os.getenv('TEST_EMAIL_ACCOUNT')
            kwargs['email_username'] = os.getenv('TEST_EMAIL_USER')
            kwargs['email_password'] = os.getenv('TEST_EMAIL_PASSWORD')
        super(Admin, self).__init__(existing_driver=existing_driver,
                                    **kwargs)
        extension = '' if self.url.endswith('/') else '/'
        self.base = self.url + extension + 'admin'

    def goto_admin_control(self):
        """Access the administrator controls."""
        self.get('%s' % self.base)

    def goto_catalog_offerings(self):
        """Access the catalog."""
        self.get('%s%s' % (self.base, '/catalog_offerings'))

    def goto_course_list(self):
        """Access the course list."""
        self.get('%s%s' % (self.base, '/courses'))

    def goto_school_list(self):
        """Access the school list."""
        self.get('%s%s' % (self.base, '/school'))

    def goto_district_list(self):
        """Access the district list."""
        self.get('%s%s' % (self.base, '/districts'))

    def goto_tag_list(self):
        """Access the tag list."""
        self.get('%s%s' % (self.base, '/tags'))

    def goto_ecosystems(self):
        """Access the ecosystem list."""
        self.get('%s%s' % (self.base, '/ecosystems'))

    def goto_terms_and_contracts(self):
        """Access the terms and contracts list."""
        self.get('%s%s' % (self.url, '/fine_print'))

    def goto_contracts(self):
        """Access the targeted contracts."""
        self.get('%s%s' % (self.base, '/targeted_contracts'))

    def goto_course_stats(self):
        """Access the course stats."""
        self.get('%s%s' % (self.base, '/stats/courses'))

    def goto_concept_coach_stats(self):
        """Access the Concept Coach stats."""
        self.get('%s%s' % (self.base, '/stats/concept_coach'))

    def goto_user_list(self):
        """Access the user list."""
        self.get('%s%s' % (self.base, '/users'))

    def goto_jobs(self):
        """Access the jobs list."""
        self.get('%s%s' % (self.base, '/jobs'))

    def goto_research_data(self):
        """Access the researcher data."""
        self.get('%s%s' % (self.base, '/research_data'))

    def goto_salesforce_control(self):
        """Access the Salesforce controls."""
        self.get('%s%s' % (self.base, '/salesforce'))

    def goto_system_settings(self):
        """Access the system settings."""
        self.get('%s%s' % (self.base, '/settings'))

    def goto_system_notifications(self):
        """Access the system notifications."""
        self.get('%s%s' % (self.base, '/notifications'))


class ContentQA(User):
    """User extention for content users."""

    CONDENSED_WIDTH = User.CONDENSED_WIDTH
    DEFAULT_WAIT_TIME = User.DEFAULT_WAIT_TIME

    def __init__(self, use_env_vars=False, existing_driver=None, **kwargs):
        """Content analyst initialization with User pass-through."""
        if use_env_vars:
            if not kwargs:
                kwargs = {}
            kwargs['username'] = os.getenv('CONTENT_USER')
            kwargs['password'] = os.getenv('CONTENT_PASSWORD')
            kwargs['site'] = os.getenv('SERVER_URL')
            kwargs['email'] = os.getenv('TEST_EMAIL_ACCOUNT')
            kwargs['email_username'] = os.getenv('TEST_EMAIL_USER')
            kwargs['email_password'] = os.getenv('TEST_EMAIL_PASSWORD')
        super(ContentQA, self).__init__(existing_driver=existing_driver,
                                        **kwargs)


class Webview(object):
    """Webview navigation and control."""

    def __init__(self, driver, wait_time=30, site='https://demo.cnx.org/'):
        """Webview constructor."""
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        self.site = site

    def goto_section(self, section_name=None, section_number=None):
        """Go to a specific page module."""
        raise NotImplementedError(inspect.currentframe().f_code.co_name)

    def next(self):
        """Go to the next page module."""
        raise NotImplementedError(inspect.currentframe().f_code.co_name)

    def previous(self):
        """Go to the previous page module."""
        raise NotImplementedError(inspect.currentframe().f_code.co_name)

    def goto_concept_coach(self):
        """Go to the Concept Coach widget."""
        raise NotImplementedError(inspect.currentframe().f_code.co_name)


if __name__ == '__main__':
    # execute if run as a script
    initialization = Helper
