"""Validate a browser-assisted share capture and adapt it to the offline renderer.

Only local, explicitly captured files are opened. No browser credentials, network
requests or signed URLs belong in the durable capture manifest.
"""
from __future__ import annotations
import hashlib
import html
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlsplit


def share_url(value):
    if not isinstance(value, str):
        raise ValueError('Share URL must be text.')
    p = urlsplit(value)
    if (p.scheme != 'https' or p.netloc != 'chatgpt.com' or p.query or p.fragment or
            not re.fullmatch(r'/share/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', p.path)):
        raise ValueError('Expected a canonical https://chatgpt.com/share/<id> URL without query/fragment.')
    return value


def normalize_capture(source: Path, converter, strip_metadata=True):
    c = converter
    document = json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(document, dict) or document.get('schemaVersion') != 1 or document.get('kind') != 'chatgpt-share-capture':
        raise c.ExportError('Expected schemaVersion 1 chatgpt-share-capture.')
    url = share_url(document.get('sourceUrl', ''))
    messages = document.get('messages', [])
    if not isinstance(messages, list) or not messages:
        raise c.ExportError('The capture contains no messages.')
    ids, media_ids, problems = [], [], []
    def problem(kind, target, step='capture'):
        item = {'kind': kind, 'target': str(target), 'step': step}
        if item not in problems:
            problems.append(item)
    for message in messages:
        if not isinstance(message, dict) or message.get('role') not in ('user', 'assistant'):
            raise c.ExportError('Capture messages need a user/assistant role.')
        if not isinstance(message.get('id'), str) or not message['id'] or message['id'] in ids:
            raise c.ExportError('Missing or duplicate capture message ID.')
        ids.append(message['id'])
        if not isinstance(message.get('text'), str) or message.get('format') not in ('plain', 'markdown'):
            raise c.ExportError('Capture messages need text and format: plain/markdown.')
        if not message['text'].strip() and not message.get('media'):
            problem('empty_message', message['id'])
        if not isinstance(message.get('media', []), list):
            raise c.ExportError('Capture media must be an array.')
        for media in message.get('media', []):
            if not isinstance(media, dict) or media.get('kind') not in ('image', 'file'):
                raise c.ExportError('Capture media need an image/file kind.')
            if not isinstance(media.get('id'), str) or not media['id'] or media['id'] in media_ids:
                raise c.ExportError('Missing or duplicate capture media ID.')
            if 'url' in media:
                raise c.ExportError('Do not persist temporary media URLs; use a local verified path.')
            media_ids.append(media['id'])

    scans = document.get('scans', [])
    if not isinstance(scans, list) or any(not isinstance(s, dict) for s in scans):
        raise c.ExportError('Capture scans must be an array of objects.')
    if len(scans) < 2:
        problem('incomplete_scan', 'Two complete, stable top-to-bottom scans are required')
    for scan in scans[-2:]:
        if scan.get('reachedTop') is not True or scan.get('reachedBottom') is not True:
            problem('incomplete_scan', 'Conversation boundaries were not both observed')
        if scan.get('messageIds') != ids:
            problem('message_inventory_mismatch', 'Missing, added or reordered messages between scans')
        if scan.get('mediaIds') != media_ids:
            problem('media_inventory_mismatch', 'Missing, added or reordered media between scans')
    for issue in document.get('issues', []):
        problem('capture_review_required', issue)

    # Reuse ZIP resource inspection/deduplication without extracting anything.
    buffer = io.BytesIO()
    captured_files, total = {}, 0
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('Capture.md', '# Browser capture')
        for message in messages:
            for media in message.get('media', []):
                mid = media['id']
                if media.get('status') != 'ready' or not media.get('path'):
                    problem('missing_capture_media', mid, message['id'])
                    continue
                relative = c.canonical(media['path'])
                file = (source.parent/relative).resolve()
                if not file.is_relative_to(source.parent.resolve()):
                    raise c.ExportError('Capture media must stay inside the capture folder, including symlinks.')
                if not file.is_file():
                    problem('missing_capture_media', mid, message['id']); continue
                size = file.stat().st_size
                total += size
                if size > c.MAX_MEMBER or total > c.MAX_TOTAL:
                    raise c.ExportError('Capture exceeds media size limits.')
                raw = file.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                if digest != media.get('sha256'):
                    problem('capture_checksum_mismatch', mid, message['id']); continue
                name = 'files/' + str(len(captured_files)) + Path(relative).suffix
                z.writestr(name, raw)
                captured_files[mid] = name
    buffer.seek(0)
    arc = c.Archive(buffer, 'Capture.md')
    arc.problems.extend(problems)
    steps, removed = [], 0
    try:
        for message in messages:
            is_user = message['role'] == 'user'
            if is_user:
                n = len(steps)+1
                steps.append({'id': f'step-{n:03}', 'title': f'Adım {n}', 'lessonTitle': f'Adım {n}',
                              'note': '', 'prompt': '', 'promptHtml': '', 'text': '', 'answerHtml': '',
                              'images': [], 'attachments': [], 'userFiles': [], 'files': [],
                              'compareTo': None, 'choice': None, 'sourceMessageIds': []})
            if not steps:
                arc.problem('orphan_assistant', message['id'], 'preamble'); continue
            step = steps[-1]
            step['sourceMessageIds'].append(message['id'])
            text, count = c.strip_export_metadata(message['text'], assistant=not is_user, enabled=strip_metadata)
            removed += count
            # Browser images are separate media records. Never re-interpret user
            # text as resource paths; it must remain exactly copyable.
            if message['format'] == 'markdown':
                renderer = c.MarkdownIt('commonmark', {'html': False}).enable('table')
                renderer.renderer.rules['image'] = lambda *args: '<span>[Görsel referansı]</span>'
                rendered = renderer.render(text)
            else:
                rendered = '<p>' + html.escape(text).replace('\n', '<br>') + '</p>' if text else ''
            field = 'prompt' if is_user else 'text'
            html_field = 'promptHtml' if is_user else 'answerHtml'
            step[field] += ('\n\n' if step[field] else '') + text
            step[html_field] += rendered
            for media in message.get('media', []):
                if media['id'] not in captured_files:
                    continue
                ref = arc.resource(captured_files[media['id']], media.get('name', ''), step['id'], media['kind'] == 'image')
                if not ref:
                    continue
                if media['kind'] == 'image' and (ref['width'], ref['height']) != (media.get('width'), media.get('height')):
                    arc.problem('capture_dimensions_mismatch', media['id'], step['id'])
                ref['name'] = Path(media.get('name') or ref['name']).name
                bucket = ('attachments' if is_user else 'images') if media['kind'] == 'image' else ('userFiles' if is_user else 'files')
                if not any(r['id'] == ref['id'] for r in step[bucket]):
                    step[bucket].append(ref)
        if not steps:
            raise c.ExportError('Capture has no user turns.')
        for step in steps:
            if len(step['sourceMessageIds']) < 2 or not (step['text'] or step['images'] or step['files']):
                arc.problem('missing_response', step['id'], step['id'])
        # Relocation, signed URL renewal and retry counts do not invalidate notes.
        stable = [{k: m[k] for k in ('id', 'role', 'text', 'format')} |
                  {'media': [{k: a.get(k) for k in ('id', 'kind', 'sha256')} for a in m.get('media', [])]} for m in messages]
        digest = hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        return {'schemaVersion': 1, 'generatorVersion': c.VERSION, 'title': document.get('title') or 'Paylaşılan sohbet',
                'sourceHash': digest, 'steps': steps, 'assets': arc.assets,
                'audit': {'sourceType': 'chatgpt-share-capture', 'sourceUrl': url,
                          'stepCount': len(steps), 'assetCount': len(arc.assets), 'messageCount': len(messages),
                          'scanCount': len(scans), 'references': arc.references, 'problems': arc.problems,
                          'unreferencedFiles': [], 'strippedMetadataBlocks': removed,
                          'completenessScope': 'Two stable scans of the accessible rendered branch; not hidden or deleted server data.'}}
    finally:
        arc.close()
