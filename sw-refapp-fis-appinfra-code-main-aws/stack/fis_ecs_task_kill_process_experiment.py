from aws_cdk import aws_fis as fis

def create_fis_ecs_task_kill_process_experiment_body(self, config, role, log_group, ecs_app_name, percent, process_name):
    """
    Creates a FIS experiment to kill a process inside ECS tasks using the aws:ecs:task:kill-process action.
    - percent: percentage of tasks to target
    - process_name: name of the process to kill (e.g., 'nginx', 'python')
    """
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskkillprocess-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
        description=f"Kill process '{process_name}' in ECS tasks for {ecs_app_name} ({percent}%)",
        role_arn=role.role_arn,
        targets={
            "ECSTaskKillProcess": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ecs:task",
                parameters={
                    "cluster": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-cluster-fra-{config['resource_suffix']}",
                    "service": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-service-fra-{config['resource_suffix']}"
                },
                selection_mode=f"PERCENT({percent})",
                resource_tags={"sw:product": "mra", "sw:app": ecs_app_name}
            )
        },
        actions={
            "ECSTaskKillProcessAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:ecs:task-kill-process",
                description=f"Kill process '{process_name}' in ECS tasks for {ecs_app_name}",
                parameters={
                    "processName": process_name,
                    "installDependencies": "true"
                },
                targets={
                    "Tasks": "ECSTaskKillProcess"
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskkillprocess-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
