#!/usr/bin/env python3
"""
Helper script to run integration tests and capture extracted text.

Usage:
    python run_integration_test.py

This will run the integration test with real Azure OCR and print
the extracted text so you can update EXPECTED_RESULTS in test_e2e.py.
"""

import subprocess
import sys


def main():
    """Run integration test with Azure."""
    print("Running integration test with Azure OCR...")
    print("Make sure you have set up your Azure credentials in .env file\n")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_e2e.py::test_integration_with_azure",
        "-v",
        "-s",  # Capture output
        "-m", "integration"
    ]
    
    result = subprocess.run(cmd, cwd="/Users/fernando/ws/photototext/backend")
    
    if result.returncode == 0:
        print("\n✅ Integration test completed successfully!")
        print("\nNext steps:")
        print("1. Copy the extracted text from the output above")
        print("2. Update EXPECTED_RESULTS in tests/test_e2e.py")
        print("3. Remove the placeholder values (PLACEHOLDER_TEXT_1, etc.)")
        print("4. Uncomment the assertions in test_integration_with_azure")
    else:
        print("\n❌ Integration test failed")
        print("Check the error output above")
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())