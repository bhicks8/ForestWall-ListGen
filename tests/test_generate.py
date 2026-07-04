import unittest
from unittest.mock import patch

import requests

import generate


class BuildListErrorHandlingTests(unittest.TestCase):
    @patch("generate.fetch_and_parse_source")
    def test_skips_source_when_url_retrieval_fails(self, mock_fetch):
        mock_fetch.side_effect = [
            requests.exceptions.HTTPError("404 Client Error"),
            ["1.1.1.1", "2.2.2.2"],
        ]

        result = generate.build_list(
            name="test-list",
            dedupe_strategy="simple",
            sources=[
                {"url": "https://example.com/missing.txt", "format": "hostlist"},
                {"url": "https://example.com/ok.txt", "format": "hostlist"},
            ],
        )

        self.assertEqual(len(result), 2)
        self.assertTrue(result.contains("1.1.1.1"))
        self.assertTrue(result.contains("2.2.2.2"))
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("generate.fetch_and_parse_source")
    def test_skips_source_when_local_file_missing(self, mock_fetch):
        mock_fetch.side_effect = FileNotFoundError("No such file")

        result = generate.build_list(
            name="test-list",
            dedupe_strategy="simple",
            sources=[
                {"url": "file:///tmp/missing.txt", "format": "hostlist"},
            ],
        )

        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
