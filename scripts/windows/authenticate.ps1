param (
    [Parameter(Mandatory=$true)]
    [string]$account
)

$account_id=(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq $account --raw-output)
$creds=(aws sts assume-role --role-arn ("arn:aws:iam::" + $account_id + ":role/CI") --role-session-name retrieve-ecr-token)
$env:AWS_ACCESS_KEY_ID=($creds | jq .Credentials.AccessKeyId --raw-output)
$env:AWS_SECRET_ACCESS_KEY=($creds | jq .Credentials.SecretAccessKey --raw-output)
$env:AWS_SESSION_TOKEN=($creds | jq .Credentials.SessionToken --raw-output)
$docker_password=("docker_password = `"" + (aws ecr get-login-password) + "`"")
$utf8_no_bom_encoding = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines("terraform.tfvars", $docker_password, $utf8_no_bom_encoding)