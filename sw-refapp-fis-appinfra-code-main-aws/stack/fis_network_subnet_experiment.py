from aws_cdk import aws_fis as fis

# Note: ElastiCacheCluster target and related actions are commented out as per user request.
def create_fis_network_subnet_experiment_body(self, config, subnet_list, test_name, role, log_group, az_name, db_app_list):
    db_arns = []
    for db_app_name in db_app_list.split(","):
        db_arns.append(f"arn:aws:rds:{self.region}:{self.account}:cluster:{config['resource_prefix']}-mra-{config['app_env']}-{db_app_name}-{config['resource_suffix']}")

    subnet_arns = []
    for subnet in subnet_list.split(","):
        subnet_arns.append(f"arn:aws:ec2:{self.region}:{self.account}:subnet/{subnet}")

    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-azfailure-experiment-{test_name}-{config['resource_suffix']}",
        description=f"AZ Power Failure Simulation in {test_name}",
        role_arn=role.role_arn,
        targets={
            "SubnetDown": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ec2:subnet",
                resource_arns=subnet_arns,
                selection_mode="ALL",
                parameters={}
            ),
            "RDSFailover": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:rds:cluster",
                resource_tags={"sw:product" : "mra"},
                selection_mode="ALL",
                parameters={
                    "writerAvailabilityZoneIdentifiers": az_name
                }
            ),
            # "ElastiCacheCluster": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
            #     resource_type="aws:elasticache:replicationgroup",
            #     resource_tags={"sw:product" : "mra"},
            #     selection_mode="ALL",
            #     parameters={
            #         "availabilityZoneIdentifier": az_name
            #     }
            # )
        },
        actions={
            "DisruptNetworkConnectivity": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:network:disrupt-connectivity",
                description=f"Disrupt network connectivity for subnets in {test_name}",
                parameters={
                    "duration": "PT15M",  # Duration of the network disruption
                    "scope": "all"
                },
                targets={
                    "Subnets": "SubnetDown"
                }
            ),
            "RDSFailoverAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:rds:failover-db-cluster",
                description="Aurora Serverless RDS Failover DB",
                parameters={},
                targets={
                    "Clusters": "RDSFailover"
                }
            ),
            # "PauseElastiCache": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
            #     action_id="aws:elasticache:replicationgroup-interrupt-az-power",
            #     parameters={
            #         "duration": "PT15M"
            #     },
            #     targets={
            #         "ReplicationGroups": "ElastiCacheCluster"
            #     }
            # ),
            "FISWait": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:fis:wait",
                parameters={
                    "duration": "PT15M"
                },
                targets={}
            )
        },
        experiment_options=fis.CfnExperimentTemplate.ExperimentTemplateExperimentOptionsProperty(
            account_targeting="single-account",
            empty_target_resolution_mode="fail"
        ),
        log_configuration=fis.CfnExperimentTemplate.ExperimentTemplateLogConfigurationProperty(
            cloud_watch_logs_configuration={
                "LogGroupArn": log_group.log_group_arn
            },
            log_schema_version=2
        ),
        stop_conditions=[
            {
                "source": "none"
            }
        ],
        tags={
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-azfailure-experiment-{test_name}-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
