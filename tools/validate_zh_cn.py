#!/usr/bin/env python3
"""Reproduce/check the display-only patch against the pinned upstream commit (stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '90d9568d576d93ebb2d6c1c207596d21e9900651'
MENU = 'OptiScaler/menu/menu_common.cpp'
PROJECT = 'OptiScaler/OptiScaler.vcxproj'
DATA = ROOT / 'tools/l10n/zh-CN.json'
LEX = re.compile(r'//[^\n]*|/\*.*?\*/|\'(?:\\.|[^\'\\])*\'|(?:u8|L|u|U)?"(?:\\.|[^"\\])*"', re.S)
PRINTF = re.compile(r'%(?:%|(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|I64|I32|[hljztL])?[diuoxXfFeEgGaAcspn])')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def upstream(path):
    return git('show', BASE + ':' + path).decode('utf-8-sig')


def literals(text):
    return [m for m in LEX.finditer(text) if m.group().startswith('"')]


def translate(text, records):
    tokens = literals(text)
    edits = []
    seen = set()
    for r in records:
        i, source, target = r['index'], r['source'], r['target']
        assert i not in seen, f'duplicate index {i}'
        seen.add(i)
        m = tokens[i]
        assert m.group()[1:-1] == source, f'source drift at {i}'
        assert text.count('\n', 0, m.start()) + 1 == r['line'], f'line drift at {i}'
        assert PRINTF.findall(source) == PRINTF.findall(target), f'printf mismatch at {i}: {source}'
        assert re.findall(r'\{[^{}]*\}', source) == re.findall(r'\{[^{}]*\}', target), f'format mismatch at {i}'
        assert re.findall(r'##.*', source) == re.findall(r'##.*', target), f'hidden ID mismatch at {i}'
        assert '\n' not in target and '\r' not in target
        assert not re.search(r'(?<!\\)"', target), f'unescaped quote at {i}'
        # Translating logs or include directives is never allowed.
        line = text[text.rfind('\n', 0, m.start()) + 1:text.find('\n', m.end())]
        assert not re.search(r'LOG_|#include', line), f'non-UI string at {i}'
        edits.append((m.start(), m.end(), '"' + target + '"'))
    for start, end, value in sorted(edits, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def format_menu(text, stage, executable=None):
    # Apply clang-format's recorded UTF-8 byte offsets only AFTER baseline translation/font patches.
    # Exact input/config hashes prevent drift; the validator still needs only Python stdlib + Git.
    raw = text.encode('utf-8')
    assert stage['version'] == '20.1.8'
    assert hashlib.sha256(raw).hexdigest() == stage['input_sha256'], 'format input drift'
    assert hashlib.sha256((ROOT / '.clang-format').read_bytes()).hexdigest() == stage['style_sha256'], 'format style drift'
    end = len(raw)
    for patch in reversed(stage['replacements']):
        start, length = patch['offset'], patch['length']
        assert 0 <= start <= start + length <= end, 'invalid/overlapping format offsets'
        old, new = raw[start:start + length], patch['text'].encode('utf-8')
        assert not old.strip() and not new.strip(), 'format edit is not whitespace-only'
        raw = raw[:start] + new + raw[start + length:]
        end = start
    formatted = raw.decode('utf-8')
    # Also preserve comments and whole literal tokens, including whitespace inside strings.
    tokens = re.compile(LEX.pattern + r'|\S', re.S)
    assert tokens.findall(text) == tokens.findall(formatted), 'formatter changed non-whitespace tokens'
    if executable:
        version = subprocess.check_output([executable, '--version'], text=True)
        assert re.search(r'\bversion 20\.1\.8\b', version), f'clang-format version drift: {version}'
        actual = subprocess.check_output(
            [executable, '--style=file', '--assume-filename=' + str(ROOT / MENU)],
            input=text.encode('utf-8')).decode('utf-8')
        assert actual == formatted, 'recorded replacements differ from clang-format 20.1.8'
    return formatted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='apply to an otherwise baseline menu/project only')
    parser.add_argument('--inventory', action='store_true', help='print all baseline string literals, including non-UI tokens')
    parser.add_argument('--verify-clang-format', metavar='PATH', help='also reproduce recorded edits with clang-format 20.1.8')
    args = parser.parse_args()
    if args.inventory:
        text = upstream(MENU)
        print(json.dumps([{'index': i, 'line': text.count('\n', 0, m.start()) + 1,
                           'source': m.group()[1:-1]} for i, m in enumerate(literals(text))],
                         ensure_ascii=False, indent=2))
        return
    data = json.loads(DATA.read_text(encoding='utf-8'))
    menu = translate(upstream(MENU), data['translations'])
    for patch in data['font_patches']:
        assert menu.count(patch['old']) == 1
        menu = menu.replace(patch['old'], patch['new'], 1)
    menu = format_menu(menu, data['clang_format'], args.verify_clang_format)
    def utf8(match):
        block = match.group()
        if '<AdditionalOptions>' in block:
            return block.replace('<AdditionalOptions>', '<AdditionalOptions>/utf-8 ', 1)
        return block.replace('</ClCompile>', '  <AdditionalOptions>/utf-8 %(AdditionalOptions)</AdditionalOptions>\n    </ClCompile>')
    project = re.sub(r'<ClCompile>.*?</ClCompile>', utf8, upstream(PROJECT), flags=re.S)
    expected = {MENU: menu, PROJECT: project}
    if args.apply:
        for path, value in expected.items():
            current = (ROOT / path).read_text(encoding='utf-8-sig')
            assert current in (upstream(path), value), f'refusing to overwrite changes in {path}'
        for path, value in expected.items():
            (ROOT / path).write_text('\ufeff' + value, encoding='utf-8')
    for path, value in expected.items():
        assert (ROOT / path).read_text(encoding='utf-8-sig') == value, f'unapproved change in {path}'
    for path, sha in data['support_hashes'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, f'support file drift: {path}'
    # Every tracked file outside the explicit allowlist, including all INIs, must be byte-identical.
    allowed = {MENU, PROJECT, *data['support_hashes'], 'tools/validate_zh_cn.py', 'tools/l10n/zh-CN.json',
               'docs/LOCALIZATION.zh-CN.md', '.github/workflows/build-zh-cn.yml',
               'tools/l10n/font_smoke.cpp', 'tools/l10n/test-font.ps1'}
    changed = set(git('diff', '--name-only', BASE).decode().splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    assert changed <= allowed, f'out-of-scope changes: {changed - allowed}'
    ini_files = [p for p in git('ls-tree', '-r', '--name-only', BASE).decode().splitlines() if p.lower().endswith('.ini')]
    for path in ini_files:
        assert (ROOT / path).read_bytes() == git('show', BASE + ':' + path), f'INI changed: {path}'
    print(f'PASS: {len(data["translations"])} literal occurrences; printf/format/hidden IDs preserved; '
          f'exact display/font/project reconstruction; {len(ini_files)} INIs byte-identical; tracked diff allowlist.')


if __name__ == '__main__':
    main()
