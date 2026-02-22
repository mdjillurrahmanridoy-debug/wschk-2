import requests
import telebot
from telebot import types
import re
import io
import threading
import time

# --- Bot Configuration ---
# Your provided Telegram Bot Token
API_TOKEN = '8469842973:AAGBhc6sFXFJ3zmHgptfrfBiczme2tF5FGw'
bot = telebot.TeleBot(API_TOKEN)

# In-memory storage for user sessions (Separate for each user)
user_sessions = {}

# --- Formatting Toolkit ---

def main_keyboard():
    """Creates a permanent reply keyboard with English labels."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("➕ Add Session")
    btn2 = types.KeyboardButton("🔗 Session Check")
    btn3 = types.KeyboardButton("📊 Bulk Check")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup

def get_progress_bar(current, total):
    """Generates a visual loading bar for progress tracking."""
    size = 10
    filled = int((current / total) * size)
    bar = "█" * filled + "░" * (size - filled)
    percent = int((current / total) * 100)
    return f"[{bar}] {percent}%"

# --- Core Logic ---

def check_whatsapp(number, session):
    """Checks WhatsApp registration status via Maytapi API."""
    url = f"https://api.maytapi.com/api/{session['p_id']}/{session['ph_id']}/checkNumberStatus"
    params = {'token': session['token'], 'number': f"{number}@c.us"}
    try:
        # Optimized timeout for high-speed checking
        response = requests.get(url, params=params, timeout=1.5)
        data = response.json()
        if data.get('success') and data.get('result', {}).get('status') == 200:
            return True
        return False
    except:
        return None

# --- Message Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! This bot helps you check WhatsApp registration in bulk with high speed.", 
                 reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🔗 Session Check")
def session_status(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        bot.reply_to(message, f"✅ **Session Active**\n\nProduct ID: `{s['p_id']}`\nPhone ID: `{s['ph_id']}`", 
                     parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ No active session found for your account.")

@bot.message_handler(func=lambda message: message.text == "➕ Add Session")
def ask_session_link(message):
    user_id = message.from_user.id
    # Guardrail: Prevent redundant session activation
    if user_id in user_sessions:
        bot.reply_to(message, "⚠️ Session is already activated! You are ready to check numbers.")
        return
        
    msg = bot.send_message(message.chat.id, "Please paste your full Maytapi API link:")
    bot.register_next_step_handler(msg, process_session_link)

def process_session_link(message):
    try:
        # Extracting credentials using Regex
        match = re.search(r'api/([^/]+)/([^/?&]+)', message.text)
        token_match = re.search(r'token=([^&]+)', message.text)
        
        if match and token_match:
            user_sessions[message.from_user.id] = {
                'p_id': match.group(1),
                'ph_id': match.group(2),
                'token': token_match.group(1)
            }
            bot.reply_to(message, "✅ Success! Your session has been linked successfully.")
        else:
            bot.reply_to(message, "❌ Invalid link. Please provide a valid Maytapi API URL.")
    except Exception:
        bot.reply_to(message, "⚠️ An error occurred while parsing the link.")

@bot.message_handler(func=lambda message: message.text == "📊 Bulk Check")
def ask_bulk(message):
    if message.from_user.id not in user_sessions:
        bot.reply_to(message, "❌ Please add a session first using the 'Add Session' button.")
        return
    bot.reply_to(message, "Send a list of numbers or upload a `.txt` file (Maximum 100).")

@bot.message_handler(content_types=['document', 'text'])
def handle_bulk_input(message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        return
    
    # Filter out navigation commands
    if message.content_type == 'text' and message.text in ["➕ Add Session", "🔗 Session Check", "📊 Bulk Check"]:
        return

    numbers = []
    if message.content_type == 'document':
        if message.document.file_name.endswith('.txt'):
            file_info = bot.get_file(message.document.file_id)
            numbers = bot.download_file(file_info.file_path).decode('utf-8').splitlines()
    else:
        numbers = re.findall(r'\d+', message.text)

    if numbers:
        # Run processing in a background thread to keep the bot responsive
        threading.Thread(target=process_with_loading, args=(message, numbers, user_sessions[user_id])).start()

def process_with_loading(message, numbers, session):
    clean_nums = [n.strip().replace('+', '') for n in numbers if n.strip()][:100]
    total = len(clean_nums)
    status_msg = bot.send_message(message.chat.id, f"🚀 Initializing...\n{get_progress_bar(0, total)}")
    
    reg_list = []
    unreg_list = []

    for index, num in enumerate(clean_nums):
        status = check_whatsapp(num, session)
        
        # Mandatory formatting: Adding '+' prefix to output
        formatted_num = f"+{num}"
        
        if status is True:
            reg_list.append(formatted_num)
        elif status is False:
            unreg_list.append(formatted_num)
        
        # Update progress bar every 5 iterations or at the end
        if (index + 1) % 5 == 0 or (index + 1) == total:
            try:
                bar = get_progress_bar(index + 1, total)
                bot.edit_message_text(f"⏳ **Processing Bulk Data...**\n\n{bar}\nProgress: {index + 1}/{total}", 
                                      chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
            except Exception:
                pass

    # Generate and send Result Files
    if reg_list:
        reg_file = io.BytesIO("\n".join(reg_list).encode())
        reg_file.name = "Registered.txt"
        bot.send_document(message.chat.id, reg_file, caption=f"✅ Registered: {len(reg_list)} numbers found.")
    
    if unreg_list:
        unreg_file = io.BytesIO("\n".join(unreg_list).encode())
        unreg_file.name = "Unregistered.txt"
        bot.send_document(message.chat.id, unreg_file, caption=f"❌ Unregistered: {len(unreg_list)} numbers found.")

    bot.delete_message(message.chat.id, status_msg.message_id)

# Start the bot
bot.infinity_polling()