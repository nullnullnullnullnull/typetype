#!/usr/bin/env python3
"""Validate pinned sources and generate the TypeType public dictionary bundle."""
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
SOURCES = LOCAL / 'sources'
PUBLIC = ROOT / 'public'
MANIFEST = json.loads(Path(__file__).with_name('dictionary-sources.json').read_text())
CNS_URL = 'https://www.cns11643.gov.tw/searchSY.jsp?ID=122'
NAER_PATH = quote('臺灣華語文能力基準漢字表_111-09-20.ods')
JACK_URL = f"https://raw.githubusercontent.com/Jackchows/Cangjie5/{MANIFEST['cangjieCommit']}"
URLS = {
    'moe.ods': 'https://language.moe.gov.tw/uploads/files/17694982751710.ods',
    'naer.ods': f'https://coct.naer.edu.tw/file/files/{NAER_PATH}',
    'Unihan.zip': 'https://www.unicode.org/Public/18.0.0/ucd/Unihan.zip',
    'Unicode-LICENSE.txt': 'https://www.unicode.org/license.txt',
    'cangjie5.txt': f'{JACK_URL}/Cangjie5.txt',
    'Cangjie5-LICENSE.txt': f'{JACK_URL}/LICENSE',
}
TABLE_NS = {'t': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'}
CNS_ROW = re.compile(
    r"<li aria-posinset='(\d+)'>[^\n]*?src='/char/sung/64/([\da-f]{4,6})\.png'"
    r" alt='([^']*)'></div><var>([^<]+)</var>"
)
FULL_CODE = re.compile(r'[a-y]{1,5}')
UNVERIFIED_TAGS = re.compile(r'[!Uuv]|MARK|\[i\]')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(task):
    target, url = task
    if target.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urlopen(url, timeout=20) as response:
                content = response.read()
            target.write_bytes(content)
            return
        except OSError:
            if attempt == 2:
                raise


def download():
    tasks = [(SOURCES / name, url) for name, url in URLS.items()]
    tasks += [
        (SOURCES / 'cns' / f'{page:02}.html', f'{CNS_URL}&page={page}')
        for page in range(1, 98)
    ]
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(fetch, tasks))


def ods_rows(filename):
    with ZipFile(SOURCES / filename) as archive:
        document = ET.fromstring(archive.read('content.xml'))
    table = document.find('.//t:table', TABLE_NS)
    for row in table.findall('t:table-row', TABLE_NS):
        cells = [''.join(cell.itertext()).strip() for cell in row]
        if cells and cells[0].isdigit():
            yield cells


def taiwan_characters():
    records = []
    for page in range(1, 98):
        html = (SOURCES / 'cns' / f'{page:02}.html').read_text()
        records.extend(CNS_ROW.findall(html))

    require([int(record[0]) for record in records] == list(range(1, 4809)),
            'CNS index must contain exactly 4808 entries in order')
    characters = [chr(int(code, 16)) for _, code, _, _ in records]
    require(len(set(characters)) == 4808, 'CNS index contains duplicate characters')
    require(all(character == unescape(record[2]) for character, record in zip(characters, records)),
            'CNS Unicode values differ from the display characters')
    canonical_index = ''.join(f'{cns_code}\t{character}\n' for character, (*_, cns_code) in zip(characters, records))
    require(sha256(canonical_index.encode()) == MANIFEST['cnsIndexSha256'], 'CNS index checksum changed')
    official = {row[3] for row in ods_rows('moe.ods')}
    require(official == set(characters),
            f'MOE/CNS differences: MOE only {sorted(official - set(characters))}, CNS only {sorted(set(characters) - official)}')
    return characters


def mainland_characters():
    with ZipFile(SOURCES / 'Unihan.zip') as archive:
        mappings = archive.read('Unihan_OtherMappings.txt').decode()
    records = re.findall(r'^U\+([0-9A-F]+)\tkTGH\t2013:(\d+)$', mappings, re.MULTILINE)
    ranked = sorted((int(rank), chr(int(code, 16))) for code, rank in records if int(rank) <= 3500)
    require([rank for rank, _ in ranked] == list(range(1, 3501)), 'Unihan indices 1–3500 are incomplete')
    characters = [character for _, character in ranked]
    require(len(set(characters)) == 3500, 'Unihan index contains duplicate characters')
    return characters


def character_codes(targets):
    approved = defaultdict(dict)
    excluded = defaultdict(list)
    for line in (SOURCES / 'cangjie5.txt').read_text(encoding='utf-8-sig').splitlines():
        fields = line.split('\t')
        if len(fields) < 2 or fields[0] not in targets:
            continue
        character, code, *notes = fields
        tag = ' '.join(notes)
        # The table includes compatibility lookups prefixed with X and Z.
        if not FULL_CODE.fullmatch(code) or UNVERIFIED_TAGS.search(tag) or (code.startswith('x') and 'O' not in tag):
            excluded[character].append({'code': code, 'tag': tag})
            continue
        approved[character][code.upper()] = 'O' in tag or approved[character].get(code.upper(), False)

    codes = {
        character: sorted(candidates, key=lambda code: (not candidates[code], code))
        for character, candidates in sorted(approved.items())
    }
    return codes, dict(sorted(excluded.items()))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def generate():
    for name, checksum in MANIFEST['sha256'].items():
        require(sha256((SOURCES / name).read_bytes()) == checksum, f'Source checksum changed: {name}')

    taiwan = taiwan_characters()
    mainland = mainland_characters()
    codes, excluded = character_codes(set(taiwan) | set(mainland))
    starter_tw = {row[1] for row in ods_rows('naer.ods') if row[3] in ('第1級', '第1*級')}
    require(len(starter_tw) == 246, 'NAER level 1 must contain 246 characters')
    starter_cn = set(''.join(Path(__file__).with_name('simplified-beginner.txt').read_text().split()))

    banks = {
        'traditional': {
            'full': [character for character in taiwan if character in codes],
            'beginner': [character for character in taiwan if character in codes and character in starter_tw],
        },
        'simplified': {
            'full': [character for character in mainland if character in codes],
            'beginner': [
                character for character in mainland
                if character in codes and character in starter_cn
                and len(codes[character][0]) <= 3
            ],
        },
    }

    report = {
        'sources': MANIFEST,
        'banks': {},
        'excludedCodes': excluded,
        'multipleCodes': [character for character, options in codes.items() if len(options) > 1],
    }
    for bank, original in [('traditional', taiwan), ('simplified', mainland)]:
        counts = {mode: len(members) for mode, members in banks[bank].items()}
        require(min(counts.values()) >= 20, f'{bank} cannot support 20 questions in each difficulty')
        report['banks'][bank] = {
            'sourceCharacters': len(original),
            **counts,
            'missingCharacters': [character for character in original if character not in codes],
        }

    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name in ['Unicode-LICENSE.txt', 'Cangjie5-LICENSE.txt']:
        shutil.copyfile(SOURCES / name, PUBLIC / name)
    write_json(PUBLIC / 'dictionaries.json', {'banks': banks, 'codes': codes})
    write_json(LOCAL / 'dictionary-report.json', report)
    print(json.dumps(report['banks'], ensure_ascii=False, indent=2))
    print(f'{len(codes)} unique playable characters, {len(report["multipleCodes"])} with multiple accepted codes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='download missing upstream sources')
    args = parser.parse_args()
    if args.download:
        download()
    generate()
