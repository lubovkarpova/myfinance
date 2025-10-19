# 🚀 Deploy to Railway - Step by Step

## Before You Start

Make sure you have:
- ✅ Telegram Bot Token
- ✅ OpenAI API Key
- ✅ Google Credentials JSON file
- ✅ Google Spreadsheet created and shared with service account email

## Deployment Steps

### 1️⃣ Push to GitHub

```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### 2️⃣ Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository: `lubovkarpova/myfinance`
5. Railway will automatically detect Python and start building

### 3️⃣ Configure Environment Variables

Click on your project → **Variables** tab → Add these variables:

#### Required Variables:

**TELEGRAM_BOT_TOKEN**
```
8496780942:AAE4mWrg-EVbiHrdwvJcQk6Q9BDeqdNTWW0
```

**OPENAI_API_KEY**
```
sk-proj-...your key...
```

**SPREADSHEET_NAME**
```
My finance
```

**GOOGLE_CREDENTIALS_JSON**
```json
{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
```

⚠️ **Important**: For `GOOGLE_CREDENTIALS_JSON`, copy the ENTIRE content of your `google_credentials.json` file as a single line (no line breaks, just one long JSON string).

### 4️⃣ Deploy

After adding all variables:
1. Railway will automatically redeploy
2. Wait for deployment to complete (watch the logs)
3. Look for: `🚀 Бот запущен!`

### 5️⃣ Test

Send a message to your Telegram bot:
```
100₽ coffee
```

You should see:
- 👍 reaction on your message
- New row in Google Sheets

## Monitoring

### Check Logs
Railway Dashboard → Your Project → **Logs** tab

Look for:
```
✅ Подключено к таблице: https://docs.google.com/...
✅ OpenAI готов
🚀 Бот запущен!
```

### Check Status
Your bot should show "Active" status in Railway dashboard.

## Updating the Bot

1. Make changes locally
2. Test: `python bot.py`
3. Commit: `git commit -am "Your changes"`
4. Push: `git push`
5. Railway auto-deploys!

## Rollback to v1.0

If something breaks:
```bash
git checkout v1.0
git push -f origin main
```

Railway will auto-deploy the stable version.

## Cost Estimate

Railway free tier: **$5/month credit**
Expected usage: **~$2-3/month** (for small bot)

Should be free or very cheap! 💰

## Support

If deployment fails, check:
1. ✅ All environment variables set correctly
2. ✅ Google credentials JSON is valid
3. ✅ Spreadsheet is shared with service account
4. ✅ Railway logs for specific errors

Good luck! 🚀

