"""SQLite persistence for the latest upload, review cache, and on-demand replies."""
import json
import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS analysis_cache (
                review_hash TEXT PRIMARY KEY, analysis TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reply_cache (
                review_hash TEXT PRIMARY KEY, reply TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
                stats TEXT NOT NULL, imported_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS review_rows (
                import_id INTEGER NOT NULL, row_num INTEGER NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(import_id, row_num)
            );
        ''')


def get_cached(reviews):
    if not reviews:
        return {}
    with connection() as db:
        hashes = [r['hash'] for r in reviews]
        result = {}
        for i in range(0, len(hashes), 500):
            part = hashes[i:i + 500]
            sql = 'SELECT review_hash, analysis FROM analysis_cache WHERE review_hash IN (' + ','.join('?' for _ in part) + ')'
            for row in db.execute(sql, part):
                result[row['review_hash']] = json.loads(row['analysis'])
        return result


def put_cached(review_hash, analysis):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO analysis_cache (review_hash, analysis) VALUES (?, ?)',
                   (review_hash, json.dumps(analysis, ensure_ascii=False)))


def save_import(filename, rows, stats):
    with connection() as db:
        cursor = db.execute('INSERT INTO imports (filename, stats) VALUES (?, ?)',
                            (filename[:160], json.dumps(stats)))
        import_id = cursor.lastrowid
        db.executemany('INSERT INTO review_rows (import_id, row_num, payload) VALUES (?, ?, ?)',
                       [(import_id, r['row_num'], json.dumps(r, ensure_ascii=False)) for r in rows])
        return import_id


def last_import():
    with connection() as db:
        entry = db.execute('SELECT * FROM imports ORDER BY id DESC LIMIT 1').fetchone()
        if entry is None:
            return None
        rows = [json.loads(r['payload']) for r in db.execute(
            'SELECT payload FROM review_rows WHERE import_id = ? ORDER BY row_num', (entry['id'],))]
        return {'id': entry['id'], 'filename': entry['filename'],
                'imported_at': entry['imported_at'], 'stats': json.loads(entry['stats']), 'rows': rows}


def get_reply(review_hash):
    with connection() as db:
        row = db.execute('SELECT reply FROM reply_cache WHERE review_hash = ?', (review_hash,)).fetchone()
        return row['reply'] if row else None


def put_reply(review_hash, reply):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO reply_cache(review_hash, reply) VALUES(?, ?)',
                   (review_hash, reply))
