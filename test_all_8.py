#!/usr/bin/env python3
"""Test all 8 images with sequential processing."""
import requests
import time
import sys

image_dir = "/Users/fernando/Downloads/temp"
files_to_test = [f"{i}.jpeg" for i in range(1, 9)]

print("Testing All 8 Images with Sequential Processing")
print("=" * 60)

results = []
errors = []
total_start = time.time()

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
    
    # 5-second delay between images
    if current < total:
        print(f"  ⏳ Waiting 5 seconds...")
        time.sleep(5)

total_duration = time.time() - total_start

# Summary
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"Total images: {len(files_to_test)}")
print(f"Successful: {len(results)}")
print(f"Failed: {len(errors)}")
print(f"Total time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")

if results:
    total_chars = sum(len(r['text']) for r in results)
    print(f"Total characters extracted: {total_chars}")
    
    print(f"\n{'='*60}")
    print("COMBINED TEXT:")
    print('='*60)
    combined = "\n\n".join(r['text'] for r in results)
    print(combined)
    
    # Save to file
    with open('/Users/fernando/ws/photototext/extracted_text.txt', 'w', encoding='utf-8') as f:
        f.write(combined)
    print(f"\n{'='*60}")
    print("✅ Saved to: extracted_text.txt")

if errors:
    print(f"\n{'='*60}")
    print("ERRORS:")
    print('='*60)
    for err in errors:
        print(f"  - {err}")
