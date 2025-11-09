import json
from typing import Dict, Any
from datetime import datetime


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Format detailed, formal SNS notification message
    """
    # Handle different event structures
    summary = event.get("summary", {})
    if not summary and "result" in event:
        result = event.get("result", {})
        summary = result.get("summary", {})
    
    dataset_id = summary.get("datasetId", event.get("datasetId", "unknown"))
    status = event.get("status", "COMPLETED")
    
    # Check if this is a failure case
    if "error" in event or status == "FAILED":
        return format_failure_message(event)
    else:
        return format_success_message(summary, event)


def format_success_message(summary: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    """Format formal success notification"""
    # Handle case where summary might be nested
    if isinstance(summary, dict) and "summary" in summary:
        summary = summary["summary"]
    dataset_id = summary.get("datasetId", event.get("datasetId", "unknown"))
    point_count = summary.get("pointCount", 0)
    polygon_count = summary.get("polygonCount", 0)
    polygon_area = summary.get("polygonArea", 0.0)
    bbox = summary.get("bbox")
    centroid = summary.get("pointCentroid")
    tiles = summary.get("tiles", [])
    
    # Calculate processing time if available
    processing_time = "N/A"
    if "processingStartTime" in event:
        try:
            start = datetime.fromisoformat(event["processingStartTime"].replace("Z", "+00:00"))
            end = datetime.utcnow()
            duration = (end - start).total_seconds()
            processing_time = f"{duration:.2f} seconds"
        except:
            pass
    
    message = f"""
═══════════════════════════════════════════════════════════════
    SERVERLESS GEOSPATIAL ANALYSIS FRAMEWORK (SGAF)
    PROCESSING COMPLETION NOTIFICATION
═══════════════════════════════════════════════════════════════

Dear User,

This is to inform you that your geospatial data processing job has been 
successfully completed by the Serverless Geospatial Analysis Framework.

JOB DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dataset ID:        {dataset_id}
  Status:            COMPLETED
  Completion Time:   {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
  Processing Time:   {processing_time}

PROCESSING SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Point Features:    {point_count:,}
  Polygon Features:  {polygon_count:,}
  Total Area:        {polygon_area:.6f} square units
  Other Features:    {summary.get('otherCount', 0):,}
"""
    
    if bbox:
        message += f"""
  Bounding Box:      [{bbox[0]:.6f}, {bbox[1]:.6f}, {bbox[2]:.6f}, {bbox[3]:.6f}]
                      [minX, minY, maxX, maxY]
"""
    
    if centroid:
        message += f"""
  Point Centroid:    [{centroid[0]:.6f}, {centroid[1]:.6f}]
"""
    
    if tiles:
        message += f"""
TILE PROCESSING DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Tiles:       {len(tiles)}
"""
        for tile in tiles:
            message += f"""
  Tile {tile.get('tile', 'N/A')}:
    - Status:        {tile.get('status', 'unknown')}
    - Points:        {tile.get('pointCount', 0):,}
    - Polygons:      {tile.get('polygonCount', 0):,}
    - Area:          {tile.get('polygonAreaSum', 0.0):.6f}
"""
    
    message += f"""
AWS SERVICES UTILIZED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1.  Amazon S3                    - File storage and retrieval
  2.  Amazon DynamoDB              - Job metadata storage
  3.  Amazon CloudWatch             - Monitoring and metrics
  4.  Amazon SNS                    - Notification delivery
  5.  AWS Lambda                    - Serverless compute (5 functions)
  6.  AWS Step Functions            - Workflow orchestration
  7.  Amazon EventBridge           - Event-driven processing
  8.  Amazon API Gateway            - REST API endpoints
  9.  AWS Secrets Manager           - Secure configuration
  10. AWS Systems Manager           - Parameter storage
  11. Amazon SES                    - Email service
  12. AWS X-Ray                     - Distributed tracing
  13. Amazon SQS                     - Dead letter queue
  14. Amazon Cognito                 - User authentication

OUTPUT LOCATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Manifest File:     s3://[OUTPUT_BUCKET]/{dataset_id}/manifest.json
  DynamoDB Record:   JobsTable - Key: {dataset_id}
  
  You can access the complete results through:
  - API Gateway endpoint: /status/{dataset_id}
  - DynamoDB table: JobsTable
  - S3 output bucket: [OUTPUT_BUCKET]/{dataset_id}/

NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Access results via the web frontend
  2. Query the API Gateway endpoint for detailed data
  3. Download the manifest.json file from S3
  4. Review CloudWatch dashboard for metrics

═══════════════════════════════════════════════════════════════
This is an automated notification from the SGAF system.
For support, please check CloudWatch logs or contact your administrator.
═══════════════════════════════════════════════════════════════
"""
    
    return {
        "message": message.strip(),
        "subject": f"SGAF Processing Complete: {dataset_id}",
        "datasetId": dataset_id,
        "summary": summary
    }


def format_failure_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """Format formal failure notification"""
    error = event.get("error", {})
    dataset_id = event.get("datasetId", error.get("datasetId", "unknown"))
    error_type = error.get("Error", "Unknown Error")
    error_cause = error.get("Cause", "No additional details available")
    
    message = f"""
═══════════════════════════════════════════════════════════════
    SERVERLESS GEOSPATIAL ANALYSIS FRAMEWORK (SGAF)
    PROCESSING FAILURE NOTIFICATION
═══════════════════════════════════════════════════════════════

Dear User,

We regret to inform you that your geospatial data processing job has 
encountered an error and could not be completed successfully.

JOB DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dataset ID:        {dataset_id}
  Status:            FAILED
  Failure Time:      {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}

ERROR INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Error Type:        {error_type}
  
  Error Details:
  {error_cause}

TROUBLESHOOTING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Check CloudWatch Logs for detailed error information
  2. Verify input file format and size (max 1MB)
  3. Review Step Functions execution history
  4. Check SQS Dead Letter Queue for failed messages
  5. Contact system administrator if issue persists

SUPPORT RESOURCES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - CloudWatch Dashboard: SGAF-Monitoring
  - Step Functions Console: Check execution history
  - X-Ray Service Map: View distributed traces
  - SQS DLQ: Review failed message details

═══════════════════════════════════════════════════════════════
This is an automated notification from the SGAF system.
Please review the error details and retry if appropriate.
═══════════════════════════════════════════════════════════════
"""
    
    return {
        "message": message.strip(),
        "subject": f"SGAF Processing Failed: {dataset_id}",
        "datasetId": dataset_id,
        "error": error
    }

