from aws_cdk import aws_fis as fis

def create_fis_ecs_cluster_drain_experiment_body(self, config, role, log_group, percent):
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-drain-p{percent}-experiment-{config['resource_suffix']}",
        description=f"Drain ECS cluster container instances in percent {percent}",
        role_arn=role.role_arn,
        targets={
            "ECSClusterDrain": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ecs:cluster",
                resource_arns=[
                    f"arn:aws:ecs:{self.region}:{self.account}:cluster/{config['resource_prefix']}-mra-{config['app_env']}-ecs-cluster-fra-{config['resource_suffix']}"
                ],
                selection_mode="ALL"
            )
        },
        actions={
            "ECSDrain": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:ecs:drain-container-instances",
                description=f"Drain ECS cluster container instances in percent {percent}",
                parameters={
                    "drainagePercentage": percent,
                    "duration": "PT15M"
                },
                targets={
                    "Clusters": "ECSClusterDrain"
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-drain-p{percent}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
