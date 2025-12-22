# Tech Stack

## Runtime
- Python 3.8+
- Async/await pattern throughout (asyncio)

## Core Libraries
- **playwright** - Browser automation (Firefox preferred)
- **aiohttp** - Async HTTP client for proxy management
- **python-dotenv** - Environment configuration

## Configuration
- `.env` file for sensitive config (proxy credentials, API URLs)
- `config.py` for application settings

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install browser for Playwright
playwright install firefox

# Run main application
python main.py

# Extract TikTok cookies from source files
python extract_tiktok_cookies.py

# Analyze cookie files
python analyze_cookies.py

# Test proxy connection
python check_proxy.py
python test_proxy_rotation.py
```

## Environment Variables

```
PROXY_SERVER=<proxy_host>
PROXY_PORT=<proxy_port>
PROXY_USERNAME=<username>
PROXY_PASSWORD=<password>
PROXY_REFRESH_URL=<api_url_for_ip_refresh>
USE_PROXY_ROTATION=true|false
```

## Code Conventions
- Classes use PascalCase
- Functions/methods use snake_case
- Async methods prefixed with `async`
- Comments and print statements in Russian
- Error handling with try/except and screenshot capture
