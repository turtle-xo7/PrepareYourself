from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile, Board, Subject, Class, Question
import time
import sys
import warnings


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1280,800')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('detach', False)
    service = Service(ChromeDriverManager().install())
    service.suppress_output = True
    import io
    import contextlib
    with contextlib.redirect_stderr(io.StringIO()):
        driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    driver.set_page_load_timeout(30)
    return driver


def wait_for_page_load(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(0.1)
    except Exception:
        pass


def safe_click(driver, element_or_locator, timeout=10):
    try:
        if isinstance(element_or_locator, tuple):
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(element_or_locator)
            )
        else:
            element = element_or_locator
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.05)
        element.click()
    except Exception:
        pass


def safe_send_keys(driver, locator, text, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        element.clear()
        element.send_keys(text)
    except Exception:
        pass


def login(driver, live_server_url, username, password):
    driver.get(f'{live_server_url}/login/')
    wait_for_page_load(driver)
    safe_send_keys(driver, (By.NAME, 'username'), username)
    safe_send_keys(driver, (By.NAME, 'password'), password)
    submit_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '#form-login button[type=submit]'))
    )
    safe_click(driver, submit_btn)
    WebDriverWait(driver, 10).until(
        lambda d: '/login/' not in d.current_url
    )
    wait_for_page_load(driver)


def is_element_present(driver, by, value, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except Exception:
        return False


def create_student(username='student1', email='student@test.com', plan='PREMIUM'):
    user = User.objects.create_user(username=username, email=email, password='testpass123')
    UserProfile.objects.create(user=user, role='STUDENT', plan=plan)
    return user


def create_teacher(username='teacher1', email='teacher@test.com'):
    user = User.objects.create_user(username=username, email=email, password='testpass123')
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE')
    return user


def create_superadmin(username='superadmin1'):
    user = User.objects.create_user(username=username, email='admin@test.com', password='testpass123')
    UserProfile.objects.create(user=user, role='ADMIN', plan='FREE', is_superadmin=True)
    return user


def create_board():
    return Board.objects.create(name='Dhaka Board', student_count='100000', is_active=True)


def create_subject():
    return Subject.objects.create(name='Physics', icon='⚛️', color='blue', is_active=True)


def create_class():
    return Class.objects.create(name='Class 9', numeric_value=9)


class BaseSeleniumTest(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        warnings.filterwarnings("ignore")
        if hasattr(cls, 'live_server_url'):
            cls.live_server_url = cls.live_server_url

    def setUp(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        self.driver = setup_driver()
        self.driver.implicitly_wait(5)

    def tearDown(self):
        if hasattr(self, 'driver') and self.driver:
            try:
                time.sleep(0.2)
                try:
                    self.driver.delete_all_cookies()
                    self.driver.execute_script("window.localStorage.clear();")
                    self.driver.execute_script("window.sessionStorage.clear();")
                except Exception:
                    pass
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        time.sleep(0.1)
        super().tearDownClass()


class AuthSeleniumTests(BaseSeleniumTest):

    def test_login_page_loads(self):
        self.driver.get(f'{self.live_server_url}/login/')
        wait_for_page_load(self.driver)
        self.assertIn('Prepare Yourself', self.driver.title)

    def test_successful_login(self):
        create_student()
        login(self.driver, self.live_server_url, 'student1', 'testpass123')
        self.assertNotIn('/login/', self.driver.current_url)
        self.assertTrue(is_element_present(self.driver, By.CSS_SELECTOR, 'nav'))

    def test_failed_login(self):
        self.driver.get(f'{self.live_server_url}/login/')
        wait_for_page_load(self.driver)
        safe_send_keys(self.driver, (By.NAME, 'username'), 'wronguser')
        safe_send_keys(self.driver, (By.NAME, 'password'), 'wrongpass')
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, '#form-login button[type=submit]')
        safe_click(self.driver, submit_btn)
        WebDriverWait(self.driver, 5).until(
            EC.url_contains('/login/')
        )
        self.assertIn('/login/', self.driver.current_url)

    def test_signup(self):
        self.driver.get(f'{self.live_server_url}/login/')
        wait_for_page_load(self.driver)
        signup_tab = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'tab-signup'))
        )
        safe_click(self.driver, signup_tab)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#form-signup'))
        )
        safe_send_keys(self.driver, (By.CSS_SELECTOR, '#form-signup input[name=username]'), 'newuser')
        safe_send_keys(self.driver, (By.CSS_SELECTOR, '#form-signup input[name=email]'), 'new@test.com')
        safe_send_keys(self.driver, (By.CSS_SELECTOR, '#form-signup input[name=password]'), 'testpass123')
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, '#form-signup button[type=submit]')
        safe_click(self.driver, submit_btn)
        WebDriverWait(self.driver, 20).until(
            lambda d: User.objects.filter(username='newuser').exists()
        )
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout(self):
        create_student()
        login(self.driver, self.live_server_url, 'student1', 'testpass123')
        self.driver.get(f'{self.live_server_url}/logout/')
        WebDriverWait(self.driver, 10).until(
            EC.url_contains('/login/')
        )
        self.assertIn('/login/', self.driver.current_url)

    def test_forgot_password_link_visible(self):
        self.driver.get(f'{self.live_server_url}/login/')
        wait_for_page_load(self.driver)
        forgot = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Forgot'))
        )
        self.assertTrue(forgot.is_displayed())


class NavbarSeleniumTests(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        create_student()
        login(self.driver, self.live_server_url, 'student1', 'testpass123')

    def test_navbar_links_visible(self):
        self.driver.get(f'{self.live_server_url}/')
        wait_for_page_load(self.driver)
        links = self.driver.find_elements(By.CSS_SELECTOR, 'nav a')
        self.assertGreater(len(links), 3)

    def test_profile_dropdown_works(self):
        self.driver.get(f'{self.live_server_url}/')
        wait_for_page_load(self.driver)
        self.assertIn('Log Out', self.driver.page_source)


class QuestionBankSeleniumTests(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        self.board = create_board()
        self.subject = create_subject()
        self.class_obj = create_class()
        Question.objects.create(
            board=self.board,
            subject=self.subject,
            class_obj=self.class_obj,
            year=2024,
            chapter='Chapter 1',
            question_text='What is force?',
            question_type='MCQ',
            difficulty='Easy',
            option1='Push',
            option2='Pull',
            option3='Both',
            option4='None',
            correct_option=3,
            answer_hint='Force is push or pull.',
            is_active=True
        )
        create_student()
        login(self.driver, self.live_server_url, 'student1', 'testpass123')

    def test_question_bank_loads(self):
        self.driver.get(f'{self.live_server_url}/question-bank/')
        wait_for_page_load(self.driver)
        self.assertIn('Question Bank', self.driver.page_source)

    def test_question_visible(self):
        self.driver.get(f'{self.live_server_url}/question-bank/')
        wait_for_page_load(self.driver)
        self.assertIn('What is force?', self.driver.page_source)


class SuperAdminSeleniumTests(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        create_superadmin()
        create_student()
        login(self.driver, self.live_server_url, 'superadmin1', 'testpass123')

    def test_superadmin_dashboard_loads(self):
        self.driver.get(f'{self.live_server_url}/superadmin/')
        wait_for_page_load(self.driver)
        self.assertIn('Super Admin', self.driver.page_source)

    def test_export_excel_button_visible(self):
        self.driver.get(f'{self.live_server_url}/superadmin/')
        wait_for_page_load(self.driver)
        btn = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Export')]"))
        )
        self.assertTrue(btn.is_displayed())

    def test_user_table_visible(self):
        self.driver.get(f'{self.live_server_url}/superadmin/')
        wait_for_page_load(self.driver)
        table = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table'))
        )
        self.assertTrue(table.is_displayed())

    def test_student_visible_in_table(self):
        self.driver.get(f'{self.live_server_url}/superadmin/')
        wait_for_page_load(self.driver)
        self.assertIn('student1', self.driver.page_source)