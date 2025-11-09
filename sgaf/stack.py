import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
    aws_ses as ses,
    aws_sqs as sqs,
    aws_cognito as cognito,
)
from constructs import Construct


class SgafStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ============================================================================
        # SERVICE 1: S3 - Input/Output Buckets
        # ============================================================================
        input_bucket = s3.Bucket(self, "InputBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(3))],
            removal_policy=RemovalPolicy.DESTROY,  # For easy cleanup
        )

        output_bucket = s3.Bucket(self, "OutputBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(3))],
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ============================================================================
        # SERVICE 2: DynamoDB - Job Metadata Storage
        # ============================================================================
        jobs_table = dynamodb.Table(self, "JobsTable",
            partition_key=dynamodb.Attribute(
                name="datasetId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # Free tier: 25 GB storage
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",  # Optional TTL for auto-cleanup
        )

        # ============================================================================
        # SERVICE 3: CloudWatch - Metrics and Alarms
        # ============================================================================
        # CloudWatch Alarm for processing errors
        error_alarm = cloudwatch.Alarm(self, "ProcessingErrorAlarm",
            metric=cloudwatch.Metric(
                namespace="SGAF/Errors",
                metric_name="ProcessingErrors",
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=5,
            evaluation_periods=1,
            alarm_description="Alert when processing errors exceed threshold",
        )

        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(self, "SGAFDashboard",
            dashboard_name="SGAF-Monitoring"
        )

        # ============================================================================
        # SERVICE 4: SNS - Notifications
        # ============================================================================
        success_topic = sns.Topic(self, "SgafSuccess",
            display_name="SGAF Success Notifications",
            topic_name="sgaf-success"
        )
        failure_topic = sns.Topic(self, "SgafFailure",
            display_name="SGAF Failure Notifications",
            topic_name="sgaf-failure"
        )

        # Email subscription - user must confirm via email
        email_address = "harshavardan.n2023@vitstudent.ac.in"
        success_topic.add_subscription(
            subs.EmailSubscription(email_address)
        )
        failure_topic.add_subscription(
            subs.EmailSubscription(email_address)
        )

        # Add SNS action to CloudWatch alarm
        error_alarm.add_alarm_action(cw_actions.SnsAction(failure_topic))

        # ============================================================================
        # SERVICE 9: Secrets Manager - Store sensitive configuration
        # ============================================================================
        email_secret = secretsmanager.Secret(self, "EmailSecret",
            description="Email configuration for SGAF notifications",
            secret_object_value={
                "email": cdk.SecretValue.unsafe_plain_text(email_address),
                "region": cdk.SecretValue.unsafe_plain_text(self.region),
            },
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ============================================================================
        # SERVICE 10: Systems Manager Parameter Store - Configuration
        # ============================================================================
        config_parameter = ssm.StringParameter(self, "SgafConfig",
            parameter_name="/sgaf/config",
            string_value=json.dumps({
                "max_file_size": "1048576",
                "max_items": "3",
                "region": self.region,
                "email": email_address,
            }),
            description="SGAF configuration parameters",
        )

        # ============================================================================
        # SERVICE 11: SES - Email Service (for better email delivery)
        # ============================================================================
        # Note: SES requires email verification in sandbox mode
        # This is set up but requires manual verification in AWS Console
        ses_configuration_set = ses.ConfigurationSet(self, "SesConfigurationSet",
            configuration_set_name="sgaf-email-config"
        )

        # ============================================================================
        # SERVICE 12: X-Ray - Distributed Tracing
        # ============================================================================
        # Enable X-Ray tracing for Lambda functions
        tracing = _lambda.Tracing.ACTIVE

        # ============================================================================
        # SERVICE 13: SQS - Dead Letter Queue for failed messages
        # ============================================================================
        dlq = sqs.Queue(self, "SgafDLQ",
            queue_name="sgaf-dead-letter-queue",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ============================================================================
        # SERVICE 14: Cognito - User Authentication for Frontend
        # ============================================================================
        user_pool = cognito.UserPool(self, "SgafUserPool",
            user_pool_name="sgaf-users",
            sign_in_aliases=cognito.SignInAliases(
                email=True,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
            ),
            self_sign_up_enabled=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        user_pool_client = user_pool.add_client("SgafWebClient",
            user_pool_client_name="sgaf-web-client",
            generate_secret=False,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=["http://localhost:3000", "https://localhost:3000"],
            ),
        )

        user_pool_domain = user_pool.add_domain("SgafUserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="sgaf-app",
            ),
        )

        common_env = {
            "INPUT_BUCKET": input_bucket.bucket_name,
            "OUTPUT_BUCKET": output_bucket.bucket_name,
            "DYNAMODB_TABLE": jobs_table.table_name,
            "MAX_FILE_SIZE_BYTES": "1048576",  # 1 MiB cap
            "MAX_ITEMS": "3"
        }

        # ============================================================================
        # SERVICE 5: Lambda Functions
        # ============================================================================

        # Process Lambda (invoked by Step Functions Map)
        process_fn = _lambda.Function(self, "ProcessFn",
            code=_lambda.Code.from_asset("lambda/process"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment=common_env,
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,  # Enable X-Ray tracing
            dead_letter_queue=dlq,  # Use DLQ for failed invocations
        )
        output_bucket.grant_read_write(process_fn)
        input_bucket.grant_read(process_fn)
        jobs_table.grant_read_data(process_fn)
        jobs_table.grant_write_data(process_fn)
        process_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
        ))

        # Aggregate Lambda
        aggregate_fn = _lambda.Function(self, "AggregateFn",
            code=_lambda.Code.from_asset("lambda/aggregate"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment=common_env,
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,  # Enable X-Ray tracing
            dead_letter_queue=dlq,  # Use DLQ for failed invocations
        )
        output_bucket.grant_read_write(aggregate_fn)
        aggregate_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
        ))

        # Update Status Lambda (updates DynamoDB)
        update_status_fn = _lambda.Function(self, "UpdateStatusFn",
            code=_lambda.Code.from_asset("lambda/update_status"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment={
                **common_env,
            },
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,  # Enable X-Ray tracing
            dead_letter_queue=dlq,  # Use DLQ for failed invocations
        )
        jobs_table.grant_read_data(update_status_fn)
        jobs_table.grant_write_data(update_status_fn)
        output_bucket.grant_read(update_status_fn)

        # Update aggregate function environment
        aggregate_fn.add_environment("UPDATE_STATUS_FUNCTION", update_status_fn.function_name)
        aggregate_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[update_status_fn.function_arn],
        ))

        # API Lambda
        api_fn = _lambda.Function(self, "ApiFn",
            code=_lambda.Code.from_asset("lambda/api"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment={
                **common_env,
                "CONFIG_PARAMETER": config_parameter.parameter_name,
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
            },
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,  # Enable X-Ray tracing
            dead_letter_queue=dlq,  # Use DLQ for failed invocations
        )
        
        # Grant permissions for Secrets Manager, SSM, and Cognito
        email_secret.grant_read(api_fn)
        config_parameter.grant_read(api_fn)
        user_pool.grant(api_fn, "cognito-idp:AdminGetUser", "cognito-idp:AdminListGroupsForUser")
        input_bucket.grant_read_write(api_fn)
        jobs_table.grant_read_data(api_fn)
        jobs_table.grant_write_data(api_fn)
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["stepfunctions:StartExecution"],
            resources=["*"],  # Will be restricted below
        ))

        # Ingest Lambda: triggered by S3, validates and starts Step Functions
        ingest_fn = _lambda.Function(self, "IngestFn",
            code=_lambda.Code.from_asset("lambda/ingest"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment={
                **common_env,
            },
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,  # Enable X-Ray tracing
            dead_letter_queue=dlq,  # Use DLQ for failed invocations
        )
        
        # Format SNS Lambda: Formats detailed notification messages
        format_sns_fn = _lambda.Function(self, "FormatSnsFn",
            code=_lambda.Code.from_asset("lambda/format_sns"),
            handler="app.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment={
                "OUTPUT_BUCKET": output_bucket.bucket_name,
            },
            log_retention=logs.RetentionDays.THREE_DAYS,
            tracing=tracing,
        )
        
        # Grant permissions for Secrets Manager and SSM
        email_secret.grant_read(ingest_fn)
        config_parameter.grant_read(ingest_fn)
        input_bucket.grant_read(ingest_fn)
        jobs_table.grant_read_data(ingest_fn)
        jobs_table.grant_write_data(ingest_fn)
        
        # Grant permissions for format_sns
        output_bucket.grant_read(format_sns_fn)

        # ============================================================================
        # SERVICE 6: Step Functions - Workflow Orchestration
        # ============================================================================
        
        # Update DynamoDB task
        update_dynamodb_task = tasks.LambdaInvoke(self, "UpdateDynamoDB",
            lambda_function=update_status_fn,
            payload_response_only=True,
        )

        # Process task
        process_task = tasks.LambdaInvoke(self, "ProcessItem",
            lambda_function=process_fn,
            payload_response_only=True,
        )

        # Map state for parallel processing
        map_state = sfn.Map(self, "MapProcess",
            items_path=sfn.JsonPath.string_at("$.workItems"),
            max_concurrency=1
        ).iterator(process_task)

        # Aggregate task
        aggregate_task = tasks.LambdaInvoke(self, "AggregateResults",
            lambda_function=aggregate_fn,
            payload_response_only=True,
        )

        # Format SNS message task (Service 9: Lambda for message formatting)
        format_sns_task = tasks.LambdaInvoke(self, "FormatSnsMessage",
            lambda_function=format_sns_fn,
            payload_response_only=True,
        )

        # SNS Success notification (Service 4: SNS)
        notify_success = tasks.SnsPublish(self, "NotifySuccess",
            topic=success_topic,
            subject=sfn.JsonPath.string_at("$.subject"),
            message=sfn.TaskInput.from_text(sfn.JsonPath.string_at("$.message")),
        )

        # Format failure message task
        format_failure_task = tasks.LambdaInvoke(self, "FormatFailureMessage",
            lambda_function=format_sns_fn,
            payload_response_only=True,
        )

        # SNS Failure notification (Service 4: SNS)
        notify_failure = tasks.SnsPublish(self, "NotifyFailure",
            topic=failure_topic,
            subject=sfn.JsonPath.string_at("$.subject"),
            message=sfn.TaskInput.from_text(sfn.JsonPath.string_at("$.message")),
        )

        # Error handling with formatted messages
        failure_chain = format_failure_task.next(notify_failure)
        map_state.add_catch(failure_chain, result_path="$.error")
        aggregate_task.add_catch(failure_chain, result_path="$.error")
        update_dynamodb_task.add_catch(failure_chain, result_path="$.error")
        format_sns_task.add_catch(failure_chain, result_path="$.error")

        # Workflow definition showing all services:
        # 1. S3 (trigger) -> 2. Lambda (Ingest) -> 3. Step Functions (orchestration)
        # 4. Lambda (Process) -> 5. Lambda (Aggregate) -> 6. DynamoDB (Update)
        # 7. Lambda (Format SNS) -> 8. SNS (Notify) -> 9. CloudWatch (Metrics)
        # 10. EventBridge (Monitoring) -> 11. X-Ray (Tracing) -> 12. SQS (DLQ)
        # 13. Secrets Manager (Config) -> 14. SSM (Parameters)
        definition = (
            map_state
            .next(aggregate_task)
            .next(update_dynamodb_task)
            .next(format_sns_task)
            .next(notify_success)
        )

        state_machine = sfn.StateMachine(self, "SgafStateMachine",
            definition=definition,
            timeout=Duration.minutes(2),
            state_machine_type=sfn.StateMachineType.STANDARD,
            logs=sfn.LogOptions(
                destination=logs.LogGroup(self, "SgafSfnLogs",
                    retention=logs.RetentionDays.THREE_DAYS
                ),
                level=sfn.LogLevel.ALL
            ),
            tracing_enabled=True,  # Enable X-Ray tracing for Step Functions
        )

        # Grant permissions
        state_machine.grant_start_execution(ingest_fn)
        state_machine.grant_start_execution(api_fn)
        api_fn.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)

        # Update ingest function environment
        ingest_fn.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)

        # ============================================================================
        # SERVICE 7: EventBridge - Event-Driven Processing
        # ============================================================================
        
        # EventBridge rule to trigger periodic cleanup (optional)
        cleanup_rule = events.Rule(self, "CleanupRule",
            schedule=events.Schedule.rate(Duration.days(1)),
            enabled=False,  # Disabled by default, can be enabled for cleanup
            description="Daily cleanup of old jobs"
        )

        # EventBridge rule for monitoring Step Functions executions
        sfn_event_rule = events.Rule(self, "StepFunctionsEventRule",
            event_pattern=events.EventPattern(
                source=["aws.states"],
                detail_type=["Step Functions Execution Status Change"],
                detail={
                    "status": ["FAILED", "TIMED_OUT", "ABORTED"]
                }
            ),
            description="Monitor failed Step Functions executions"
        )
        sfn_event_rule.add_target(targets.SnsTopic(failure_topic))

        # ============================================================================
        # SERVICE 8: API Gateway - REST API for Frontend
        # ============================================================================
        
        api = apigateway.RestApi(self, "SgafApi",
            rest_api_name="SGAF Geospatial API",
            description="API for uploading and querying geospatial data",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization"],
            ),
        )

        # Upload endpoint
        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST",
            apigateway.LambdaIntegration(api_fn),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    }
                )
            ]
        )

        # Status endpoint
        status_resource = api.root.add_resource("status").add_resource("{datasetId}")
        status_resource.add_method("GET",
            apigateway.LambdaIntegration(api_fn),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    }
                )
            ]
        )

        # Jobs list endpoint
        jobs_resource = api.root.add_resource("jobs")
        jobs_resource.add_method("GET",
            apigateway.LambdaIntegration(api_fn),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    }
                )
            ]
        )

        # Note: OPTIONS methods are automatically created by default_cors_preflight_options

        # S3 event: trigger ingest on object created
        input_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(ingest_fn)
        )

        # ============================================================================
        # CloudWatch Dashboard Widgets
        # ============================================================================
        
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Files Processed",
                left=[
                    cloudwatch.Metric(
                        namespace="SGAF/Processing",
                        metric_name="FilesProcessed",
                        statistic="Sum",
                    ),
                ],
            ),
            cloudwatch.GraphWidget(
                title="Processing Metrics",
                left=[
                    cloudwatch.Metric(
                        namespace="SGAF/Processing",
                        metric_name="FilesProcessed",
                        statistic="Sum",
                    ),
                    cloudwatch.Metric(
                        namespace="SGAF/Aggregation",
                        metric_name="JobsCompleted",
                        statistic="Sum",
                    ),
                ],
            ),
            cloudwatch.AlarmWidget(
                alarm=error_alarm,
                title="Processing Errors",
            ),
        )

        # ============================================================================
        # Outputs
        # ============================================================================

        cdk.CfnOutput(self, "InputBucketName", value=input_bucket.bucket_name)
        cdk.CfnOutput(self, "OutputBucketName", value=output_bucket.bucket_name)
        cdk.CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
        cdk.CfnOutput(self, "ApiGatewayUrl", value=api.url)
        cdk.CfnOutput(self, "SuccessTopicArn", value=success_topic.topic_arn)
        cdk.CfnOutput(self, "FailureTopicArn", value=failure_topic.topic_arn)
        cdk.CfnOutput(self, "DynamoDBTableName", value=jobs_table.table_name)
        cdk.CfnOutput(self, "CloudWatchDashboard", value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=SGAF-Monitoring")
        cdk.CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        cdk.CfnOutput(self, "UserPoolDomain", value=user_pool_domain.domain_name)
        cdk.CfnOutput(self, "CognitoDomainUrl", value=f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com")
        cdk.CfnOutput(self, "DLQUrl", value=dlq.queue_url)
        cdk.CfnOutput(self, "SecretsManagerArn", value=email_secret.secret_arn)
        cdk.CfnOutput(self, "SSMParameterName", value=config_parameter.parameter_name)
        cdk.CfnOutput(self, "SNSSubscriptionNote", value=f"IMPORTANT: Check your email ({email_address}) and confirm SNS subscription!")
