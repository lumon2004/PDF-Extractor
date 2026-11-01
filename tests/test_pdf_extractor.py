import sys
import unittest
from unittest.mock import patch

from pdf_extractor import parse_page_selection, setup_readline


class ParsePageSelectionTests(unittest.TestCase):
    def test_parses_mixed_pages_and_removes_duplicates(self):
        self.assertEqual(parse_page_selection("1,3-5,4", 5), [0, 2, 3, 4])

    def test_rejects_page_outside_document(self):
        with self.assertRaisesRegex(ValueError, "only 3 pages"):
            parse_page_selection("4", 3)


class ReadlineCompatibilityTests(unittest.TestCase):
    def test_setup_succeeds_when_readline_is_unavailable(self):
        with patch.dict(sys.modules, {"readline": None}):
            setup_readline()


if __name__ == "__main__":
    unittest.main()
