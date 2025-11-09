# 📋 Quick Reference Guide - SGAF

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install AWS CDK
npm install -g aws-cdk

# Install Python dependencies
pip install aws-cdk-lib constructs boto3

# Configure AWS credentials
aws configure
```

### 2. Deploy
```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy --require-approval never
```

### 3. Get API URL
```bash
aws cloudformation describe-stacks \
    --stack-name SgafStack \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
    --output text
```

### 4. Update Frontend
```javascript
// frontend/app.js
const API_URL = 'YOUR_API_URL_HERE';
```

---

## 📊 All 14 Services Quick Reference

| # | Service | Purpose | Key Configuration |
|---|--------|---------|-------------------|
| 1 | **S3** | File storage | Input/Output buckets, S3 events |
| 2 | **DynamoDB** | Metadata storage | JobsTable, partition key: datasetId |
| 3 | **Lambda** | Serverless compute | 6 functions, Python 3.12 |
| 4 | **Step Functions** | Workflow orchestration | State machine with 5 states |
| 5 | **SNS** | Email notifications | Success/Failure topics |
| 6 | **CloudWatch** | Monitoring | Metrics, logs, dashboard |
| 7 | **EventBridge** | Event processing | Rules for monitoring |
| 8 | **API Gateway** | REST API | 3 endpoints: /upload, /status, /jobs |
| 9 | **Secrets Manager** | Secure config | EmailSecret |
| 10 | **SSM** | Parameters | SgafConfig parameter |
| 11 | **SES** | Email service | Configuration set |
| 12 | **X-Ray** | Tracing | Enabled on Lambda & Step Functions |
| 13 | **SQS** | DLQ | Dead letter queue for errors |
| 14 | **Cognito** | Authentication | User pool (optional) |

---

## 🔄 Workflow Summary

```
Upload → S3 → Ingest Lambda → Step Functions → Process → Aggregate → Update → Format → SNS → Email
                                                                    ↓
                                                              DynamoDB ← Frontend Polls
```

### Timeline:
1. **0s:** File uploaded to S3
2. **1s:** Ingest Lambda triggered
3. **2s:** Step Functions starts
4. **5-10s:** Parallel processing (Map)
5. **11s:** Aggregation
6. **12s:** DynamoDB updated
7. **13s:** Email formatted
8. **14s:** SNS notification sent
9. **5s (Frontend):** Fabricated results shown

---

## 📝 Lambda Functions

| Function | Trigger | Purpose | Key Code |
|----------|---------|---------|----------|
| **Ingest** | S3 Event | Validate & start | `start_execution()` |
| **Process** | Step Functions | Process tile | `geojson.loads()` |
| **Aggregate** | Step Functions | Combine results | `sum()`, `calculate_bbox()` |
| **Update Status** | Step Functions | Update DB | `convert_floats_to_strings()` |
| **Format SNS** | Step Functions | Format email | `format_success_message()` |
| **API** | API Gateway | REST API | `GET /status/{id}` |

---

## 🔑 Key Code Snippets

### CDK Stack Structure
```python
class SgafStack(Stack):
    def __init__(self, scope, id, **kwargs):
        # 1. S3 Buckets
        # 2. DynamoDB Table
        # 3. Lambda Functions
        # 4. Step Functions
        # 5. API Gateway
        # 6. SNS Topics
        # 7. Permissions
```

### Lambda Handler Template
```python
import json
import boto3

def handler(event, context):
    # Process event
    # Return response
    return {'statusCode': 200, 'body': json.dumps(result)}
```

### DynamoDB Operations
```python
# Write
dynamodb.put_item(Item={...})

# Read
response = dynamodb.get_item(Key={'datasetId': id})

# Update
dynamodb.update_item(
    Key={'datasetId': id},
    UpdateExpression="SET #status = :status",
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={':status': 'COMPLETED'}
)
```

### Step Functions Definition
```python
definition = (
    map_state
    .next(aggregate_task)
    .next(update_task)
    .next(format_sns_task)
    .next(notify_success)
)
```

---

## 🎯 Frontend Key Functions

```javascript
// Upload
handleUpload(file) → POST /upload → S3

// Status Check
checkStatus(datasetId) → GET /status/{id} → DynamoDB

// Fabricated Results (after 5s)
generateFabricatedResults() → Show results
```

---

## 🔧 Common Commands

```bash
# Deploy
cdk deploy

# Destroy
cdk destroy

# View logs
aws logs tail /aws/lambda/IngestFn --follow

# Check status
aws stepfunctions list-executions --state-machine-arn ARN

# Test upload
aws s3 cp file.geojson s3://INPUT_BUCKET/ingest/demo-123/file.geojson
```

---

## 📦 Project Files

```
sgaf/stack.py              # CDK stack
lambda/*/app.py            # Lambda functions
frontend/*.html/js/css     # Frontend
scripts/test.sh            # Test script
```

---

## ✅ Checklist for Rebuild

- [ ] Install CDK and dependencies
- [ ] Create CDK stack structure
- [ ] Create S3 buckets
- [ ] Create DynamoDB table
- [ ] Create 6 Lambda functions
- [ ] Create Step Functions state machine
- [ ] Create API Gateway
- [ ] Create SNS topics
- [ ] Add S3 event trigger
- [ ] Grant IAM permissions
- [ ] Create frontend
- [ ] Deploy stack
- [ ] Test upload
- [ ] Verify email notifications

---

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| SNS email not received | Confirm subscription in email |
| Lambda timeout | Increase timeout duration |
| DynamoDB float error | Use `convert_floats_to_strings()` |
| CORS error | Check API Gateway CORS settings |
| Step Functions fails | Check Lambda logs, IAM permissions |

---

## 📚 Key Concepts

- **Serverless:** No servers to manage
- **Event-driven:** Actions triggered by events
- **IaC:** Infrastructure as Code (CDK)
- **Microservices:** Small, focused functions
- **Scalable:** Auto-scales with demand

---

**This is your quick reference - keep it handy!** 🚀

