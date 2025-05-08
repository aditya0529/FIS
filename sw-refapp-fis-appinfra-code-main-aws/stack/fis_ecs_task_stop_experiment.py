from aws_cdk import aws_fis as fis

def create_fis_ecs_task_stop_experiment_body(self, config, role, log_group, ecs_app_name, percent):
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskstop-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
        description=f"Stop ECS Task for service app {ecs_app_name} with percent {percent}",
        role_arn=role.role_arn,
        targets={
            "ECSTaskStop": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ecs:task",
                parameters={
                    "cluster": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-cluster-fra-{config['resource_suffix']}",
                    "service": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-service-fra-{config['resource_suffix']}"
                },
                selection_mode=f"PERCENT({percent})",
                resource_tags={"sw:product": "mra", "sw:application": ecs_app_name}
            )
        },
        actions={
            "ECSTaskStopAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:ecs:stop-task",
                description=f"Stop ECS Task for service app {ecs_app_name} with percent {percent}",
                parameters={},
                targets={
                    "Tasks": "ECSTaskStop"
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskstop-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
