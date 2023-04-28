import json
import time
from google.cloud import firestore
import requests
from flask import jsonify

db = firestore.Client()

def store_event(data):
    event_id = data["id"]
    doc_ref = db.collection("snapshot_events").document(event_id)
    doc_ref.set(data)
    return event_id

def fetch_proposal_data(proposal_id, max_retries=3, delay=2):
    url = 'https://hub.snapshot.org/graphql'
    query = '''
    query ($id: String!) {
      proposal(id: $id) {
        id
        title
        body
        choices
        start
        end
        snapshot
        state
        author
        created
        scores
        scores_by_strategy
        scores_total
        scores_updated
        plugins
        network
        strategies {
          name
          network
          params
        }
        space {
          id
          name
        }
      }
    }
    '''

    variables = {
        'id': proposal_id
    }

    for i in range(max_retries):
        try:
            response = requests.post(url, json={'query': query, 'variables': variables})
            data = response.json()
            return data['data']['proposal']
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(delay)
            else:
                raise e

def webhook(request):
    if request.method == 'POST':
        data = json.loads(request.data)

        event_data = {
            'id': data['id'],
            'event': data['event'],
            'space': data['space'],
            'expire': data['expire']
        }

        # Fetch the additional proposal data
        proposal_id = event_data['id'].split('/')[-1]
        
        try:
            proposal_data = fetch_proposal_data(proposal_id)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Error fetching proposal data: {str(e)}"})

        # Merge the event data and the proposal data
        merged_data = {**event_data, **proposal_data}

        # Store the merged data in Firestore
        event_id = store_event(merged_data)

        return jsonify({"status": "OK"})

