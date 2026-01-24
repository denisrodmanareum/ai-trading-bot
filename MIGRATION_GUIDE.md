# How to Migrate Your Trading Bot to Another PC

To ensure all the fixes and logic improvements work on your other PC, follow these steps:

## 1. Commit and Push Changes (On CURRENT PC)
Your code changes are currently only on this machine. You need to push them to GitHub (or your Git remote):

```bash
# In the root directory (c:\ai\ai-trading-bot)
git add .
git commit -m "Fix: logic hangs, WebSocket reliability, and order precision errors"
git push origin main
```

## 2. Prepare the Other PC
On your other PC, download the latest code:

```bash
# Clone the repo if you haven't
git clone <your-repo-url>

# OR update existing repo
git pull origin main
```

## 3. Transfer Sensitive Files (IMPORTANT)
The following files are **Gitignored** for security and local dependency. You MUST copy them manually from this PC to the other:
- `backend/.env`: Contains your Binance API keys.
- `backend/data/models/`: Contains your trained AI models (zip files).
- `backend/trading_bot.db`: (Optional) If you want to keep your trade history.

## 4. Install Dependencies
On the new PC, make sure you have all the required libraries:

```bash
cd backend
pip install -r requirements.txt
```

## 5. Start the Bot
Run the bot as usual:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
