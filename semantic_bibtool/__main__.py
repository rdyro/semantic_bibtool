import sys
from pathlib import Path

try:
    from . import main
except ImportError:
    sys.path.append(str(Path(__file__).absolute().parents[1]))
    from semantic_bibtool import main

if __name__ == "__main__":
    main()