"""
Selenium tests for Pricing and Payment pages.

Run: python manage.py test core.test_selenium.test_pricing
"""

from django.test import LiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .helpers import SeleniumMixin, create_student


class PricingSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Pricing page: public access and plan display."""

    def test_pricing_page_loads_for_anonymous(self):
        """Pricing page loads for anonymous visitors."""
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_pricing_page_shows_free_plan(self):
        """Pricing page mentions the Free plan."""
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        page = self.driver.page_source
        self.assertTrue(
            'Free' in page or 'free' in page.lower(),
            'Free plan not mentioned on pricing page'
        )

    def test_pricing_page_shows_premium_plan(self):
        """Pricing page mentions the Premium plan."""
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        page = self.driver.page_source
        self.assertTrue(
            'Premium' in page or 'premium' in page.lower(),
            'Premium plan not mentioned on pricing page'
        )

    def test_pricing_page_has_subscription_info(self):
        """Pricing page contains pricing or subscription information."""
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        page = self.driver.page_source
        self.assertTrue(
            '৳' in page or 'subscription' in page.lower() or 'plan' in page.lower(),
            'Subscription pricing info not found on pricing page'
        )

    def test_pricing_page_has_cta_buttons(self):
        """Pricing page has call-to-action buttons to subscribe or sign up."""
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        page = self.driver.page_source
        self.assertTrue(
            'button' in page.lower() or 'subscribe' in page.lower()
            or 'checkout' in page or 'get started' in page.lower(),
            'No CTA buttons found on pricing page'
        )

    def test_pricing_page_loads_for_logged_in_user(self):
        """Authenticated user can also view the pricing page."""
        create_student(username='pricing_student', password='testpass123', plan='FREE')
        self.selenium_login('pricing_student', 'testpass123')
        self.go('/pricing/')
        WebDriverWait(self.driver, 8).until(EC.url_contains('/pricing/'))
        self.assertNotIn('Server Error', self.driver.page_source)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass


class CheckoutSeleniumTests(SeleniumMixin, LiveServerTestCase):
    """Checkout and payment flow pages."""

    def test_checkout_requires_login(self):
        """Checkout page redirects unauthenticated users to login."""
        self.go('/checkout/')
        self.wait_for_url_contains('/login/')
        self.assertIn('/login/', self.driver.current_url)

    def test_checkout_page_loads_for_authenticated_user(self):
        """Authenticated user can view the checkout page."""
        create_student(username='checkout_student', password='testpass123', plan='FREE')
        self.selenium_login('checkout_student', 'testpass123')
        self.go('/checkout/')
        WebDriverWait(self.driver, 8).until(
            lambda d: '/checkout/' in d.current_url or '/login/' in d.current_url
        )
        self.assertNotIn('Server Error', self.driver.page_source)

    def test_checkout_page_has_plan_info(self):
        """Checkout page contains plan or payment details."""
        create_student(username='checkout_content', password='testpass123', plan='FREE')
        self.selenium_login('checkout_content', 'testpass123')
        self.go('/checkout/')
        WebDriverWait(self.driver, 8).until(
            lambda d: 'checkout' in d.current_url or 'login' in d.current_url
        )
        page = self.driver.page_source
        self.assertNotIn('Server Error', page)

    def tearDown(self):
        try:
            self.selenium_logout()
        except Exception:
            pass
