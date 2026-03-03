#!/usr/bin/env python3
"""Test OCR with delays to avoid Azure rate limits."""
import requests
import time
import sys

# Test with all 8 images one by one with delays
image_dir = "/Users/fernando/Downloads/temp"
files_to_test = [f"{i}.jpeg" for i in range(1, 9)]

print("Testing OCR with individual requests (with delays)...")
print("=" * 60)

all_results = []

for filename in files_to_test:
    filepath = f"{image_dir}/{filename}"
    
    print(f"\nProcessing {filename}...")
    start_time = time.time()
    
    with open(filepath, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/extract-text',
            files={'files': (filename, f, 'image/jpeg')}
        )
    
    duration = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        if data['success'] and data['results']:
            result = data['results'][0]
            text = result['text']
            
            if text.startswith('Error:'):
                print(f"  ❌ FAILED: {text}")
                all_results.append({
                    'filename': filename,
                    'success': False,
                    'error': text,
                    'duration': duration
                })
            else:
                print(f"  ✅ SUCCESS: {len(text)} characters")
                print(f"     Preview: {text[:100]}...")
                all_results.append({
                    'filename': filename,
                    'success': True,
                    'text': text,
                    'duration': duration
                })
        else:
            print(f"  ⚠️  UNEXPECTED: {data.get('message', 'Unknown')}")
    else:
        print(f"  ❌ HTTP ERROR: {response.status_code}")
        print(f"     {response.text}")
    
    # Add delay to avoid rate limiting
    if filename != files_to_test[-1]:
        print(f"  ⏳ Waiting 3 seconds before next image...")
        time.sleep(3)

# Summary
print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)

success_count = sum(1 for r in all_results if r['success'])
error_count = len(all_results) - success_count

print(f"Total images: {len(all_results)}")
print(f"Successful: {success_count}")
print(f"Failed: {error_count}")

if success_count > 0:
    print(f"\nCombined text preview:")
    print("-" * 60)
    combined = []
    for r in all_results:
        if r['success']:
            combined.append(r['text'])
    
    full_text = "\n\n".join(combined)
    print(full_text[:2000])
    if len(full_text) > 2000:
        print(f"\n... ({len(full_text) - 2000} more characters)")

print("\n" + "=" * 60)