#!/usr/bin/env python3
import aws_cdk as cdk
from sgaf.stack import SgafStack

app = cdk.App()

# Default to user's account and region; allow override via context
account = "841722555450"
region = app.node.try_get_context("region") or "us-east-1"

SgafStack(app, "SgafStack",
          env=cdk.Environment(account=account, region=region))

app.synth()

