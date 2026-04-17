from django.test import TestCase, Client
from django.urls import reverse


# ─── Unit Tests ───────────────────────────────────────────────

class QuestionBankViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('question_bank')

    def test_page_loads_successfully(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_correct_template_used(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'core/question_bank.html')

    def test_questions_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('questions', response.context)

    def test_questions_not_empty(self):
        response = self.client.get(self.url)
        self.assertGreater(len(response.context['questions']), 0)

    def test_boards_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('boards', response.context)

    def test_subjects_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('subjects', response.context)

    def test_classes_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('classes', response.context)

    def test_years_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('years', response.context)

    def test_question_has_required_fields(self):
        response = self.client.get(self.url)
        q = response.context['questions'][0]
        self.assertIn('board', q)
        self.assertIn('subject', q)
        self.assertIn('chapter', q)
        self.assertIn('difficulty', q)
        self.assertIn('year', q)

    def test_mcq_question_has_options(self):
        response = self.client.get(self.url)
        mcq_questions = [q for q in response.context['questions'] if q.get('is_mcq')]
        self.assertGreater(len(mcq_questions), 0)
        for q in mcq_questions:
            self.assertIn('options', q)
            self.assertEqual(len(q['options']), 4)

    def test_mcq_correct_option_index_valid(self):
        response = self.client.get(self.url)
        for q in response.context['questions']:
            if q.get('is_mcq'):
                idx = q['correct_option_index']
                self.assertGreaterEqual(idx, 0)
                self.assertLess(idx, len(q['options']))

    def test_difficulty_values_valid(self):
        response = self.client.get(self.url)
        valid = {'Easy', 'Medium', 'Hard'}
        for q in response.context['questions']:
            self.assertIn(q['difficulty'], valid)

    def test_page_contains_question_bank_heading(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Question Bank')

    def test_page_contains_filter_dropdowns(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'All Boards')
        self.assertContains(response, 'All Subjects')

    def test_post_request_not_allowed(self):
        response = self.client.post(self.url)
        self.assertNotEqual(response.status_code, 200)


# ─── Selenium Tests ───────────────────────────────────────────

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


class QuestionBankSeleniumTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.implicitly_wait(5)
        cls.base_url = 'http://127.0.0.1:8000'

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def test_page_title(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        self.assertIn('Question Bank', self.driver.title)

    def test_question_cards_visible(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        cards = self.driver.find_elements(By.CSS_SELECTOR, '#q-1, #q-2, #q-3')
        self.assertGreater(len(cards), 0)

    def test_mcq_options_visible(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        opts = self.driver.find_elements(By.CLASS_NAME, 'mcq-btn')
        self.assertGreater(len(opts), 0)

    def test_click_mcq_option_enables_check_button(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        first_opt = self.driver.find_element(By.CSS_SELECTOR, '#opts-1 .mcq-btn')
        first_opt.click()
        check_btn = self.driver.find_element(By.ID, 'check-1')
        self.assertFalse(check_btn.get_attribute('disabled'))

    def test_check_answer_shows_result(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        first_opt = self.driver.find_element(By.CSS_SELECTOR, '#opts-1 .mcq-btn')
        first_opt.click()
        check_btn = self.driver.find_element(By.ID, 'check-1')
        check_btn.click()
        reveal = self.driver.find_element(By.ID, 'reveal-1')
        self.assertTrue(reveal.is_displayed())

    def test_navigator_sidebar_visible(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        nav = self.driver.find_element(By.ID, 'nav-grid')
        self.assertTrue(nav.is_displayed())

    def test_navigator_scroll_to_question(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        nav_btn = self.driver.find_element(By.ID, 'nav-1')
        nav_btn.click()
        time.sleep(0.5)
        q_card = self.driver.find_element(By.ID, 'q-1')
        self.assertTrue(q_card.is_displayed())

    def test_correct_answer_turns_nav_green(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        # Physics question এর correct index = 1 (খ)
        opts = self.driver.find_elements(By.CSS_SELECTOR, '#opts-1 .mcq-btn')
        opts[1].click()
        self.driver.find_element(By.ID, 'check-1').click()
        nav_dot = self.driver.find_element(By.ID, 'nav-1')
        classes = nav_dot.get_attribute('class')
        self.assertIn('bg-green-400', classes)

    def test_wrong_answer_turns_nav_red(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        # ভুল option (ক) click করো
        opts = self.driver.find_elements(By.CSS_SELECTOR, '#opts-1 .mcq-btn')
        opts[0].click()
        self.driver.find_element(By.ID, 'check-1').click()
        nav_dot = self.driver.find_element(By.ID, 'nav-1')
        classes = nav_dot.get_attribute('class')
        self.assertIn('bg-red-400', classes)

    def test_progress_bar_updates(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        opts = self.driver.find_elements(By.CSS_SELECTOR, '#opts-1 .mcq-btn')
        opts[0].click()
        self.driver.find_element(By.ID, 'check-1').click()
        progress_text = self.driver.find_element(By.ID, 'progress-text').text
        self.assertNotEqual(progress_text, '0 / 3')

    def test_search_bar_present(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        search = self.driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="Search"]')
        self.assertTrue(search.is_displayed())

    def test_filter_dropdowns_present(self):
        self.driver.get(f'{self.base_url}/question-bank/')
        selects = self.driver.find_elements(By.TAG_NAME, 'select')
        self.assertGreaterEqual(len(selects), 4)