import unittest
from app.validation import AnalysisValidationError, validate_analysis

GOOD = {'sentiment': 'negative', 'topics': ['quality', 'support'],
        'summary': 'The device stopped working.', 'needs_reply': True}


class ValidationTests(unittest.TestCase):
    def test_accepts_exact_schema(self):
        self.assertEqual(validate_analysis(GOOD), GOOD)

    def test_rejects_wrong_sentiment_and_extra_keys(self):
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'sentiment': 'horrible'})
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'confidence': 99})
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'sentiment': ['negative']})

    def test_rejects_bad_topics_and_boolean_strings(self):
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'topics': ['refund']})
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'needs_reply': 'true'})
        with self.assertRaises(AnalysisValidationError):
            validate_analysis({**GOOD, 'summary': 'Good\nBad'})


if __name__ == '__main__':
    unittest.main()
