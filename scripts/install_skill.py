#!/usr/bin/env python3
"""Copy the self-contained skill to a user-selected skills directory."""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination', type=Path, default=Path.home()/'.codex/skills',
                    help='Parent skills directory; defaults to ~/.codex/skills')
args = parser.parse_args()
source = ROOT/'skills/chatgpt-chat-to-html'
target = args.destination.resolve()/'chatgpt-chat-to-html'
if target.exists():
    parser.error(f'{target} already exists. Compare it first; installer does not overwrite.')
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'Installed: {target}')
print(f'Python dependencies: {target / "scripts/requirements.txt"}')
