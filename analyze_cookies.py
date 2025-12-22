import os
import glob

COOKIES_DIR = r'd:\Projects\соцсети боти\tik-tok-auto-upload\cookies'

def inspect_cookies():
    files = glob.glob(os.path.join(COOKIES_DIR, "extracted_*.txt"))
    
    print(f"Found {len(files)} extracted cookie files.\n")
    
    for filepath in files[:10]: # Check first 10
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                line_count = len(lines)
                content = "".join(lines)
                
                has_sessionid = "sessionid" in content
                has_sid_tt = "sid_tt" in content
                
                print(f"File: {filename}")
                print(f"  Size: {size} bytes")
                print(f"  Lines: {line_count}")
                print(f"  Has sessionid: {has_sessionid}")
                print(f"  Has sid_tt: {has_sid_tt}")
                print("-" * 30)
                
        except Exception as e:
            print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    inspect_cookies()
