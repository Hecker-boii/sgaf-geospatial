#!/usr/bin/env bash
# Update frontend API URL with deployed API Gateway URL
set -euo pipefail

STACK=SgafStack
FRONTEND_DIR="../frontend"

# Get API Gateway URL from stack outputs
API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo "Error: Could not get API Gateway URL from stack '$STACK'"
    echo "Make sure the stack is deployed and API Gateway is created."
    exit 1
fi

# Remove trailing slash if present
API_URL=${API_URL%/}

echo "Updating frontend API URL to: $API_URL"

# Update app.js
if [ -f "${FRONTEND_DIR}/app.js" ]; then
    # Use sed to replace the API_URL constant
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|const API_URL = '.*';|const API_URL = '${API_URL}';|g" "${FRONTEND_DIR}/app.js"
    else
        # Linux
        sed -i "s|const API_URL = '.*';|const API_URL = '${API_URL}';|g" "${FRONTEND_DIR}/app.js"
    fi
    echo "✓ Updated ${FRONTEND_DIR}/app.js"
else
    echo "Warning: ${FRONTEND_DIR}/app.js not found"
fi

echo "Frontend API URL updated successfully!"
echo "You can now serve the frontend from the ${FRONTEND_DIR} directory"

