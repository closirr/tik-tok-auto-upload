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
# Proxy Configuration
PROXY_DISABLED=true|false          # Disable proxy completely (overrides PROXY_MODE)
PROXY_MODE=free|paid              # Proxy type: 'free' or 'paid'

# Paid Proxy Settings
PROXY_SERVER=<proxy_host>
PROXY_PORT=<proxy_port>
PROXY_USERNAME=<username>
PROXY_PASSWORD=<password>
PROXY_REFRESH_URL=<api_url_for_ip_refresh>

# Free Proxy Settings
FREE_PROXY_COUNTRIES=US,GB,DE,CA,AU
FREE_PROXY_HTTPS=true|false
FREE_PROXY_ANONYM=true|false
FREE_PROXY_TIMEOUT=5.0
FREE_PROXY_POOL_SIZE=5
FREE_PROXY_CACHE_TIME=300

# General Proxy Settings
USE_PROXY_ROTATION=true|false
IPINFO_TOKEN=<your_ipinfo_token>
```

## Code Conventions
- Classes use PascalCase
- Functions/methods use snake_case
- Async methods prefixed with `async`
- Comments and print statements in Russian
- Error handling with try/except and screenshot capture
