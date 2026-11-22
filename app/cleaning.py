"""Defensive CSV ingestion: invalid rows are flagged, not allowed to crash."""
import csv
import hashlib
import html
import io
import re
from html.parser import HTMLParser

MAX_BYTES = 3 * 1024 * 1024
MAX_ROWS = 2000
EXPECTED_COLUMNS = {'review_id', 'product', 'rating', 'date', 'review_text'}


class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []

    def handle_data(self, data):
        self.fragments.append(data)


def tidy_text(value):
    if not isinstance(value, str):
        return ''
    parser = _StripHTML()
    try:
        parser.feed(value)
        text = ' '.join(parser.fragments)
    except ValueError:
        text = html.unescape(re.sub(r'<[^>]+>', '', value))
    return ' '.join(text.split()).strip()


def text_hash(text):
    """Normalize spacing and casing for repeat detection and reusable cache."""
    return hashlib.sha256(' '.join(text.casefold().split()).encode('utf-8')).hexdigest()


def parse_rating(raw):
    try:
        value = int(str(raw).strip())
        return value if 1 <= value <= 5 else None
    except (TypeError, ValueError, OverflowError):
        return None


def clean_csv(blob):
    if len(blob) > MAX_BYTES:
        raise ValueError('The CSV exceeds the 3 MB upload limit.')
    try:
        decoded = blob.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Please upload a UTF-8 encoded CSV file.') from exc
    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=''))
        if not reader.fieldnames:
            raise ValueError('The CSV needs a header row.')
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        missing = EXPECTED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError('Missing CSV columns: ' + ', '.join(sorted(missing)))
        rows, seen = [], {}
        for index, entry in enumerate(reader, start=1):
            if index > MAX_ROWS:
                raise ValueError('CSV exceeds the 2,000 review limit.')
            raw = entry.get('review_text') or ''
            text = tidy_text(raw)
            original_rating = entry.get('rating', '')
            rating = parse_rating(original_rating)
            record = {
                'row_num': index,
                'review_id': (entry.get('review_id') or f'ROW-{index}').strip()[:60],
                'product': (entry.get('product') or 'Unknown product').strip()[:120],
                'rating': rating,
                'rating_unknown': rating is None,
                'date': (entry.get('date') or '').strip()[:30],
                'text': text[:5000],
                'hash': text_hash(text) if text else '',
                'status': 'pending',
                'duplicate_of': None,
                'analysis': None,
                'error': None,
            }
            if not text:
                record['status'] = 'empty'
                record['error'] = 'No review text'
            elif record['hash'] in seen:
                record['status'] = 'duplicate'
                record['duplicate_of'] = seen[record['hash']]
            else:
                seen[record['hash']] = record['review_id']
            rows.append(record)
    except csv.Error as exc:
        raise ValueError(f'Could not parse CSV: {exc}') from exc
    if not rows:
        raise ValueError('The CSV contains no reviews.')
    return rows
