import os
import glob
import shutil

SOURCE_DIRECTORY = r'.\cookies_example'
TARGET_DIRECTORY = r'.\cookies'

def main():
    if not os.path.exists(TARGET_DIRECTORY):
        os.makedirs(TARGET_DIRECTORY)

    count_processed = 0
    count_extracted = 0

    print(f"Scanning {SOURCE_DIRECTORY}...")
    
    # Recursive search for .txt files in Cookies folders or Browser folders
    for root, dirs, files in os.walk(SOURCE_DIRECTORY):
        for filename in files:
            # Ищем .txt файлы в папках Cookies или Browser, или файлы с "Cookies" в названии
            is_in_cookies_folder = "Cookies" in root or "Browser" in root
            is_cookies_file = "Cookies" in filename or "cookies" in filename.lower()
            if filename.endswith(".txt") and (is_in_cookies_folder or is_cookies_file):
                filepath = os.path.join(root, filename)
                
                # Determine a safe unique name
                path_parts = os.path.normpath(filepath).split(os.sep)
                
                log_id = "unknown"
                for part in reversed(path_parts[:-1]):
                    # Ищем папку с ID в формате XX[...][...] (например AE[ABC123][2025-12-21T...])
                    if "[" in part and "]" in part and len(part) > 5:
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
                
                # Output as .txt instead of .json
                output_filename = f"extracted_{safe_log_id}_{safe_filename}.txt"
                output_path = os.path.join(TARGET_DIRECTORY, output_filename)
                
                extracted_lines = []
                header_line = ""
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                        # Preserve header if present
                        if lines and (lines[0].startswith("# Netscape") or lines[0].startswith("# HTTP")):
                            header_line = lines[0]
                            
                        for line in lines:
                            # Keep empty lines or comments? Maybe minimal filtering.
                            # User said "по минимуму что-то менял".
                            # But we strictly need tiktok cookies. 
                            
                            # Always keep the header
                            if line.startswith("# Netscape") or line.startswith("# HTTP"):
                                continue # We added it to header_line, will write at start
                                
                            # Filter for tiktok.com
                            if "tiktok.com" in line:
                                extracted_lines.append(line)
                                
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    continue

                if extracted_lines:
                    # VALIDATION LOGIC
                    # 1. Check if we have enough lines (at least 2, including potentially header or just multiple cookies)
                    # Actually, a single line might be valid if it's the sessionid, but usually we need more.
                    # 2. Key check: MUST contain 'sessionid'
                    
                    content_str = "".join(extracted_lines)
                    is_valid = False
                    
                    if "sessionid" in content_str:
                        is_valid = True
                    
                    if not is_valid:
                        print(f"Skipping {filename}: No sessionid found (Lines: {len(extracted_lines)})")
                        continue

                    print(f"Found {len(extracted_lines)} TikTok cookies in {log_id}/{filename} (Valid)")
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            if header_line:
                                f.write(header_line)
                            
                            for line in extracted_lines:
                                f.write(line)
                                
                        count_extracted += 1
                    except Exception as e:
                        print(f"Error writing to {output_path}: {e}")
                
                count_processed += 1

    print(f"Done. Scanned {count_processed} files. Extracted {count_extracted} cookie files to {TARGET_DIRECTORY}.")

if __name__ == '__main__':
    main()
