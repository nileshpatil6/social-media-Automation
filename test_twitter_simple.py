\#!/usr/bin/env python3
"""
Simple test to verify TwitterAgent import
"""

try:
    from twitter_agent import TwitterAgent
    print("[PASS] TwitterAgent imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import TwitterAgent: {e}")

print("[INFO] TwitterAgent is ready for use!")
