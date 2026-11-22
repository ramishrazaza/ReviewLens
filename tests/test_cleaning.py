import unittest
from pathlib import Path

from app.cleaning import clean_csv, parse_rating, text_hash, tidy_text

ROOT = Path(__file__).resolve().parent.parent


class CleaningTests(unittest.TestCase):
    def test_assessment_fixture_cleaning(self):
        rows = clean_csv((ROOT / 'reviews.csv').read_bytes())
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(r['status'] == 'pending' for r in rows), 28)
        self.assertEqual(rows[4]['status'], 'empty')
        self.assertEqual(rows[14]['status'], 'duplicate')
        self.assertEqual(rows[14]['duplicate_of'], 'R012')
        self.assertIsNone(rows[9]['rating'])
        self.assertIsNone(rows[21]['rating'])
        self.assertIn('आवाज़', rows[15]['text'])
        self.assertEqual(rows[23]['text'][:8], 'Love it!')

    def test_rating_and_duplicate_normalization(self):
        self.assertIsNone(parse_rating('five'))
        self.assertIsNone(parse_rating('6'))
        self.assertEqual(parse_rating(' 4 '), 4)
        self.assertEqual(text_hash(' HI  There '), text_hash('hi there'))
        self.assertEqual(tidy_text('<b>Love it!</b>'), 'Love it!')

    def test_missing_csv_header_has_friendly_error(self):
        with self.assertRaisesRegex(ValueError, 'Missing CSV columns'):
            clean_csv(b'id,content\n1,Hello')


if __name__ == '__main__':
    unittest.main()
