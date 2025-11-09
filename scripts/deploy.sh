#!/usr/bin/env bash
set -euo pipefail

export CDK_DEFAULT_ACCOUNT=${CDK_DEFAULT_ACCOUNT:-841722555450}
export CDK_DEFAULT_REGION=${CDK_DEFAULT_REGION:-us-east-1}

pip install --user --upgrade pip --break-system-packages || pip install --upgrade pip --break-system-packages
pip install --user -r requirements.txt --break-system-packages || pip install -r requirements.txt --break-system-packages

if command -v cdk >/dev/null 2>&1; then
  CDK_CMD="cdk"
else
  CDK_CMD="npx --yes aws-cdk@2"
fi

$CDK_CMD bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION || true
$CDK_CMD deploy --require-approval never

