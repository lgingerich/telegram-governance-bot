import os
import http
from google.cloud import pubsub_v1, firestore
from flask import Flask, request
from werkzeug.wrappers import Response

from telegram import Bot, Update
from telegram.ext import Dispatcher, Filters, MessageHandler, CallbackContext, CommandHandler


app = Flask(__name__)

# Initialize the Pub/Sub client
publisher = pubsub_v1.PublisherClient()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to the Crypto Governance Event Notifications bot!\n\n"
        "Subscribe to be notified of governance proposal actions in real-time. "
        "Notifications can be set for specific projects, keywords, and proposal events (created, started, ended, deleted)."
        "Here's some tips to get started."
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
        # Document doesn't exist, create it with the provided keywords and projects
        user_doc_ref.set(
            {
                "keywords": keywords,
                "projects": projects
            }
        )
    else:
        # Document exists, update the keywords and projects
        user_doc_ref.update(
            {
                "keywords": firestore.ArrayUnion(keywords),
                "projects": firestore.ArrayUnion(projects)
            }
        )

    response = ""
    if projects:
        if len(projects) == 1:
            response += f"Successfully subscribed to project: {projects[0]}\n"
        else:
            response += f"Successfully subscribed to projects: {', '.join(projects)}\n"
    if keywords:
        if len(keywords) == 1:
            response += f"Successfully subscribed to keyword: {keywords[0]}\n"
        else:
            response += f"Successfully subscribed to keywords: {', '.join(keywords)}"

    update.message.reply_text(response)



def unsubscribe(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        update.message.reply_text("Please provide a project or keyword.")
        return

    projects = []
    keywords = []

    for arg in args:
        if arg.startswith("project"):
            projects.extend(arg.split()[1:])
        elif arg.startswith("keyword"):
            keywords.extend(arg.split()[1:])

    if not projects and not keywords:
        update.message.reply_text("Please provide a project or keyword.")
        return

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Remove projects
    if projects:
        for project in projects:
            project_doc_ref = user_doc_ref.collection("projects").document(project)
            project_doc_ref.delete()

    # Remove keywords
    if keywords:
        for keyword in keywords:
            keyword_doc_ref = user_doc_ref.collection("keywords").document(keyword)
            keyword_doc_ref.delete()

    response = ""
    if projects:
        if len(projects) == 1:
            response += f"Successfully unsubscribed from project: {projects[0]}\n"
        else:
            response += f"Successfully unsubscribed from projects: {', '.join(projects)}\n"
    if keywords:
        if len(keywords) == 1:
            response += f"Successfully unsubscribed from keyword: {keywords[0]}\n"
        else:
            response += f"Successfully unsubscribed from keywords: {', '.join(keywords)}"

    update.message.reply_text(response)



def list_subscriptions(update: Update, context):
    user_id = str(update.effective_user.id)

    # Initialize Firestore
    db = firestore.Client()

    # Firestore document reference for the user
    user_doc_ref = db.collection("user_subscriptions").document(user_id)

    # Retrieve projects and keywords from Firestore
    projects_snapshot = user_doc_ref.collection("projects").stream()
    keywords_snapshot = user_doc_ref.collection("keywords").stream()

    projects = [project.id for project in projects_snapshot]
    keywords = [keyword.id for keyword in keywords_snapshot]

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



bot = Bot(token=os.environ["TOKEN"])
dispatcher = Dispatcher(bot=bot, update_queue=None)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("subscribe", subscribe))
dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))
dispatcher.add_handler(CommandHandler("list_subscriptions", list_subscriptions))
dispatcher.add_handler(CommandHandler("help", help_command))

@app.post("/")
def index() -> Response:
    dispatcher.process_update(
        Update.de_json(request.get_json(force=True), bot))

    return "", http.HTTPStatus.NO_CONTENT

