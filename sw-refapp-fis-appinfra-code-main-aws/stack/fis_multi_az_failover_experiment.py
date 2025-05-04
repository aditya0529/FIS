from aws_cdk import aws_fis as fis

def create_fis_multi_az_failover_experiment_body(self, config, subnet_list_az1, subnet_list_az2, test_name, role, log_group, az_names, db_app_list):
    """
    subnet_list_az1: comma-separated subnet IDs for AZ1
    subnet_list_az2: comma-separated subnet IDs for AZ2
    az_names: comma-separated AZ names (e.g. 'eu-central-1a,eu-central-1b')
    db_app_list: comma-separated DB app names
    """
    db_arns = []
    for db_app_name in db_app_list.split(","):
        db_arns.append(f"arn:aws:rds:{self.region}:{self.account}:cluster:{config['resource_prefix']}-mra-{config['app_env']}-{db_app_name}-{config['resource_suffix']}")

    subnet_arns = []
    for subnet in subnet_list_az1.split(","):
        subnet_arns.append(f"arn:aws:ec2:{self.region}:{self.account}:subnet/{subnet}")
    for subnet in subnet_list_az2.split(","):
        subnet_arns.append(f"arn:aws:ec2:{self.region}:{self.account}:subnet/{subnet}")

    az_list = [az.strip() for az in az_names.split(",") if az.strip()]
    if len(az_list) < 2:
        raise ValueError("At least two AZs must be specified for multi-AZ failover experiment.")

    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-multi-azfailover-experiment-{test_name}-{config['resource_suffix']}",
        description=f"Multi-AZ Power Failure Simulation in {test_name} ({az_list[0]}, {az_list[1]})",
        role_arn=role.role_arn,
        targets={
            "SubnetDown": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ec2:subnet",
                resource_tags={"sw:product" : "refapp"},
                # resource_arns=subnet_arns,
                selection_mode="ALL",
                parameters={}
            ),
            "RDSFailover": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:rds:cluster",
                resource_tags={"sw:product" : "mra"},
                selection_mode="ALL",
                parameters={
                    "writerAvailabilityZoneIdentifiers": ",".join(az_list[:2])
                }
            )
        },
        actions={
            "DisruptNetworkConnectivity": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:network:disrupt-connectivity",
                description=f"Disrupt network connectivity for subnets in {test_name} ({az_list[0]}, {az_list[1]})",
                parameters={
                    "duration": "PT15M",
                    "scope": "all"
                },
                targets={
                    "Subnets": "SubnetDown"
                }
            ),
            "RDSFailoverAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:rds:failover-db-cluster",
                description="Aurora Serverless RDS Multi-AZ Failover DB",
                parameters={},
                targets={
                    "Clusters": "RDSFailover"
                }
            ),
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-multi-azfailover-experiment-{test_name}-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
