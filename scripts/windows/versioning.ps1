function Get-ServiceVersion {
    param (
        [Parameter(Mandatory=$true)]
        [string]$service
    )

    $account_id=(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq .management_account --raw-output)
    $creds=(aws sts assume-role --role-arn ("arn:aws:iam::" + $account_id + ":role/CI") --role-session-name retrieve-ecr-token)
    $env:AWS_ACCESS_KEY_ID=($creds | jq .Credentials.AccessKeyId --raw-output)
    $env:AWS_SECRET_ACCESS_KEY=($creds | jq .Credentials.SecretAccessKey --raw-output)
    $env:AWS_SESSION_TOKEN=($creds | jq .Credentials.SessionToken --raw-output)
    jq --null-input --arg name ($service + "-deployment") --arg version "$(aws ssm get-parameter --name ("/ecs/versions/" + $service) | jq .Parameter.Value)" '{"name": $name, "version": $version}' | Out-File -FilePath ".\package.json"
}

function Set-ServiceVersion {
    param (
        [Parameter(Mandatory=$true)]
        [string]$service
    )

    $account_id=(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq .management_account --raw-output)
    $creds=(aws sts assume-role --role-arn ("arn:aws:iam::" + $account_id + ":role/CI") --role-session-name retrieve-ecr-token)
    $env:AWS_ACCESS_KEY_ID=($creds | jq .Credentials.AccessKeyId --raw-output)
    $env:AWS_SECRET_ACCESS_KEY=($creds | jq .Credentials.SecretAccessKey --raw-output)
    $env:AWS_SESSION_TOKEN=($creds | jq .Credentials.SessionToken --raw-output)
    aws ssm put-parameter --name ("/ecs/versions/" + $service) --value "$(Get-Content -Path ".\package.json" | jq .version --raw-output)" --overwrite
}

