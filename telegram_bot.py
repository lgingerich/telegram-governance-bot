import json
import logging
from google.cloud import pubsub_v1, firestore
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Initialize Firestore
db = firestore.Client()

# Initialize the Pub/Sub client
publisher = pubsub_v1.PublisherClient()

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to the Crypto Governance Event Notifications bot!")

def subscribe(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    keywords = context.args

    if not keywords:
        update.message.reply_text("Please provide keywords to subscribe to.")
        return

    # Add subscription to Firestore
    doc_ref = db.collection("subscriptions").document(str(user_id))
    doc_ref.set({"keywords": firestore.ArrayUnion(keywords)}, merge=True)

    update.message.reply_text(f"Successfully subscribed to: {', '.join(keywords)}")

def unsubscribe(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    keywords = context.args

    if not keywords:
        update.message.reply_text("Please provide keywords to unsubscribe from.")
        return

    # Remove subscription from Firestore
    doc_ref = db.collection("subscriptions").document(str(user_id))
    doc_ref.update({"keywords": firestore.ArrayRemove(keywords)})

    update.message.reply_text(f"Successfully unsubscribed from: {', '.join(keywords)}")

def list_subscriptions(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Retrieve user's subscriptions from Firestore
    doc_ref = db.collection("subscriptions").document(str(user_id))
    doc = doc_ref.get()

    if doc.exists:
        preferences = doc.to_dict()
        keywords = preferences["keywords"]
        update.message.reply_text(f"Your current subscriptions: {', '.join(keywords)}")
    else:
        update.message.reply_text("You have no subscriptions.")

def help(update: Update, context: CallbackContext):
    help_text = (
        "Available commands:\n\n"
        "/start - Welcome message\n"
        "/subscribe <keywords> - Subscribe to event notifications for the given keywords\n"
        "/unsubscribe <keywords> - Unsubscribe from event notifications for the given keywords\n"
        "/list - List your current subscriptions\n"
        "/help - Show this help message"
    )
    update.message.reply_text(help_text)

def send_notification(user_id, message):
    topic_path = publisher.topic_path('your-gcp-project-id', 'crypto-events')
    data = {
        "user_id": user_id,
        "message": message
    }
    data_json = json.dumps(data)
    data_bytes = data_json.encode('utf-8')
    publisher.publish(topic_path, data=data_bytes)

updater = Updater(TOKEN)

updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CommandHandler("subscribe", subscribe))
updater.dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))
updater.dispatcher.add_handler(CommandHandler("list", list_subscriptions))
updater.dispatcher.add_handler(CommandHandler("help", help))

updater.start_polling()
updater.idle()
