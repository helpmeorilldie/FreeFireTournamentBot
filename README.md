# Free Fire Tournament Bot - Hosted By Erebus | Owner Haze @Noxmirage

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill it in (bot token, your Telegram ID in ADMIN_IDS, UPI ID).
3. Put your payment QR image next to `bot.py` as `qr.jpg`.
4. Make the bot an **admin** in `@ecochamber` (needed to check membership) and in your private storage channel.
5. `python bot.py`

## Admin
`/admin` opens the panel: approve/reject (with reason), add tournaments, set prizes, post updates,
broadcast to all, message a single team, CSV export, stats, backup and restore.

Commands: `/addtournament` `/backup` `/restore` `/export` `/cancel`

## Data
- SQLite DB: `data/erebus_ff.db`
- Backups saved on the host in `backups/` (last 20 kept) and sent to the private channel every 6 hours and on demand.
- Every registration (with payment screenshot), approval/rejection and broadcast is logged to the private channel.
- Restore: `/restore`, then send any backup `.db` file (a safety backup of current data is taken first).
