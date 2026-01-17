# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official



import os
import asyncio
import random
import time
import shutil
import re
import pyrogram
import platform
import sys
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant,
    InviteHashExpired, UsernameNotOccupied, AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import MessageMediaType
from config import API_ID, API_HASH, ERROR_MESSAGE, LOG_CHANNEL, ADMINS
from database.db import db
import math
from Rexbots.strings import HELP_TXT, COMMANDS_TXT
from logger import LOGGER

def clean_caption(caption: str) -> str:
    """Remove Telegram links and channel references from caption"""
    if not caption:
        return None
    
    # Remove Telegram t.me links
    caption = re.sub(r'https?:\/\/t\.me\/\S*', '', caption)
    # Remove t.me references without https
    caption = re.sub(r't\.me\/\S*', '', caption)
    # Remove channel references like @channelname
    caption = re.sub(r'@\w+', '', caption)
    # Clean up extra whitespace
    caption = re.sub(r'\s+', ' ', caption).strip()
    
    return caption if caption else None

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    
    if not tmp:
        tmp = ((str(milliseconds) + "ms, ") if milliseconds else "")
        
    return tmp[:-2] if tmp else "0s"

logger = LOGGER(__name__)

class batch_temp(object):
    IS_BATCH = {}

# Simple ask function for Pyrogram
async def ask_user(client, chat_id, text):
    """Simple ask function to get user input"""
    from asyncio import Queue, TimeoutError
    import asyncio

    # Create a queue for responses
    response_queue = Queue()
    user_queues[chat_id] = response_queue

    await client.send_message(chat_id, text)

    try:
        # Wait for response with timeout
        response = await asyncio.wait_for(response_queue.get(), timeout=300)  # 5 minutes timeout
        return response
    except TimeoutError:
        await client.send_message(chat_id, "Timeout! Please try again.")
        return None
    finally:
        user_queues.pop(chat_id, None)

# Global queue for user responses
user_queues = {}

def get_link(string):
    """Extract link from text"""
    import re
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»""'']))"
    url = re.findall(regex, string)
    try:
        link = [x[0] for x in url][0]
        if link:
            return link
        else:
            return False
    except Exception:
        return False

async def chk_user(message, user_id):
    """Check if user is premium or admin"""
    # For now, allow all users - you can implement premium check later
    return 0

def get_chat_id_from_link(link):
    """Extract chat ID from link"""
    if 't.me/c/' in link:
        return int('-100' + link.split("/")[-2])
    elif 't.me/b/' in link:
        return link.split("/")[-2]
    else:
        return link.split("/")[-2]

def get_msg_id_from_link(link):
    """Extract message ID from link"""
    return int(link.split("/")[-1])

# -------------------
# Batch processing users
# -------------------
users_loop = {}

# Conversation states for batch
batch_states = {}

# -------------------
# Supported Telegram Reactions
# -------------------

REACTIONS = [
    "🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩",
    "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡",
    "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"
]

# Animated loading spinner frames
LOADING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠃"]
PULSE_FRAMES = ["▓", "▒", "░"]
SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]

# Progress system constants
START_STICKER_ID = "xxxx"  # Replace with actual animated sticker file ID for start
DONE_STICKER_ID = "xxxx"   # Replace with actual animated sticker file ID for done

# File type emojis
FILE_TYPE_EMOJIS = {
    "Video": "📹",
    "Audio": "🎵",
    "Document": "📄",
    "Photo": "🖼️",
    "Animation": "🎞️",
    "Sticker": "🎭",
    "Voice": "🎤",
    "Text": "📝"
}

# Global dict to store progress message IDs
progress_messages = {}



# -------------------
# Download status
# -------------------

async def downstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(2)
    while os.path.exists(statusfile):
        try:
            with open(statusfile, "r", encoding='utf-8') as downread:
                txt = downread.read()
            await client.edit_message_text(
                chat,
                message.id,
                f"📥 **DOWNLOADING**\n{txt}",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await asyncio.sleep(20)
        except:
            await asyncio.sleep(20)

# -------------------
# Upload status
# -------------------

async def upstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(2)
    while os.path.exists(statusfile):
        try:
            with open(statusfile, "r", encoding='utf-8') as upread:
                txt = upread.read()
            await client.edit_message_text(
                chat,
                message.id,
                f"📤 **UPLOADING**\n{txt}",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await asyncio.sleep(20)
        except:
            await asyncio.sleep(20)

# -------------------
# Progress writer
# -------------------
def progress(current, total, client, progress_msg_id, message, type_, msg, user_name, source):
    """
    Progress callback for download/upload with real-time updates, stickers, and detailed info.
    """
    # Check for cancellation
    if batch_temp.IS_BATCH.get(message.from_user.id):
        raise Exception("Cancelled")

    key = f"{message.id}_{type_}"
    if not hasattr(progress, "start_time"):
        progress.start_time = {}
    if key not in progress.start_time:
        progress.start_time[key] = time.time()
    if not hasattr(progress, "last_update"):
        progress.last_update = {}
    if key in progress.last_update and time.time() - progress.last_update[key] < 2:
        return
    progress.last_update[key] = time.time()

    start_time = progress.start_time[key]
    now = time.time()
    elapsed = now - start_time
    if total > 0:
        percentage = (current / total) * 100
        speed = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
    else:
        percentage = 0
        speed = 0
        eta = 0

    # Get file info
    msg_type = get_message_type(msg)
    file_emoji = FILE_TYPE_EMOJIS.get(msg_type, "📦")
    file_name = getattr(msg, 'document', None) and getattr(msg.document, 'file_name', None) or \
               getattr(msg, 'video', None) and getattr(msg.video, 'file_name', None) or \
               getattr(msg, 'audio', None) and getattr(msg.audio, 'file_name', None) or \
               getattr(msg, 'photo', None) and "Photo" or \
               msg_type
    if not file_name:
        file_name = msg_type

    # Sizes
    done_size = humanbytes(current)
    total_size = humanbytes(total)
    percent = int(percentage)
    speed_str = f"{humanbytes(speed)}/s"
    eta_str = TimeFormatter(int(eta))
    elapsed_str = TimeFormatter(int(elapsed))

    # Progress bar
    filled = percent // 10
    remaining = 10 - filled
    if percent < 100:
        current_block = "🟨" if percent % 10 != 0 else ""
        empty_count = remaining - len(current_block)
        bar = "🟩" * filled + current_block + "⬜" * empty_count
    else:
        bar = "🟩" * 10

    # Status
    status = "📥 Downloading…" if type_ == "down" else "📤 Uploading…"

    # Message text
    text = f"""{status}
{file_emoji} File: {file_name}
📦 Size: {done_size}/{total_size}
⚡ Speed: {speed_str}
⏳ Elapsed: {elapsed_str}
⏳ ETA: {eta_str}
📊 Done: {percent}%
{bar}
👤 User: {user_name}
📍 Source: {source}
"""

    # Edit the message
    client.loop.create_task(client.edit_message_text(message.chat.id, progress_msg_id, text, parse_mode=enums.ParseMode.MARKDOWN))

    # On complete
    if current >= total:
        if DONE_STICKER_ID:
            client.loop.create_task(client.send_sticker(message.chat.id, DONE_STICKER_ID, reply_to_message_id=message.id))
        # Clean up
        progress.start_time.pop(key, None)
# -------------------
# Start command
# -------------------

@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    try:
        if not await db.is_user_exist(message.from_user.id):
            await db.add_user(message.from_user.id, message.from_user.first_name)

        session = await db.get_session(message.from_user.id)
        login_status = "✅ Logged In" if session else "❌ Not Logged In"

        buttons = [
            [
                InlineKeyboardButton("🆘 How To Use", callback_data="help_btn"),
                InlineKeyboardButton("ℹ️ About Bot", callback_data="about_btn"),
            ],
            [
                  InlineKeyboardButton("⚙️ Settings", callback_data="settings_btn")
            ],
            [
                InlineKeyboardButton('📢 Official Channel', url='https://t.me/RexBots_Official'),
                InlineKeyboardButton('👨‍💻 Developer', url='https://t.me/about_zani/143')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        try:
            await client.send_message(
                chat_id=message.chat.id,
                text=(
                    f"<blockquote><b>👋 Welcome {message.from_user.mention}!</b></blockquote>\n\n"
                    "<b>I am the Advanced Save Restricted Content Bot by RexBots.</b>\n\n"
                    "<blockquote><b>🚀 What I Can Do:</b>\n"
                    "<b>‣ Save Restricted Post (Text, Media, Files)</b>\n"
                    "<b>‣ Support Private & Public Channels</b>\n"
                    "<b>‣ Batch/Bulk Mode Supported</b></blockquote>\n\n"
                    f"<blockquote><b>🔐 Status:</b> {login_status}</blockquote>\n\n"
                    "<blockquote><b>⚠️ Note:</b> <i>You must <code>/login</code> to your account to use the downloading features.</i></blockquote>"
                ),
                reply_markup=reply_markup,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML
            )
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message after the wait period
            try:
                await client.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"<blockquote><b>👋 Welcome {message.from_user.mention}!</b></blockquote>\n\n"
                        "<b>I am the Advanced Save Restricted Content Bot by RexBots.</b>\n\n"
                        "<blockquote><b>🚀 What I Can Do:</b>\n"
                        "<b>‣ Save Restricted Post (Text, Media, Files)</b>\n"
                        "<b>‣ Support Private & Public Channels</b>\n"
                        "<b>‣ Batch/Bulk Mode Supported</b></blockquote>\n\n"
                        f"<blockquote><b>🔐 Status:</b> {login_status}</blockquote>\n\n"
                        "<blockquote><b>⚠️ Note:</b> <i>You must <code>/login</code> to your account to use the downloading features.</i></blockquote>"
                    ),
                    reply_markup=reply_markup,
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception as e2:
                # If retry also fails, send a simple message
                await client.send_message(
                    chat_id=message.chat.id,
                    text="Welcome to Save Restricted Content Bot! Please try again later.",
                    reply_to_message_id=message.id
                )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Send a simple error message
        try:
            await client.send_message(
                chat_id=message.chat.id,
                text="Welcome to Save Restricted Content Bot! There was an issue loading your data.",
                reply_to_message_id=message.id
            )
        except:
            pass  # If even this fails, ignore

    # try:
    #     await message.react(
    #         emoji=random.choice(REACTIONS),
    #         big=True
    #     )
    # except Exception as e:
    #     print(f"Reaction failed: {e}")

# -------------------
# Help command (standalone)
# -------------------

@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(
        chat_id=message.chat.id,
        text=f"{HELP_TXT}"
    )

# -------------------
# Info command for diagnostics
# -------------------

@Client.on_message(filters.command(["info"]))
async def send_info(client: Client, message: Message):
    """Send diagnostic information about the bot"""
    try:
        # Get bot information
        me = await client.get_me()
        
        # Get user information
        user = message.from_user
        
        # Check login status
        session = await db.get_session(user.id)
        login_status = "✅ Logged In" if session else "❌ Not Logged In"
        
        # Check if user is admin
        is_admin = user.id in ADMINS
        
        # Get system info
        import platform
        import sys
        import psutil
        
        info_text = (
            "<b>🤖 Bot Information</b>\n"
            f"<b>• Name:</b> {me.first_name}\n"
            f"<b>• Username:</b> @{me.username}\n"
            f"<b>• ID:</b> {me.id}\n\n"
            
            "<b>👤 User Information</b>\n"
            f"<b>• Name:</b> {user.first_name}\n"
            f"<b>• Username:</b> @{user.username}\n"
            f"<b>• ID:</b> {user.id}\n"
            f"<b>• Is Admin:</b> {'✅ Yes' if is_admin else '❌ No'}\n\n"
            
            "<b>🔐 Login Status</b>\n"
            f"<b>• Status:</b> {login_status}\n\n"
            
            "<b>💻 System Information</b>\n"
            f"<b>• Platform:</b> {platform.system()} {platform.release()}\n"
            f"<b>• Python:</b> {sys.version}\n"
            f"<b>• Pyrogram:</b> {pyrogram.__version__}\n\n"
            
            "<b>⚠️ Troubleshooting</b>\n"
            "If you're experiencing issues:\n"
            "• Check if you're logged in (/login)\n"
            "• Verify your session is valid\n"
            "• Check if the bot has admin permissions in target channels\n"
            "• Try restarting the bot if issues persist"
        )
        
        await client.send_message(
            chat_id=message.chat.id,
            text=info_text,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        # If there's an error, send a simpler message
        error_info = (
            "<b>❌ Error getting full diagnostic info</b>\n\n"
            f"<b>Error:</b> {str(e)}\n\n"
            "<b>Basic Info:</b>\n"
            f"<b>• User:</b> {message.from_user.first_name}\n"
            f"<b>• User ID:</b> {message.from_user.id}\n"
            f"<b>• Command:</b> /info"
        )
        
        await client.send_message(
            chat_id=message.chat.id,
            text=error_info,
            parse_mode=enums.ParseMode.HTML
        )

# -------------------
# Batch command handler
# -------------------

# Store batch conversation state
batch_conversations = {}

@Client.on_message(filters.private & filters.command(["batch"]))
async def batch_command(client: Client, message: Message):
    user_id = message.chat.id
    lol = await chk_user(message, user_id)
    if lol == 1:
        return

    # Check if the command includes a link as argument
    if len(message.command) > 1:
        # Handle direct link format: /batch https://t.me/c/123456789/1-100
        link_arg = message.command[1]
        if "https://t.me/" in link_arg and "-" in link_arg:
            # Extract start and end message IDs from the link
            parts = link_arg.split("/")
            if len(parts) >= 2:
                last_part = parts[-1]
                if "-" in last_part:
                    try:
                        # Extract start and end IDs
                        start_id_part, end_id_part = last_part.split("-")
                        start_msg_id = int(start_id_part)
                        end_msg_id = int(end_id_part)
                        
                        # Reconstruct the base link
                        base_link = "/".join(parts[:-1]) + "/"
                        start_link = f"{base_link}{start_msg_id}"
                        end_link = f"{base_link}{end_msg_id}"
                        
                        # Process the batch directly
                        is_premium = await db.check_premium(user_id)
                        is_admin = user_id in ADMINS
                        limit = 1000 if is_premium or is_admin else 100
                        
                        # Calculate message count
                        message_count = end_msg_id - start_msg_id + 1
                        
                        if message_count > limit:
                            await client.send_message(message.chat.id, f"Only {limit} messages allowed in batch size... Purchase premium to fly 💸")
                            return
                        
                        # Send confirmation before starting
                        await client.send_message(message.chat.id, f"✅ Starting batch processing for {message_count} message(s)...")
                        
                        try:
                            user_data = await db.get_session(user_id)
                            
                            if user_data:
                                session = user_data
                                try:
                                    userbot = Client(":userbot:", api_id=API_ID, api_hash=API_HASH, session_string=session)
                                    await userbot.start()
                                except:
                                    return await client.send_message(message.chat.id, "Your login expired ... /login again")
                            else:
                                await client.send_message(message.chat.id, "Login in bot first ...")
                                return
                            
                            try:
                                users_loop[user_id] = True
                                
                                # Process each message in the range
                                for current_msg_id in range(start_msg_id, end_msg_id + 1):
                                    if user_id in users_loop and users_loop[user_id]:
                                        try:
                                            # Create processing message
                                            processing_msg = await client.send_message(message.chat.id, f"🔄 Processing message {current_msg_id}...")

                                            # Build the URL
                                            url = f"{base_link}{current_msg_id}"
                                            link = get_link(url)

                                            if not link:
                                                await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Invalid link format for message {current_msg_id}")
                                                continue

                                            # Get chat and message IDs
                                            chat_id = get_chat_id_from_link(link)
                                            msg_id = get_msg_id_from_link(link)

                                            # Get the message
                                            msg = await userbot.get_messages(chat_id, msg_id)
                                            if msg.empty or msg.service:
                                                await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Message {current_msg_id} not found or empty")
                                                continue

                                            # Download
                                            await client.edit_message_text(message.chat.id, processing_msg.id, f"📥 Downloading message {current_msg_id}...")
                                            file = await userbot.download_media(msg)
                                            if not file or not os.path.exists(file):
                                                await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Failed to download message {current_msg_id}")
                                                continue
                                            await asyncio.sleep(1)

                                            # Upload
                                            await client.edit_message_text(message.chat.id, processing_msg.id, f"📤 Uploading message {current_msg_id}...")
                                            await process_and_upload_simple(client, message.chat.id, processing_msg.id, msg, file)

                                            # Add delay to avoid floodwait (only every 5 messages)
                                            if (current_msg_id - start_msg_id) % 5 == 0 and current_msg_id != end_msg_id:
                                                sleep_msg = await client.send_message(message.chat.id, "⏳ Sleeping for 3 seconds to avoid flood...")
                                                await asyncio.sleep(3)
                                                await sleep_msg.delete()

                                        except Exception as e:
                                            error_msg = f"❌ Error processing message {current_msg_id}: {str(e)}"
                                            print(error_msg)
                                            await client.send_message(message.chat.id, error_msg)
                                            continue
                                    else:
                                        await client.send_message(message.chat.id, "⚠️ Batch processing cancelled by user.")
                                        break
                                
                                # Send completion message
                                completed_count = end_msg_id - start_msg_id + 1
                                await client.send_message(message.chat.id, f"🎉 Batch processing completed! Successfully processed {completed_count} message(s).")
                            except Exception as e:
                                error_msg = f"❌ Fatal error in batch processing: {str(e)}"
                                print(error_msg)
                                await client.send_message(message.chat.id, error_msg)
                            finally:
                                # Clean up
                                if user_id in users_loop:
                                    del users_loop[user_id]
                        except Exception as e:
                            await client.send_message(message.chat.id, f"❌ Error starting batch process: {str(e)}")
                        return
                    except (ValueError, IndexError):
                        pass

    # If no direct link provided or invalid format, start interactive mode
    # Initialize batch conversation
    batch_conversations[user_id] = {
        "step": "waiting_for_start_link",
        "start_link": None,
        "end_link": None
    }
    
    await client.send_message(message.chat.id, "📋 Please send the start link.")

@Client.on_message(filters.private & filters.text & ~filters.regex("^/"))
async def handle_batch_conversation(client: Client, message: Message):
    user_id = message.chat.id
    
    # Check if user is in batch conversation
    if user_id in batch_conversations:
        conversation = batch_conversations[user_id]
        text = message.text.strip()
        
        if conversation["step"] == "waiting_for_start_link":
            if "https://t.me/" in text:
                conversation["start_link"] = text
                conversation["step"] = "waiting_for_end_link"
                await client.send_message(message.chat.id, "📋 Please send the end link.")
            else:
                await client.send_message(message.chat.id, "❌ Please send a valid Telegram link starting with https://t.me/")
                
        elif conversation["step"] == "waiting_for_end_link":
            if "https://t.me/" in text:
                conversation["end_link"] = text
                
                # Process the batch
                is_premium = await db.check_premium(user_id)
                is_admin = user_id in ADMINS
                limit = 1000 if is_premium or is_admin else 100
                
                start_id = conversation["start_link"]
                last_id = conversation["end_link"]
                
                s = start_id.split("/")[-1]
                l = last_id.split("/")[-1]
                
                try:
                    cs = int(s)
                    cl = int(l)
                except ValueError:
                    await client.send_message(message.chat.id, "❌ Invalid message IDs in links. Please send valid links.")
                    del batch_conversations[user_id]
                    return

                # Check if range is valid (at least 1 message)
                if cl < cs:
                    await client.send_message(message.chat.id, "❌ End message ID must be greater than start message ID.")
                    del batch_conversations[user_id]
                    return
                
                if cl == cs:
                    # Single message case
                    message_count = 1
                else:
                    message_count = cl - cs + 1

                if message_count > limit:
                    await client.send_message(message.chat.id, f"Only {limit} messages allowed in batch size... Purchase premium to fly 💸")
                    del batch_conversations[user_id]
                    return
                
                # Send confirmation before starting
                await client.send_message(message.chat.id, f"✅ Starting batch processing for {message_count} message(s)...")

                # Clean up conversation state
                del batch_conversations[user_id]
                
                try:
                    user_data = await db.get_session(user_id)

                    if user_data:
                        session = user_data
                        try:
                            userbot = Client(":userbot:", api_id=API_ID, api_hash=API_HASH, session_string=session)
                            await userbot.start()
                        except:
                            return await client.send_message(message.chat.id, "Your login expired ... /login again")
                    else:
                        await client.send_message(message.chat.id, "Login in bot first ...")
                        return

                    try:
                        users_loop[user_id] = True

                        # Handle single message case or range
                        start_msg_id = int(s)
                        end_msg_id = int(l)
                        
                        # Debug: Log the processing start
                        print(f"Starting batch processing for user {user_id}: messages {start_msg_id} to {end_msg_id}")
                        
                        for current_msg_id in range(start_msg_id, end_msg_id + 1):
                            if user_id in users_loop and users_loop[user_id]:
                                try:
                                    # Create processing message
                                    processing_msg = await client.send_message(message.chat.id, f"🔄 Processing message {current_msg_id}...")

                                    # Build the URL
                                    x = start_id.split('/')
                                    y = x[:-1]
                                    result = '/'.join(y)
                                    url = f"{result}/{current_msg_id}"
                                    link = get_link(url)

                                    if not link:
                                        await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Invalid link format for message {current_msg_id}")
                                        continue

                                    # Get chat and message IDs
                                    chat_id = get_chat_id_from_link(link)
                                    msg_id = get_msg_id_from_link(link)

                                    # Get the message
                                    msg = await userbot.get_messages(chat_id, msg_id)
                                    if msg.empty or msg.service:
                                        await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Message {current_msg_id} not found or empty")
                                        continue

                                    # Download
                                    await client.edit_message_text(message.chat.id, processing_msg.id, f"📥 Downloading message {current_msg_id}...")
                                    file = await userbot.download_media(msg)
                                    if not file or not os.path.exists(file):
                                        await client.edit_message_text(message.chat.id, processing_msg.id, f"❌ Failed to download message {current_msg_id}")
                                        continue
                                    await asyncio.sleep(1)

                                    # Upload
                                    await client.edit_message_text(message.chat.id, processing_msg.id, f"📤 Uploading message {current_msg_id}...")
                                    await process_and_upload_simple(client, message.chat.id, processing_msg.id, msg, file)

                                    # Add delay to avoid floodwait (only every 5 messages)
                                    if (current_msg_id - start_msg_id) % 5 == 0 and current_msg_id != end_msg_id:
                                        sleep_msg = await client.send_message(message.chat.id, "⏳ Sleeping for 3 seconds to avoid flood...")
                                        await asyncio.sleep(3)
                                        await sleep_msg.delete()

                                except Exception as e:
                                    error_msg = f"❌ Error processing message {current_msg_id}: {str(e)}"
                                    print(error_msg)
                                    await client.send_message(message.chat.id, error_msg)
                                    continue
                            else:
                                await client.send_message(message.chat.id, "⚠️ Batch processing cancelled by user.")
                                break
                        
                        # Send completion message
                        completed_count = end_msg_id - start_msg_id + 1
                        await client.send_message(message.chat.id, f"🎉 Batch processing completed! Successfully processed {completed_count} message(s).")
                        
                    except Exception as e:
                        error_msg = f"❌ Fatal error in batch processing: {str(e)}"
                        print(error_msg)  # Debug log
                        await client.send_message(message.chat.id, error_msg)
                    finally:
                        # Clean up
                        if user_id in users_loop:
                            del users_loop[user_id]

                except Exception as e:
                    await client.send_message(message.chat.id, f"❌ Error starting batch process: {str(e)}")
            else:
                await client.send_message(message.chat.id, "❌ Please send a valid Telegram link starting with https://t.me/")

# -------------------
# Cancel command
# -------------------

@Client.on_message(filters.private & filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    logger.info(f"Cancel command received from user {message.from_user.id}")

    user_id = message.chat.id
    if user_id in users_loop:
        users_loop[user_id] = False
        await client.send_message(message.chat.id, "Batch processing stopped.")
    else:
        await client.send_message(message.chat.id, "No active batch processing to stop.")


# -------------------
# Handle incoming messages
# -------------------


@Client.on_message(filters.private & filters.regex(r'https?://[^\s]+') & ~filters.create(lambda _, __, msg: msg.chat.id in user_queues))
async def single_link(client: Client, message: Message):
    user_id = message.chat.id
    lol = await chk_user(message, user_id)
    if lol == 1:
        return

    link = get_link(message.text)

    try:
        try:
            msg = await message.reply("Processing...")
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message after the wait period
            msg = await message.reply("Processing...")

        # Try to get user session if available
        user_data = await db.get_session(user_id)
        session = None
        userbot = None

        if user_data:
            session = user_data
            try:
                userbot = Client(":userbot:", api_id=API_ID, api_hash=API_HASH, session_string=session)
                await userbot.start()
            except:
                await msg.edit_text("Login expired /login again...")
                return

        if 't.me/' in link:
            await process_single_link(client, userbot, user_id, msg.id, link, message)

    except Exception as e:
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")

async def process_single_link(client, userbot, sender, edit_id, msg_link, message):
    edit = ""
    chat = ""

    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    msg_id = int(msg_link.split("/")[-1])

    if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
        if 't.me/b/' not in msg_link:
            chat = int('-100' + str(msg_link.split("/")[-2]))
        else:
            chat = msg_link.split("/")[-2]

        try:
            if userbot:
                msg = await userbot.get_messages(chat, msg_id)
                if msg.service or msg.empty:
                    await msg.edit_text("Message not found or empty.")
                    return

                if msg.media and msg.media == MessageMediaType.WEB_PAGE:
                    await client.edit_message_text(sender, edit_id, "Cloning...")
                    safe_repo = await client.send_message(sender, msg.text.markdown)
                    if LOG_CHANNEL:
                        await safe_repo.copy(LOG_CHANNEL)
                    await client.delete_messages(sender, edit_id)
                    return

                if not msg.media and msg.text:
                    await client.edit_message_text(sender, edit_id, "Cloning...")
                    safe_repo = await client.send_message(sender, msg.text.markdown)
                    if LOG_CHANNEL:
                        await safe_repo.copy(LOG_CHANNEL)
                    await client.delete_messages(sender, edit_id)
                    return

                await client.edit_message_text(sender, edit_id, "📥 Downloading...")
                file = await userbot.download_media(msg)

                # Process file and upload
                await process_and_upload_simple(client, sender, edit_id, msg, file)

            else:
                # No userbot - for private channels, tell user to login
                if 't.me/c/' in msg_link:
                    await client.edit_message_text(sender, edit_id, "**🔒 This is a private channel link.**\n\nPlease /login first to download restricted content.")
                    return
                # For public/batch channels, try direct copy
                chat = msg_link.split("/")[-2]
                await copy_message_public(client, sender, chat, msg_id, message)
                await client.delete_messages(sender, edit_id)
        except Exception as e:
            logger.error(f"Error in process_single_link: {e}")
            await client.edit_message_text(sender, edit_id, f"Error: {str(e)}")

async def process_and_upload_simple(client, sender, edit_id, msg, file):
    """Simple upload without progress to avoid stuck issues"""
    try:
        await client.edit_message_text(sender, edit_id, "📤 Uploading...")
        
        # Verify file exists and is valid before uploading
        if not file or not os.path.exists(file):
            raise Exception("Media file not found for upload")
        
        if msg.media == MessageMediaType.VIDEO:
            await client.send_video(
                chat_id=sender,
                video=file,
                caption=clean_caption(msg.caption)
            )
        elif msg.media == MessageMediaType.PHOTO:
            await client.send_photo(sender, file, caption=clean_caption(msg.caption))
        else:
            await client.send_document(
                chat_id=sender,
                document=file,
                caption=clean_caption(msg.caption)
            )
        
        # Cleanup
        if os.path.exists(file):
            os.remove(file)
        
        await client.delete_messages(sender, edit_id)
        
    except Exception as e:
        logger.error(f"Error in upload: {e}")
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        # Send error message to user
        await client.edit_message_text(sender, edit_id, f"❌ Upload failed: {str(e)}")

async def copy_message_public(client, sender, chat_id, message_id, original_message):
    try:
        msg = await client.get_messages(chat_id, message_id)

        if msg.media:
            if msg.media == MessageMediaType.VIDEO:
                result = await client.send_video(sender, msg.video.file_id, caption=msg.caption)
            elif msg.media == MessageMediaType.DOCUMENT:
                result = await client.send_document(sender, msg.document.file_id, caption=msg.caption)
            elif msg.media == MessageMediaType.PHOTO:
                result = await client.send_photo(sender, msg.photo.file_id, caption=msg.caption)
            else:
                result = await client.copy_message(sender, chat_id, message_id)
        else:
            result = await client.copy_message(sender, chat_id, message_id)

        # Copy to log channel if available
        try:
            log_channel = os.environ.get("LOG_CHANNEL")
            if log_channel:
                await result.copy(log_channel)
        except:
            pass

        if msg.pinned_message:
            try:
                await result.pin(both_sides=True)
            except:
                await result.pin()

    except Exception as e:
        # If direct copy fails, try with userbot if available
        raise e

async def process_and_upload(client, userbot, sender, edit_id, msg, file, message):
    await client.edit_message_text(sender, edit_id, 'Trying to Upload...')

    if msg.media == MessageMediaType.VIDEO:
        try:
            await client.send_video(
                chat_id=sender,
                video=file,
                caption=clean_caption(msg.caption),
                progress=progress,
                progress_args=[message, "up"]
            )
        except:
            await client.edit_message_text(sender, edit_id, "The bot is not an admin in the specified chat...")

    elif msg.media == MessageMediaType.PHOTO:
        await client.send_photo(sender, file, caption=clean_caption(msg.caption))

    else:
        await client.send_document(
            chat_id=sender,
            document=file,
            caption=clean_caption(msg.caption),
            progress=progress,
            progress_args=[message, "up"]
        )

    # Cleanup
    if os.path.exists(file):
        os.remove(file)

    await client.delete_messages(sender, edit_id)

@Client.on_message(filters.private & filters.text & ~filters.regex("^/") & ~filters.create(lambda _, __, msg: msg.chat.id in user_queues) & ~filters.regex(r'^https?://t\.me/'))
async def save(client: Client, message: Message):
    try:
        logger.info(f"Received message from {message.from_user.id}: {message.text}")
        if "https://t.me/" in message.text:
            try:
                await message.reply("🔄 **Processing your link...**", parse_mode=enums.ParseMode.HTML)
            except FloodWait as e:
                # Handle flood wait by sleeping for the required duration
                await asyncio.sleep(e.value)
                # Retry the message after the wait period
                await message.reply("🔄 **Processing your link...**", parse_mode=enums.ParseMode.HTML)
        # Check if batch is already running
        if batch_temp.IS_BATCH.get(message.from_user.id) == False:
            return await message.reply_text(
                "**__⚠️ One Task Is Already Processing. Wait For Complete It.\nIf You Want To Cancel This Task Then Use - /cancel__**",
                parse_mode=enums.ParseMode.HTML
            )

        # Initialize batch flag
        batch_temp.IS_BATCH[message.from_user.id] = False

        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        is_private = "https://t.me/c/" in message.text
        is_batch = "https://t.me/b/" in message.text
        
        # Calculate total messages for progress
        total_msgs = toID - fromID + 1
        
        # Send batch start confirmation
        start_msg = await message.reply_text(
            f"**__📦 Batch Processing Started__**\n"
            f"**📋 Range:** {fromID} - {toID} ({total_msgs} messages)\n"
            f"**🔄 Status:** Processing...",
            parse_mode=enums.ParseMode.HTML
        )
        
        for msgid in range(fromID, toID + 1):
            if batch_temp.IS_BATCH.get(message.from_user.id):
                break
            
            # Update progress message
            current_num = msgid - fromID + 1
            percentage = (current_num / total_msgs) * 100 if total_msgs > 0 else 0
            try:
                await start_msg.edit(
                    f"**__📦 Batch Processing__**\n"
                    f"**📋 Progress:** {current_num}/{total_msgs} ({percentage:.1f}%)\n"
                    f"**🔄 Processing ID:** {msgid}",
                    parse_mode=enums.ParseMode.HTML
                )
            except:
                pass
            
            # 1. Try Public Copy (No Login Required)
            if not is_private and not is_batch:
                username = datas[3]
                try:
                    msg = await client.get_messages(username, msgid)
                    await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    await asyncio.sleep(1)
                    continue
                except Exception as e:
                    logger.error(f"Public copy failed for {username}/{msgid}: {e}")
                    pass # Fallback to login method
            
            # 2. Login Check
            user_data = await db.get_session(message.from_user.id)
            if user_data is None:
                await message.reply("**__🚪 For Downloading Restricted Content You Have To /login First.__**")
                batch_temp.IS_BATCH[message.from_user.id] = True
                await start_msg.edit("**__❌ Batch Stopped: Not Logged In__**", parse_mode=enums.ParseMode.HTML)
                return

            # 3. Connect User Client
            try:
                acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID, in_memory=True)
                await acc.connect()
            except (AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan) as e:
                batch_temp.IS_BATCH[message.from_user.id] = True
                await db.set_session(message.from_user.id, None)
                await message.reply(f"**__🚪 Your Login Session Invalid/Expired. Please /login again.__**\nError: {e}")
                await start_msg.edit("**__❌ Batch Stopped: Session Expired__**", parse_mode=enums.ParseMode.HTML)
                return
            except Exception:
                batch_temp.IS_BATCH[message.from_user.id] = True
                await message.reply("**__🚪 Your Login Session Error. So /logout First Then Login Again By - /login__**")
                await start_msg.edit("**__❌ Batch Stopped: Session Error__**", parse_mode=enums.ParseMode.HTML)
                return

            # 4. Handle Content
            if is_private:
                chatid = int("-100" + datas[4])
                try:
                    await handle_private(client, acc, message, chatid, msgid)
                except Exception as e:
                    logger.error(f"Error handling private chat: {e}")
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            elif is_batch:
                username = datas[4]
                try:
                    await handle_private(client, acc, message, username, msgid)
                except Exception as e:
                    logger.error(f"Error handling batch channel: {e}")
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            else:
                # Restricted Public Channel
                username = datas[3]
                try:
                    await handle_private(client, acc, message, username, msgid)
                except Exception as e:
                    logger.error(f"Error copy/handle private: {e}")
                    if ERROR_MESSAGE:
                         await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)
            
            # Enhanced logging for debugging channel issues
            logger.info(f"Processed message {msgid} from channel {username if not is_private else chatid}")
            logger.info(f"User: {message.from_user.id}, Session valid: {await db.get_session(message.from_user.id) is not None}")

            await asyncio.sleep(2)

        batch_temp.IS_BATCH[message.from_user.id] = True
        
        # Send completion message
        if not batch_temp.IS_BATCH.get(message.from_user.id, True):
            await start_msg.edit("**__✅ Batch Processing Completed Successfully!__**", parse_mode=enums.ParseMode.HTML)
        else:
            await start_msg.edit("**__ℹ️ Batch Processing Ended__**", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in save function: {e}")
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

# -------------------
# Handle private content
# -------------------

async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int) -> bool:
    try:
        msg: Message = await acc.get_messages(chatid, msgid)
    except (AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan) as e:
        batch_temp.IS_BATCH[message.from_user.id] = True
        await db.set_session(message.from_user.id, None)
        await client.send_message(message.chat.id, f"Session Token Invalid/Expired. Please /login again.\nError: {e}")
        return False
    except Exception as e:
        # Handle PeerIdInvalid (which might come as generic Exception or RPCError)
        # We try to refresh dialogs to learn about the peer.
        logger.warning(f"Error fetching message: {e}. Refreshing dialogs...")
        
        # Special error handling for channel -1003508871162
        if chatid == -1003508871162:
            await client.send_message(
                message.chat.id,
                f"❌ **Error accessing channel -1003508871162**\n\n"
                f"**Error Details:** {str(e)}\n\n"
                "**Possible Solutions:**\n"
                "• Check if the channel exists\n"
                "• Verify you have access to the channel\n"
                "• Ensure your session is valid\n"
                "• Try /login again if needed\n\n"
                "The bot will continue processing other messages."
            )
        
        # Enhanced error handling for specific channels like https://t.me/Rk_Movie096
        if "Rk_Movie096" in str(e) or chatid == -1003508871162:
            logger.error(f"Specific channel error - Rk_Movie096: {str(e)}")
            await client.send_message(
                message.chat.id,
                f"❌ **Channel-Specific Error - Rk_Movie096**\n\n"
                f"**Error Type:** {type(e).__name__}\n"
                f"**Error Details:** {str(e)}\n\n"
                "**Debugging Information:**\n"
                f"• Channel ID: {chatid}\n"
                f"• Message ID: {msgid}\n"
                "• This channel may have restrictions or require special permissions\n"
                "• The bot will attempt to continue with other messages"
            )
        
        try:
            async for dialog in acc.get_dialogs(limit=None):
                if dialog.chat.id == chatid:
                    break
            msg: Message = await acc.get_messages(chatid, msgid)
        except (AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan) as e:
            batch_temp.IS_BATCH[message.from_user.id] = True
            await db.set_session(message.from_user.id, None)
            await client.send_message(message.chat.id, f"Session Token Invalid/Expired. Please /login again.\nError: {e}")
            return False
        except Exception as e2:
            logger.error(f"Retry failed: {e2}")
            
            # Additional error reporting for the specific channel
            if chatid == -1003508871162:
                await client.send_message(
                    message.chat.id,
                    f"❌ **Persistent error with channel -1003508871162**\n\n"
                    f"**Final Error:** {str(e2)}\n\n"
                    "Please check:\n"
                    "• Channel accessibility\n"
                    "• Your permissions\n"
                    "• Bot session validity"
                )
            
            # Enhanced logging for debugging
            logger.error(f"Final error for channel {chatid}, message {msgid}: {str(e2)}")
            logger.error(f"Channel ID: {chatid}, Message ID: {msgid}")
            logger.error(f"User ID: {message.from_user.id}")
            logger.error(f"Session valid: {await db.get_session(message.from_user.id) is not None}")
            
            return False

    if msg.empty:
        return False

    msg_type = get_message_type(msg)
    if not msg_type:
        return False

    chat = message.chat.id
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return False

    if "Text" == msg_type:
        try:
            await client.send_message(chat, f"**__{msg.text}__**", entities=msg.entities, reply_to_message_id=message.id,
                                      parse_mode=enums.ParseMode.HTML)
            return True
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id,
                                          parse_mode=enums.ParseMode.HTML)
            return False

    smsg = await client.send_message(
        message.chat.id,
        '🚀 **PROCESSING**\nPreparing your file... Please wait...',
        reply_to_message_id=message.id,
        parse_mode=enums.ParseMode.MARKDOWN
    )
    
    # ----------------------------------------
    # Create unique temp directory for this task
    # ----------------------------------------
    temp_dir = f"downloads/{message.id}"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

        
    try:
        # Get source info for progress
        try:
            chat_info = await acc.get_chat(chatid)
            source_title = chat_info.title if chat_info else str(chatid)
        except:
            source_title = str(chatid)
        user_name = message.from_user.first_name

        # Send start sticker and progress message
        if START_STICKER_ID:
            await client.send_sticker(message.chat.id, START_STICKER_ID, reply_to_message_id=message.id)
        progress_msg = await client.send_message(message.chat.id, "Starting download...", reply_to_message_id=message.id)

        # Download into unique directory (folder path must end with / for Pyrogram)
        file = await acc.download_media(msg, file_name=f"{temp_dir}/", progress=progress, progress_args=[client, progress_msg.id, message, "down", msg, user_name, source_title])
        
        # Ensure file was downloaded successfully
        if not file or not os.path.exists(file):
            raise Exception("Failed to download media file")
        if os.path.exists(f'{message.id}downstatus.txt'):
            os.remove(f'{message.id}downstatus.txt')
    except Exception as e:
        # Check if cancelled (flag is True) or exception message contains "Cancelled"
        if batch_temp.IS_BATCH.get(message.from_user.id) or "Cancelled" in str(e):
            if os.path.exists(f'{message.id}downstatus.txt'):
                try:
                    os.remove(f'{message.id}downstatus.txt')
                except:
                    pass
            
            # Robust Cleanup: Delete the entire temp directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
            return await smsg.edit("❌ **Task Cancelled**")
            
        logger.error(f"Error downloading media: {e}")
        
        # Cleanup on error
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
                
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id,
                                      parse_mode=enums.ParseMode.HTML)
        return await smsg.delete()

    if batch_temp.IS_BATCH.get(message.from_user.id):
        # Cleanup if cancelled during gap
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return False

    caption = clean_caption(msg.caption) if msg.caption else None
    
    if batch_temp.IS_BATCH.get(message.from_user.id):
         # Cleanup if cancelled during gap
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return False

    try:
        # Send start sticker and progress message for upload
        if START_STICKER_ID:
            await client.send_sticker(message.chat.id, START_STICKER_ID, reply_to_message_id=message.id)
        progress_msg = await client.send_message(message.chat.id, "Starting upload...", reply_to_message_id=message.id)

        # Ensure file exists before attempting to send
        if not file or not os.path.exists(file):
            raise Exception("Media file not found for upload")
        try:
            chat_info = await acc.get_chat(chatid)
            source_title = chat_info.title if chat_info else str(chatid)
        except:
            source_title = str(chatid)
        user_name = message.from_user.first_name
            
        if "Document" == msg_type:
            try:
                ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
            except:
                ph_path = None
            await client.send_document(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id,
                                       parse_mode=enums.ParseMode.HTML, progress=progress,
                                       progress_args=[client, progress_msg.id, message, "up", msg, user_name, source_title])
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif "Video" == msg_type:
            try:
                ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
            except:
                ph_path = None
            await client.send_video(chat, file, duration=msg.video.duration, width=msg.video.width,
                                    height=msg.video.height, thumb=ph_path, caption=caption,
                                    reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML,
                                    progress=progress, progress_args=[client, progress_msg.id, message, "up", msg, user_name, source_title])
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif "Animation" == msg_type:
            await client.send_animation(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

        elif "Sticker" == msg_type:
            await client.send_sticker(chat, file, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

        elif "Voice" == msg_type:
            await client.send_voice(chat, file, caption=caption, caption_entities=msg.caption_entities,
                                    reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML,
                                    progress=progress, progress_args=[client, progress_msg.id, message, "up", msg, user_name, source_title])

        elif "Audio" == msg_type:
            try:
                ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
            except:
                ph_path = None
            await client.send_audio(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=message.id,
                                    parse_mode=enums.ParseMode.HTML, progress=progress,
                                    progress_args=[client, progress_msg.id, message, "up", msg, user_name, source_title])
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        elif "Photo" == msg_type:
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=message.id,
                                    parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        # Check if cancelled (flag is True) or exception message contains "Cancelled"
        if batch_temp.IS_BATCH.get(message.from_user.id) or "Cancelled" in str(e):
            if os.path.exists(f'{message.id}upstatus.txt'):
                try:
                    os.remove(f'{message.id}upstatus.txt')
                except:
                    pass
            
            # Robust Cleanup: Delete the entire temp directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            return await smsg.edit("❌ **Task Cancelled**")

        logger.error(f"Error sending media: {e}")
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id,
                                      parse_mode=enums.ParseMode.HTML)

    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
        
    # Final cleanup of temp directory
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

    await client.delete_messages(message.chat.id, [smsg.id])
    return True

#-------------------
# Get message type
# -------------------

def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass
    try:
        msg.video.file_id
        return "Video"
    except:
        pass
    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass
    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass
    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass
    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass
    try:
        msg.text
        return "Text"
    except:
        pass

# -------------------
# Inline button callback
# -------------------

@Client.on_callback_query()
async def button_callbacks(client: Client, callback_query):
    data = callback_query.data
    message = callback_query.message

    # Help button  
    if data == "help_btn":
        help_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close_btn"),
                InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="start_btn")
            ]
        ])
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=HELP_TXT,
                reply_markup=help_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message edit after the wait period
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=HELP_TXT,
                reply_markup=help_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        await callback_query.answer()

    # About button
    elif data == "about_btn":
        me = await client.get_me()
        about_text = (
            "<b><blockquote>‣ ℹ️ 𝐁𝐎𝐓 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍</blockquote>\n\n"
            "<i>• 🤖 𝐍𝐚𝐦𝐞 : 𝐒𝐚𝐯𝐞 𝐑𝐞𝐬𝐭𝐫𝐢𝐜𝐭𝐞𝐝 𝐂𝐨𝐧𝐭𝐞𝐧𝐭\n"
            "• 👨‍💻 𝐎𝐰𝐧𝐞𝐫 : <a href='https://t.me/RexBots_Official'>𝐑𝐞𝐱𝐁𝐨𝐭𝐬</a>\n"
            "• 📡 𝐔𝐩𝐝𝐚𝐭𝐞𝐬 : <a href='https://t.me/RexBots_Official'>𝐑𝐞𝐱𝐁𝐨𝐭𝐬 𝐎𝐟𝐟𝐢𝐜𝐢𝐚𝐥</a>\n"
            "• 🐍 𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞 : <a href='https://www.python.org/'>𝐏𝐲𝐭𝐡𝐨𝐧 𝟑</a>\n"
            "• 📚 𝐋𝐢𝐛𝐫𝐚𝐫𝐲 : <a href='https://docs.pyrogram.org/'>𝐏𝐲𝐫𝐨𝐠𝐫𝐚𝐦</a>\n"
            "• 🗄 𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 : <a href='#'>𝐉𝐒𝐎𝐍 𝐅𝐢𝐥𝐞</a>\n"
            "• 📊 𝐕𝐞𝐫𝐬𝐢𝐨𝐧 : 𝟐.𝟎.𝟏 [𝐒𝐭𝐚𝐛𝐥𝐞]</i></b>"
        )

        about_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Join Channel", url="https://t.me/RexBots_Official")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close_btn"),
                InlineKeyboardButton("🔙 Back", callback_data="start_btn")
            ]
        ])

        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=about_text,
                reply_markup=about_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message edit after the wait period
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=about_text,
                reply_markup=about_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        await callback_query.answer()

    # Home / Start button
    elif data == "start_btn":
        session = await db.get_session(callback_query.from_user.id)
        login_status = "✅ Logged In" if session else "❌ Not Logged In"

        start_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🆘 How To Use", callback_data="help_btn"),
                InlineKeyboardButton("ℹ️ About Bot", callback_data="about_btn")
            ],
            [
                InlineKeyboardButton('📢 Official Channel', url='https://t.me/RexBots_Official'),
                InlineKeyboardButton('👨‍💻 Developer', url='https://t.me/RexBots_Official')
            ]
        ])
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=(
                    f"<blockquote><b>👋 Welcome {callback_query.from_user.mention}!</b></blockquote>\n\n"
                    "<b>I am the Advanced Save Restricted Content Bot by RexBots.</b>\n\n"
                    "<blockquote><b>🚀 What I Can Do:</b>\n"
                    "<b>‣ Save Restricted Post (Text, Media, Files)</b>\n"
                    "<b>‣ Support Private & Public Channels</b>\n"
                    "<b>‣ Batch/Bulk Mode Supported</b></blockquote>\n\n"
                    f"<blockquote><b>🔐 Status:</b> {login_status}</blockquote>\n\n"
                    "<blockquote><b>⚠️ Note:</b> <i>You must <code>/login</code> to your account to use the downloading features.</i></blockquote>"
                ),
                reply_markup=start_buttons,
                parse_mode=enums.ParseMode.HTML
            )
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message edit after the wait period
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=(
                    f"<blockquote><b>👋 Welcome {callback_query.from_user.mention}!</b></blockquote>\n\n"
                    "<b>I am the Advanced Save Restricted Content Bot by RexBots.</b>\n\n"
                    "<blockquote><b>🚀 What I Can Do:</b>\n"
                    "<b>‣ Save Restricted Post (Text, Media, Files)</b>\n"
                    "<b>‣ Support Private & Public Channels</b>\n"
                    "<b>‣ Batch/Bulk Mode Supported</b></blockquote>\n\n"
                    f"<blockquote><b>🔐 Status:</b> {login_status}</blockquote>\n\n"
                    "<blockquote><b>⚠️ Note:</b> <i>You must <code>/login</code> to your account to use the downloading features.</i></blockquote>"
                ),
                reply_markup=start_buttons,
                parse_mode=enums.ParseMode.HTML
            )
        await callback_query.answer()

    # Settings button (Command List)
    elif data == "settings_btn":
        settings_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Close", callback_data="close_btn"),
                InlineKeyboardButton("🔙 Back", callback_data="start_btn")
            ]
        ])
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=COMMANDS_TXT,
                reply_markup=settings_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        except FloodWait as e:
            # Handle flood wait by sleeping for the required duration
            await asyncio.sleep(e.value)
            # Retry the message edit after the wait period
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=COMMANDS_TXT,
                reply_markup=settings_buttons,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        await callback_query.answer()

    # Close button
    elif data == "close_btn":
        await client.delete_messages(message.chat.id, [message.id])
        await callback_query.answer()


# Don't remove Credits
# Rexbots
# Developer Telegram @RexBots_Official
# Update channel - @RexBots_Official

# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

