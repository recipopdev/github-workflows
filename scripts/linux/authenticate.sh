ACCOUNT_ID=$(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq $1 --raw-output)
CREDS=$(aws sts assume-role --role-arn "arn:aws:iam::"$ACCOUNT_ID":role/CI" --role-session-name retrieve-ecr-token)
export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq .Credentials.AccessKeyId --raw-output)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq .Credentials.SecretAccessKey --raw-output)
export AWS_SESSION_TOKEN=$(echo $CREDS | jq .Credentials.SessionToken --raw-output)
export DOCKER_PASSWORD=$(aws ecr get-login-password)
echo 'docker_password = "'$DOCKER_PASSWORD'"' > terraform.tfvars