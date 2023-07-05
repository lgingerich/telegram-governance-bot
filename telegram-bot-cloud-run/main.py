import os
import http
import json
import base64
import time
import openai
from datetime import datetime
from google.cloud import firestore, secretmanager
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
        "/subscribe - Subscribe to projects, keywords, and token tickers\n"
        "    To subscribe to projects: /subscribe project project1 project2\n"
        "    To subscribe to keywords: /subscribe keyword keyword1 keyword2\n"
        "    To subscribe to token tickers: /subscribe ticker\n"
        "/unsubscribe - Unsubscribe from projects, keywords, and token tickers\n"
        "    To unsubscribe from projects: /unsubscribe project project1 project2\n"
        "    To unsubscribe from keywords: /unsubscribe keyword keyword1 keyword2\n"
        "    To unsubscribe from token tickers: /unsubscribe ticker\n"
        "/list_subscriptions - List your current subscriptions\n"
        "/help - Show this help message"
    )


def subscribe(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args
    projects = []
    keywords = []
    ticker_subscription = None

    if len(args) < 1:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    if args[0] == "keyword":
        keywords.extend(args[1:])
    elif args[0] == "project":
        projects.extend(args[1:])
    elif args[0] == "ticker":
        ticker_subscription = True
    else:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    if not projects and not keywords and ticker_subscription is None:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Check document existence
    doc = user_doc_ref.get()
    if not doc.exists:
        # Document doesn't exist
        user_doc_ref.set({"keywords": keywords, "projects": projects, "tickers": ticker_subscription})

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
                    f"Successfully subscribed to keywords: {', '.join(keywords)}\n"
                )
        if ticker_subscription is not None:
            response += f"Successfully subscribed to ticker notifications."

        update.message.reply_text(response)
    else:
        # Document exists
        existing_projects = doc.get("projects")
        existing_keywords = doc.get("keywords")
        already_subscribed_tickers = doc.get("tickers")

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

        if ticker_subscription is not None and not already_subscribed_tickers:
            user_doc_ref.update({"tickers": ticker_subscription})
            response += f"Successfully subscribed to ticker notifications.\n"
        elif ticker_subscription is not None and already_subscribed_tickers:
            response += "You are already subscribed to ticker notifications.\n"

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
    ticker_subscription = None

    if len(args) < 1:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    if args[0] == "keyword":
        keywords.extend(args[1:])
    elif args[0] == "project":
        projects.extend(args[1:])
    elif args[0] == "ticker":
        ticker_subscription = False
    else:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    if not projects and not keywords and ticker_subscription is None:
        update.message.reply_text("Please provide a project, keyword, or ticker.")
        return

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Check document existence
    doc = user_doc_ref.get()
    if not doc.exists:
        update.message.reply_text("You are not subscribed to any projects, keywords or tickers.")
        return

    existing_projects = doc.get("projects")
    existing_keywords = doc.get("keywords")
    already_subscribed_tickers = doc.get("tickers")

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

    if ticker_subscription is not None and already_subscribed_tickers:
        user_doc_ref.update({"tickers": ticker_subscription})
        response += "Successfully unsubscribed from ticker notifications.\n"
    elif ticker_subscription is not None and not already_subscribed_tickers:
        response += "You are not subscribed to ticker notifications.\n"

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
    tickers = data.get("tickers", None)

    response = ""
    if projects:
        response += f"Your current project subscriptions: {', '.join(projects)}\n"
    if keywords:
        response += f"Your current keyword subscriptions: {', '.join(keywords)}\n"
    if tickers:
        response += "You are currently subscribed to ticker notifications.\n"
    if not projects and not keywords and not tickers:
        response = "You have no subscriptions."

    update.message.reply_text(response)


def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot and get some tips\n"
        "/subscribe - Subscribe to projects, keywords, and token tickers\n"
        "    To subscribe to projects: /subscribe project project1 project2\n"
        "    To subscribe to keywords: /subscribe keyword keyword1 keyword2\n"
        "    To subscribe to token tickers: /subscribe ticker\n"
        "/unsubscribe - Unsubscribe from projects, keywords, and token tickers\n"
        "    To unsubscribe from projects: /unsubscribe project project1 project2\n"
        "    To unsubscribe from keywords: /unsubscribe keyword keyword1 keyword2\n"
        "    To unsubscribe from token tickers: /unsubscribe ticker\n"
        "/list_subscriptions - List your current subscriptions\n"
        "/help - Show this help message"
    )

    update.message.reply_text(help_text)


def get_secret_value(secret_name, version_id="latest"):
    # GCP project id
    project_id = 'telegram-governance-bot'
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def process_pubsub_message(pubsub_message: dict):
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        message = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()

        # Assuming message is a JSON string
        return json.loads(message)
    else:
        return None
    

def get_openai_summary(body):
    # Get summary of the proposal body field using OpenAI
    openai.api_key = get_secret_value("OPENAI_API_KEY")

    for i in range(3):
        try:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt="Provide a concise summary of the given content, using no more than 100 words, while accurately conveying its main points and ideas.\n\n" + body,
                temperature=0,
                max_tokens=1000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            summary = response.choices[0].text.strip()

            return summary

        except Exception as e:
            if i < 2:
                # If the OpenAI request fails, retry after a short delay
                time.sleep(2)
            else:
                # If the OpenAI request fails 3 times, return an error response
                return f"Error generating summary: {str(e)}"


def format_event(event_data):
    title = event_data.get('title', {}).get('stringValue')
    body = event_data.get('body', {}).get('stringValue')
    start = event_data.get('start', {}).get('integerValue')
    end = event_data.get('end', {}).get('integerValue')
    space_map = event_data.get('space', {}).get('mapValue', {}).get('fields', {})
    space_name = space_map.get('name', {}).get('stringValue')
    space_id = space_map.get('id', {}).get('stringValue')
    event_id = event_data.get('id', {}).get('stringValue')

    # Get choices and join them into a single string
    choices_list = event_data.get('choices', {}).get('arrayValue', {}).get('values', [])
    choices = ", ".join([choice.get('stringValue', '') for choice in choices_list])

    body_summary = get_openai_summary(body)

    formatted_event = {
        'title': title,
        'body': body_summary,
        'start': start,
        'end': end,
        'space_name': space_name,
        'choices': choices,
        'space_id': space_id,
        'event_id': event_id,
    }
    print("formatted_event = ", formatted_event)
    
    return formatted_event


def send_telegram_message(message_json: dict):
    # Initialize Firestore
    db = firestore.Client()

    # Send a message to the user with the new event for each matched user
    for user_id, sent_status in message_json["matched_users"].items():
        # Only send the message if it hasn't been sent to this user yet
        if not sent_status:
            try:
                event = format_event(message_json["event_data"])
                
                start_time = datetime.utcfromtimestamp(int(event['start'])).strftime("%Y-%m-%d %H:%M")
                end_time = datetime.utcfromtimestamp(int(event['end'])).strftime("%Y-%m-%d %H:%M")

                # Create a hyperlink for the title
                title_url = f"https://snapshot.org/#/{event['space_id']}/proposal/{event['event_id']}"
                title_with_link = f"[{event['title']}]({title_url})"
            
                message = (
                    f"Proposal Created:\n"
                    f"Title: {title_with_link}\n"
                    f"Space: {event['space_name']}\n"
                    f"Summary: {event['body']}\n"
                    f"Choices: {event['choices']}\n"
                    f"Start: {start_time} UTC\n"
                    f"End: {end_time} UTC"
                )

                bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')

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