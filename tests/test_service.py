import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import config, service, store
from app.validation import validate_analysis

CSV=b'review_id,product,rating,date,review_text\nR1,Widget,1,2026-10-02,Bad quality\nR2,Widget,1,2026-10-03,Bad quality\nR3,Widget,5,2026-10-03,Great quality\nR4,Widget,five,2026-10-03,\n'

class FakeClient:
    def __init__(self):
        self.api_calls=0
        self.rate_retries=0
        self.batches=[]
    def analyse_batch(self,rows):
        self.api_calls+=1
        self.batches.append([r['review_id'] for r in rows])
        result={}
        for r in rows:
            pos='Great' in r['text']
            result[r['row_num']]=validate_analysis({'sentiment':'positive' if pos else 'negative',
                'topics':['quality'],'summary':'Great product.' if pos else 'Poor quality.',
                'needs_reply':not pos})
        return result,{}

class ServiceTests(unittest.TestCase):
    def test_cache_persists_across_uploads(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(store, 'DB_PATH', Path(tmp) / 'test.db'), patch.object(config,'DEMO_MODE',False):
            store.initialize()
            first=FakeClient()
            result=service.import_csv(CSV,client=first)
            self.assertEqual(result['stats']['unique'],2)
            self.assertEqual(result['stats']['duplicates'],1)
            self.assertEqual(result['stats']['skipped_empty'],1)
            self.assertEqual(result['stats']['ai_calls'],1)
            self.assertEqual(result['dashboard']['overview']['total'],2)
            second=FakeClient()
            next_result=service.import_csv(CSV,client=second)
            self.assertEqual(next_result['stats']['cache_hits'],2)
            self.assertEqual(next_result['stats']['ai_calls'],0)
            self.assertEqual(second.batches,[])

if __name__=='__main__':
    unittest.main()
