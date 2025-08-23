#!/usr/bin/env python3
"""
Clean test runner that suppresses deprecation warnings for production-ready test output.
"""
import sys
import os
import warnings

# Suppress all deprecation warnings for clean test output
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

# Import and run pytest
import pytest

if __name__ == "__main__":
    # Run pytest with clean output
    exit_code = pytest.main([
        "-v", 
        "--tb=short", 
        "--strict-markers", 
        "--disable-warnings"
    ] + sys.argv[1:])
    sys.exit(exit_code)