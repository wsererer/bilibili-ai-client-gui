# Data Directory

This directory contains runtime data and configuration files.

## Required Files

### login_cookie.txt
Your B站 login cookie. Format:
```
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

To obtain:
1. Login to https://bilibili.com
2. Open Developer Tools (F12) → Application → Cookies
3. Copy SESSDATA, bili_jct, DedeUserID values

### config.json (optional)
Application configuration. Created automatically on first run.

## Notes
- This directory is excluded from git (see .gitignore)
- Database file `bilibili_client.db` is created automatically