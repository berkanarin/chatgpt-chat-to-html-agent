#!/usr/bin/env python3
"""Build deterministic, allowlisted source/skill archives; exclude private inputs."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ['README.md', 'AGENT.md', 'AGENTS.md', 'CHANGELOG.md', 'THIRD_PARTY.md', '.gitignore', '.gitattributes',
           'package.json', 'package-lock.json', 'skills', 'scripts', 'examples', 'tests', '.github']


def entries(paths):
    files = []
    for relative in paths:
        p = ROOT/relative
        candidates = [p] if p.is_file() else p.rglob('*')
        for f in candidates:
            if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc', '.zip', '.skill'):
                files.append(f)
    return sorted(set(files))


def pack(output, files, prefix):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            name = (Path(prefix)/path.relative_to(ROOT)).as_posix() if prefix else path.relative_to(ROOT/'skills').as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            data = path.read_bytes()
            if b'\0' not in data:
                data = data.replace(b'\r\n', b'\n')
            z.writestr(info, data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'dist')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bundle = args.output/'chatgpt-chat-to-html-agent.zip'
    skill = args.output/'chatgpt-chat-to-html.skill'
    pack(bundle, entries(ALLOWED), 'chatgpt-chat-to-html-agent')
    pack(skill, entries(['skills/chatgpt-chat-to-html']), '')
    checksums = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (bundle, skill)}
    (args.output/'SHA256SUMS.json').write_text(json.dumps(checksums, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'bundle': str(bundle), 'skill': str(skill), 'sha256': checksums}, indent=2))


if __name__ == '__main__':
    main()
