import os
import glob
import json

SOURCE_DIRECTORY = r'd:\Projects\соцсети боти\tik-tok-auto-upload\cookies_example'
TARGET_DIRECTORY = r'd:\Projects\соцсети боти\tik-tok-auto-upload\cookies_extracted'

def get_expected_filename(filepath):
    filename = os.path.basename(filepath)
    path_parts = os.path.normpath(filepath).split(os.sep)
    
    log_id = "unknown"
    for part in reversed(path_parts[:-1]):
        if (part.startswith("AE") or part.startswith("IN")) and "[" in part:
            log_id = part
            break
    
    if log_id == "unknown":
        try:
            if path_parts[-2].lower() == 'cookies':
                log_id = path_parts[-3]
            else:
                log_id = path_parts[-2]
        except:
            log_id = "unknown"

    safe_log_id = "".join(x for x in log_id if x.isalnum() or x in "[]_-")
    safe_filename = "".join(x for x in filename if x.isalnum() or x in "._-").replace(".txt", "")
    
    return f"extracted_{safe_log_id}_{safe_filename}.json"

def verify():
    print(f"Verifying extraction from {SOURCE_DIRECTORY} to {TARGET_DIRECTORY}")
    
    files_with_tiktok = []
    
    # 1. Find all source files with tiktok cookies
    for root, dirs, files in os.walk(SOURCE_DIRECTORY):
        for filename in files:
            if "Cookies" in filename and filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "tiktok.com" in content:
                            files_with_tiktok.append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    print(f"\nFound {len(files_with_tiktok)} files in source containing 'tiktok.com'.")

    # 2. Check if they exist in target
    missing_extractions = []
    successful_extractions = []
    
    for filepath in files_with_tiktok:
        expected_name = get_expected_filename(filepath)
        target_path = os.path.join(TARGET_DIRECTORY, expected_name)
        
        if os.path.exists(target_path):
            successful_extractions.append((filepath, target_path))
        else:
            missing_extractions.append(filepath)
            print(f"MISSING: {filepath} -> Expected: {expected_name}")

    print(f"Successfully verified: {len(successful_extractions)}")
    print(f"Missing extractions: {len(missing_extractions)}")

    # 3. Check for empty or invalid JSONs in target
    print("\nChecking extracted files validity...")
    extracted_files = glob.glob(os.path.join(TARGET_DIRECTORY, "*.json"))
    empty_files = []
    valid_files_count = 0
    
    for json_file in extracted_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    valid_files_count += 1
                else:
                    empty_files.append(json_file)
                    print(f"EMPTY/INVALID: {json_file}")
        except Exception as e:
            print(f"CORRUPT: {json_file} - {e}")
            empty_files.append(json_file)

    print(f"Valid extracted files (not empty): {valid_files_count}")

    if not missing_extractions and not empty_files:
        print("\nSUCCESS: All detected source files were extracted correctly.")
    else:
        print("\nWARNING: Some files were missed or extracted as empty.")

if __name__ == '__main__':
    verify()
