# telegram-governance-bot


## Cloud Run Deploy Steps
1. Set Region 
   - gcloud config set run/region us-central1
2. Set Variables
    - export PROJECT_ID=your-google-s-project-id
    - export TOKEN=your-telegram-bot-token
3. Deploy to Cloud Run
    - gcloud beta run deploy bot --source . --set-env-vars TOKEN=${TOKEN} --platform managed --allow-unauthenticated --project ${PROJECT_ID} --set-env-vars FLASK_APP=main.py
4. Set Webhook (Once)
    - curl "https://api.telegram.org/bot${TOKEN}/setWebhook?url=$(gcloud run services describe bot --format 'value(status.url)' --project ${PROJECT_ID})"

Ref: https://nullonerror.org/2021/01/08/hosting-telegram-bots-on-google-cloud-run/
