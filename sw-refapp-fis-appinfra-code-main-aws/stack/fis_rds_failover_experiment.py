from aws_cdk import aws_fis as fis

def create_fis_rds_failover_experiment_body(self, config, role, log_group, db_app_name):
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-rdsfailover-{db_app_name}-experiment-{config['resource_suffix']}",
        description=f"Aurora Serverless RDS Failover DB {db_app_name}",
        role_arn=role.role_arn,
        targets={
            "RDSFailover": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:rds:cluster",
                resource_arns=[
                    f"arn:aws:rds:{self.region}:{self.account}:cluster:{config['resource_prefix']}-mra-{config['app_env']}-{db_app_name}-{config['resource_suffix']}"
                ],
                selection_mode="ALL"
            )
        },
        actions={
            "RDSFailoverAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:rds:failover-db-cluster",
                description=f"Aurora Serverless RDS Failover DB {db_app_name}",
                parameters={},
                targets={
                    "Clusters": "RDSFailover"
                }
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-rdsfailover-{db_app_name}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
