import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('converter', ROOT/'skills/chatgpt-chat-to-html/scripts/chat_to_html.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def png(color='navy', size=(32, 18)):
    b = io.BytesIO(); Image.new('RGB', size, color).save(b, format='PNG'); return b.getvalue()


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, md, files=None, member='Sohbet.md'):
        path = self.root/'source.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr(member, md)
            for name, value in (files or {}).items():
                z.writestr(name, value)
        return path

    def notes(self, data):
        notes = c.scaffold(data)
        for s in notes['steps']:
            s.update(lessonTitle='Kararı incele.', note='Bu adım kayıttaki değişimi gösteriyor.')
        path = self.root/'lessons.json'; c.dump(path, notes); return path

    def test_variable_turns_and_fenced_headings(self):
        md = '# Örnek\n## User\n```md\n## ChatGPT\nörnek\n```\n## Assistant\nBir\n## Assistant\nİki\n## User\nSon\n## Assistant\nBitti'
        data = c.normalize(self.archive(md))
        self.assertEqual(len(data['steps']), 2)
        self.assertIn('## ChatGPT', data['steps'][0]['prompt'])
        self.assertIn('Bir\n\nİki', data['steps'][0]['text'])

    def test_unicode_parentheses_percent_paths_and_dedup(self):
        payload = png()
        md = '# Örnek\n## You\nÜret\n## ChatGPT\n![İlk](files/İlk görsel (1).png)\n![Tekrar](files/kopya.png)\n![URL](files/%C4%B0lk%20g%C3%B6rsel%20(1).png)'
        data = c.normalize(self.archive(md, {'files/İlk görsel (1).png': payload, 'files/kopya.png': payload}))
        self.assertEqual(len(data['assets']), 1)
        self.assertEqual(len(data['steps'][0]['images']), 1)
        self.assertEqual(data['steps'][0]['images'][0]['width'], 32)
        self.assertEqual(data['audit']['problems'], [])

    def test_quoted_speaker_heading_is_not_a_turn(self):
        data = c.normalize(self.archive('## You\n> ## Assistant\n> quoted example\n## ChatGPT\nActual response'))
        self.assertEqual(len(data['steps']), 1)
        self.assertIn('quoted example', data['steps'][0]['prompt'])
        self.assertEqual(data['steps'][0]['text'], 'Actual response')

    def test_nested_markdown_and_downloadable_bytes(self):
        data = c.normalize(self.archive('## Sen\n[Ek](files/a.csv)\n## Asistan\nAlındı',
                                        {'course/files/a.csv': 'a,b\n1,2\n'}, member='course/Sohbet.md'))
        ref = data['steps'][0]['userFiles'][0]
        asset = data['assets'][ref['id']]
        self.assertEqual(asset['mime'], 'application/octet-stream')
        self.assertEqual(c.base64.b64decode(asset['data'].split(',')[1]), b'a,b\n1,2\n')

    def test_code_link_examples_are_not_downloads(self):
        data = c.normalize(self.archive('## You\n`![demo](missing.png)`\n```md\n![demo](missing2.png)\n```\n## ChatGPT\nKod örneği.'))
        self.assertEqual(data['audit']['problems'], [])
        self.assertIn('missing.png', data['steps'][0]['prompt'])

    def test_missing_files_fail_unless_explicit_partial(self):
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\n![x](files/absent.png)'))
        with self.assertRaises(c.ExportError):
            c.build(data, self.root/'out.html')
        c.build(data, self.root/'out.html', allow_missing=True)
        self.assertTrue(c.validate(self.root/'out.html')['valid'])
        self.assertEqual(data['audit']['problems'][0]['kind'], 'missing_file')

    def test_unsafe_archive_and_reference(self):
        with self.assertRaises(c.ExportError):
            c.normalize(self.archive('## You\nx\n## ChatGPT\ny', {'../outside.txt': 'no'}))
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\n[x](../outside.txt)'))
        self.assertEqual(data['audit']['problems'][0]['kind'], 'unsafe_reference')
        self.assertFalse((self.root.parent/'outside.txt').exists())

    def test_multiple_markdown_requires_selection(self):
        path = self.archive('## You\nx\n## ChatGPT\ny', {'Other.md': '## You\na\n## ChatGPT\nb'})
        with self.assertRaises(c.ExportError):
            c.normalize(path)
        self.assertEqual(c.normalize(path, 'Other.md')['steps'][0]['prompt'], 'a')

    def test_metadata_cleanup_preserves_user_but_hides_assistant_thinking(self):
        source = '## You\n### Thinking\nBu gerçek bir prompt.\n## ChatGPT\nCevap\n### Thinking\nBu okunabilir bir açıklama.\n### Worked for 2s\n*Worked for 2s*'
        data = c.normalize(self.archive(source))
        self.assertIn('Bu gerçek', data['steps'][0]['prompt'])
        self.assertNotIn('Bu okunabilir', data['steps'][0]['text'])
        self.assertNotIn('Worked for', data['steps'][0]['text'])
        self.assertIn('Worked for', c.normalize(self.archive(source), strip_metadata=False)['steps'][0]['text'])

    def test_tool_error_appended_to_user_is_hidden_but_prompt_is_copyable(self):
        prompt = 'Satır 1\n\n  Satır 2 — **aynı**'
        source = '## You\n' + prompt + '\n\n### Thinking\nError parsing function call: Invalid JSON\n\n## ChatGPT\nTamam'
        data = c.normalize(self.archive(source))
        self.assertEqual(data['steps'][0]['prompt'], prompt)
        self.assertNotIn('Error parsing', data['steps'][0]['promptHtml'])
        self.assertEqual(data['audit']['strippedMetadataBlocks'], 1)

    def test_reasoning_cleanup_keeps_final_response_images_and_code_examples(self):
        source = '## You\nÜret\n## ChatGPT\n### Thinking\nAra değerlendirme\n![çıktı](a.png)\n### Sonuç\nHazır\n\n```text\nError parsing function call: example\n```'
        data = c.normalize(self.archive(source, {'a.png': png()}))
        self.assertNotIn('Ara değerlendirme', data['steps'][0]['text'])
        self.assertIn('Hazır', data['steps'][0]['text'])
        self.assertIn('example', data['steps'][0]['text'])
        self.assertEqual(len(data['steps'][0]['images']), 1)

    def test_standalone_tool_error_hidden_and_empty_response_flagged(self):
        data = c.normalize(self.archive('## User\nError parsing function call: bunu açıkla\n## Assistant\nError parsing function call: Invalid JSON'))
        self.assertIn('bunu açıkla', data['steps'][0]['prompt'])
        self.assertEqual(data['steps'][0]['text'], '')
        self.assertEqual(data['audit']['problems'][0]['kind'], 'missing_response')

    def test_raw_html_and_template_markers_stay_inert(self):
        md = '# /*__RUNTIME__*/\n## You\n</script><script>window.pwned=1</script>\n## ChatGPT\n<img src="https://example.invalid/x" onerror="alert(1)">\n\n**Güvenli**'
        data = c.normalize(self.archive(md))
        self.assertNotIn('<img ', data['steps'][0]['answerHtml'])
        self.assertIn('<strong>Güvenli</strong>', data['steps'][0]['answerHtml'])
        out = self.root/'safe.html'; c.build(data, out)
        payload = json.loads(c.re.search(r'id="conversation-data">(.*?)</script>', out.read_text(encoding='utf-8'), c.re.S)[1])
        self.assertIn('</script>', payload['steps'][0]['prompt'])
        self.assertEqual(payload['title'], '/*__RUNTIME__*/')
        self.assertTrue(c.validate(out)['valid'])

    def test_lessons_hash_order_and_empty_notes(self):
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\ny'))
        with self.assertRaises(c.ExportError):
            c.apply_lessons(data, None, require=True)
        notes = self.notes(data); c.apply_lessons(data, notes, require=True)
        changed = json.loads(notes.read_text(encoding='utf-8')); changed['sourceHash'] = 'wrong'; c.dump(notes, changed)
        with self.assertRaises(c.ExportError):
            c.apply_lessons(data, notes)

    def test_comparison_mapping_and_choice_validation(self):
        md = '## You\na\n## ChatGPT\n![a](a.png)\n## You\nb\n## ChatGPT\n![b](b.png)'
        data = c.normalize(self.archive(md, {'a.png': png(), 'b.png': png('gold')}))
        path = self.notes(data); notes = json.loads(path.read_text(encoding='utf-8'))
        notes['steps'][1]['compareTo'] = 'step-001'; c.dump(path, notes)
        c.apply_lessons(data, path); self.assertEqual(data['steps'][1]['compareTo'], 'step-001')
        notes['steps'][0]['compareTo'] = 'step-002'; c.dump(path, notes)
        with self.assertRaises(c.ExportError): c.apply_lessons(data, path)
        notes['steps'][0]['compareTo'] = None
        notes['steps'][1]['choice'] = {'options': ['a'], 'selected': 2}; c.dump(path, notes)
        with self.assertRaises(c.ExportError): c.apply_lessons(data, path)

    def test_remote_image_not_fetched_and_normal_citation_kept(self):
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\n![remote](https://example.invalid/a.png)\n[Kaynak](https://example.org/)'))
        self.assertEqual(data['assets'], {})
        self.assertIn('remote_image', [p['kind'] for p in data['audit']['problems']])
        self.assertIn('rel="noopener noreferrer"', data['steps'][0]['answerHtml'])

    def test_reference_style_image_reported(self):
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\n![x][ref]\n\n[ref]: files/a.png', {'files/a.png': png()}))
        self.assertIn('unresolved_image_syntax', [p['kind'] for p in data['audit']['problems']])

    def test_checksum_validation_detects_tampering(self):
        data = c.normalize(self.archive('## You\nx\n## ChatGPT\n![x](a.png)', {'a.png': png()}))
        data['assets'][next(iter(data['assets']))]['sha256'] = '0'*64
        out = self.root/'bad.html'; c.build(data, out)
        with self.assertRaises(c.ExportError): c.validate(out)

    def test_orphan_and_missing_response_reported(self):
        data = c.normalize(self.archive('## Assistant\nÖnceki mesaj\n## User\nYanıt yok'))
        self.assertEqual({p['kind'] for p in data['audit']['problems']}, {'orphan_assistant', 'missing_response'})


if __name__ == '__main__':
    unittest.main()
