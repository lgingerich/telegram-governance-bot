import json
import time
import requests
import openai
from google.cloud import firestore, secretmanager
from flask import jsonify

db = firestore.Client()

def get_secret_value(secret_name):
    # Create the Secret Manager client
    client = secretmanager.SecretManagerServiceClient()

    project_id = 'telegram-governance-bot'

    # Build the resource name of the secret version
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

    # Access the secret version
    response = client.access_secret_version(request={"name": name})

    # Return the secret payload as a string
    return response.payload.data.decode("UTF-8")

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

        # Check if the webhook payload contains a 'secret' field and compare it to the provided secret token
        if 'secret' in data and data['secret'] == get_secret_value("SNAPSHOT_WEBHOOK_SECRET"):

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

            # Get summary of the proposal body field using OpenAI
            # openai.api_key = get_secret_value("OPENAI_API_KEY")

            # for i in range(3):
            #     try:
            #         body = merged_data["body"]
            #         response = openai.Completion.create(
            #             model="text-davinci-003",
            #             prompt="Provide a concise summary of the given content, using no more than 100 words, while accurately conveying its main points and ideas.\n\n" + body,
            #             temperature=0,
            #             max_tokens=1000,
            #             top_p=1,
            #             frequency_penalty=0,
            #             presence_penalty=0
            #         )
            #         summary = response.choices[0].text.strip()

            #         # Store the merged data and the summary in Firestore
            #         merged_data["summary"] = summary
            #         event_id = store_event(merged_data)
            #         return jsonify({"status": "OK"})

            #     except Exception as e:
            #         if i < 2:
            #             # If the OpenAI request fails, retry after a short delay
            #             time.sleep(2)
            #         else:
            #             # If the OpenAI request fails 3 times, return an error response
            #             return jsonify({"status": "error", "message": f"Error generating summary: {str(e)}"})

        return jsonify({"status": "OK"})
    else:
        return jsonify({"status": "error", "message": "Invalid secret token"})