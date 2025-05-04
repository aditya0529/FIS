from constructs import Construct
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_ecr as ecr,
    aws_ec2 as ec2,
    aws_certificatemanager as cert,
    aws_logs as logs,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_fis as fis,
    aws_synthetics as synthetics,
)

from util.app_config import ApplicationConfig

from .fis_network_subnet_experiment import create_fis_network_subnet_experiment_body
from .fis_ecs_cluster_drain_experiment import create_fis_ecs_cluster_drain_experiment_body
from .fis_rds_failover_experiment import create_fis_rds_failover_experiment_body
from .fis_ecs_task_stop_experiment import create_fis_ecs_task_stop_experiment_body
from .fis_ecs_task_cpustress_experiment import create_fis_ecs_task_cpustress_experiment_body
from .fis_ecs_task_iostress_experiment import create_fis_ecs_task_iostress_experiment_body
from .fis_multi_az_failover_experiment import create_fis_multi_az_failover_experiment_body
from .fis_role import create_fis_role_body
from .fis_ecs_task_kill_process_experiment import create_fis_ecs_task_kill_process_experiment_body
from .fis_ecs_task_packet_loss_experiment import create_fis_ecs_task_packet_loss_experiment_body

class cloud_infra(Stack):

    def create_canary_security_group(self, config, vpc):

        # security group
        sg = ec2.SecurityGroup(
            self,
            id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-sg-{config['deployment_region']}-{config['resource_suffix']}",
            security_group_name=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-sg-{config['deployment_region']}-{config['resource_suffix']}",
            description="Allow the communication from Canary",
            allow_all_outbound=False,
            # if this is set to false then no egress rule will be automatically created
            vpc=vpc
        )

        sg.add_egress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(443)
        )

        s3_prefix_list = ec2.PrefixList.from_prefix_list_id(
            self, id="S3PrefixList",
            prefix_list_id=config['s3_prefix_list']
        )

        sg.add_egress_rule(
            ec2.Peer.prefix_list(s3_prefix_list.prefix_list_id),
            ec2.Port.tcp(443)
        )

        return sg

    def create_artifact_store(self, config) -> s3.Bucket:

        bucket = s3.Bucket(self,
                           id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-s3-{config['deployment_region']}-{config['resource_suffix']}",
                           bucket_name=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-s3-{config['workload_account']}-{config['deployment_region']}-{config['resource_suffix']}",
                           block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                           encryption=s3.BucketEncryption.S3_MANAGED,
                           minimum_tls_version=1.2,
                           object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
                           object_lock_enabled=False,
                           enforce_ssl=True,
                           versioned=True,
                           lifecycle_rules=[s3.LifecycleRule(
                               enabled=True,
                               id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-s3-lifecycle-{config['resource_suffix']}",
                               noncurrent_version_expiration=Duration.days(
                                   7),
                               noncurrent_versions_to_retain=1
                           )
                           ]
                           )

        return bucket

    #create canary role
    def create_canary_role(self, config, bucket_name) -> iam.Role:
        canary_role = iam.Role(self,
                               id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-role-{config['deployment_region']}-{config['resource_suffix']}",
                               assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
                               role_name=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-role-{config['deployment_region']}-{config['resource_suffix']}",
                               managed_policies=[
                                   iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchSyntheticsFullAccess'),
                                   iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2FullAccess')
                               ]
                               )

        canary_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:GetObject"
                ],
                resources=[
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            )
        )

        canary_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetBucketLocation"
                ],
                resources=[
                    f"arn:aws:s3:::{bucket_name}"
                ]
            )
        )

        canary_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:CreateLogGroup"
                ],
                resources=[
                    f"arn:aws:logs:*:{self.account}:log-group:/aws/lambda/*"
                ]
            )
        )

        canary_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:ListAllMyBuckets",
                    "xray:PutTraceSegments",
                    "cloudwatch:PutMetricData",
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface"
                ],
                resources=["*"]
            )
        )

        return canary_role

    def canary_script_data(self, config):
        canary_script = '''import json
import os
import http.client
from selenium.webdriver.common.by import By
import urllib.parse
from aws_synthetics.selenium import synthetics_webdriver as syn_webdriver
from aws_synthetics.common import synthetics_logger as logger

def verify_request(method, url, post_data=None, headers={}):
    parsed_url = urllib.parse.urlparse(url)
    user_agent = str(syn_webdriver.get_canary_user_agent_string())
    if "User-Agent" in headers:
        headers["User-Agent"] = f"{user_agent} {headers['User-Agent']}"
    else:
        headers["User-Agent"] = user_agent

    logger.info(f"Making request with Method: '{method}' URL: {url}: Data: {json.dumps(post_data)} Headers: {json.dumps(headers)}")

    if parsed_url.scheme == "https":
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port)
    else:
        conn = http.client.HTTPConnection(parsed_url.hostname, parsed_url.port)

    conn.request(method, url, post_data, headers)
    response = conn.getresponse()
    logger.info(f"Status Code: {response.status}")
    logger.info(f"Response Headers: {json.dumps(response.headers.as_string())}")

    if not response.status or response.status < 200 or response.status > 299:
        try:
            logger.error(f"Response: {response.read().decode()}")
        finally:
            if response.reason:
                conn.close()
                raise Exception(f"Failed: {response.reason}")
            else:
                conn.close()
                raise Exception(f"Failed with status code: {response.status}")

    logger.info(f"Response: {response.read().decode()}")
    logger.info("HTTP request successfully executed.")
    conn.close()
    
def handler(event, context):
    
    url = os.environ['TARGET_URL']  # Read the environment variable for the URL
    method = 'GET'
    postData = ""
    headers1 = {}
    
    verify_request(method, url, None, headers1)
    logger.info("Canary successfully executed.")
'''

        return canary_script

    def create_canary(self, config, vpc, subnet_ids, security_group_id, canary_role,
                      target_url, canary_script, app_name, bucket_name):
        # Create the Canary inside the existing VPC
        canary = synthetics.CfnCanary(self,
                                      id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-{app_name}-{config['deployment_region']}-{config['resource_suffix']}",
                                      name=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-{app_name}-{config['deployment_region']}-{config['resource_suffix']}",
                                      runtime_version="syn-python-selenium-5.0",
                                      artifact_s3_location=f"s3://{bucket_name}/canary/{self.region}/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-canary-{app_name}-{config['resource_suffix']}",
                                      execution_role_arn=canary_role.role_arn,
                                      code=synthetics.CfnCanary.CodeProperty(
                                          handler="index.handler",
                                          script=canary_script
                                      ),
                                      run_config=synthetics.CfnCanary.RunConfigProperty(
                                          active_tracing=False,
                                          environment_variables={
                                              'TARGET_URL': target_url  # Set the environment variable here
                                          }
                                      ),
                                      schedule=synthetics.CfnCanary.ScheduleProperty(
                                          expression="rate(1 minute)"  # Set the canary to run every 1 minute
                                      ),
                                      vpc_config=synthetics.CfnCanary.VPCConfigProperty(
                                          vpc_id=vpc.vpc_id,
                                          subnet_ids= subnet_ids,
                                          security_group_ids=security_group_id
                                      ),
                                      success_retention_period=30,
                                      failure_retention_period=30,
                                      start_canary_after_creation=True
                                      )

        return canary

    # Create task execution role for FIS service
    def create_fis_role(self, config):
        return create_fis_role_body(self, config)

    def lookup_vpc(self, config):
        # vpc lookup from account
        vpc = ec2.Vpc.from_lookup(
            self,
            f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-vpc-{config['resource_suffix']}",
            vpc_id=f"{config['vpc_id']}"
        )

        return vpc

    def lookup_subnet(self, subnet_1, subnet_2):
        subnet = ec2.SubnetSelection(
            one_per_az=True,
            subnet_filters=[
                ec2.SubnetFilter.by_ids([
                    f"{subnet_1}", f"{subnet_2}"
                ])
            ]
        )

        return subnet

    def create_log_group(self, config):
        log_group = logs.LogGroup(
            self,
            id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-fis-logs-{config['deployment_region']}-{config['resource_suffix']}",
            log_group_name=f"/sw/fis/{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-fis-logs-{config['deployment_region']}-{config['resource_suffix']}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        return log_group

    def create_fis_network_subnet_experiment(self, config, subnet_list, test_name, role, log_group, az_name, db_app_list):
        return create_fis_network_subnet_experiment_body(self, config, subnet_list, test_name, role, log_group, az_name, db_app_list)

    def create_fis_ecs_cluster_drain_experiment(self, config, role, log_group, percent):
        return create_fis_ecs_cluster_drain_experiment_body(self, config, role, log_group, percent)

    def create_fis_rds_failover_experiment(self, config, role, log_group, db_app_name):
        return create_fis_rds_failover_experiment_body(self, config, role, log_group, db_app_name)

    def create_fis_ecs_task_stop_experiment(self, config, role, log_group, ecs_app_name, percent):
        return create_fis_ecs_task_stop_experiment_body(self, config, role, log_group, ecs_app_name, percent)

    def create_fis_ecs_task_cpustress_experiment(self, config, role, log_group, ecs_app_name, percent):
        return create_fis_ecs_task_cpustress_experiment_body(self, config, role, log_group, ecs_app_name, percent)

    def create_fis_ecs_task_iostress_experiment(self, config, role, log_group, ecs_app_name, percent):
        return create_fis_ecs_task_iostress_experiment_body(self, config, role, log_group, ecs_app_name, percent)

    def create_fis_ecs_task_kill_process_experiment(self, config, role, log_group, ecs_app_name, percent, process_name):
        return create_fis_ecs_task_kill_process_experiment_body(self, config, role, log_group, ecs_app_name, percent, process_name)

    def create_fis_ecs_task_packet_loss_experiment(self, config, role, log_group, ecs_app_name, percent, loss_percent, duration="PT5M"):
        return create_fis_ecs_task_packet_loss_experiment_body(self, config, role, log_group, ecs_app_name, percent, loss_percent, duration)

    def create_fis_multi_az_failover_experiment(self, config, subnet_list_az1, subnet_list_az2, test_name, role, log_group, az_names, db_app_list):
        return create_fis_multi_az_failover_experiment_body(self, config, subnet_list_az1, subnet_list_az2, test_name, role, log_group, az_names, db_app_list)

    def __init__(self, scope: Construct, construct_id: str, resource_config, app_config, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get configuration variables from resource file
        config = resource_config
        app_config = app_config

        # bucket = self.create_artifact_store(config)

        # vpc lookup from account
        vpc = self.lookup_vpc(config=config)

        log_group = self.create_log_group(config=config)
        fis_role = self.create_fis_role(config=config)

        # FIS Experiment Template - App AZ subnet fail
        self.create_fis_network_subnet_experiment(config=config, subnet_list=config['subnet_az1_list'],
                                                  test_name="az1", role=fis_role, log_group=log_group,
                                                  az_name=config['az1_name'], db_app_list=config['db_clusters']
                                                  )
        self.create_fis_network_subnet_experiment(config=config, subnet_list=config['subnet_az2_list'],
                                                  test_name="az2", role=fis_role, log_group=log_group,
                                                  az_name=config['az2_name'], db_app_list=config['db_clusters']
                                                  )

        # FIS Experiment Template - ECS stop
        for ecs_name in config['ecs_services'].split(","):
            for percent_val in config['ecs_taks_percents'].split(","):
                self.create_fis_ecs_task_stop_experiment(config=config, role=fis_role, log_group=log_group,
                                                         ecs_app_name=ecs_name, percent=percent_val
                                                         )

        # DO NOT ENABLE ---- FIS Experiment Template - ECS CPU stress
        for ecs_name in config['ecs_services'].split(","):
            for percent_val in config['ecs_taks_percents'].split(","):
                self.create_fis_ecs_task_cpustress_experiment(config=config, role=fis_role, log_group=log_group,
                                                              ecs_app_name=ecs_name, percent=percent_val
                                                              )

        # DO NOT ENABLE ---- FIS Experiment Template - ECS IO stress - Future test cases
        for ecs_name in config['ecs_services'].split(","):
            for percent_val in config['ecs_taks_percents'].split(","):
                self.create_fis_ecs_task_iostress_experiment(config=config, role=fis_role, log_group=log_group,
                                                             ecs_app_name=ecs_name, percent=percent_val
                                                             )

        for percent_val in config['ecs_drain_percents'].split(","):
            self.create_fis_ecs_cluster_drain_experiment(config=config, role=fis_role,
                                                         log_group=log_group, percent=percent_val
                                                         )

        for db_name in config['db_clusters'].split(","):
            self.create_fis_rds_failover_experiment(config=config, role=fis_role, log_group=log_group, db_app_name=db_name)

        # FIS Experiment Template - Multi-AZ failover
        self.create_fis_multi_az_failover_experiment(
            config=config,
            subnet_list_az1=config['subnet_az1_list'],
            subnet_list_az2=config['subnet_az2_list'],
            test_name="multi-az-failover",
            role=fis_role,
            log_group=log_group,
            az_names=f"{config['az1_name']},{config['az2_name']}",
            db_app_list=config['db_clusters']
        )

        # FIS Experiment Template - ECS task kill process
        for ecs_name in config['ecs_services'].split(","):
            for percent_val in config['ecs_taks_percents'].split(","):
                self.create_fis_ecs_task_kill_process_experiment(
                    config=config,
                    role=fis_role,
                    log_group=log_group,
                    ecs_app_name=ecs_name,
                    percent=percent_val,
                    process_name="java" 
                )

        # FIS Experiment Template - ECS packet loss
        for ecs_name in config['ecs_services'].split(","):
            for percent_val in config['ecs_taks_percents'].split(","):
                self.create_fis_ecs_task_packet_loss_experiment(
                    config=config,
                    role=fis_role,
                    log_group=log_group,
                    ecs_app_name=ecs_name,
                    percent=percent_val,
                    loss_percent=30,  # 10% packet loss;
                    duration="PT5M"  # 5 minutes
                )

        # --- Canary creation logic disabled: will not be included in CDK synth template ---
        if False:
            canary_role = self.create_canary_role(config=config, bucket_name=bucket.bucket_name)
            canary_script = self.canary_script_data(config=config)
            canary_sg = self.create_canary_security_group(config=config, vpc=vpc)

            for app in app_config:
                for app_name, app_url in zip(app.get_app_names(), app.get_app_urls()):
                    self.create_canary(config=config, vpc=vpc, subnet_ids=[app.get_subnet_id()],
                                       security_group_id=[canary_sg.security_group_id], canary_role=canary_role,
                                       target_url=app_url, canary_script=canary_script,
                                       app_name=f"{app_name}-{app.get_canary_name()}", bucket_name=bucket.bucket_name)