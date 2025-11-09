#!/usr/bin/env bash
set -euo pipefail

if command -v cdk >/dev/null 2>&1; then
  CDK_CMD="cdk"
else
  CDK_CMD="npx --yes aws-cdk@2"
fi

$CDK_CMD destroy --force

