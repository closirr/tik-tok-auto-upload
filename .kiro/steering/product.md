# TikTok Auto Upload

Automated video upload and publishing tool for TikTok using browser automation with cookie-based authentication.

## Core Functionality

- Batch process multiple TikTok accounts via cookie files
- Validate cookie authentication before operations
- Upload and publish videos to TikTok Studio
- Proxy support with IP rotation for account safety
- Screenshot capture for debugging and verification
- Automatic marking of processed cookies as valid/invalid

## Workflow

1. Load cookie files from `cookies/` directory
2. Refresh proxy IP (if configured)
3. Validate TikTok session via cookies
4. Upload video from `videos/` directory
5. Publish video and verify success
6. Mark cookie file with result prefix (`valid_`/`invalid_`)

## Language

Primary documentation and code comments are in Russian.
