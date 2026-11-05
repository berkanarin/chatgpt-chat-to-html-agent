#!/usr/bin/env python3
"""Portable structural check; behavior is covered by tests, not this validator."""
import re
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
skill = ROOT/'skills/chatgpt-chat-to-html'
text = (skill/'SKILL.md').read_text(encoding='utf-8')
assert text.startswith('---\n')
assert re.search(r'^name: chatgpt-chat-to-html$', text, re.M)
assert re.search(r'^description: .{30,}$', text, re.M)
for file in skill.rglob('*.md'):
    for block in MarkdownIt().parse(file.read_text(encoding='utf-8')):
        for token in block.children or []:
            if token.type != 'link_open':
                continue
            target = token.attrGet('href')
            if not target.startswith(('http:', 'https:', '#')):
                assert (file.parent/target).is_file(), f'Broken reference: {file} -> {target}'
assert '$chatgpt-chat-to-html' in (skill/'agents/openai.yaml').read_text(encoding='utf-8')
for required in ('scripts/chat_to_html.py', 'scripts/requirements.txt', 'assets/template.html', 'assets/runtime.js', 'assets/design.css'):
    assert (skill/required).is_file(), required
print('PASS: skill metadata, references, invocation and self-contained resources.')
