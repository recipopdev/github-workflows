get_service_version() {
    ACCOUNT_ID=$(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq .management_account --raw-output)
    CREDS=$(aws sts assume-role --role-arn "arn:aws:iam::"$ACCOUNT_ID":role/CI" --role-session-name retrieve-ecr-token)
    export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq .Credentials.AccessKeyId --raw-output)
    export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq .Credentials.SecretAccessKey --raw-output)
    export AWS_SESSION_TOKEN=$(echo $CREDS | jq .Credentials.SessionToken --raw-output)
    if [ ! -f ../package.json ]; then
        jq --null-input --arg name "$1-deployment" --arg version "$(aws ssm get-parameter --name "/ecs/versions/$1" | jq .Parameter.Value --raw-output)" '{"name": $name, "version": $version}' > "package.json"
    else
        cat ../package.json | jq --arg version "$(aws ssm get-parameter --name "/ecs/versions/$1" | jq .Parameter.Value --raw-output)" > "package.json"
    fi
    
}

set_service_version() {
    ACCOUNT_ID=$(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq .management_account --raw-output)
    CREDS=$(aws sts assume-role --role-arn "arn:aws:iam::"$ACCOUNT_ID":role/CI" --role-session-name retrieve-ecr-token)
    export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq .Credentials.AccessKeyId --raw-output)
    export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq .Credentials.SecretAccessKey --raw-output)
    export AWS_SESSION_TOKEN=$(echo $CREDS | jq .Credentials.SessionToken --raw-output)
    aws ssm put-parameter --name "/ecs/versions/$1" --value "$(cat package.json | jq .version --raw-output)" --overwrite
}

"$@"