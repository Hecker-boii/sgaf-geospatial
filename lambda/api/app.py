import json
import os
from typing import Dict, Any
import boto3
from datetime import datetime

INPUT_BUCKET = os.environ.get("INPUT_BUCKET", "")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "")

s3 = boto3.client("s3") if INPUT_BUCKET else None
sfn = boto3.client("stepfunctions") if STATE_MACHINE_ARN else None
dynamodb = boto3.resource("dynamodb") if DYNAMODB_TABLE else None
table = dynamodb.Table(DYNAMODB_TABLE) if dynamodb and DYNAMODB_TABLE else None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway Lambda handler for file upload and job status"""
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_parameters = event.get("pathParameters") or {}
    
    try:
        if http_method == "POST" and "/upload" in path:
            return handle_upload(event)
        elif http_method == "GET" and "/status" in path:
            dataset_id = path_parameters.get("datasetId") or path.split("/")[-1]
            if dataset_id:
                return handle_status(dataset_id)
            else:
                return error_response(400, "Missing datasetId")
        elif http_method == "GET" and "/jobs" in path:
            return handle_list_jobs()
        elif http_method == "OPTIONS":
            return cors_response({})
        else:
            return error_response(404, f"Not Found: {path}")
    except Exception as e:
        return error_response(500, str(e))


def handle_upload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle file upload via API Gateway"""
    body = json.loads(event.get("body", "{}"))
    dataset_id = body.get("datasetId")
    file_content = body.get("fileContent")  # Base64 encoded
    file_name = body.get("fileName", "upload.geojson")
    file_type = body.get("fileType", "geojson")
    
    if not dataset_id or not file_content:
        return error_response(400, "Missing datasetId or fileContent")
    
    # Decode base64
    import base64
    file_bytes = base64.b64decode(file_content)
    
    if not s3 or not INPUT_BUCKET:
        return error_response(500, "S3 not configured")
    
    # Upload to S3
    key = f"ingest/{dataset_id}/{file_name}"
    s3.put_object(
        Bucket=INPUT_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType="application/json" if file_type == "geojson" else "image/tiff"
    )
    
    # Create DynamoDB record
    if table:
        try:
            table.put_item(
                Item={
                    "datasetId": dataset_id,
                    "status": "PENDING",
                    "fileName": file_name,
                    "fileType": file_type,
                    "createdAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            print(f"Error writing to DynamoDB: {e}")
    
    # Note: S3 event will trigger ingest Lambda which starts Step Functions
    
    return cors_response({
        "datasetId": dataset_id,
        "status": "PENDING",
        "message": "File uploaded successfully"
    })


def handle_status(dataset_id: str) -> Dict[str, Any]:
    """Get job status from DynamoDB"""
    if not table:
        return error_response(500, "DynamoDB not configured")
    
    try:
        response = table.get_item(Key={"datasetId": dataset_id})
        
        if "Item" not in response:
            return error_response(404, "Job not found")
        
        item = response["Item"]
        
        # Extract result and ensure it's properly formatted
        result = item.get("result")
        if result and isinstance(result, dict):
            # Ensure result structure is clean for frontend
            # Handle nested summary if needed
            if "summary" in result and isinstance(result["summary"], dict):
                # Result already has summary, use as is
                pass
            elif "M" in result and "summary" in result["M"]:
                # DynamoDB format - convert
                import json
                result = json.loads(json.dumps(result, default=str))
        
        return cors_response({
            "datasetId": dataset_id,
            "status": item.get("status", "UNKNOWN"),
            "fileName": item.get("fileName"),
            "fileType": item.get("fileType"),
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
            "result": result,
            "error": item.get("error"),
        })
    except Exception as e:
        return error_response(500, f"Error querying DynamoDB: {str(e)}")


def handle_list_jobs() -> Dict[str, Any]:
    """List all jobs from DynamoDB"""
    if not table:
        return error_response(500, "DynamoDB not configured")
    
    try:
        response = table.scan()
        jobs = [
            {
                "datasetId": item.get("datasetId"),
                "status": item.get("status"),
                "fileName": item.get("fileName"),
                "createdAt": item.get("createdAt"),
            }
            for item in response.get("Items", [])
        ]
        
        return cors_response({"jobs": jobs})
    except Exception as e:
        return error_response(500, f"Error scanning DynamoDB: {str(e)}")


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps({"error": message}),
    }


def cors_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps(data),
    }

