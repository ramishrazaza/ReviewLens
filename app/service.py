"""Coordinate ingestion, caching, AI calls, and dashboard analytics."""
import time
from collections import Counter
from itertools import islice

from app import config, store
from app.ai import GeminiClient
from app.cleaning import clean_csv
from app.demo_data import demo_analysis, demo_reply


def batches(items, size=5):
    iterator = iter(items)
    while group := list(islice(iterator, size)):
        yield group


def import_csv(blob, filename='reviews.csv', client=None):
    start = time.perf_counter()
    rows = clean_csv(blob)
    originals = [r for r in rows if r['status'] == 'pending']
    if not config.DEMO_MODE and not config.is_configured() and client is None:
        raise ValueError('Gemini API key is missing. Set GEMINI_API_KEY in .env, or turn on explicit offline preview mode.')
    client = client or GeminiClient()
    cached = {} if config.DEMO_MODE else store.get_cached(originals)
    pending = []
    for row in originals:
        if row['hash'] in cached:
            row['analysis'] = cached[row['hash']]
            row['status'] = 'analysed'
        else:
            pending.append(row)
    for group in batches(pending, 5):
        if config.DEMO_MODE:
            results, failures = {r['row_num']: demo_analysis(r) for r in group}, {}
        else:
            results, failures = client.analyse_batch(group)
        for row in group:
            analysis = results.get(row['row_num'])
            if analysis is not None:
                row['analysis'] = analysis
                row['status'] = 'analysed'
                if not config.DEMO_MODE:
                    store.put_cached(row['hash'], analysis)
            else:
                row['status'] = 'analysis_failed'
                row['error'] = failures.get(row['row_num'], 'The LLM did not return valid structured JSON')[:180]
    # Duplicates are never analyzed twice; still appear for auditing.
    for row in rows:
        if row['status'] == 'duplicate':
            match = next((r for r in originals if r['hash'] == row['hash']), None)
            if match is not None:
                row['analysis'] = match['analysis']
    stats = {
        'total': len(rows), 'unique': len(originals),
        'analysed': sum(r['status'] == 'analysed' for r in rows),
        'skipped_empty': sum(r['status'] == 'empty' for r in rows),
        'duplicates': sum(r['status'] == 'duplicate' for r in rows),
        'failed': sum(r['status'] == 'analysis_failed' for r in rows),
        'cache_hits': len(cached), 'ai_calls': client.api_calls if not config.DEMO_MODE else 0,
        'rate_retries': client.rate_retries if not config.DEMO_MODE else 0,
        'duration_ms': round((time.perf_counter() - start) * 1000),
        'mode': 'offline_preview' if config.DEMO_MODE else 'gemini',
    }
    import_id = store.save_import(filename, rows, stats)
    return {'id': import_id, 'stats': stats, 'dashboard': dashboard_data(rows, stats, filename)}


def dashboard_data(rows, stats=None, filename=None):
    valid = [r for r in rows if r['status'] == 'analysed' and r['analysis'] is not None]
    total = len(valid)
    sentiment = Counter(r['analysis']['sentiment'] for r in valid)
    reply_count = sum(bool(r['analysis']['needs_reply']) for r in valid)
    ratings_compared, agreements = 0, 0
    for r in valid:
        rating = r['rating']
        if rating is None:
            continue
        ratings_compared += 1
        expected = 'positive' if rating >= 4 else 'negative' if rating <= 2 else 'neutral'
        agreements += expected == r['analysis']['sentiment']
        r['rating_mismatch'] = expected != r['analysis']['sentiment']
    counts = {'positive': sentiment['positive'], 'neutral': sentiment['neutral'], 'negative': sentiment['negative']}
    percent = {k: round(100 * v / total, 1) if total else 0 for k, v in counts.items()}

    def top_insights(target):
        counter = Counter()
        examples = {}
        for row in valid:
            if row['analysis']['sentiment'] != target:
                continue
            for topic in row['analysis']['topics']:
                counter[topic] += 1
                examples.setdefault(topic, row['analysis']['summary'])
        return [{'topic': k, 'count': v, 'example': examples[k]} for k, v in counter.most_common(3)]

    by_product = []
    for product in sorted({r['product'] for r in valid}):
        relevant = [r for r in valid if r['product'] == product]
        splits = Counter(r['analysis']['sentiment'] for r in relevant)
        issues = Counter(t for r in relevant if r['analysis']['sentiment'] == 'negative'
                         for t in r['analysis']['topics'])
        by_product.append({'name': product, 'count': len(relevant),
                           'positive': splits['positive'], 'neutral': splits['neutral'],
                           'negative': splits['negative'],
                           'issues': [{'topic': t, 'count': n} for t, n in issues.most_common(3)]})
    return {'filename': filename, 'stats': stats or {}, 'rows': rows,
            'overview': {'total': total, 'sentiment': counts, 'percent': percent,
                         'needs_reply': reply_count,
                         'rating_agreement': round(100 * agreements / ratings_compared, 1) if ratings_compared else None,
                         'ratings_compared': ratings_compared},
            'complaints': top_insights('negative'), 'praises': top_insights('positive'),
            'products': by_product}


def latest_dashboard():
    entry = store.last_import()
    if entry is None:
        return None
    return dashboard_data(entry['rows'], entry['stats'], entry['filename'])


def generate_reply(row_num, client=None):
    entry = store.last_import()
    if entry is None:
        raise ValueError('Please upload a file first.')
    row = next((r for r in entry['rows'] if r['row_num'] == row_num), None)
    if not row or row['status'] != 'analysed' or not row['analysis']['needs_reply']:
        raise ValueError('Suggested replies are only available for analysed complaints.')
    cached = None if config.DEMO_MODE else store.get_reply(row['hash'])
    if cached:
        return {'reply': cached, 'cached': True}
    if config.DEMO_MODE:
        return {'reply': demo_reply(row), 'cached': False, 'preview': True}
    client = client or GeminiClient()
    response = client.suggest_reply(row)
    store.put_reply(row['hash'], response)
    return {'reply': response, 'cached': False, 'preview': False}
