#!/usr/bin/env bash
set -euo pipefail

STACK=SgafStack
INPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='InputBucketName'].OutputValue" --output text)
DATASET_ID="demo-$(date +%s)"

echo "Uploading tiny demo geojson to s3://${INPUT_BUCKET}/ingest/${DATASET_ID}/demo.geojson"
aws s3 cp sample/demo.geojson "s3://${INPUT_BUCKET}/ingest/${DATASET_ID}/demo.geojson"

echo "Check Step Functions executions and SNS email for completion."

