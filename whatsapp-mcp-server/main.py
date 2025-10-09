#!/usr/bin/env python3
"""
Backward compatibility wrapper for main.py -> server.py migration.
This ensures existing scripts, Dockerfiles, and documentation continue to work.
"""

if __name__ == "__main__":
    # Execute the server module directly
    import runpy
    runpy.run_module('server', run_name='__main__')
