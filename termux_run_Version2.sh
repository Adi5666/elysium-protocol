#!/data/data/com.termux/files/usr/bin/bash
# Elysium Protocol: Termux setup & run script

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Upgrade pip & install requirements
pip install --upgrade pip
pip install discord.py aiosqlite aiohttp typing-extensions

# Run migrations
python3 -c "import asyncio; import utils.db as db; asyncio.run(db.run_migrations())"

# Run bot
python3 elysium.py