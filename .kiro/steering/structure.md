# Project Structure

```
├── main.py                    # Entry point - orchestrates account processing
├── config.py                  # Configuration from .env
├── tiktok_manager.py          # Core class: browser automation, video upload, proxy
├── tiktok_cookies_loader.py   # Cookie file parsing (JSON, Netscape, text formats)
├── extract_tiktok_cookies.py  # Utility to extract TikTok cookies from raw files
├── analyze_cookies.py         # Cookie analysis utility
├── verify_extraction.py       # Verification utility
│
├── cookies/                   # Cookie files for processing
│   ├── extracted_*.txt        # Unprocessed cookies
│   ├── valid_*.txt            # Successfully authenticated
│   └── invalid_*.txt          # Failed authentication
│
├── videos/                    # Videos to upload (first file used)
├── screenshots/               # Session screenshots organized by cookie file
│   └── <cookie_name>_<timestamp>/
│       ├── proxy_check_*.png
│       ├── tiktok_*.png
│       └── proxy_report.txt
│
├── cookies_example/           # Source directory for cookie extraction
├── cookies_extracted/         # Output for extracted cookies
│
├── check_proxy*.py            # Proxy testing utilities
├── test_proxy*.py             # Proxy test scripts
└── playwright_proxy.py        # Playwright proxy configuration
```

## Key Classes

- **TikTokManager** (`tiktok_manager.py`): Main orchestrator
  - Browser lifecycle management
  - Proxy configuration and IP refresh
  - Cookie injection and auth verification
  - Video upload and publishing
  - Screenshot management

- **CookiesLoader** (`tiktok_cookies_loader.py`): Cookie handling
  - Multi-format parsing (JSON, Netscape, tab-separated)
  - File discovery and filtering
  - Valid/invalid marking

## File Naming Conventions

- Cookie files: `extracted_<source_id>_<browser>_<profile>.txt`
- Processed cookies: `valid_` or `invalid_` prefix added
- Screenshots: `<cookie_name>_<YYYYMMDD_HHMMSS>/`
