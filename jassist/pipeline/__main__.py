"""
Pipeline module execution entry point.

This file enables running the pipeline module directly with:
python -m jassist.pipeline
"""

import sys
from jassist.pipeline.pipeline import main

if __name__ == "__main__":
    sys.exit(main()) 