#!/bin/bash

gcloud functions deploy monitor_snapshot_events \
  --runtime python310 \
  --region us-east1 \
  --trigger-event providers/cloud.firestore/eventTypes/document.create \
  --trigger-resource 'projects/telegram-governance-bot/databases/(default)/documents/snapshot_events/{eventId}' \
  --source ./process-events-cloud-function