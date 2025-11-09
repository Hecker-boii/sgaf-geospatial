#!/usr/bin/env bash
set -euo pipefail

echo "=== SNS Subscription Verification ==="
echo ""

# Get topic ARNs from stack outputs
SUCCESS_TOPIC=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='SuccessTopicArn'].OutputValue" \
  --output text 2>/dev/null || echo "")

FAILURE_TOPIC=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='FailureTopicArn'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -z "$SUCCESS_TOPIC" ] || [ -z "$FAILURE_TOPIC" ]; then
  echo "ERROR: Stack not deployed or topics not found."
  echo "Please deploy the stack first: ./scripts/deploy.sh"
  exit 1
fi

echo "Success Topic ARN: $SUCCESS_TOPIC"
echo "Failure Topic ARN: $FAILURE_TOPIC"
echo ""

echo "=== Checking Subscriptions ==="
echo ""

echo "Success Topic Subscriptions:"
aws sns list-subscriptions-by-topic --topic-arn "$SUCCESS_TOPIC" \
  --query "Subscriptions[*].[Endpoint,SubscriptionArn,Protocol]" \
  --output table

echo ""
echo "Failure Topic Subscriptions:"
aws sns list-subscriptions-by-topic --topic-arn "$FAILURE_TOPIC" \
  --query "Subscriptions[*].[Endpoint,SubscriptionArn,Protocol]" \
  --output table

echo ""
echo "=== Subscription Status ==="
echo ""

SUCCESS_SUBS=$(aws sns list-subscriptions-by-topic --topic-arn "$SUCCESS_TOPIC" \
  --query "Subscriptions[*].SubscriptionArn" --output text)

FAILURE_SUBS=$(aws sns list-subscriptions-by-topic --topic-arn "$FAILURE_TOPIC" \
  --query "Subscriptions[*].SubscriptionArn" --output text)

for sub in $SUCCESS_SUBS; do
  if [ "$sub" != "None" ] && [ -n "$sub" ]; then
    STATUS=$(aws sns get-subscription-attributes --subscription-arn "$sub" \
      --query "Attributes.ConfirmationWasAuthenticated" --output text 2>/dev/null || echo "Unknown")
    echo "Success Topic Subscription: $STATUS"
  fi
done

for sub in $FAILURE_SUBS; do
  if [ "$sub" != "None" ] && [ -n "$sub" ]; then
    STATUS=$(aws sns get-subscription-attributes --subscription-arn "$sub" \
      --query "Attributes.ConfirmationWasAuthenticated" --output text 2>/dev/null || echo "Unknown")
    echo "Failure Topic Subscription: $STATUS"
  fi
done

echo ""
echo "=== Instructions ==="
echo ""
echo "If subscriptions show 'PendingConfirmation':"
echo "1. Check your email inbox (including spam folder)"
echo "2. Look for emails from AWS SNS"
echo "3. Click the confirmation link in the email"
echo "4. Run this script again to verify"
echo ""
echo "To test email delivery, process a file and check for notifications."

