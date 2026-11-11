import unittest
from unittest.mock import patch, Mock
import tempfile
from datetime import datetime
from pathlib import Path
from app.TCGApi import TCGApi


class ApiDataTests(unittest.TestCase):
    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden in offline tests'))
        self.network.start()
        self.addCleanup(self.network.stop)
        clock = patch('app.TCGApi.datetime', wraps=datetime)
        self.clock = clock.start()
        self.clock.now.return_value = datetime(2026, 11, 11)
        self.addCleanup(clock.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = TCGApi.__new__(TCGApi)
        self.api.base_url = 'https://example.invalid/'
        self.api.headers = {}
        self.api.state = {'used_expansions': []}
        self.api.expansion_images_dir = self.tmp.name
        self.api.path_state = str(Path(self.tmp.name) / 'state.json')

    @patch('app.TCGApi.requests.get')
    def test_skips_future_and_missing_logos(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'data': [
            {'id': 747, 'name': 'Flowing Fists', 'released_at': '2027-02-05', 'logo': None},
            {'id': 748, 'name': 'Future with logo', 'released_at': '2999-01-01', 'logo': 'https://example.invalid/logo'},
            {'id': 749, 'name': 'No logo', 'released_at': '2020-01-01', 'logo': None},
            {'id': 437, 'name': 'Delta Reign', 'released_at': '2026-11-06', 'logo': 'https://example.invalid/logo', 'cards_total': 0},
        ], 'paging': {'total': 1}}
        self.assertEqual(self.api.get_expansion()['id'], 437)
        self.assertEqual(self.api.state['used_expansions'], ['Delta Reign'])
        self.assertEqual(get.call_count, 1)

    @patch('app.TCGApi.requests.get')
    def test_null_logo_does_not_request_details_or_download(self, get):
        self.api.expansion = {'id': 747, 'name': 'Flowing Fists', 'logo': None}
        get.return_value.json.return_value = {'data': self.api.expansion}
        self.assertIsNone(self.api.get_detail_expansion())
        get.assert_not_called()

    @patch('app.TCGApi.requests.get')
    def test_listing_logo_requires_only_image_download(self, get):
        self.api.expansion = {'id': 21, 'name': 'Crown Zenith', 'logo': 'https://example.invalid/logo'}
        get.return_value = Mock(status_code=200, content=b'fixture image')
        path = self.api.get_detail_expansion()
        self.assertEqual(Path(path).read_bytes(), b'fixture image')
        get.assert_called_once_with('https://example.invalid/logo')

    @patch('app.TCGApi.requests.get')
    def test_cards_with_zero_null_and_missing_prices(self, get):
        self.api.expansion = {'id': 21}
        cards = []
        for i, tcg, cm in [(1, 194.31, 259), (2, 0, 197), (3, None, 170), (4, None, None)]:
            cards.append({'name_numbered': f'Card {i}', 'image': f'https://example.invalid/{i}',
                          'prices': {'tcg_player': {'market_price': tcg, 'currency': 'EUR'},
                                     'cardmarket': {'lowest_near_mint': cm, 'currency': 'EUR'}}})
        cards.append({'name_numbered': 'No image', 'image': None})
        response = Mock(status_code=200)
        response.json.return_value = {'data': cards}
        get.side_effect = [response] + [Mock(status_code=200, content=b'image') for _ in range(4)]
        result = self.api.retrieve_cards_list()
        self.assertEqual(len(result), 4)
        self.assertEqual(result['Card 2']['marketPrice'], 197)
        self.assertEqual(result['Card 3']['marketPrice'], 170)
        self.assertEqual(result['Card 4']['marketPrice'], 0)
        self.assertEqual(result['Card 1']['currency'], 'EUR')
        self.assertEqual(list(result)[-1], 'Card 2')

    @patch('app.TCGApi.requests.get')
    def test_pagination_skips_ineligible_page(self, get):
        first = Mock(status_code=200)
        first.json.return_value = {'data': [{'name': 'No logo', 'logo': None}], 'paging': {'total': 2}}
        second = Mock(status_code=200)
        second.json.return_value = {'data': [{'id': 21, 'name': 'Crown Zenith', 'logo': 'https://example.invalid/logo'}], 'paging': {'total': 2}}
        get.side_effect = [first, second]
        self.assertEqual(self.api.get_expansion()['id'], 21)
        self.assertEqual(get.call_count, 2)

    @patch('app.TCGApi.requests.get')
    def test_http_failure_is_not_silently_an_empty_card_set(self, get):
        from requests.exceptions import HTTPError
        self.api.expansion = {'id': 21}
        get.return_value.raise_for_status.side_effect = HTTPError('429 quota exceeded')
        with self.assertRaises(HTTPError):
            self.api.retrieve_cards_list()
        self.assertEqual(get.call_count, 1)

    @patch('app.TCGApi.requests.get')
    def test_pipeline_continues_past_sets_with_too_few_cards(self, get):
        self.api.check_state = Mock()
        self.api.get_expansion = Mock(side_effect=[{'id': 437}, {'id': 21}])
        self.api.get_detail_expansion = Mock(return_value='fixture-logo.png')
        cards = {str(i): {'marketPrice': i} for i in range(15)}
        self.api.retrieve_cards_list = Mock(side_effect=[{}, cards])
        expansion, result, logo = self.api.get_cards_expansion()
        self.assertEqual(expansion['id'], 21)
        self.assertEqual(result, cards)
        self.assertEqual(logo, 'fixture-logo.png')
        get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
