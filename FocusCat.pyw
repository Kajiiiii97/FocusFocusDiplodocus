# Double-click launcher (pythonw runs it without a console window).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscat.app import main

if __name__ == "__main__":
    raise SystemExit(main())
