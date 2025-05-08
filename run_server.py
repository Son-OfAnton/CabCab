#!/usr/bin/env python3
"""
Direct script to run the custom JSON server for CabCab.
"""

import sys
import os
import subprocess

# Execute the custom test_server.py
try:
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_server.py')
    
    print(f"Starting custom JSON server on port 3000...")
    print(f"Using script: {script_path}")
    
    # Execute the script directly
    os.execv(sys.executable, [sys.executable, script_path])
    
except Exception as e:
    print(f"Error running JSON server: {e}", file=sys.stderr)
    sys.exit(1)