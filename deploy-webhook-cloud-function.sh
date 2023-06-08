#!/bin/bash

gcloud functions deploy snapshot_webhook \
  --gen2 \
  --region=us-central1 \
  --runtime=python310 \
  --source=./webhook-cloud-function \
  --entry-point=webhook \
  --trigger-http