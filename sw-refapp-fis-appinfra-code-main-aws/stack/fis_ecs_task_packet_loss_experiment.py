from aws_cdk import aws_fis as fis

def create_fis_ecs_task_packet_loss_experiment_body(self, config, role, log_group, ecs_app_name, percent, loss_percent, duration="PT5M"):
    """
    Creates a FIS experiment to inject packet loss into ECS tasks using the aws:ecs:inject-network-packet-loss action.
    - percent: percentage of tasks to target
    - loss_percent: percent of packets to drop (e.g., 10 for 10%)
    - duration: duration of the network disruption (default 5 minutes)
    """
    experiment_template = fis.CfnExperimentTemplate(
        self,
        f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskpacketloss-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
        description=f"Inject {loss_percent}% packet loss in ECS tasks for {ecs_app_name} ({percent}%)",
        role_arn=role.role_arn,
        targets={
            "ECSTaskPacketLoss": fis.CfnExperimentTemplate.ExperimentTemplateTargetProperty(
                resource_type="aws:ecs:task",
                parameters={
                    "cluster": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-cluster-fra-{config['resource_suffix']}",
                    "service": f"{config['resource_prefix']}-mra-{config['app_env']}-ecs-service-fra-{config['resource_suffix']}"
                },
                selection_mode=f"PERCENT({percent})"
            )
        },
        actions={
            "ECSTaskPacketLossAction": fis.CfnExperimentTemplate.ExperimentTemplateActionProperty(
                action_id="aws:ecs:inject-network-packet-loss",
                description=f"Inject {loss_percent}% packet loss in ECS tasks for {ecs_app_name}",
                parameters={
                    "lossPercent": str(loss_percent),
                    "duration": duration,
                    "installDependencies": "true",
                    "useEcsFaultInjectionEndpoints": "true"
                },
                targets={
                    "Tasks": "ECSTaskPacketLoss"
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
            "Name": f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-ecs-taskpacketloss-{ecs_app_name}-p{percent}-experiment-{config['resource_suffix']}",
            "Environment": f"{config['app_env']}"
        }
    )
    return experiment_template
