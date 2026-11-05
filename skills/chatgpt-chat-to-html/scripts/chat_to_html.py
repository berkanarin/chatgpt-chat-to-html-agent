#!/usr/bin/env python3
"""Inspect a Markdown chat ZIP and build a portable, offline HTML replay.

No model/API calls, network access, extraction or executable transcript content.
See ../references/input-format.md for supported syntax and explicit limitations.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import re
import sys
import unicodedata
import warnings
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from PIL import Image

VERSION = '1.0.0'
SKILL = Path(__file__).resolve().parent.parent
MD = MarkdownIt('commonmark', {'html': False, 'linkify': False}).enable('table')
MAX_TOTAL = 256 * 1024 * 1024
MAX_MEMBER = 80 * 1024 * 1024
USER_ROLES = {'you', 'user', 'kullanıcı', 'sen'}
ASSISTANT_ROLES = {'chatgpt', 'assistant', 'asistan'}
IMAGE_TYPES = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp', 'GIF': 'image/gif'}


class ExportError(ValueError):
    pass


def canonical(name: str) -> str:
    name = unicodedata.normalize('NFC', name.replace('\\', '/'))
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or ':' in name or '\x00' in name:
        raise ExportError(f'Unsafe archive path: {name!r}')
    return p.as_posix()


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fenced_mask(text: str) -> list[bool]:
    """Mark fenced code so embedded headings/links are treated as examples."""
    mask = [False] * len(text)
    for token in MD.parse(text):
        if token.type not in ('fence', 'code_block') or token.map is None:
            continue
        lines = text.splitlines(keepends=True)
        start, end = (sum(map(len, lines[:x])) for x in token.map)
        mask[start:end] = [True] * (end - start)
    return mask


def links(text: str):
    """Exporter-compatible links: spaces, Unicode and balanced filename parentheses.

    Returns spans for inline links/images only. Reference-style links are resolved
    separately by MarkdownIt; unsupported local ones are reported, never fetched.
    """
    mask = fenced_mask(text)
    for code in re.finditer(r'(?<!`)(`+)(?!`)(.*?)\1(?!`)', text, re.S):
        if not mask[code.start()]:
            mask[code.start():code.end()] = [True] * (code.end()-code.start())
    pattern = re.compile(r'(!?)\[([^\]\n]*)\]\(')
    pos = 0
    while match := pattern.search(text, pos):
        if mask[match.start()] or (match.start() and text[match.start()-1] == '\\'):
            pos = match.end()
            continue
        depth, end = 1, match.end()
        while end < len(text) and depth:
            if text[end] == '\\':
                end += 2
                continue
            if text[end] == '(':
                depth += 1
            elif text[end] == ')':
                depth -= 1
            if depth:
                end += 1
        if depth:
            pos = match.end()
            continue
        target = text[match.end():end].strip()
        if target.startswith('<') and '>' in target:
            target = target[1:target.index('>')]
        else:
            target = re.sub(r'\s+["\'][^\n]*["\']$', '', target)
        target = re.sub(r'\\([()\\])', r'\1', target)
        yield match.start(), end+1, bool(match[1]), match[2], target
        pos = end+1


def strip_export_metadata(text: str, *, assistant: bool, enabled: bool) -> tuple[str, int]:
    if not enabled:
        return text.strip(), 0
    lines = text.splitlines(keepends=True)
    ranges = []
    tokens = MD.parse(text)
    for i, token in enumerate(tokens[:-1]):
        if token.type != 'heading_open' or token.level != 0 or token.tag != 'h3' or token.map is None:
            continue
        label = tokens[i+1].content.strip()
        known = re.fullmatch(r'(?:Thinking|Worked for .+|\d+s düşündü|Birkaç saniye düşündü)', label)
        if not known:
            continue
        start = token.map[0]
        end = len(lines)
        for later in tokens[i+2:]:
            if later.type == 'heading_open' and later.map and int(later.tag[1:]) <= 3:
                end = later.map[0]
                break
        body = ''.join(lines[token.map[1]:end]).strip()
        # Thinking isn't automatically private reasoning: strip only recognisable
        # exporter/tool bookkeeping, and preserve arbitrary readable summaries.
        tool_only = bool(re.fullmatch(r'```json\s*\{[^`]*\}\s*```', body, re.S))
        generated_path = body.startswith('Generated images from the last `image_gen.')
        duration = label != 'Thinking' and (not body or body.strip('*').strip() == label)
        if duration or (assistant and (tool_only or generated_path)):
            ranges.append((start, end))
    excluded = {i for start, end in ranges for i in range(start, end)}
    kept = ''.join(line for i, line in enumerate(lines) if i not in excluded)
    if assistant:
        # Only paragraph-prefixed exporter captions; never remove user prompt text.
        kept, captions = re.subn(r'(?m)^Model caption:.*?(?=\n\s*\n|\Z)', '', kept, flags=re.S)
    else:
        captions = 0
    return kept.strip(), len(ranges) + captions


class Archive:
    def __init__(self, source: Path, member: str | None = None):
        self.z = zipfile.ZipFile(source)
        self.entries = {}
        total = 0
        for entry in self.z.infolist():
            name = canonical(entry.filename)
            if entry.is_dir():
                continue
            total += entry.file_size
            if entry.file_size > MAX_MEMBER or total > MAX_TOTAL:
                raise ExportError('Archive exceeds the 80 MiB/member or 256 MiB total limit.')
            if name in self.entries:
                raise ExportError(f'Duplicate normalized archive path: {name}')
            self.entries[name] = entry
        markdowns = [n for n in self.entries if n.lower().endswith('.md')]
        if member:
            self.member = canonical(member)
            if self.member not in markdowns:
                raise ExportError(f'Markdown member not found: {member}')
        elif len(markdowns) == 1:
            self.member = markdowns[0]
        else:
            raise ExportError(f'Choose one Markdown file with --markdown; found: {markdowns}')
        self.text = self.z.read(self.entries[self.member]).decode('utf-8-sig')
        self.assets = {}
        self.problems = []
        self.references = []
        self.used = {self.member}

    def problem(self, kind, target, step):
        item = {'kind': kind, 'target': target, 'step': step}
        if item not in self.problems:
            self.problems.append(item)

    def resource(self, target: str, alt: str, step: str, image: bool):
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or target.startswith('#'):
            if image:
                self.problem('remote_image', target, step)
            return None
        try:
            path = canonical((PurePosixPath(self.member).parent / unquote(parts.path)).as_posix())
        except ExportError:
            self.problem('unsafe_reference', target, step)
            return None
        if path not in self.entries:
            self.problem('missing_file', target, step)
            return None
        self.used.add(path)
        data = self.z.read(self.entries[path])
        digest = hashlib.sha256(data).hexdigest()
        asset_id = 'asset-' + digest[:20]
        width = height = None
        mime = 'application/octet-stream'
        is_image = False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as picture:
                    if picture.format in IMAGE_TYPES:
                        mime = IMAGE_TYPES[picture.format]
                        width, height = picture.size
                        picture.verify()
                        is_image = True
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            pass
        if image and not is_image:
            self.problem('unsupported_image', path, step)
            return None
        if asset_id not in self.assets:
            self.assets[asset_id] = {'mime': mime, 'bytes': len(data), 'sha256': digest,
                                     'data': f'data:{mime};base64,' + base64.b64encode(data).decode(),
                                     'paths': [path]}
        elif path not in self.assets[asset_id]['paths']:
            self.assets[asset_id]['paths'].append(path)
        ref = {'id': asset_id, 'alt': alt or PurePosixPath(path).name,
               'name': PurePosixPath(path).name, 'path': path, 'image': is_image}
        if is_image:
            ref.update(width=width, height=height)
        self.references.append({'step': step, 'path': path, 'asset': asset_id})
        return ref

    def content(self, text: str, step: str):
        pictures, files, substitutions = [], [], []
        for start, end, image, alt, target in links(text):
            remote = bool(urlsplit(target).scheme or target.startswith(('#', '//')))
            if remote and not image:
                continue
            ref = self.resource(target, alt, step, image)
            if ref:
                bucket = pictures if image else files
                if not any(i['id'] == ref['id'] for i in bucket):
                    bucket.append(ref)
                substitutions.append((start, end, ''))
            else:
                substitutions.append((start, end, f'[Dosya alınamadı: {alt or target}]'))
        clean = text
        for start, end, replacement in reversed(substitutions):
            clean = clean[:start] + replacement + clean[end:]

        # Disable remaining reference-style/HTML images to keep the output offline.
        renderer = MarkdownIt('commonmark', {'html': False}).enable('table')
        def missing_image(tokens, idx, options, env):
            target = tokens[idx].attrGet('src') or ''
            self.problem('unresolved_image_syntax', target, step)
            return '<span class="missing-file">[Görsel dışa aktarılamadı]</span>'
        def safe_link(tokens, idx, options, env):
            target = tokens[idx].attrGet('href') or ''
            if urlsplit(target).scheme not in ('http', 'https', 'mailto'):
                self.problem('unresolved_link', target, step)
                return '<span class="unresolved-link">'
            return '<a href="' + html.escape(target, quote=True) + '" target="_blank" rel="noopener noreferrer">'
        # Pair tag names rather than allowing a local link to escape to disk.
        link_stack = []
        def open_link(tokens, idx, options, env):
            rendered = safe_link(tokens, idx, options, env)
            link_stack.append('a' if rendered.startswith('<a ') else 'span')
            return rendered
        def close_link(tokens, idx, options, env):
            return '</' + link_stack.pop() + '>'
        renderer.renderer.rules.update(image=missing_image, link_open=open_link, link_close=close_link)
        rendered = renderer.render(clean)
        return clean.strip(), rendered, pictures, files

    def close(self):
        self.z.close()


def normalize(source: Path, member=None, strip_metadata=True):
    arc = Archive(source, member)
    try:
        tokens = MD.parse(arc.text)
        lines = arc.text.splitlines(keepends=True)
        headings, title = [], PurePosixPath(arc.member).stem
        for i, token in enumerate(tokens[:-1]):
            if token.type != 'heading_open' or token.level != 0 or not token.map:
                continue
            label = tokens[i+1].content.strip()
            if token.tag == 'h1' and not headings:
                title = label
            if token.tag not in ('h2', 'h3'):
                continue
            role = label.casefold()
            if role in USER_ROLES | ASSISTANT_ROLES:
                headings.append(('user' if role in USER_ROLES else 'assistant', *token.map))
        if not headings:
            raise ExportError('No speaker headings found. Expected ## You / ## ChatGPT (or documented aliases).')
        groups = []
        for i, (role, start, content_start) in enumerate(headings):
            end = headings[i+1][1] if i+1 < len(headings) else len(lines)
            body = ''.join(lines[content_start:end]).strip()
            if role == 'user':
                groups.append({'user': body, 'assistant': []})
            elif groups:
                groups[-1]['assistant'].append(body)
            else:
                arc.problem('orphan_assistant', 'Response before the first user message', 'preamble')
        if not groups:
            raise ExportError('The export has no user turns.')
        steps, removed = [], 0
        for i, group in enumerate(groups):
            sid = f'step-{i+1:03}'
            user, n1 = strip_export_metadata(group['user'], assistant=False, enabled=strip_metadata)
            assistant, n2 = strip_export_metadata('\n\n'.join(group['assistant']), assistant=True, enabled=strip_metadata)
            removed += n1+n2
            prompt, user_html, attached_images, user_files = arc.content(user, sid)
            answer, answer_html, pictures, answer_files = arc.content(assistant, sid)
            if not group['assistant']:
                arc.problem('missing_response', sid, sid)
            steps.append({'id': sid, 'title': f'Adım {i+1}', 'lessonTitle': f'Adım {i+1}',
                          'note': '', 'prompt': prompt, 'promptHtml': user_html,
                          'text': answer, 'answerHtml': answer_html,
                          'images': pictures, 'attachments': attached_images,
                          'userFiles': user_files, 'files': answer_files,
                          'compareTo': None, 'choice': None})
        source_hash = hashlib.sha256(arc.text.encode('utf-8')).hexdigest()
        return {'schemaVersion': 1, 'generatorVersion': VERSION, 'title': title,
                'sourceHash': source_hash, 'steps': steps, 'assets': arc.assets,
                'audit': {'markdown': arc.member, 'stepCount': len(steps), 'assetCount': len(arc.assets),
                          'references': arc.references, 'problems': arc.problems,
                          'unreferencedFiles': sorted(set(arc.entries)-arc.used),
                          'strippedMetadataBlocks': removed}}
    finally:
        arc.close()


def apply_lessons(data, lesson_path: Path | None, require=False):
    if lesson_path:
        notes = json.loads(lesson_path.read_text(encoding='utf-8-sig'))
        if not isinstance(notes, dict) or notes.get('schemaVersion') != 1:
            raise ExportError('Lessons must be an object with schemaVersion: 1.')
        if notes.get('sourceHash') != data['sourceHash']:
            raise ExportError('Lesson sourceHash does not match this Markdown export. Inspect again before editing lessons.')
        items = notes.get('steps', [])
        if not isinstance(items, list) or len(items) != len(data['steps']):
            raise ExportError('Lessons must contain one entry per source step.')
        for i, (step, note) in enumerate(zip(data['steps'], items)):
            if not isinstance(note, dict):
                raise ExportError('Each lesson entry must be an object.')
            if note.get('id') != step['id']:
                raise ExportError('Lesson IDs must match source order exactly.')
            for key in ('title', 'lessonTitle', 'note'):
                if key in note:
                    if not isinstance(note[key], str):
                        raise ExportError(f'{step["id"]}.{key} must be text.')
                    step[key] = note[key]
            target = note.get('compareTo')
            if target is not None:
                earlier = next((s for s in data['steps'][:i] if s['id'] == target), None)
                if not earlier or not earlier['images'] or not step['images']:
                    raise ExportError(f'{step["id"]}: compareTo must name an earlier step with images; both steps need an image.')
                step['compareTo'] = target
            choice = note.get('choice')
            if choice is not None:
                if not isinstance(choice, dict) or not isinstance(choice.get('options'), list) or not choice['options']:
                    raise ExportError('choice requires a nonempty options array.')
                if not all(isinstance(x, str) for x in choice['options']):
                    raise ExportError('choice options must be strings.')
                if type(choice.get('selected')) is not int or not 0 <= choice['selected'] < len(choice['options']):
                    raise ExportError('choice.selected must index the recorded selection.')
                step['choice'] = choice
                # An explicitly reviewed choice may replace exported GenUI markup;
                # the original text remains in the payload for traceability.
                if '{@body' in step['text']:
                    step['answerHtml'] = MD.render(step['text'].split('{@body', 1)[0])
        if notes.get('title'):
            data['title'] = str(notes['title'])
    if require and any(not s['note'].strip() or not s['lessonTitle'].strip() for s in data['steps']):
        raise ExportError('Every step needs a reviewed lessonTitle and note with --require-lessons.')


def scaffold(data):
    return {'schemaVersion': 1, 'sourceHash': data['sourceHash'], 'title': data['title'],
            'steps': [{k: step[k] for k in ('id', 'title', 'lessonTitle', 'note', 'compareTo', 'choice')}
                      for step in data['steps']]}


def build(data, output: Path, allow_missing=False):
    problems = data['audit']['problems']
    if problems and not allow_missing:
        raise ExportError('Export has unresolved items. Inspect the report, repair the source or explicitly use --allow-missing: ' +
                          ', '.join(sorted({p['kind'] for p in problems})))
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = (SKILL / 'assets/template.html').read_text(encoding='utf-8')
    replacements = {'/*__PAYLOAD__*/': payload,
                    '/*__TITLE__*/': html.escape(data['title'], quote=True),
                    '/*__RUNTIME__*/': (SKILL / 'assets/runtime.js').read_text(encoding='utf-8'),
                    '/*__STYLES__*/': (SKILL / 'assets/design.css').read_text(encoding='utf-8')}
    template = re.sub(r'/\*__(?:PAYLOAD|TITLE|RUNTIME|STYLES)__\*/',
                      lambda match: replacements[match[0]], template)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template, encoding='utf-8')
    return {'output': str(output), 'bytes': output.stat().st_size,
            'steps': len(data['steps']), 'assets': len(data['assets']), 'problems': len(problems)}


def validate(path: Path):
    text = path.read_text(encoding='utf-8')
    match = re.search(r'<script type="application/json" id="conversation-data">(.*?)</script>', text, re.S)
    if not match:
        raise ExportError('Missing embedded conversation-data.')
    data = json.loads(match[1])
    if not data.get('steps'):
        raise ExportError('No steps embedded.')
    for key, asset in data['assets'].items():
        raw = base64.b64decode(asset['data'].split(',', 1)[1], validate=True)
        if hashlib.sha256(raw).hexdigest() != asset['sha256'] or len(raw) != asset['bytes']:
            raise ExportError(f'Asset checksum/size mismatch: {key}')
    for step in data['steps']:
        for key in ('images', 'attachments', 'userFiles', 'files'):
            for ref in step[key]:
                if ref['id'] not in data['assets']:
                    raise ExportError(f'Broken asset reference: {ref["id"]}')
    if re.search(r'<(?:script|img|link|iframe)\b[^>]*(?:src|href)=["\'](?:https?:|//|files/)', text, re.I):
        raise ExportError('External runtime resource found.')
    return {'valid': True, 'steps': len(data['steps']), 'assets': len(data['assets']),
            'scope': 'payload, checksums and external resource references; not browser layout'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'build'):
        p = commands.add_parser(command)
        p.add_argument('source', type=Path)
        p.add_argument('--markdown', help='Markdown member when a ZIP contains several')
        p.add_argument('--keep-metadata', action='store_true')
        if command == 'inspect':
            p.add_argument('--report', type=Path)
            p.add_argument('--lessons-out', type=Path)
        else:
            p.add_argument('--output', type=Path, required=True)
            p.add_argument('--lessons', type=Path)
            p.add_argument('--require-lessons', action='store_true')
            p.add_argument('--allow-missing', action='store_true')
            p.add_argument('--title')
    p = commands.add_parser('validate')
    p.add_argument('html', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            result = validate(args.html)
        else:
            data = normalize(args.source, args.markdown, not args.keep_metadata)
            if args.command == 'inspect':
                result = {k: v for k, v in data.items() if k != 'assets'}
                result['assets'] = {k: {a: b for a, b in v.items() if a != 'data'} for k, v in data['assets'].items()}
                if args.report:
                    dump(args.report, result)
                if args.lessons_out:
                    if args.lessons_out.exists():
                        raise ExportError('Refusing to overwrite an existing lesson file; choose a new --lessons-out path.')
                    dump(args.lessons_out, scaffold(data))
                if args.report:
                    result = {'report': str(args.report), **data['audit']}
            else:
                apply_lessons(data, args.lessons, args.require_lessons)
                if args.title:
                    data['title'] = args.title
                result = build(data, args.output, args.allow_missing)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ExportError, OSError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
