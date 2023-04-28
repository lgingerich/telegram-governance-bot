from google.cloud import firestore
from telegram_bot import send_notification

db = firestore.Client()

def process_event(event_id, event_data):
    event_keywords = set(event_data["event"].split("/"))

    for doc in db.collection("subscriptions").stream():
        user_id = doc.id
        user_subscriptions = doc.to_dict()["keywords"]

        if any(keyword in event_keywords for keyword in user_subscriptions):
            message = (
                f"An event matching your subscription has occurred:\n"
                f"Event ID: {event_id}\n"
                f"Event Type: {event_data['event']}\n"
                f"Space: {event_data['space']}\n"
                f"Proposal ID: {event_data['id']}\n"
                f"Expire: {event_data['expire']}"
            )
            send_notification(user_id, message)

def events_listener():
    events_query = db.collection("events").order_by("timestamp", direction=firestore.Query.DESCENDING)

    def on_snapshot(doc_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == "ADDED":
                event_id = change.document.id
                event_data = change.document.to_dict()
                process_event(event_id, event_data)

    events_query.on_snapshot(on_snapshot)

if __name__ == '__main__':
    events_listener()
