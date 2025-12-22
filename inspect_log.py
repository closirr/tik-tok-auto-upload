import os
import glob

base_dir = r"d:\Projects\соцсети боти\tik-tok-auto-upload\cookies_example"
files = glob.glob(os.path.join(base_dir, "**", "*Cookies*.txt"), recursive=True)

if files:
    print(f"Found {len(files)} files.")
    with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
        print(f"File: {files[0]}")
        for i in range(5):
             print(f.readline().strip())
else:
    print("No cookie files found.")
