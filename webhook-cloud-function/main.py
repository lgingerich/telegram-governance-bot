import json
from google.cloud import firestore
from flask import jsonify

db = firestore.Client()

def store_event(event_data):
    event_ref = db.collection("events").document()
    event_data["timestamp"] = firestore.SERVER_TIMESTAMP
    event_ref.set(event_data)

    return event_ref.id

def webhook(request):
    if request.method == 'POST':
        data = json.loads(request.data)

        event_data = {
            'id': data['id'],
            'event': data['event'],
            'space': data['space'],
            'expire': data['expire']
        }

        event_id = store_event(event_data)

        return jsonify({"status": "OK"})