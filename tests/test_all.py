import sys
from tempfile import TemporaryDirectory
import unittest

from pathlib import Path

root_path = Path(__file__).absolute().parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))
data_path = Path(__file__).absolute().parent / "data"

from semantic_bibtool import main

class AllTests(unittest.TestCase):
    def test_string(self):
        assert data_path.exists()
        sys.argv = sys.argv[:1] + ["-i", "attention is all you need"]
        main()

    def test_zotero_csv(self):
        assert data_path.exists()
        tmp = TemporaryDirectory()
        tempfile = Path(tmp.name) / "output.txt"
        sys.argv = sys.argv[:1] + ["-i", str(data_path / "zotero.csv"), "-o", str(tempfile)]
        main()
        tmp.cleanup()

    def test_txt(self):
        assert data_path.exists()
        tmp = TemporaryDirectory()
        tempfile = Path(tmp.name) / "output.txt"
        sys.argv = sys.argv[:1] + ["-i", str(data_path / "titles.txt"), "-o", str(tempfile)]
        main()
        tmp.cleanup()

if __name__ == "__main__":
    unittest.main()
