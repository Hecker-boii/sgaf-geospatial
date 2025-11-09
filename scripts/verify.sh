#!/usr/bin/env bash
# Verify input and output correctness for a given dataset
set -euo pipefail

STACK=SgafStack

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <dataset-id>"
    echo "Example: $0 demo-1234567890"
    echo ""
    echo "To list available datasets, run:"
    echo "  python3 scripts/view_output.py"
    exit 1
fi

DATASET_ID="$1"

echo "=== Verification for dataset: ${DATASET_ID} ==="
echo ""

# Get bucket names
OUTPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='OutputBucketName'].OutputValue" \
  --output text 2>/dev/null)

INPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='InputBucketName'].OutputValue" \
  --output text 2>/dev/null)

if [ -z "$OUTPUT_BUCKET" ] || [ -z "$INPUT_BUCKET" ]; then
    echo "Error: Could not get bucket names from stack '$STACK'"
    exit 1
fi

# 1. Check input file
echo "1. Checking input file..."
INPUT_FILES=$(aws s3 ls "s3://${INPUT_BUCKET}/ingest/${DATASET_ID}/" --recursive 2>/dev/null || true)
if [ -z "$INPUT_FILES" ]; then
    echo "   ⚠ No input files found for dataset ${DATASET_ID}"
else
    echo "   ✓ Input files found:"
    echo "$INPUT_FILES" | while read -r line; do
        echo "     - $line"
    done
fi
echo ""

# 2. Check output manifest
echo "2. Checking output manifest..."
MANIFEST_KEY="${DATASET_ID}/manifest.json"
if aws s3 ls "s3://${OUTPUT_BUCKET}/${MANIFEST_KEY}" >/dev/null 2>&1; then
    echo "   ✓ Manifest exists"
    
    # Download and verify
    TEMP_FILE=$(mktemp)
    aws s3 cp "s3://${OUTPUT_BUCKET}/${MANIFEST_KEY}" "$TEMP_FILE" >/dev/null 2>&1
    
    # Use Python for verification
    python3 <<EOF
import json
import sys

try:
    with open('$TEMP_FILE') as f:
        data = json.load(f)
    
    errors = []
    warnings = []
    
    # Check structure
    if 'tiles' not in data:
        errors.append("Missing 'tiles' field")
    if 'ok' not in data:
        errors.append("Missing 'ok' field")
    if 'total_area' not in data:
        errors.append("Missing 'total_area' field")
    
    if errors:
        print("   ✗ Structure errors:")
        for e in errors:
            print(f"     - {e}")
        sys.exit(1)
    
    # Check tiles
    tiles = data['tiles']
    if len(tiles) != 3:
        warnings.append(f"Expected 3 tiles, found {len(tiles)}")
    
    all_ok = all(t.get('status') == 'ok' for t in tiles)
    if not all_ok:
        errors.append("Not all tiles have status 'ok'")
    
    if errors:
        print("   ✗ Validation errors:")
        for e in errors:
            print(f"     - {e}")
        sys.exit(1)
    
    print(f"   ✓ Structure valid")
    print(f"   ✓ Tiles: {len(tiles)}")
    print(f"   ✓ All OK: {data['ok']}")
    print(f"   ✓ Total area: {data['total_area']}")
    
    if warnings:
        print("   ⚠ Warnings:")
        for w in warnings:
            print(f"     - {w}")
    
    # Show tile details
    print("\n   Tile details:")
    for tile in tiles:
        print(f"     Tile {tile.get('tile', '?')}: area={tile.get('area', '?')}, status={tile.get('status', '?')}")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
EOF
    
    rm -f "$TEMP_FILE"
else
    echo "   ✗ Manifest not found"
fi
echo ""

# 3. Check Step Functions execution (if available)
echo "3. Checking Step Functions execution..."
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -n "$STATE_MACHINE_ARN" ]; then
    # Try to find execution with this dataset ID
    EXECUTIONS=$(aws stepfunctions list-executions \
      --state-machine-arn "$STATE_MACHINE_ARN" \
      --max-results 10 \
      --query "executions[?contains(executionArn, '${DATASET_ID}') || contains(input, '${DATASET_ID}')]" \
      --output json 2>/dev/null || echo "[]")
    
    EXEC_COUNT=$(echo "$EXECUTIONS" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    
    if [ "$EXEC_COUNT" -gt 0 ]; then
        echo "   ✓ Found $EXEC_COUNT execution(s)"
        echo "$EXECUTIONS" | python3 -c "
import sys, json
for ex in json.load(sys.stdin):
    print(f\"     - {ex.get('name', 'unknown')}: {ex.get('status', 'unknown')}\")
"
    else
        echo "   ⚠ No executions found matching dataset ID"
    fi
else
    echo "   ⚠ Could not get state machine ARN"
fi
echo ""

echo "=== Verification complete ==="




