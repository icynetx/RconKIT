#!/usr/bin/env python3
"""Compatibility wrapper for ReconKit.

The real implementation lives in the `reconkit` package. Existing usage such as
`python3 recon.py example.com --deep --ai` continues to work.
"""

from reconkit.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
