import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/chatgpt-chat-to-html/scripts'))
import chat_to_html as c


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        buf = io.BytesIO(); Image.new('RGB', (40, 20), 'navy').save(buf, 'PNG')
        self.raw = buf.getvalue()
        (self.root/'image.png').write_bytes(self.raw)
        self.capture = {'schemaVersion': 1, 'kind': 'chatgpt-share-capture',
                        'sourceUrl': 'https://chatgpt.com/share/00000000-0000-0000-0000-000000000001',
                        'title': 'Synthetic', 'issues': [], 'messages': [
                            {'id': 'u1', 'role': 'user', 'text': '# Komut\n\nSatır 2', 'format': 'markdown', 'media': []},
                            {'id': 'a1', 'role': 'assistant', 'text': '', 'format': 'plain', 'media': [
                                {'id': 'a1:image:0', 'kind': 'image', 'name': 'Örnek.png', 'path': 'image.png',
                                 'status': 'ready', 'sha256': hashlib.sha256(self.raw).hexdigest(), 'width': 40, 'height': 20}]}]}
        scan = {'reachedTop': True, 'reachedBottom': True, 'messageIds': ['u1', 'a1'], 'mediaIds': ['a1:image:0']}
        self.capture['scans'] = [dict(scan), dict(scan)]
        self.path = self.root/'capture.json'

    def normalize(self):
        c.dump(self.path, self.capture)
        return c.normalize(self.path)

    def test_complete_capture_embeds_original_bytes_and_exact_prompt(self):
        data = self.normalize()
        self.assertEqual(data['audit']['problems'], [])
        self.assertEqual(data['steps'][0]['prompt'], '# Komut\n\nSatır 2')
        self.assertEqual(len(data['assets']), 1)
        c.build(data, self.root/'output.html')
        self.assertTrue(c.validate(self.root/'output.html')['valid'])
        self.assertNotIn('image.png', (self.root/'output.html').read_text(encoding='utf-8'))

    def test_truncated_scan_or_missing_message_blocks_build(self):
        self.capture['scans'][1]['messageIds'] = ['u1']
        self.capture['scans'][0]['reachedTop'] = False
        data = self.normalize()
        self.assertEqual({p['kind'] for p in data['audit']['problems']}, {'message_inventory_mismatch', 'incomplete_scan'})
        with self.assertRaises(c.ExportError): c.build(data, self.root/'out.html')

    def test_expired_or_failed_media_is_never_a_complete_export(self):
        media = self.capture['messages'][1]['media'][0]
        media.update(status='missing', attempts=3)
        data = self.normalize()
        self.assertIn('missing_capture_media', [p['kind'] for p in data['audit']['problems']])
        with self.assertRaises(c.ExportError): c.build(data, self.root/'out.html')

    def test_corrupt_bytes_and_wrong_thumbnail_dimensions_are_reported(self):
        (self.root/'image.png').write_bytes(b'<Error>AuthenticationFailed</Error>')
        data = self.normalize()
        self.assertIn('capture_checksum_mismatch', [p['kind'] for p in data['audit']['problems']])
        (self.root/'image.png').write_bytes(self.raw)
        self.capture['messages'][1]['media'][0]['width'] = 10
        self.assertIn('capture_dimensions_mismatch', [p['kind'] for p in self.normalize()['audit']['problems']])

    def test_invalid_image_even_with_matching_checksum_is_rejected(self):
        raw = b'<html>Login</html>'; (self.root/'image.png').write_bytes(raw)
        self.capture['messages'][1]['media'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertIn('unsupported_image', [p['kind'] for p in self.normalize()['audit']['problems']])

    def test_paths_signed_urls_duplicates_and_foreign_sources_are_rejected(self):
        media = self.capture['messages'][1]['media'][0]
        for path in ('../private.png', 'C:/private.png', '/private.png'):
            media['path'] = path
            with self.assertRaises(c.ExportError): self.normalize()
        media['path'] = 'image.png'; media['url'] = 'https://example.invalid/private?token=secret'
        with self.assertRaises(c.ExportError): self.normalize()
        del media['url']
        self.capture['messages'][1]['id'] = 'u1'
        with self.assertRaises(c.ExportError): self.normalize()
        self.capture['messages'][1]['id'] = 'a1'
        self.capture['sourceUrl'] = 'https://evil.invalid/share/x'
        with self.assertRaises(ValueError): self.normalize()

    def test_retry_and_relocation_do_not_change_source_hash(self):
        first = self.normalize()['sourceHash']
        media = self.capture['messages'][1]['media'][0]
        (self.root/'renamed.png').write_bytes(self.raw)
        media.update(path='renamed.png', attempts=3)
        self.assertEqual(first, self.normalize()['sourceHash'])

    def test_extra_attachment_or_unsupported_widget_requires_review(self):
        self.capture['scans'][1]['mediaIds'] = []
        self.capture['issues'] = ['unsupported_embed:a1']
        data = self.normalize()
        self.assertEqual({p['kind'] for p in data['audit']['problems']}, {'media_inventory_mismatch', 'capture_review_required'})

    def test_markdown_attachment_is_a_file_not_an_extra_conversation(self):
        raw = b'# Attachment\nOriginal file bytes'
        (self.root/'notes.md').write_bytes(raw)
        media = self.capture['messages'][1]['media'][0]
        media.update(kind='file', name='notes.md', path='notes.md', sha256=hashlib.sha256(raw).hexdigest())
        data = self.normalize()
        self.assertEqual(data['audit']['problems'], [])
        self.assertEqual(len(data['steps'][0]['files']), 1)
        self.assertEqual(data['steps'][0]['files'][0]['name'], 'notes.md')


if __name__ == '__main__': unittest.main()
