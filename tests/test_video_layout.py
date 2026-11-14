"""Exercise the actual frame renderer with local synthetic artwork, never auth/API calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from app.VideoCreation import VideoCreation
from app.pricing import psa10_price

REPO = Path(__file__).resolve().parents[1]


def make_renderer(root):
    root = Path(root)
    (root / 'temp' / 'images').mkdir(parents=True, exist_ok=True)
    if not (root / 'font').exists():
        (root / 'font').symlink_to(REPO / 'font', target_is_directory=True)
    # Avoid __init__: it refreshes Google credentials and is unnecessary for rendering.
    renderer = VideoCreation.__new__(VideoCreation)
    renderer.BASE_DIR = str(root)
    renderer.width, renderer.height = 1080, 1980
    renderer.shorts_safe_bottom = 1730
    renderer._name_font_cache = {}
    renderer.NAME_FONT_MAX, renderer.NAME_FONT_MIN = 120, 64
    font_path = str(REPO / 'font' / 'Bangers-Regular.ttf')
    renderer.font_type_large = ImageFont.truetype(font_path, 150)
    renderer.font_type_cards = ImageFont.truetype(font_path, 120)
    renderer.font_type_price = ImageFont.truetype(font_path, 90)
    renderer.font_type_psa = ImageFont.truetype(font_path, 64)
    renderer.fillcolor = (255, 255, 255)
    renderer.shadowcolor_cards = renderer.shadowcolor_headers = 'black'
    # Use the bundled background and clearly marked local placeholder card art.
    renderer.background_image = str(REPO / 'backgrounds' / 'Giratina.jpg')
    card_path = root / 'fixture-card.png'
    card = Image.new('RGB', (600, 840), '#e9c951')
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((20, 20, 580, 820), radius=20, fill='#243545', outline='white', width=4)
    draw.multiline_text((70, 330), 'OFFLINE\nCARD PREVIEW', font=ImageFont.truetype(font_path, 60), fill='white')
    card.save(card_path)
    renderer.header_image_path = str(root / 'temp' / 'images' / '{}_HEADER.jpg')
    return renderer, str(card_path)


class VideoLayoutTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.socket.connect', 'requests.sessions.Session.request'):
            blocker = patch(target, side_effect=AssertionError('Network forbidden in offline tests'))
            blocker.start()
            self.addCleanup(blocker.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.renderer, self.card_path = make_renderer(tmp.name)

    def render_text(self, card):
        original = ImageDraw.Draw
        draws = []

        def tracking_draw(*args, **kwargs):
            draw = original(*args, **kwargs)
            draw.text = unittest.mock.Mock(wraps=draw.text)
            draws.append(draw)
            return draw

        with patch('app.VideoCreation.ImageDraw.Draw', side_effect=tracking_draw):
            outputs = self.renderer.process_cards({'Origin Forme Palkia VSTAR GG67': dict(card, imgPath=self.card_path)})
        with Image.open(outputs[0]) as output:
            self.assertEqual(output.size, (1080, 1980))
        calls = [call for draw in draws for call in draw.text.call_args_list]
        return calls

    def test_psa_badge_uses_usd_without_changing_eur_market_price(self):
        calls = self.render_text({'marketPrice': 194.31, 'currency': 'EUR', 'psa10Price': 622.8})
        texts = [call.args[1] for call in calls]
        self.assertIn('€194.31', texts)
        self.assertIn('PSA 10 $622.80', texts)
        psa = next(call for call in calls if call.args[1].startswith('PSA 10'))
        draw = ImageDraw.Draw(Image.new('RGB', (1080, 1980)))
        bounds = draw.textbbox(psa.args[0], psa.args[1], font=psa.kwargs['font'])
        self.assertLessEqual(bounds[2], 940)
        self.assertLessEqual(bounds[3], self.renderer.shorts_safe_bottom)

    def test_missing_and_invalid_psa_are_omitted(self):
        for price in (None, 0, -1, 'invalid', 'NaN'):
            with self.subTest(price=price):
                calls = self.render_text({'marketPrice': 0, 'psa10Price': price})
                texts = [call.args[1] for call in calls]
                self.assertIn('Price unavailable', texts)
                self.assertFalse(any(text.startswith('PSA 10') for text in texts))

    def test_long_name_fits_available_space(self):
        draw = ImageDraw.Draw(Image.new('RGB', (1080, 1980)))
        font, lines, _, height = self.renderer.fit_name_block(
            draw, "#20 Origin Forme Palkia VSTAR Special Illustration Rare GG67", 980, 250)
        self.assertLessEqual(height, 250)
        self.assertTrue(all(draw.textlength(line, font=font) <= 980 for line in lines))

    def test_header_renders_multiline_date(self):
        logo = Path(self.card_path).with_name('fixture-logo.png')
        Image.new('RGBA', (600, 200), '#245684').save(logo)
        self.renderer.create_header_image(str(logo))
        self.assertTrue(Path(self.renderer.header_image_path).exists())

    def test_supplied_psa_payload_and_incomplete_variants(self):
        card = {'prices': {'ebay': {'currency': 'USD', 'graded': {
            'psa': {'10': {'median_price': 622.8, 'sample_size': 5}}}}}}
        self.assertEqual(psa10_price(card), 622.8)
        entry = card['prices']['ebay']['graded']['psa']['10']
        entry['sample_size'] = 4
        self.assertIsNone(psa10_price(card))
        entry['sample_size'] = None
        self.assertIsNone(psa10_price(card))
        self.assertIsNone(psa10_price({'prices': None}))
        self.assertIsNone(psa10_price({'prices': {'ebay': {'graded': []}}}))
