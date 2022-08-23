param (
    [Parameter(Mandatory=$true)]
    [string]$account,

    [Parameter(Mandatory=$true)]
    [string]$service
)

$account_id=(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq $account --raw-output)
$creds=(aws sts assume-role --role-arn ("arn:aws:iam::" + $account_id + ":role/CI") --role-session-name retrieve-ecr-token)
$env:AWS_ACCESS_KEY_ID=($creds | jq .Credentials.AccessKeyId --raw-output)
$env:AWS_SECRET_ACCESS_KEY=($creds | jq .Credentials.SecretAccessKey --raw-output)
$env:AWS_SESSION_TOKEN=($creds | jq .Credentials.SessionToken --raw-output)

echo "[+] Starting rollout polling"

$deployment_json=$(aws ecs describe-services --cluster core-services --services $service | jq '.services[0].deployments' --raw-output)
$old_task_definition=$(echo $deployment_json | jq '.[1].taskDefinition' --raw-output)
$rollout_status=$(echo $deployment_json | jq '.[0].rolloutState' --raw-output)

$i=0

$timer = [Diagnostics.Stopwatch]::StartNew()

while ($rollout_status -ne "COMPLETED")
{
    $seconds = $timer.elapsed.totalseconds
    echo ("[+] Polling rollout status: " + $rollout_status + " (" + [math]::Floor($seconds/60) + "m" + [math]::Floor($seconds%60) + "s)")
    if ($i -eq 50)
    {
        echo "[!] Rollout timeout"
        exit 1
    }
    if ($rollout_status -eq "FAILED")
    {
        echo "[!] Rollout failed"
        exit 1
    }
    if ($failed_tasks -gt 0)
    {
        echo "[!] Task failed to start, backing out of deployment and exiting"
        aws ecs update-service --cluster core-services --service $service --task-definition $old_task_definition >$null
        exit 1
    }
    $i++
    Start-Sleep -Seconds 28.56
    $deployment_json=$(aws ecs describe-services --cluster core-services --services $service | jq '.services[0].deployments' --raw-output)
    $rollout_status=$(echo $deployment_json | jq '.[0].rolloutState' --raw-output)
    $failed_tasks=$(echo $deployment_json | jq '.[0].failedTasks' --raw-output)
}

$seconds = $timer.elapsed.totalseconds
$timer.Stop()

echo ("[+] Rollout completed after " + [math]::Floor($seconds/60) + "m " + [math]::Floor($seconds%60) + "s")