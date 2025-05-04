from aws_cdk import aws_fis as fis

def create_fis_ecs_task_cpustress_experiment_body(self, config, role, log_group, ecs_app_name, percent):
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskcpustress-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
        description=f"CPU Stress ECS Task for service app {ecs_app_name} with percent {percent}",
        role_arn=role.role_arn,
        targets={
            "ECSTaskCPUStress": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ecs:task",
                resource_tags={"sw:product": "mra", "sw:app": ecs_app_name},
                selection_mode="PERCENTAGE",
                parameters={"percentage": percent}
            )
        },
        actions={
            "ECSTaskCPUStressAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:ecs:run-cpu-stress",
                description=f"CPU Stress ECS Task for service app {ecs_app_name} with percent {percent}",
                parameters={"duration": "PT15M"},
                targets={
                    "Tasks": "ECSTaskCPUStress"
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskcpustress-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
