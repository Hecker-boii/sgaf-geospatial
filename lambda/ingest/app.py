import json
import os
import re
from typing import List, Dict, Any
from datetime import datetime

import boto3

MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE_BYTES", "1048576"))
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "3"))
INPUT_BUCKET = os.environ["INPUT_BUCKET"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "")

sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE) if DYNAMODB_TABLE else None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Expect S3 event; validate size and start state machine with tiny work plan
    if "Records" not in event:
        raise Exception("Expected S3 event Records")

    rec = event["Records"][0]
    key = rec["s3"]["object"]["key"]
    size = int(rec["s3"]["object"].get("size", "0"))

    if size > MAX_FILE_SIZE:
        raise Exception(f"File too large: {size} > {MAX_FILE_SIZE}")

    dataset_id = _derive_dataset_id(key)
    # Include objectKey so process workers can read the GeoJSON from S3
    # Include numTiles to coordinate sharding logic
    num_tiles = min(MAX_ITEMS, 3)
    work_items = _derive_work_items(dataset_id, key, num_tiles)

    input_payload = {
        "datasetId": dataset_id,
        "objectKey": key,
        "workItems": work_items,
        "numTiles": num_tiles,
    }

    response = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(input_payload),
    )

    # Update DynamoDB with job status
    if table:
        try:
            # Determine file type
            file_type = "geojson"
            if key.lower().endswith((".tif", ".tiff", ".geotiff")):
                file_type = "geotiff"
            
            table.put_item(
                Item={
                    "datasetId": dataset_id,
                    "status": "PROCESSING",
                    "fileName": key.split("/")[-1],
                    "fileType": file_type,
                    "executionArn": response.get("executionArn"),
                    "createdAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }
            )
        except Exception:
            pass  # Non-blocking

    return {"executionArn": response.get("executionArn"), "datasetId": dataset_id}


def _derive_dataset_id(key: str) -> str:
    m = re.search(r"ingest/([^/]+)/", key)
    return m.group(1) if m else "unknown"


def _derive_work_items(dataset_id: str, object_key: str, num_tiles: int) -> List[Dict[str, Any]]:
    # Create ≤3 tiny work items that all reference the same source object
    return [
        {
            "datasetId": dataset_id,
            "tile": i,
            "objectKey": object_key,
            "numTiles": num_tiles,
        }
        for i in range(num_tiles)
    ]

