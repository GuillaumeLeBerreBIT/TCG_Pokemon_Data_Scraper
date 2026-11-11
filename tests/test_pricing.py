import unittest
from app.pricing import format_card_price, positive_price


class PricingTests(unittest.TestCase):
    def test_zero_price_does_not_turn_into_float_none(self):
        self.assertEqual(format_card_price({'marketPrice': 0}), 'Price unavailable')
        self.assertEqual(format_card_price({'marketPrice': None, 'midPrice': None}), 'Price unavailable')

    def test_real_prices_keep_currency(self):
        self.assertEqual(format_card_price({'marketPrice': 194.31, 'currency': 'EUR'}), '€194.31')
        self.assertEqual(format_card_price({'marketPrice': '12.50'}), '$12.50')
        self.assertEqual(format_card_price({'marketPrice': None, 'midPrice': 10}), '$10.00')

    def test_invalid_prices_are_not_rendered(self):
        for value in (None, '', 'invalid', 'NaN', 'inf', -1, 0):
            with self.subTest(value=value):
                self.assertIsNone(positive_price(value))
                self.assertEqual(format_card_price({'marketPrice': value}), 'Price unavailable')
