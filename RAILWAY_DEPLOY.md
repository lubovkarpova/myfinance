# 🚂 Deployment to Railway

## Quick Deploy Steps

### 1. Create Railway Account
- Go to [railway.app](https://railway.app)
- Sign up with GitHub

### 2. Create New Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose `lubovkarpova/myfinance` repository
- Railway will detect Python automatically

### 3. Set Environment Variables
In Railway dashboard → Variables tab, add:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
SPREADSHEET_NAME=My finance
```

### 4. Upload Google Credentials
You need to upload `google_credentials.json`:

**Option A: Using Railway CLI**
```bash
railway login
railway link
railway run python test_setup.py
```

**Option B: Base64 encode and use env variable**
```bash
# On your local machine:
base64 google_credentials.json > credentials_base64.txt

# In Railway Variables, add:
GOOGLE_CREDENTIALS_BASE64=<paste the content>
```

Then modify `config.py` to decode it:
```python
import base64
import json
import os

if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
    creds = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
    with open('google_credentials.json', 'wb') as f:
        f.write(creds)
```

**Option C: Paste JSON directly (recommended for Railway)**
- Copy entire content of `google_credentials.json`
- In Railway Variables, add:
```
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...whole JSON...}
```

Then update `google_sheets.py` to read from env variable.

### 5. Deploy
- Railway will auto-deploy after you push changes
- Or click "Deploy" button in Railway dashboard

### 6. Check Logs
- Go to "Deployments" tab
- Click on latest deployment
- View logs to ensure bot started successfully

## Important Notes

⚠️ **Google Credentials**: The easiest way is to use environment variable for credentials JSON.

⚠️ **No .env file**: Railway uses environment variables from dashboard, not `.env` file.

⚠️ **Always On**: Railway free tier gives you $5 credit/month, should be enough for a simple bot.

## Monitoring

Check if bot is running:
- Send `/start` to your bot
- Check Railway logs for errors
- View Google Sheets to confirm transactions are being logged

## Troubleshooting

If bot doesn't start:
1. Check Railway logs
2. Verify all environment variables are set
3. Make sure Google credentials are properly configured
4. Check that all dependencies installed correctly

## Local Testing Before Deploy

Always test locally first:
```bash
python test_setup.py
```

If all checks pass ✅, you're ready to deploy!

