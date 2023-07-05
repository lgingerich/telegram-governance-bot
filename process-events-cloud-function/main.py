from google.cloud import firestore
from google.cloud import pubsub_v1
import json
import re

# Initialize Firestore client
db = firestore.Client()

# Initialize Publisher client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("telegram-governance-bot", "matched-events-topic")

# Regex to match 3-5 uppercase letters. Used to match tickers
TOKEN_TICKER_REGEX = r'\b[A-Z]{3,5}\b'


# Function to publish a matched event
def publish_matched_event(matched_event):
    data = json.dumps(matched_event)
    data = data.encode("utf-8")

    future = publisher.publish(topic_path, data)
    print(f"Published message: {future.result()}")



def monitor_snapshot_events(data, context):
    # Get event data from the snapshot
    event_data = data["value"]["fields"]

    # Get the project ID and body and title text from the event data
    event_project_id = event_data["space"]["mapValue"]["fields"]["id"]["stringValue"]
    event_body_text = event_data["body"]["stringValue"].lower()  # Convert to lower case for case-insensitive matching
    event_title_text = event_data["title"]["stringValue"].lower()  # Convert to lower case for case-insensitive matching

    # Get all potential tickers in body and title text
    body_text_tickers = re.findall(TOKEN_TICKER_REGEX, event_body_text.upper())
    title_text_tickers = re.findall(TOKEN_TICKER_REGEX, event_title_text.upper())
    event_tickers = set(body_text_tickers + title_text_tickers)  # Combine and remove duplicates

    # Initialize a set to hold all matching user IDs
    matched_users = set()

    # Fetch all user subscriptions
    user_subscriptions_ref = db.collection("user_subscriptions")
    user_subscriptions_docs = user_subscriptions_ref.stream()

    # Loop through user subscriptions and check if project ID, any keyword, or any ticker matches
    for doc in user_subscriptions_docs:
        user_subscription = doc.to_dict()

        # Check if the event's project ID is in the user's subscription projects
        if "projects" in user_subscription and event_project_id in user_subscription["projects"]:
            matched_users.add(doc.id)

        # Check if any of the user's keywords is in the body or title text
        if "keywords" in user_subscription:
            for keyword in user_subscription["keywords"]:
                if keyword.lower() in event_body_text or keyword.lower() in event_title_text:
                    matched_users.add(doc.id)
                    break  # Stop checking other keywords once a match is found

        # Check if any of the event's tickers are in the user's subscription tickers
        if "tickers" in user_subscription:
            for ticker in user_subscription["tickers"]:
                if ticker in event_tickers:
                    matched_users.add(doc.id)
                    break  # Stop checking other tickers once a match is found

    # Check if there were any matches
    if matched_users:
        # Create a new document in the matched_events collection with the event data and the matched user IDs
        matched_event_data = {
            "event_data": event_data,
            "matched_users": {user_id: False for user_id in matched_users},
        }

        db.collection("matched_events").document().set(matched_event_data)

        # Publish the matched event to Firestore collection
        publish_matched_event(matched_event_data)