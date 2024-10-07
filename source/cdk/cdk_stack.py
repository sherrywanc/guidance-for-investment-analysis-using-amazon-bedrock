from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_secretsmanager as secretsmanager,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    SecretValue,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_ssm as ssm,
    aws_lambda as _lambda,
)
from constructs import Construct
from docker_app.config_file import Config
import os

CUSTOM_HEADER_NAME = "X-Custom-Header"

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
       
        # Define prefix that will be used in some resource names
        prefix = Config.STACK_NAME
        
        # Create Cognito user pool
        user_pool = cognito.UserPool(self, f"{prefix}UserPool")

        # Create Cognito client
        user_pool_client = cognito.UserPoolClient(self, f"{prefix}UserPoolClient",
                                                  user_pool=user_pool,
                                                  generate_secret=True
                                                  )

        # Store Cognito parameters in a Secrets Manager secret
        secret = secretsmanager.Secret(self, f"{prefix}ParamCognitoSecret",
                                       secret_object_value={
                                           "pool_id": SecretValue.unsafe_plain_text(user_pool.user_pool_id),
                                           "app_client_id": SecretValue.unsafe_plain_text(user_pool_client.user_pool_client_id),
                                           "app_client_secret": user_pool_client.user_pool_client_secret
                                       },
                                       secret_name=Config.SECRETS_MANAGER_ID
                                       )

        # create parameters for storing agentid in parameter store
        agent_id_parameter = ssm.StringParameter(
            self,
            "AgentIDParameter",
            parameter_name="/InvestmentAnalystAssistant/agent_id",
            string_value=Config.AGENT_ID
        )
        
        # create parameters for storing agent aliasid in parameter store
        agent_alias_parameter = ssm.StringParameter(
            self,
            "AgentAliasIDParameter",
            parameter_name="/InvestmentAnalystAssistant/agent_alias_id",
            string_value=Config.AGENT_ALIAS_ID
        )
  
        # VPC for ALB and ECS cluster
        vpc = ec2.Vpc(
            self,
            f"{prefix}AppVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            vpc_name=f"{prefix}-stl-vpc",
            nat_gateways=1,
        )

        ecs_security_group = ec2.SecurityGroup(
            self,
            f"{prefix}SecurityGroupECS",
            vpc=vpc,
            security_group_name=f"{prefix}-stl-ecs-sg",
        )

        alb_security_group = ec2.SecurityGroup(
            self,
            f"{prefix}SecurityGroupALB",
            vpc=vpc,
            security_group_name=f"{prefix}-stl-alb-sg",
        )

        ecs_security_group.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(8501),
            description="ALB traffic",
        )

        # ECS cluster and service definition
        cluster = ecs.Cluster(
            self,
            f"{prefix}Cluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc)

        # ALB to connect to ECS
        alb = elbv2.ApplicationLoadBalancer(
            self,
            f"{prefix}Alb",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name=f"{prefix}-stl",
            security_group=alb_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        fargate_task_definition = ecs.FargateTaskDefinition(
            self,
            f"{prefix}WebappTaskDef",
            memory_limit_mib=512,
            cpu=256,
        )

        # Build Dockerfile from local folder and push to ECR
        image = ecs.ContainerImage.from_asset('docker_app')

        fargate_task_definition.add_container(
            f"{prefix}WebContainer",
            image=image,
            port_mappings=[
                ecs.PortMapping(
                    container_port=8501,
                    protocol=ecs.Protocol.TCP)],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="WebContainerLogs"),
        )

        service = ecs.FargateService(
            self,
            f"{prefix}ECSService",
            cluster=cluster,
            task_definition=fargate_task_definition,
            service_name=f"{prefix}-stl-front",
            security_groups=[ecs_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # Grant access to Bedrock
        bedrock_policy = iam.Policy(self, f"{prefix}BedrockPolicy",
                                    statements=[
                                        iam.PolicyStatement(
                                            actions=["bedrock:InvokeModel*", "secretsmanager:GetSecretValue", "bedrock:InvokeAgent*", "ssm:GetParameter" ],
                                            resources=["*"]
                                        )
                                    ]
                                    )
        task_role = fargate_task_definition.task_role
        task_role.attach_inline_policy(bedrock_policy)

        # Grant access to read the secret in Secrets Manager
        secret.grant_read(task_role)

        # Add ALB as CloudFront Origin
        origin = origins.LoadBalancerV2Origin(
            alb,
            custom_headers={CUSTOM_HEADER_NAME: Config.CUSTOM_HEADER_VALUE},
            origin_shield_enabled=False,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        cloudfront_distribution = cloudfront.Distribution(
            self,
            f"{prefix}CfDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        # ALB Listener
        http_listener = alb.add_listener(
            f"{prefix}HttpListener",
            port=80,
            open=True,
        )

        http_listener.add_targets(
            f"{prefix}TargetGroup",
            target_group_name=f"{prefix}-tg",
            port=8501,
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    CUSTOM_HEADER_NAME,
                    [Config.CUSTOM_HEADER_VALUE])],
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
        )

        # Add a default action to the listener that will deny all requests that do not have the custom header
        http_listener.add_action(
            "default-action",
            action=elbv2.ListenerAction.fixed_response(
                status_code=403,
                content_type="text/plain",
                message_body="Access denied",
            ),
        )

        # Create Aurora PostgreSQL Serverless Database Cluster
        db_security_group = ec2.SecurityGroup(
            self,
            f"{prefix}SecurityGroupDB",
            vpc=vpc,
            security_group_name=f"{prefix}-db-sg",
        )

        # Allow ECS tasks to connect to the database
        db_security_group.add_ingress_rule(
            peer=ecs_security_group,
            connection=ec2.Port.tcp(5432),  # PostgreSQL port
            description="Allow ECS access to RDS",
        )
        
        secret_name = Config.DB_SECRET_NAME
        
        db_cluster = rds.DatabaseCluster(
            self,
            f"{prefix}AuroraDBCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_15_3),  # Use version 15.4
            security_groups=[db_security_group],
            default_database_name=f"{prefix}Database",
            credentials=rds.Credentials.from_generated_secret(
                username="postgres",
                secret_name=secret_name  # Optionally specify the secret name here
            ),
            writer=rds.ClusterInstance.serverless_v2("ServerlessInstanceWriter"), 
            parameter_group=rds.ParameterGroup.from_parameter_group_name(self, "ParameterGroup", "default.aurora-postgresql15"),
            preferred_maintenance_window="mon:09:39-mon:10:09",
            enable_data_api=True,  # Enable RDS Data API
            removal_policy=RemovalPolicy.DESTROY,  # NOT recommended for production
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Use isolated subnets for better security
            )
        )

        # Create the Lambda execution role
        lambda_role = iam.Role(self, 'LambdaExecutionRole',
                               assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
                               managed_policies=[
                                   iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
                               ])
                               
        # Define the Lambda function
        my_function = _lambda.Function(self, 'MarketNewsSentimentData',
                                       runtime=_lambda.Runtime.PYTHON_3_10,
                                       handler='main.lambda_handler',
                                       code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), '../lambda')),
                                       environment={
                                           'API_KEY': 'Alpha Vantage Key',
                                           'NEWS_TOPICS': 'earnings',
                                           'NEWS_LIMIT': '10'
                                       },
                                       timeout=Duration.seconds(600),
                                       role=lambda_role)
        
        # Add resource-based policy to allow bedrock.amazonaws.com to invoke the Lambda function
        my_function.add_permission("AllowBedrockInvoke",
                                   principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
                                   action="lambda:InvokeFunction")
                                   
                
        # Output CloudFront URL
        CfnOutput(self, "CloudFrontDistributionURL",
                  value=cloudfront_distribution.domain_name)
        # Output Cognito pool id
        CfnOutput(self, "CognitoPoolId",
                  value=user_pool.user_pool_id)
        # Output RDS Cluster endpoint
        CfnOutput(self, "RDSClusterEndpoint",
                  value=db_cluster.cluster_endpoint.hostname)
        # Output Data API Endpoint
        CfnOutput(self, "RDSClusterDataApiEndpoint",
                  value=db_cluster.cluster_arn)
        # Add the SSM parameter value as a stack output using CfnOutput
        CfnOutput(
            self,
            "AgentId",
            value=agent_id_parameter.parameter_name,
            description="Agent ID",
            export_name="AgentID"
        )
        CfnOutput(
            self,
            "AgentAliasId",
            value=agent_alias_parameter.parameter_name,
            description="Agent Alias ID",
            export_name="AgentAliasID"
        )
