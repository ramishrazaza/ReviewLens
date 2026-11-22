"""Strict, minimal contract for model-provided review assessments."""
import re

SENTIMENTS = {'positive', 'neutral', 'negative'}
TOPICS = {'quality', 'delivery', 'price', 'packaging', 'support', 'size_fit', 'other'}
KEYS = {'sentiment', 'topics', 'summary', 'needs_reply'}


class AnalysisValidationError(ValueError):
    pass


def validate_analysis(value):
    if not isinstance(value, dict) or set(value) != KEYS:
        raise AnalysisValidationError('Expected exactly four analysis fields')
    if value['sentiment'] not in SENTIMENTS:
        raise AnalysisValidationError('Invalid sentiment')
    topics = value['topics']
    if not isinstance(topics, list) or not topics or len(topics) > 7:
        raise AnalysisValidationError('Expected a nonempty topics array')
    if any(not isinstance(t, str) or t not in TOPICS for t in topics):
        raise AnalysisValidationError('Unexpected topic')
    if len(set(topics)) != len(topics):
        raise AnalysisValidationError('Duplicate topics')
    summary = value['summary']
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 300:
        raise AnalysisValidationError('Invalid one-line summary')
    if '\n' in summary or '\r' in summary or re.search(r'[\u0900-\u097F]', summary):
        raise AnalysisValidationError('Summary must be one line in English')
    if type(value['needs_reply']) is not bool:
        raise AnalysisValidationError('needs_reply must be boolean')
    return {'sentiment': value['sentiment'], 'topics': topics,
            'summary': summary.strip(), 'needs_reply': value['needs_reply']}
