class Config:
    # Stack name
    # Change this value if you want to create a new instance of the stack
    STACK_NAME = "InvestmentAnalystStack"
    
    # Put your own custom value here to prevent ALB to accept requests from
    # other clients that CloudFront. You can choose any random string.
    CUSTOM_HEADER_VALUE = "InvestmentAnalystAssistantDemo_58dsv15e4s31_int"    
    
    # ID of Secrets Manager containing cognito parameters
    # When you delete a secret, you cannot create another one immediately
    # with the same name. Change this value if you destroy your stack and need
    # to recreate it with the same STACK_NAME.
    SECRETS_MANAGER_ID = f"{STACK_NAME}ParamCognitoSecret12345Demo"
    
    BEDROCK_REGION = "us-east-1"
    
    #LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    LLM_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    #DB_SECRET_NAME = f"{STACK_NAME}RDSAuroraSecret12345Demo"
    DB_SECRET_NAME = "amazon-bedrock-kb-rds-vectordb_1"

    EMBEDDINGS_MODEL_ID = "amazon.titan-embed-text-v1"
    
    # Replace with your actual agent details
    AGENT_ID = 'ZG9PABAUXSP'
    AGENT_ALIAS_ID = 'QXZ5OA0GPH'

    # Knowledge base ID
    KB_ID = "XFG61CFOTV"
