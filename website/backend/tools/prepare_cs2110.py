"""Import the CS 2110 Fall 2026 textbook readings and supplementary lab decks.

Only generated private outputs contain course content. See website/README.md.
"""
from pathlib import Path
from collections import Counter
from zipfile import ZipFile
import argparse
import base64
import gzip
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from pypdf import PdfReader

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, required=True, help='Folder containing the syllabus, textbook PDF and lab PPTX files')
parser.add_argument('--output', type=Path, required=True, help='Private output directory; never commit its contents')
args = parser.parse_args()
ROOT = args.input.resolve()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
TEXTBOOK = next(ROOT.glob('Introduction*.pdf'))
reader = PdfReader(TEXTBOOK)
pdf = pdfium.PdfDocument(str(TEXTBOOK))

def clean(text):
    text = unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n')
    # PDFium represents discretionary word breaks using U+FFFE in this book.
    text = re.sub(r'[\u00ad\ufffe]\n?', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

def flatten(items):
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item

boundaries = []
for item in flatten(reader.outline):
    title = item.title
    section = re.match(r'^(\d+\.\d+)\s', title)
    if section or title == 'Exercises' or re.match(r'^\d+\.\s', title):
        boundaries.append({'page': reader.get_destination_page_number(item),
                           'title': clean(title),
                           'section': section.group(1) if section else None})

# The syllabus names stacks but prints 8.1 (subroutines) for that row.
# Include 8.2 to cover the explicitly named stack topic and record the decision.
selected = {b['section'] for b in boundaries if b['section']
            and 1 <= int(b['section'].split('.')[0]) <= 20
            and not b['section'].startswith('10.') and b['section'] != '8.3'}

chunks = []
superscripts_preserved = 0
manifest = {'course_id': 'cs2110', 'name': 'Computer Organization and Programming',
            'term': 'Fall 2026', 'scope_source': 'Syllabus Fall_2026.pdf, page 1',
            'textbook_sections': sorted(selected, key=lambda s: tuple(map(int, s.split('.')))),
            'scope_decisions': [
                'Use all readings listed on syllabus page 1, including introduction to C++.',
                'Treat printed 5-1-5.2 as sections 5.1-5.2.',
                'Include 8.2 because the syllabus explicitly names Stack despite citing 8.1.',
                'Exclude chapter 10, section 8.3, end-of-chapter exercises, appendices and answer keys.',
                'Lab slides are supplementary course material; retain both alternate Lab 05 and Lab 06 versions.',
                'Syllabus controls scope; administrative pages are not part of the tutoring corpus.'
            ],
            'sources': [], 'extraction_warnings': [],
            'validation_questions': [
                'why can the bus only hold one value?',
                'what is the addressability of memory?',
                'what is the purpose of using typedef before instantiating a struct?'
            ]}

def add_chunks(text, source, details, **metadata):
    text = clean(text)
    if not text:
        return
    # Keep source page / slide boundaries; split long pages near a line boundary.
    start = 0
    while start < len(text):
        end = min(start + 2400, len(text))
        if end < len(text):
            line = text.rfind('\n', start + 1400, end)
            if line > start:
                end = line
        value = text[start:end].strip()
        if value:
            chunks.append({'text': value, 'source': source, 'details': details,
                           'course_id': 'cs2110', **metadata})
        if end == len(text):
            break
        start = max(start + 1, end - 350)

def page_text(textpage):
    """Keep raised, smaller glyph runs as explicit exponents (2^(n), 2^(34))."""
    global superscripts_preserved
    text = textpage.get_text_range()
    boxes = {}
    def box(index):
        if index not in boxes:
            ci = pdfium_raw.FPDFText_GetCharIndexFromTextIndex(textpage, index)
            boxes[index] = textpage.get_charbox(ci, loose=True) if ci >= 0 else None
        return boxes[index]
    insertions = []
    i = 1
    while i < len(text):
        if not (text[i].isalnum() and text[i-1].isalnum()):
            i += 1
            continue
        prev, curr = box(i-1), box(i)
        if not prev or not curr:
            i += 1
            continue
        ph, ch = prev[3]-prev[1], curr[3]-curr[1]
        if not (ph > 3 and .45*ph < ch < .85*ph and curr[1] > prev[1]+.18*ph
                and -.2*ph < curr[0]-prev[2] < .5*ph):
            i += 1
            continue
        end = i+1
        while end < len(text) and text[end].isalnum():
            nxt = box(end)
            last = box(end-1)
            if not nxt or abs(nxt[1]-curr[1]) > 1 or nxt[0]-last[2] > .5*ph:
                break
            end += 1
        insertions.append((i, end))
        i = end
    for start, end in reversed(insertions):
        text = text[:start] + '^(' + text[start:end] + ')' + text[end:]
    superscripts_preserved += len(insertions)
    return clean(text)

boundary_pages = {}
for boundary in boundaries:
    boundary_pages.setdefault(boundary['page'], []).append(boundary)

current = None
pages_included = set()
for i in range(29, 679):
    page = pdf[i]
    tp = page.get_textpage()
    text = page_text(tp)
    tp.close()
    page.close()
    lines = text.splitlines()
    if lines and (re.match(r'^\d+\s+chapter\s+\d+\b', lines[0], re.I)
                  or re.match(r'^\d+(?:\.\d+)+\s+.*\s+\d+$', lines[0])):
        text = '\n'.join(lines[1:])
    events = []
    for boundary in boundary_pages.get(i, []):
        title = boundary['title']
        if boundary['section']:
            pattern = r'(?m)^' + re.escape(boundary['section']) + r'[ \t]+'
            match = re.search(pattern, text)
        elif title == 'Exercises':
            match = re.search(r'(?m)^Exercises\s*$', text)
        else:
            # Chapter titles precede the first section; use the first section's
            # event to activate content and the chapter start to close old scope.
            events.append((0, boundary))
            continue
        if not match:
            raise RuntimeError(f'Missing section boundary {title!r} on PDF page {i+1}')
        events.append((match.start(), boundary))
    events.sort(key=lambda x: x[0])
    offset = 0
    for pos, boundary in events + [(len(text), None)]:
        if current and current['section'] in selected and pos > offset:
            segment = text[offset:pos].strip()
            if segment:
                pages_included.add(i + 1)
                add_chunks(segment, 'CS 2110 — Patt & Patel, Introduction to Computing Systems, 3rd ed.',
                           f"Section {current['title']}; printed p. {reader.page_labels[i]}; PDF p. {i+1}",
                           doc_type='textbook', section=current['section'], pdf_page=i+1,
                           printed_page=reader.page_labels[i])
        if boundary is not None:
            current = boundary
        offset = pos

manifest['sources'].append({'path': str(TEXTBOOK), 'sha256': hashlib.sha256(TEXTBOOK.read_bytes()).hexdigest(),
                            'pdf_pages_total': len(reader.pages), 'pdf_pages_included': len(pages_included)})

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
empty_slides = []
low_text_slides = []
for path in sorted(ROOT.rglob('*.pptx')):
    with ZipFile(path) as archive:
        members = sorted((n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                         key=lambda n: int(re.search(r'slide(\d+)', n).group(1)))
        for member in members:
            number = int(re.search(r'slide(\d+)', member).group(1))
            xml = ET.fromstring(archive.read(member))
            paragraphs = [''.join(t.text or '' for t in p.findall('.//a:t', NS))
                          for p in xml.findall('.//a:p', NS)]
            text = clean('\n'.join(p for p in paragraphs if p.strip()))
            if not text:
                empty_slides.append(f'{path.name}, slide {number}')
            elif len(text) < 80:
                low_text_slides.append(f'{path.name}, slide {number}')
            add_chunks(text, f'CS 2110 — {path.stem}', f'Slide {number}',
                       doc_type='slides', filename=path.name, slide=number)
    manifest['sources'].append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                'slides': len(members)})

manifest['extraction_warnings'] = [
    'Text extraction does not describe embedded circuit diagrams, images, or handwritten content.',
    'Slides with no extractable text are omitted; slides with sparse text may rely on diagrams.'
]
manifest['empty_slides'] = empty_slides
manifest['sparse_slides'] = low_text_slides
seen_slides = {}
deduplicated = []
slide_aliases = []
for chunk in chunks:
    if chunk['doc_type'] != 'slides':
        deduplicated.append(chunk)
        continue
    key = re.sub(r'\s+', ' ', chunk['text']).strip()
    if key in seen_slides:
        original = seen_slides[key]
        slide_aliases.append({'retained': {'source': original['source'], 'details': original['details']},
                              'duplicate': {'source': chunk['source'], 'details': chunk['details']}})
    else:
        seen_slides[key] = chunk
        deduplicated.append(chunk)
chunks = deduplicated
manifest['duplicate_slide_text'] = slide_aliases
manifest['superscript_runs_preserved'] = superscripts_preserved
manifest['counts'] = {'chunks': len(chunks), 'by_type': dict(Counter(c['doc_type'] for c in chunks)),
                      'textbook_pages': len(pages_included), 'slide_decks': len(manifest['sources'])-1,
                      'empty_slides': len(empty_slides), 'sparse_slides': len(low_text_slides),
                      'duplicate_slide_chunks_removed': len(slide_aliases),
                      'superscript_runs_preserved': superscripts_preserved}
syllabus = ROOT / 'Syllabus Fall_2026.pdf'
manifest['syllabus'] = {'path': str(syllabus), 'sha256': hashlib.sha256(syllabus.read_bytes()).hexdigest()}
(OUT / 'corpus.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in chunks), encoding='utf-8')
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
# A plaintext secret-file envelope keeps the corpus outside the public image.
minimal = ''.join(json.dumps({key: c[key] for key in ('text', 'source', 'details')},
                            ensure_ascii=False, separators=(',', ':')) + '\n' for c in chunks).encode('utf-8')
(OUT / 'cs2110.jsonl.gz.b64').write_bytes(base64.b64encode(gzip.compress(minimal, mtime=0)))
print(json.dumps(manifest['counts'], indent=2))
print('Prepared:', OUT)
