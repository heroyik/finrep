import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock heavy dependencies that might fail to install or aren't needed for news testing
sys.modules['pandas_ta'] = MagicMock()
sys.modules['mplfinance'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()

# Import the module to be tested
# We will patch yfinance.Ticker inside the test methods
import main

class TestFetchNews(unittest.TestCase):

    def setUp(self):
        # Sample news data for testing
        self.mock_news_data = [
            {
                "uuid": "1",
                "title": "Major News 1 (CNN)",
                "publisher": "CNN",
                "link": "https://cnn.com/news1",
                "providerPublishTime": 1672345600,
                "type": "STORY"
            },
            {
                "uuid": "2",
                "title": "Bait News (Motley Fool)",
                "publisher": "The Motley Fool",
                "link": "https://fool.com/news2",
                "providerPublishTime": 1672345601,
                "type": "STORY"
            },
            {
                "uuid": "3",
                "title": "Major News 2 (Bloomberg)",
                "publisher": "Bloomberg",
                "link": "https://bloomberg.com/news3",
                "providerPublishTime": 1672345602,
                "type": "STORY"
            },
            {
                "uuid": "4",
                "title": "Duplicate News 1 (CNN)",
                "publisher": "CNN",
                "link": "https://cnn.com/news1", # Same link as 1
                "providerPublishTime": 1672345603,
                "type": "STORY"
            },
            {
                "uuid": "5",
                "title": "Duplicate Title (CNN)",
                "publisher": "CNN",
                "link": "https://cnn.com/news5", 
                "providerPublishTime": 1672345604,
                "type": "STORY"
            },
             {
                "uuid": "6",
                "title": "Major News 1 (CNN)", # Different link, same title
                "publisher": "CNN",
                "link": "https://cnn.com/news6",
                "providerPublishTime": 1672345605,
                "type": "STORY"
            },
            {
                "uuid": "7",
                "title": "Minor News (Unknown)",
                "publisher": "Small Blog",
                "link": "https://blog.com/news7",
                "providerPublishTime": 1672345606,
                "type": "STORY"
            },
            {
                "uuid": "8",
                "title": "Another Major (check limit) (Reuters)",
                "publisher": "Reuters",
                "link": "https://reuters.com/news8",
                "providerPublishTime": 1672345607,
                "type": "STORY"
            },
            {
                "uuid": "9",
                "title": "Forbidden News (Barrons)",
                "publisher": "Barrons.com",
                "link": "https://barrons.com/news9",
                "providerPublishTime": 1672345608,
                "type": "STORY"
            },
            {
                "uuid": "10",
                "title": "Forbidden News (WSJ)",
                "publisher": "The Wall Street Journal",
                "link": "https://wsj.com/news10",
                "providerPublishTime": 1672345609,
                "type": "STORY"
            }
        ]

    @patch('main.yf.Ticker')
    def test_fetch_news_filtering(self, mock_ticker_cls):
        # Setup mock
        mock_ticker_instance = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_instance
        
        # Configure the mock to return specific news list
        # main.fetch_news expects .news property to be a list of dicts directly (or wrapped in legacy yf format)
        # Based on current code: n.get('content', n) is used. 
        # So we can pass dicts directly and satisfy both cases if we are careful, 
        # or structure them as current code expects.
        # Let's clean up the structure to match what main.py expects typically.
        # Ideally yfinance returns a list of dicts. main.py handles if it's nested in 'content' or flat.
        # We will use flat for simplicity as the code handles `n.get('content', n)`.
        
        mock_ticker_instance.news = self.mock_news_data

        # Run function
        results, asset = main.fetch_news("AAPL")

        # Assertions
        print(f"\nTested with {len(self.mock_news_data)} articles Mixed with valid, bail, duplicates, and minor sources.")
        print("Results:")
        for r in results:
            print(f"- [{r['publisher']}] {r['title']}")

        # 1. Check Allowlist Implementation
        publishers = [r['publisher'] for r in results]
        self.assertNotIn("The Motley Fool", publishers, "Motley Fool should be excluded")
        self.assertNotIn("Small Blog", publishers, "Unknown publisher should be excluded")
        self.assertNotIn("Barrons.com", publishers, "Barrons.com should be excluded")
        self.assertNotIn("The Wall Street Journal", publishers, "WSJ should be excluded")
        
        # 2. Check Duplicates (by title or link)
        # In setup:
        # Item 1: "Major News 1 (CNN)", link "...news1"
        # Item 4: "Duplicate News 1 (CNN)", link "...news1" (Same link as 1) -> Should be deduplicated by Link
        # Item 6: "Major News 1 (CNN)", link "...news6" (Same title as 1) -> Should be deduplicated by Title
        
        # We expect Item 1 to be present.
        # Item 4 should NOT be present (duplicate link).
        # Item 6 should NOT be present (duplicate title).
        
        titles = [r['title'] for r in results]
        self.assertEqual(titles.count("Major News 1 (CNN)"), 1, "Duplicate titles should be removed")
        
        # 3. Check Major Only (Valid Publishers)
        for p in publishers:
             is_major = any(m.lower() in p.lower() for m in main.MAJOR_PUBLISHERS)
             is_preferred = any(m.lower() in p.lower() for m in main.PREFERRED_PUBLISHERS)
             self.assertTrue(is_major or is_preferred, f"Publisher {p} not in major or preferred list")

        # 4. Check Max Count (should be 3)
        self.assertTrue(len(results) <= 3, "Should return max 3 results")

    @patch('main.yf.Ticker')
    def test_fetch_news_multi_asset(self, mock_ticker_cls):
        # Setup mock for multiple tickers
        # We need side_effect to return different mock instances based on ticker symbol
        
        mock_nvda = MagicMock()
        mock_nvda.news = [{
            "uuid": "101",
            "title": "NVDA News (New)",
            "publisher": "CNBC",
            "link": "https://cnbc.com/nvda",
            "providerPublishTime": 1700000020, # Latest
            "type": "STORY"
        }]
        
        mock_amd = MagicMock()
        mock_amd.news = [{
            "uuid": "102",
            "title": "AMD News (Old)",
            "publisher": "Reuters",
            "link": "https://reuters.com/amd",
            "providerPublishTime": 1700000010, # Older
            "type": "STORY"
        }]

        def side_effect(ticker_symbol):
            if ticker_symbol == "NVDA": return mock_nvda
            if ticker_symbol == "AMD": return mock_amd
            return MagicMock()

        mock_ticker_cls.side_effect = side_effect
        
        # Manually modify UNDERLYING_MAP for test isolation if needed, 
        # but we can just use "USD" if it's already updated in main.py, or mock it.
        # Let's mock UNDERLYING_MAP to ensure test stability regardless of config.
        with patch.dict('main.UNDERLYING_MAP', {"TEST_MULTI": ["NVDA", "AMD"]}):
            results, asset_name = main.fetch_news("TEST_MULTI")
            
            print("\nTested Multi-Asset Fetching:")
            for r in results:
                print(f"- {r['title']}")

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['title'], "NVDA News (New)", "Should be sorted by latest first")
            self.assertEqual(results[1]['title'], "AMD News (Old)")

if __name__ == '__main__':
    unittest.main()
