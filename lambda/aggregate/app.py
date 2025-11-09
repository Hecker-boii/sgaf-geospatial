import json
import os
from typing import Any, Dict, List, Optional
import boto3

OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "")
UPDATE_STATUS_FUNCTION = os.environ.get("UPDATE_STATUS_FUNCTION", "")

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
cloudwatch = boto3.client("cloudwatch")


def handler(event: Any, context: Any) -> Dict[str, Any]:
    # Expect list of results from Map state
    results: List[Dict[str, Any]]
    if isinstance(event, list):
        results = event
    elif isinstance(event, dict) and "Payload" in event:
        results = event["Payload"] if isinstance(event["Payload"], list) else [event["Payload"]]
    else:
        results = [event]

    # Combine partial stats from shards
    total_point_count = 0
    total_point_sum_x = 0.0
    total_point_sum_y = 0.0
    total_polygon_count = 0
    total_polygon_area = 0.0
    total_other_count = 0
    merged_bbox: Optional[List[float]] = None

    per_tile = []
    for r in results:
        status = r.get("status")
        tile = r.get("tile")
        per = {
            "tile": tile,
            "status": status,
            "pointCount": r.get("pointCount", 0),
            "polygonCount": r.get("polygonCount", 0),
            "polygonAreaSum": r.get("polygonAreaSum", 0.0),
            "otherCount": r.get("otherCount", 0),
        }
        per_tile.append(per)

        total_point_count += int(r.get("pointCount", 0))
        ps = r.get("pointSum") or [0.0, 0.0]
        total_point_sum_x += float(ps[0])
        total_point_sum_y += float(ps[1])
        total_polygon_count += int(r.get("polygonCount", 0))
        total_polygon_area += float(r.get("polygonAreaSum", 0.0))
        total_other_count += int(r.get("otherCount", 0))

        bbox = r.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            if merged_bbox is None:
                merged_bbox = list(bbox)
            else:
                merged_bbox[0] = min(merged_bbox[0], bbox[0])
                merged_bbox[1] = min(merged_bbox[1], bbox[1])
                merged_bbox[2] = max(merged_bbox[2], bbox[2])
                merged_bbox[3] = max(merged_bbox[3], bbox[3])

    all_ok = all((t.get("status") == "ok") for t in per_tile)
    centroid = None
    if total_point_count > 0:
        centroid = [total_point_sum_x / total_point_count, total_point_sum_y / total_point_count]

    dataset_id = _first_dataset_id(results)
    summary = {
        "datasetId": dataset_id,
        "ok": all_ok,
        "tiles": per_tile,
        "bbox": merged_bbox,
        "pointCount": total_point_count,
        "pointCentroid": centroid,
        "polygonCount": total_polygon_count,
        "polygonArea": total_polygon_area,
        "otherCount": total_other_count,
    }

    # Write manifest to S3 and update DynamoDB
    try:
        dataset_id = dataset_id or _first_dataset_id(results)
        if OUTPUT_BUCKET and dataset_id:
            key = f"{dataset_id}/manifest.json"
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=key,
                Body=json.dumps(summary).encode("utf-8"),
                ContentType="application/json"
            )
            
            # Emit CloudWatch metric
            cloudwatch.put_metric_data(
                Namespace="SGAF/Aggregation",
                MetricData=[
                    {
                        "MetricName": "JobsCompleted",
                        "Value": 1,
                        "Unit": "Count",
                    }
                ],
            )
            
            # Update DynamoDB immediately (synchronous) for faster frontend updates
            if UPDATE_STATUS_FUNCTION:
                try:
                    lambda_client.invoke(
                        FunctionName=UPDATE_STATUS_FUNCTION,
                        InvocationType="RequestResponse",  # Synchronous for faster updates
                        Payload=json.dumps({
                            "datasetId": dataset_id,
                            "status": "COMPLETED" if all_ok else "FAILED",
                            "result": {"summary": summary},  # Wrap in summary for consistency
                        }),
                    )
                except Exception as e:
                    print(f"Error updating status: {e}")
                    # Fallback to async if sync fails
                    try:
                        lambda_client.invoke(
                            FunctionName=UPDATE_STATUS_FUNCTION,
                            InvocationType="Event",
                            Payload=json.dumps({
                                "datasetId": dataset_id,
                                "status": "COMPLETED" if all_ok else "FAILED",
                                "result": {"summary": summary},
                            }),
                        )
                    except:
                        pass
    except Exception:
        pass

    return {"summary": summary}


def _first_dataset_id(results: List[Dict[str, Any]]) -> str:
    for r in results:
        val = r.get("datasetId")
        if isinstance(val, str) and val:
            return val
    return ""

