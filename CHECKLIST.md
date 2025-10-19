# ✅ Pre-Deployment Checklist

## Local Testing

- [ ] Bot starts without errors: `python3 bot.py`
- [ ] Send test message: "100₽ coffee"
- [ ] Bot puts 👍 reaction
- [ ] Transaction appears in Google Sheets
- [ ] Description is brief English (e.g., "Coffee")
- [ ] No duplicate entries

## Railway Deployment

### Step 1: GitHub Push
- [ ] All changes committed
- [ ] Pushed to GitHub: `git push origin main`
- [ ] Tag v1.0 pushed: `git push origin v1.0`

### Step 2: Railway Setup
- [ ] Logged into https://railway.app
- [ ] Created new project from GitHub repo
- [ ] Repository connected: `lubovkarpova/myfinance`

### Step 3: Environment Variables
Add these in Railway Variables tab:

- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `OPENAI_API_KEY`
- [ ] `SPREADSHEET_NAME` = `My finance`
- [ ] `GOOGLE_CREDENTIALS_JSON` = (full JSON from credentials file)

### Step 4: Deployment
- [ ] Railway auto-deployed
- [ ] Check logs for: `🚀 Бот запущен!`
- [ ] No errors in logs

### Step 5: Testing on Railway
- [ ] Stop local bot: `pkill -9 -f "python.*bot.py"`
- [ ] Send test message to bot
- [ ] Check for 👍 reaction
- [ ] Verify entry in Google Sheets
- [ ] No duplicates

## Troubleshooting

If bot doesn't work on Railway:

1. **Check Railway Logs**
   - Look for errors
   - Verify all services connected

2. **Verify Variables**
   - All 4 variables set correctly
   - JSON is valid (no extra quotes)

3. **Test Locally**
   - If local works but Railway doesn't
   - Problem is likely in env variables

4. **Rollback**
   ```bash
   git checkout v1.0
   git push -f origin main
   ```

## Current Status

### ✅ Working Features:
- Instant transaction processing
- AI categorization (GPT-4o)
- Google Sheets integration
- Emoji reactions (👍)
- Brief English descriptions
- No user ID recording
- Single entry per message

### 📦 Stable Dependencies:
- python-telegram-bot==22.5
- openai==1.54.0
- httpx==0.27.2
- gspread==5.12.4

### 🔗 Links:
- **GitHub**: https://github.com/lubovkarpova/myfinance
- **Google Sheet**: https://docs.google.com/spreadsheets/d/1BgoRBYJnLmnc67NzdjCW_pCJKh_fGWk0f0MVIqzzK2M
- **Railway**: (add after deployment)

---

**Version**: v1.0  
**Last Updated**: October 19, 2025  
**Status**: ✅ Ready for Railway deployment

