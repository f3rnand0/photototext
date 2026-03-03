#!/usr/bin/env python3
"""Test the sequential processing with progress tracking simulation."""
import requests
import time
import sys

# Test the new sequential endpoint behavior
image_dir = "/Users/fernando/Downloads/temp"
files_to_test = [f"{i}.jpeg" for i in range(1, 4)]  # Test with 3 images first

print("Testing Sequential OCR Processing with Progress Tracking")
print("=" * 60)

results = []
errors = []

for i, filename in enumerate(files_to_test):
    filepath = f"{image_dir}/{filename}"
    current = i + 1
    total = len(files_to_test)
    
    print(f"\n[{current}/{total}] Processing {filename}...")
    start_time = time.time()
    
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/extract-text',
                files={'files': (filename, f, 'image/jpeg')},
                timeout=30
            )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['results']:
                result = data['results'][0]
                text = result['text']
                
                if text.startswith('Error:'):
                    print(f"  ❌ FAILED: {text}")
                    errors.append(f"{filename}: {text}")
                else:
                    char_count = len(text)
                    print(f"  ✅ SUCCESS: {char_count} characters in {duration:.1f}s")
                    print(f"     Preview: {text[:80]}...")
                    results.append(result)
            else:
                print(f"  ⚠️  UNEXPECTED: {data.get('message', 'No results')}")
        else:
            print(f"  ❌ HTTP ERROR: {response.status_code}")
            errors.append(f"{filename}: HTTP {response.status_code}")
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"  ❌ EXCEPTION: {str(e)}")
        errors.append(f"{filename}: {str(e)}")
    
    # 5-second delay (as implemented in frontend)
    if current < total:
        print(f"  ⏳ Waiting 5 seconds before next image...")
        time.sleep(5)

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total: {len(files_to_test)} | Success: {len(results)} | Failed: {len(errors)}")

if results:
    print(f"\nCombined text ({sum(len(r['text']) for r in results)} chars):")
    print("-" * 60)
    combined = "\n\n".join(r['text'] for r in results)
    print(combined[:1500])
    if len(combined) > 1500:
        print(f"\n... ({len(combined) - 1500} more characters)")

if errors:
    print("\nErrors:")
    for err in errors:
        print(f"  - {err}")