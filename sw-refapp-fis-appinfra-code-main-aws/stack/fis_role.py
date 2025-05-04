from aws_cdk import aws_iam as iam

def create_fis_role_body(self, config):
    exec_role = iam.Role(
        self,
        id=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-exec-role-{config['deployment_region']}-{config['resource_suffix']}",
        assumed_by=iam.ServicePrincipal('fis.amazonaws.com'),
        role_name=f"{config['resource_prefix']}-{config['service_name']}-{config['app_env']}-{config['app_name']}-exec-role-{config['deployment_region']}-{config['resource_suffix']}"
    )

    exec_role.add_to_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "fis:*"
            ],
            resources=[
                f"arn:aws:fis:*:{config['workload_account']}:experiment-template/*",
                f"arn:aws:fis:*:{config['workload_account']}:safety-lever/*",
                f"arn:aws:fis:*:{config['workload_account']}:action/*",
                f"arn:aws:fis:*:{config['workload_account']}:experiment/*"
            ]
        )
    )

    exec_role.add_to_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "fis:ListExperimentTemplates",
                "fis:ListActions",
                "fis:ListTargetResourceTypes",
                "fis:ListExperiments",
                "fis:GetTargetResourceType"
            ],
            resources=["*"]
        )
    )

    exec_role.add_to_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["logs:CreateLogStream", "logs:PutLogEvents", "logs:CreateLogGroup"],
            resources=[f"arn:aws:logs:*:*:log-group:/sw/fis/*:*"]
        )
    )

    exec_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSFaultInjectionSimulatorECSAccess")
    )
    exec_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSFaultInjectionSimulatorSSMAccess")
    )
    exec_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElastiCacheFullAccess")
    )
    exec_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
    )
    exec_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess")
    )

    return exec_role
