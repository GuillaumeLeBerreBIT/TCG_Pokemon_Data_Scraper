import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from app.UploadContent import UploadContentYouTube


class UploadMetadataTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.socket.connect', 'requests.sessions.Session.request'):
            blocker = patch(target, side_effect=AssertionError('Network forbidden'))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.uploader = UploadContentYouTube.__new__(UploadContentYouTube)
        self.uploader.artist_song = 'Artist_Song'
        self.uploader.card_count = 20
        self.uploader.set_expansion = 'Play! Pokémon Prize Pack Series Nine'
        self.uploader.tags = ['pokemon']
        self.uploader.video_path = 'offline-fixture.mp4'

    @patch('app.UploadContent.MediaFileUpload')
    def test_failed_run_title_fits_youtube_limit(self, media):
        youtube = Mock()
        with patch('app.UploadContent.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 14)
            self.uploader.initialize_upload(youtube)
        body = youtube.videos.return_value.insert.call_args.kwargs['body']
        title = body['snippet']['title']
        self.assertLessEqual(len(title), 100)
        self.assertIn(self.uploader.set_expansion, title)
        self.assertIn('November 2026', title)
        self.assertIn(self.uploader.set_expansion, body['snippet']['description'])

    @patch('app.UploadContent.MediaFileUpload')
    def test_extreme_name_keeps_title_valid(self, media):
        self.uploader.set_expansion = '<Name>\n' + 'Long expansion ' * 20
        youtube = Mock()
        self.uploader.initialize_upload(youtube)
        title = youtube.videos.return_value.insert.call_args.kwargs['body']['snippet']['title']
        self.assertTrue(0 < len(title) <= 100)
        for invalid in ('<', '>', '\n'):
            self.assertNotIn(invalid, title)

    def test_upload_error_preserves_original_cause(self):
        self.uploader.authenticate_youtube = Mock()
        original = ValueError('invalidTitle')
        self.uploader.initialize_upload = Mock(side_effect=original)
        with self.assertRaises(RuntimeError) as raised:
            self.uploader.upload_to_yt()
        self.assertIs(raised.exception.__cause__, original)
