# Serverless Geospatial Analysis Framework (SGAF)

A fully serverless, free-tier-compliant geospatial data processing system using **14+ AWS Services** with a modern web frontend hosted on AWS Amplify.

## 🎯 Features

- **Upload GeoJSON or GeoTIFF files** via web interface
- **Real-time job status** tracking
- **Visual results display** with user-friendly formatting
- **Job history** listing
- **14+ AWS Services** integrated in Step Functions workflow
- **100% Free Tier Compliant**
- **AWS Amplify Frontend** hosting
- **User Authentication** via AWS Cognito
- **Email Notifications** via SNS and SES
- **Distributed Tracing** via X-Ray
- **Dead Letter Queue** for error handling

## 🏗️ Architecture

The system uses **14+ AWS Services**:

1. **Amazon S3** - File storage (input/output)
2. **Amazon DynamoDB** - Job metadata storage
3. **Amazon CloudWatch** - Monitoring, metrics, and dashboards
4. **Amazon SNS** - Email notifications
5. **AWS Lambda** - Serverless compute (5 functions)
6. **AWS Step Functions** - Workflow orchestration
7. **Amazon EventBridge** - Event-driven processing
8. **Amazon API Gateway** - REST API for frontend
9. **AWS Secrets Manager** - Secure configuration storage
10. **AWS Systems Manager Parameter Store** - Configuration management
11. **Amazon SES** - Email service for better delivery
12. **AWS X-Ray** - Distributed tracing
13. **Amazon SQS** - Dead Letter Queue for failed messages
14. **Amazon Cognito** - User authentication for frontend
15. **AWS Amplify** - Frontend hosting and CI/CD

## 📋 Prerequisites

### Required Software

- **AWS Account** (Free Tier eligible)
- **AWS CLI** configured with credentials
- **Node.js 18+** (for CDK and Amplify)
- **Python 3.12+**
- **AWS CDK CLI** (`npm install -g aws-cdk`)
- **Git** (for version control)

### AWS CLI Configuration

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region (e.g., us-east-1)
# Enter default output format (json)
```

### Install Dependencies

```bash
# Install Python dependencies
pip install --user -r requirements.txt

# Install CDK globally (if not already installed)
npm install -g aws-cdk
```

## 🚀 Complete Setup and Deployment Guide

### Step 1: Clone and Navigate to Project

```bash
cd "Serverless Geospatial Analysis Framework"
```

### Step 2: Bootstrap CDK (First Time Only)

```bash
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1

cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION
```

### Step 3: Deploy Infrastructure

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy the stack
./scripts/deploy.sh
```

**This will deploy:**
- All 14+ AWS services
- Step Functions state machine
- API Gateway REST API
- CloudWatch dashboard
- SNS topics with email subscriptions
- Cognito user pool
- Secrets Manager
- Systems Manager Parameter Store
- SQS Dead Letter Queue
- X-Ray tracing enabled

**Deployment takes approximately 5-10 minutes.**

### Step 4: Confirm SNS Email Subscription

**CRITICAL STEP:** After deployment, AWS SNS will send a confirmation email to the configured address.

1. Check your email inbox (including spam folder) for: `harshavardan.n2023@vitstudent.ac.in`
2. Look for emails from AWS SNS with subject "AWS Notification - Subscription Confirmation"
3. Click the confirmation link in the email
4. You should see a confirmation page

**Without confirming the subscription, you will NOT receive email notifications!**

### Step 5: Get Deployment Outputs

After deployment completes, note the outputs:

```bash
aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs" --output table
```

**Important outputs to save:**
- `ApiGatewayUrl` - Your API endpoint
- `UserPoolId` - Cognito User Pool ID
- `UserPoolClientId` - Cognito Client ID
- `CognitoDomainUrl` - Cognito domain URL

### Step 6: Update Frontend Configuration

Update the frontend API URL:

```bash
# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

# Update frontend/app.js
sed -i "s|const API_URL = 'YOUR_API_GATEWAY_URL';|const API_URL = '${API_URL}';|g" frontend/app.js
```

Or manually edit `frontend/app.js` and replace:
```javascript
const API_URL = 'YOUR_API_GATEWAY_URL';
```
with your actual API Gateway URL.

### Step 7: Deploy Frontend to AWS Amplify

#### Option A: Using AWS Amplify Console (Recommended)

1. **Go to AWS Amplify Console:**
   - Open AWS Console → AWS Amplify
   - Click "New app" → "Host web app"

2. **Connect Repository:**
   - Choose "Deploy without Git provider" (or connect GitHub/GitLab if preferred)
   - Upload the project or connect your repository

3. **Configure Build Settings:**
   - App name: `sgaf-frontend`
   - Environment: `production`
   - Build settings: Use the provided `amplify.yml`

4. **Configure Environment Variables:**
   Add these environment variables in Amplify Console:
   ```
   API_URL=<your-api-gateway-url>
   USER_POOL_ID=<your-user-pool-id>
   USER_POOL_CLIENT_ID=<your-client-id>
   ```

5. **Deploy:**
   - Click "Save and deploy"
   - Wait for deployment to complete (5-10 minutes)

#### Option B: Using Amplify CLI

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Initialize Amplify
amplify init

# Add hosting
amplify add hosting

# Publish
amplify publish
```

#### Option C: Local Development Server

For local testing:

```bash
cd frontend
python3 -m http.server 8000
# Or
npx http-server -p 8000
```

Then open `http://localhost:8000` in your browser.

### Step 8: Test the System

#### Test via Frontend

1. Open your Amplify-hosted frontend URL (or `http://localhost:8000`)
2. Upload a GeoJSON file (use `sample/demo.geojson` as example)
3. Watch real-time status updates
4. View results when processing completes
5. Check your email for success notification

#### Test via CLI

```bash
# Upload test file
./scripts/test.sh
```

This uploads `sample/demo.geojson` to S3 and triggers processing.

#### Verify Email Notifications

1. Process a file through the system
2. Check your email inbox for:
   - Success notification when job completes
   - Failure notification if job fails
3. If emails are not received:
   - Check spam folder
   - Verify SNS subscription is confirmed
   - Check CloudWatch logs for errors

### Step 9: Monitor the System

#### CloudWatch Dashboard

Access the dashboard:
- AWS Console → CloudWatch → Dashboards → SGAF-Monitoring
- Or use the URL from stack outputs

#### X-Ray Tracing

View distributed traces:
- AWS Console → X-Ray → Service map
- See complete request flow through all services

#### Dead Letter Queue

Check for failed messages:
- AWS Console → SQS → `sgaf-dead-letter-queue`
- Messages here indicate Lambda failures

## 📁 Project Structure

```
.
├── lambda/
│   ├── api/              # API Gateway Lambda
│   ├── ingest/           # S3 trigger Lambda
│   ├── process/          # Processing Lambda
│   ├── aggregate/        # Aggregation Lambda
│   └── update_status/    # DynamoDB update Lambda
├── frontend/
│   ├── index.html        # Main UI
│   ├── styles.css        # Styling
│   └── app.js           # Frontend logic
├── sgaf/
│   └── stack.py         # CDK infrastructure (14+ services)
├── scripts/
│   ├── deploy.sh        # Deploy script
│   ├── test.sh          # Test script
│   ├── destroy.sh       # Cleanup script
│   └── verify.sh        # Verification script
├── sample/
│   └── demo.geojson     # Sample data
├── amplify.yml          # Amplify build configuration
├── requirements.txt     # Python dependencies
├── cdk.json            # CDK configuration
└── README.md           # This file
```

## 🔄 Workflow

### Step Functions State Machine

The workflow includes all services:

1. **MapProcess** (Map State)
   - Processes files in parallel tiles
   - Invokes Process Lambda
   - Emits CloudWatch metrics
   - X-Ray traces enabled

2. **AggregateResults** (Lambda Task)
   - Combines tile results
   - Calculates totals
   - Writes to S3
   - Updates DynamoDB

3. **UpdateDynamoDB** (Lambda Task)
   - Updates job status
   - Stores results

4. **NotifySuccess** (SNS Task)
   - Sends email notification via SNS
   - Uses SES for better delivery

**Error Handling:**
- Failed states → NotifyFailure (SNS)
- Failed Lambda invocations → Dead Letter Queue (SQS)
- EventBridge monitors failures
- CloudWatch alarms alert on errors
- X-Ray traces show error paths

## 📊 Monitoring

### CloudWatch Dashboard

Access the dashboard:
- AWS Console → CloudWatch → Dashboards → SGAF-Monitoring
- Or use the URL from stack outputs

### Metrics Tracked

- `FilesProcessed` - Number of files processed
- `JobsCompleted` - Number of jobs completed
- `ProcessingErrors` - Number of processing errors

### Alarms

- Error threshold alarm (triggers SNS notification)
- Step Functions execution failures (via EventBridge)

### X-Ray Service Map

- View complete request flow
- Identify bottlenecks
- Debug errors across services

## 🔒 Free Tier Compliance

All services configured for AWS Free Tier:

- **S3**: 5 GB storage, 20K GET requests/month
- **DynamoDB**: 25 GB storage, 25 read/write units
- **Lambda**: 1M requests/month, 400K GB-seconds
- **Step Functions**: 4K state transitions/month
- **API Gateway**: 1M API calls/month
- **CloudWatch**: 10 custom metrics, 5 GB logs
- **SNS**: 1M requests/month
- **EventBridge**: 1M custom events/month
- **Secrets Manager**: 10K API calls/month
- **Systems Manager**: 10K API calls/month
- **SES**: 62K emails/month (sandbox mode)
- **X-Ray**: 100K traces/month
- **SQS**: 1M requests/month
- **Cognito**: 50K MAU (Monthly Active Users)
- **Amplify**: 15 GB storage, 5 GB served/month

**Limits:**
- Max file size: 1 MB
- Max work items: 3 per job
- Log retention: 3 days
- Data lifecycle: 3 days

## 🧪 Testing

### Test via CLI

```bash
./scripts/test.sh
```

This uploads `sample/demo.geojson` to S3 and triggers processing.

### Test via Frontend

1. Open frontend in browser
2. Upload a file
3. Monitor status in real-time
4. View results when complete
5. Verify email notification received

### Verify Results

```bash
# Get output bucket
OUTPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='OutputBucketName'].OutputValue" \
  --output text)

# List manifests
aws s3 ls s3://${OUTPUT_BUCKET}/ --recursive | grep manifest.json

# View manifest
aws s3 cp s3://${OUTPUT_BUCKET}/<dataset-id>/manifest.json - | python3 -m json.tool
```

### Verify Email Delivery

```bash
# Check SNS subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn $(aws cloudformation describe-stacks --stack-name SgafStack \
    --query "Stacks[0].Outputs[?OutputKey=='SuccessTopicArn'].OutputValue" \
    --output text)
```

## 📝 API Endpoints

### POST /upload
Upload a file for processing.

**Request:**
```json
{
  "datasetId": "demo-1234567890",
  "fileName": "data.geojson",
  "fileType": "geojson",
  "fileContent": "base64-encoded-file-content"
}
```

### GET /status/{datasetId}
Get job status.

**Response:**
```json
{
  "datasetId": "demo-1234567890",
  "status": "COMPLETED",
  "fileName": "data.geojson",
  "result": { ... }
}
```

### GET /jobs
List all jobs.

**Response:**
```json
{
  "jobs": [
    {
      "datasetId": "demo-1234567890",
      "status": "COMPLETED",
      "fileName": "data.geojson",
      "createdAt": "2025-01-01T00:00:00"
    }
  ]
}
```

## 🗑️ Cleanup

### Destroy Stack

```bash
./scripts/destroy.sh
```

**Note:** If destroy fails due to non-empty buckets, empty them first:

```bash
# Get bucket names
INPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='InputBucketName'].OutputValue" \
  --output text)
OUTPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name SgafStack \
  --query "Stacks[0].Outputs[?OutputKey=='OutputBucketName'].OutputValue" \
  --output text)

# Empty buckets
aws s3 rm s3://${INPUT_BUCKET} --recursive
aws s3 rm s3://${OUTPUT_BUCKET} --recursive

# Then destroy
./scripts/destroy.sh
```

### Delete Amplify App

1. Go to AWS Amplify Console
2. Select your app
3. Click "Actions" → "Delete app"

## 🔧 Configuration

### Environment Variables

Lambda functions use these environment variables:
- `INPUT_BUCKET` - S3 input bucket name
- `OUTPUT_BUCKET` - S3 output bucket name
- `DYNAMODB_TABLE` - DynamoDB table name
- `STATE_MACHINE_ARN` - Step Functions ARN
- `MAX_FILE_SIZE_BYTES` - Max file size (1048576 = 1 MB)
- `MAX_ITEMS` - Max work items (3)
- `CONFIG_PARAMETER` - SSM Parameter Store path
- `USER_POOL_ID` - Cognito User Pool ID
- `USER_POOL_CLIENT_ID` - Cognito Client ID

### SNS Email

Update email in `sgaf/stack.py`:
```python
email_address = "your-email@example.com"
```

Then redeploy:
```bash
./scripts/deploy.sh
```

**Remember to confirm the new email subscription!**

### Secrets Manager

Access secrets:
```bash
aws secretsmanager get-secret-value \
  --secret-id $(aws cloudformation describe-stacks --stack-name SgafStack \
    --query "Stacks[0].Outputs[?OutputKey=='SecretsManagerArn'].OutputValue" \
    --output text)
```

### Systems Manager Parameter Store

Access configuration:
```bash
aws ssm get-parameter \
  --name $(aws cloudformation describe-stacks --stack-name SgafStack \
    --query "Stacks[0].Outputs[?OutputKey=='SSMParameterName'].OutputValue" \
    --output text)
```

## 🎨 Frontend Features

- **Drag & Drop Upload** - Easy file upload
- **Real-time Status** - Auto-refresh job status
- **Results Visualization** - User-friendly results display
- **Job History** - List all processed jobs
- **Responsive Design** - Works on mobile and desktop
- **Cognito Authentication** - Secure user access (optional)

## 🚧 Limitations

- Max file size: 1 MB (free tier limit)
- Max 3 work items per job
- GeoTIFF processing is simplified (no rasterio)
- Data auto-deleted after 3 days
- Logs retained for 3 days only
- SES in sandbox mode (must verify email addresses)

## 🔮 Future Enhancements

- [ ] Full GeoTIFF processing with rasterio
- [ ] Cognito authentication integration in frontend
- [ ] Larger file support
- [ ] More processing options
- [ ] Advanced visualizations
- [ ] Export results in multiple formats
- [ ] SES production mode (request production access)

## 📄 License

This project is for educational purposes and AWS Free Tier demonstration.

## 🤝 Contributing

Contributions welcome! Please ensure all changes remain free-tier compliant.

## 📞 Support

For issues or questions:

1. **Check CloudWatch Logs:**
   ```bash
   aws logs tail /aws/lambda/SgafStack-ProcessFn --follow
   ```

2. **Check Step Functions:**
   - AWS Console → Step Functions → SgafStateMachine
   - View execution history

3. **Check X-Ray Traces:**
   - AWS Console → X-Ray → Service map

4. **Verify SNS Subscription:**
   - AWS Console → SNS → Topics
   - Check subscription status

5. **Check Dead Letter Queue:**
   - AWS Console → SQS → `sgaf-dead-letter-queue`

## 🎓 Learning Resources

- [AWS Step Functions](https://docs.aws.amazon.com/step-functions/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [AWS CDK](https://docs.aws.amazon.com/cdk/)
- [AWS Amplify](https://docs.amplify.aws/)
- [AWS Cognito](https://docs.aws.amazon.com/cognito/)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/)
- [AWS Free Tier](https://aws.amazon.com/free/)

## ✅ Verification Checklist

After deployment, verify:

- [ ] Stack deployed successfully
- [ ] SNS email subscription confirmed
- [ ] API Gateway URL accessible
- [ ] Frontend deployed to Amplify
- [ ] Test file upload works
- [ ] Job processing completes
- [ ] Email notification received
- [ ] CloudWatch dashboard shows metrics
- [ ] X-Ray traces visible
- [ ] No messages in Dead Letter Queue

---

**Built with ❤️ using 14+ AWS Serverless Services**
