import os
import http
import json
import base64
from google.cloud import firestore
from flask import Flask, request
from werkzeug.wrappers import Response
from telegram import Bot, Update
from telegram.ext import (
    Dispatcher,
    Filters,
    MessageHandler,
    CallbackContext,
    CommandHandler,
)

app = Flask(__name__)


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to the Crypto Governance Event Notifications bot!\n\n"
        "Subscribe to be notified of governance proposal actions in real-time. "
        "Notifications can be set for specific projects, keywords, and proposal events (created, started, ended, deleted). "
        "Here are some commands to get started. \n\n"
        "/subscribe - Subscribe to projects and keywords\n"
        "    To subscribe to projects: /subscribe project project1 project2\n"
        "    To subscribe to keywords: /subscribe keyword keyword1 keyword2\n"
        "/unsubscribe - Unsubscribe from projects and keywords\n"
        "    To unsubscribe from projects: /unsubscribe project project1 project2\n"
        "    To unsubscribe from keywords: /unsubscribe keyword keyword1 keyword2\n"
        "/list_subscriptions - List your current subscriptions\n"
        "/help - Show the help message"
    )


def subscribe(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args
    projects = []
    keywords = []

    if len(args) < 2:
        update.message.reply_text("Please provide a project or keyword.")
        return

    if args[0] == "keyword":
        keywords.extend(args[1:])
    elif args[0] == "project":
        projects.extend(args[1:])
    else:
        update.message.reply_text("Please provide a project or keyword.")
        return

    if not projects and not keywords:
        update.message.reply_text("Please provide a project or keyword.")
        return

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Check document existence
    doc = user_doc_ref.get()
    if not doc.exists:
        # Document doesn't exist
        user_doc_ref.set({"keywords": keywords, "projects": projects})

        response = ""
        if projects:
            if len(projects) == 1:
                response += f"Successfully subscribed to project: {projects[0]}\n"
            else:
                response += (
                    f"Successfully subscribed to projects: {', '.join(projects)}\n"
                )
        if keywords:
            if len(keywords) == 1:
                response += f"Successfully subscribed to keyword: {keywords[0]}\n"
            else:
                response += (
                    f"Successfully subscribed to keywords: {', '.join(keywords)}"
                )

        update.message.reply_text(response)
    else:
        # Document exists
        existing_projects = doc.get("projects")
        existing_keywords = doc.get("keywords")

        if existing_projects is None:
            existing_projects = []
        if existing_keywords is None:
            existing_keywords = []

        new_projects = list(set(projects) - set(existing_projects))
        new_keywords = list(set(keywords) - set(existing_keywords))
        already_subscribed_projects = list(set(projects) & set(existing_projects))
        already_subscribed_keywords = list(set(keywords) & set(existing_keywords))

        response = ""

        if new_projects:
            user_doc_ref.update({"projects": firestore.ArrayUnion(new_projects)})
            if len(new_projects) == 1:
                response += f"Successfully subscribed to project: {new_projects[0]}\n"
            else:
                response += (
                    f"Successfully subscribed to projects: {', '.join(new_projects)}\n"
                )

        if new_keywords:
            user_doc_ref.update({"keywords": firestore.ArrayUnion(new_keywords)})
            if len(new_keywords) == 1:
                response += f"Successfully subscribed to keyword: {new_keywords[0]}\n"
            else:
                response += (
                    f"Successfully subscribed to keywords: {', '.join(new_keywords)}\n"
                )

        if already_subscribed_projects:
            if len(already_subscribed_projects) == 1:
                response += f"You are already subscribed to project: {already_subscribed_projects[0]}\n"
            else:
                response += f"You are already subscribed to projects: {', '.join(already_subscribed_projects)}\n"

        if already_subscribed_keywords:
            if len(already_subscribed_keywords) == 1:
                response += f"You are already subscribed to keyword: {already_subscribed_keywords[0]}\n"
            else:
                response += f"You are already subscribed to keywords: {', '.join(already_subscribed_keywords)}\n"

        update.message.reply_text(response)


def unsubscribe(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args
    projects = []
    keywords = []

    if len(args) < 2:
        update.message.reply_text("Please provide a project or keyword.")
        return

    if args[0] == "keyword":
        keywords.extend(args[1:])
    elif args[0] == "project":
        projects.extend(args[1:])
    else:
        update.message.reply_text("Please provide a project or keyword.")
        return

    if not projects and not keywords:
        update.message.reply_text("Please provide a project or keyword.")
        return

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Check document existence
    doc = user_doc_ref.get()
    if not doc.exists:
        update.message.reply_text("You are not subscribed to any projects or keywords.")
        return

    existing_projects = doc.get("projects")
    existing_keywords = doc.get("keywords")

    if existing_projects is None:
        existing_projects = []
    if existing_keywords is None:
        existing_keywords = []

    response = ""

    for project in projects:
        if project in existing_projects:
            user_doc_ref.update({"projects": firestore.ArrayRemove([project])})
            response += f"Successfully unsubscribed from project: {project}\n"
        else:
            response += f"You are not subscribed to project: {project}\n"

    for keyword in keywords:
        if keyword in existing_keywords:
            user_doc_ref.update({"keywords": firestore.ArrayRemove([keyword])})
            response += f"Successfully unsubscribed from keyword: {keyword}\n"
        else:
            response += f"You are not subscribed to keyword: {keyword}\n"

    update.message.reply_text(response)


def list_subscriptions(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Retrieve user subscriptions from Firestore
    doc = user_doc_ref.get()
    if not doc.exists:
        update.message.reply_text("You have no subscriptions.")
        return

    data = doc.to_dict()
    projects = data.get("projects", [])
    keywords = data.get("keywords", [])

    response = ""
    if projects:
        response += f"Your current project subscriptions: {', '.join(projects)}\n"
    if keywords:
        response += f"Your current keyword subscriptions: {', '.join(keywords)}\n"
    if not projects and not keywords:
        response = "You have no subscriptions."

    update.message.reply_text(response)


def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot and get some tips\n"
        "/subscribe - Subscribe to projects and keywords\n"
        "    To subscribe to projects: /subscribe project project1 project2\n"
        "    To subscribe to keywords: /subscribe keyword keyword1 keyword2\n"
        "/unsubscribe - Unsubscribe from projects and keywords\n"
        "    To unsubscribe from projects: /unsubscribe project project1 project2\n"
        "    To unsubscribe from keywords: /unsubscribe keyword keyword1 keyword2\n"
        "/list_subscriptions - List your current subscriptions\n"
        "/help - Show this help message"
    )

    update.message.reply_text(help_text)

def process_pubsub_message(pubsub_message: dict):
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        message = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()

        # Assuming message is a JSON string
        return json.loads(message)
    else:
        return None


def send_telegram_message(message_json: dict):
    # Initialize Firestore
    db = firestore.Client()
    
    # Send a message to the user with the new event for each matched user
    for user_id, sent_status in message_json["matched_users"].items():
        # Only send the message if it hasn't been sent to this user yet
        if not sent_status:
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=f"New matched event: {message_json['event_data']}",
                )  # Assuming you want to send the event_data to the user

                # Assuming you want to update the sent_status in Firestore to True
                db.collection("matched_events").document(message_json['id']).update({f"matched_users.{user_id}": True})

            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")

bot = Bot(token=os.environ["TOKEN"])
dispatcher = Dispatcher(bot=bot, update_queue=None)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("subscribe", subscribe))
dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))
dispatcher.add_handler(CommandHandler("list_subscriptions", list_subscriptions))
dispatcher.add_handler(CommandHandler("help", help_command))


@app.post("/")
def index() -> Response:
    dispatcher.process_update(Update.de_json(request.get_json(force=True), bot))

    return "", http.HTTPStatus.NO_CONTENT


@app.post("/pubsub")
def pubsub_endpoint():
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return "Bad Request: " + msg, 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return "Bad Request: " + msg, 400

    pubsub_message = envelope["message"]
    message_json = process_pubsub_message(pubsub_message)

    if message_json:
        send_telegram_message(message_json)

    return '', 204