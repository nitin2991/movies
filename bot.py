import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle
import logging
import logging.config
import asyncio
import time
from pyrogram import Client, __version__
from pyrogram.errors import FloodWait
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script
from datetime import date, datetime
import pytz
from aiohttp import web
from plugins import web_server
from Jisshu.bot import JisshuBot
from Jisshu.util.keepalive import ping_server
from Jisshu.bot.clients import initialize_clients

# Configure logging
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

# Path to plugin files
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def start_bot_with_retries():
    """Try to start the bot, retrying on flood waits."""
    while True:
        try:
            await JisshuBot.start()
            logging.info("Bot started successfully.")
            break  # Exit loop once the bot starts
        except FloodWait as e:
            logging.warning(f"Flood wait triggered. Waiting for {e.x} seconds...")
            await asyncio.sleep(e.x)  # Sleep for the required flood wait time before retrying
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            break  # Exit loop on other errors

async def Jisshu_start():
    """Initialize and start the Movie Provider Bot."""
    print('\n')
    print('Initializing The Movie Provider Bot')
    
    # Fetch bot info
    bot_info = await JisshuBot.get_me()
    JisshuBot.username = bot_info.username
    
    # Initialize clients and plugins
    await initialize_clients()
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            logging.info(f"The Movie Provider Imported => {plugin_name}")

    # Ping server if on Heroku
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Get banned users and chats
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    # Ensure indexes for the media database
    await Media.ensure_indexes()

    # Get bot details
    me = await JisshuBot.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    JisshuBot.username = '@' + me.username

    # Log bot startup details
    logging.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    logging.info(script.LOGO)
    
    # Get current time and send a restart message to the log channel
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S %p")
    await JisshuBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time_str))

    # Start the web server
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()

    # Keep the bot running
    await idle()

if __name__ == '__main__':
    try:
        # Retry mechanism for bot start
        asyncio.run(start_bot_with_retries())
        asyncio.run(Jisshu_start())  # Once the bot starts, run the main bot function
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
