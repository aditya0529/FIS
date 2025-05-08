#!/usr/bin/env python3

import configparser
import aws_cdk as cdk
import os
import json
from aws_cdk import (
    Aspects,
    Tags,
)
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from stack.cloud_infra import cloud_infra
from util.app_config import ApplicationConfig

def load_applications_from_json(file_path, region):
    with open(file_path, 'r') as f:
        data = json.load(f)
    # Get the application list for the specified region, or an empty list if region not found
    region_specific_apps = data.get(region, [])
    return [ApplicationConfig(app) for app in region_specific_apps]

def get_def_stack_synth(config):
    return cdk.DefaultStackSynthesizer(
        cloud_formation_execution_role=f"arn:aws:iam::{config['workload_account']}:role/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}dply-role-main-a",
        deploy_role_arn=f"arn:aws:iam::{config['workload_account']}:role/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}dply-role-main-a",
        file_asset_publishing_role_arn=f"arn:aws:iam::{config['workload_account']}:role/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}dply-role-main-a",
        image_asset_publishing_role_arn=f"arn:aws:iam::{config['workload_account']}:role/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}dply-role-main-a",
        lookup_role_arn=f"arn:aws:iam::{config['workload_account']}:role/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}dply-role-main-a",
        file_assets_bucket_name=f"{config['asset_prefix']}-{config['workload_account']}-{config['deployment_region']}-{config['resource_suffix']}",
        # image_assets_repository_name=cdk_custom_configs.get('bootstrap_image_assets_repository_name')
        bootstrap_stack_version_ssm_parameter=f"{config['bootstrap_stack_version']}"
    )

if __name__ == "__main__":
    # Reading Application infra resource varibales using git branch name
    branch_name = os.getenv("SRC_BRANCH", "dev")

    # Pull comma-separated config file names from env or use defaults
    region_config_files_env = os.getenv(
        "REGION_CONFIG_FILES",
        "resource_eu-central-1.config,resource_us-east-1.config"
    )
    region_config_files = [cfg.strip() for cfg in region_config_files_env.split(",")]

    # Initializing CDK app
    app = cdk.App()

    # Application infra stack for resources required for application deployment
    # (Loop over each config file to create a separate stack)
    for config_file in region_config_files:

        config_parser = configparser.ConfigParser()
        config_parser.read(filenames=config_file)
        config = config_parser[branch_name]

        # Load application config for the current region
        app_config_for_region = load_applications_from_json(
            f"config/canary_app_list_{branch_name}.json",
            config['deployment_region']
        )

        cdk_stack = cloud_infra(
            app,
            f"{config['resource_prefix']}-{config['service_name']}-"
            f"{config['app_env']}-{config['app_name']}-infra-stack-"
            f"{config['deployment_region']}-{config['resource_suffix']}",
            resource_config=config,
            app_config=app_config_for_region, # Pass region-specific app_config
            env=cdk.Environment(
                account=f"{config['workload_account']}",
                region=f"{config['deployment_region']}"
            ),
            synthesizer=get_def_stack_synth(config)
        )

        # Add a tag to all constructs in each stack
        Tags.of(cdk_stack).add("sw:application", "mra")
        Tags.of(cdk_stack).add("sw:product", "mra")
        Tags.of(cdk_stack).add("sw:environment", f"{config['app_env']}")
        Tags.of(cdk_stack).add("sw:cost_center", f"{config['cost_center']}")

        # Inspect app with cdk-nag before synth
        Aspects.of(app).add(AwsSolutionsChecks())
        NagSuppressions.add_stack_suppressions(cdk_stack, [
            {'id': 'AwsSolutions-S1',  'reason': 'Cloudtrail already capturing access of S3 data plane'},
            {'id': 'AwsSolutions-IAM5','reason': 'IAM policy with resource star'},
            {'id': 'AwsSolutions-IAM4','reason': 'IAM managed policy'}
        ])

    # Synthesize and produce CloudFormation templates (2 stacks total)
    app.synth()