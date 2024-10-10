#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.cdk_stack import CdkStack
from docker_app.config_file import Config

app = cdk.App()
CdkStack(app, Config.STACK_NAME,)

app.synth()
