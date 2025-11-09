import json
import os
from typing import Dict, Any, Union
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
s3 = boto3.client("s3")


def convert_floats_to_strings(obj: Any) -> Any:
    """
    Recursively convert all float values to strings for DynamoDB compatibility.
    DynamoDB doesn't support float types, so we convert them to strings.
    """
    if isinstance(obj, float):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_floats_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_strings(item) for item in obj]
    else:
        return obj


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update DynamoDB with job status from Step Functions"""
    # Handle both direct input and nested structure from aggregate
    if "summary" in event:
        # Coming from aggregate task
        summary = event.get("summary", {})
        dataset_id = summary.get("datasetId", event.get("datasetId", "unknown"))
        result = {"summary": summary}
    else:
        # Direct input
        dataset_id = event.get("datasetId", "unknown")
        result = event.get("result")
    
    status = event.get("status", "COMPLETED")
    error = event.get("error")
    
    update_expr = "SET #status = :status, updatedAt = :updatedAt"
    expr_attrs = {
        ":status": status,
        ":updatedAt": datetime.utcnow().isoformat(),
    }
    expr_names = {"#status": "status"}
    
    if result:
        # Convert all floats to strings for DynamoDB compatibility
        result_converted = convert_floats_to_strings(result)
        
        update_expr += ", #result = :result"
        expr_attrs[":result"] = result_converted
        expr_names["#result"] = "result"
        
        # Also store manifest key for easy access
        manifest_key = f"{dataset_id}/manifest.json"
        update_expr += ", manifestKey = :manifestKey"
        expr_attrs[":manifestKey"] = manifest_key
    
    if error:
        # Convert floats in error messages too
        error_converted = convert_floats_to_strings(error) if isinstance(error, dict) else error
        update_expr += ", #error = :error"
        expr_attrs[":error"] = error_converted
        expr_names["#error"] = "error"
    
    try:
        table.update_item(
            Key={"datasetId": dataset_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_attrs,
        )
    except Exception as e:
        print(f"Error updating DynamoDB: {e}")
        print(f"Expression: {update_expr}")
        print(f"Attributes: {json.dumps(expr_attrs, default=str)}")
        raise
    
    # Return data that preserves the summary for Step Functions (keep floats for JSON)
    response = {"statusCode": 200, "datasetId": dataset_id, "status": status}
    if result:
        response["summary"] = result.get("summary", result)
    return response

