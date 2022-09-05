#!/bin/bash
set -e

track_running_count() {
    RUNNING_COUNT=$(echo $DEPLOYMENT_JSON | jq '.[0].runningCount' --raw-output)

    declare -i i=0

    while [[ $RUNNING_COUNT -eq 0 ]]
    do
        echo "[+] Polling scale up progress: IN_PROGRESS ($((($i*30)/60))m$((($i*30)%60))s)"
        if [[ $i -eq 40 ]]; then
            echo "[!] Scale up timeout"
            exit 1
        fi
        if [[ FAILED_TASKS -gt 0 ]]; then
            echo "[!] Task failed to start, backing out of deployment and exiting"
            aws ecs update-service --cluster core-services --service $1 --task-definition $OLD_TASK_DEFINITION >/dev/null
            exit 1
        fi
        i+=1
        sleep 30
        DEPLOYMENT_JSON=$(aws ecs describe-services --cluster core-services --services $1 | jq '.services[0].deployments' --raw-output)
        RUNNING_COUNT=$(echo $DEPLOYMENT_JSON | jq '.[0].runningCount' --raw-output)
        FAILED_TASKS=$(echo $DEPLOYMENT_JSON | jq '.[0].failedTasks' --raw-output)
    done

    echo "[+] Task scaled up, waiting for steady state"

    EVENTS_JSON=$(aws ecs describe-services --cluster core-services --services $1 | jq '.services[0].events' --raw-output)
    LATEST_MESSAGE=$(echo $EVENTS_JSON | jq '.[0].message')

    i=0

    while [[ $LATEST_MESSAGE != *"has reached a steady state"* ]]
    do
        echo "[+] Polling task state: IN_PROGRESS ($((($i*30)/60))m$((($i*30)%60))s)"
        if [[ $i -eq 40 ]]; then
            echo "[!] Timed out waiting for steady state"
            exit 1
        fi
        if [[ FAILED_TASKS -gt 0 ]]; then
            echo "[!] Task failed to start, backing out of deployment and exiting"
            aws ecs update-service --cluster core-services --service $1 --task-definition $OLD_TASK_DEFINITION >/dev/null
            exit 1
        fi
        i+=1
        sleep 30
        DEPLOYMENT_JSON=$(aws ecs describe-services --cluster core-services --services $1 | jq '.services[0].deployments' --raw-output)
        EVENTS_JSON=$(aws ecs describe-services --cluster core-services --services $1 | jq '.services[0].events' --raw-output)
        LATEST_MESSAGE=$(echo $EVENTS_JSON | jq '.[0].message')
        FAILED_TASKS=$(echo $DEPLOYMENT_JSON | jq '.[0].failedTasks' --raw-output)
    done

    echo "[+] Scale up completed after $((($i*30)/60))m$((($i*30)%60))s"
}

track_rollout_status() {
    ROLLOUT_STATUS=$(echo $DEPLOYMENT_JSON | jq '.[0].rolloutState' --raw-output)

    declare -i i=0

    while [[ $ROLLOUT_STATUS != "COMPLETED" ]]
    do
        echo "[+] Polling rollout status: $ROLLOUT_STATUS ($((($i*30)/60))m$((($i*30)%60))s)"
        if [[ $i -eq 40 ]]; then
            echo "[!] Rollout timeout"
            exit 1
        fi
        if [[ $ROLLOUT_STATUS == "FAILED" ]]; then
            echo "[!] Rollout failed"
            exit 1
        fi
        if [[ FAILED_TASKS -gt 0 ]]; then
            echo "[!] Task failed to start, backing out of deployment and exiting"
            aws ecs update-service --cluster core-services --service $1 --task-definition $OLD_TASK_DEFINITION >/dev/null
            exit 1
        fi
        i+=1
        sleep 30
        DEPLOYMENT_JSON=$(aws ecs describe-services --cluster core-services --services $1 | jq '.services[0].deployments' --raw-output)
        ROLLOUT_STATUS=$(echo $DEPLOYMENT_JSON | jq '.[0].rolloutState' --raw-output)
        FAILED_TASKS=$(echo $DEPLOYMENT_JSON | jq '.[0].failedTasks' --raw-output)
    done

    echo "[+] Rollout completed after $((($i*30)/60))m$((($i*30)%60))s"
}

ACCOUNT_ID=$(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq $1 --raw-output)
CREDS=$(aws sts assume-role --role-arn "arn:aws:iam::"$ACCOUNT_ID":role/CI" --role-session-name retrieve-ecr-token)
export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq .Credentials.AccessKeyId --raw-output)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq .Credentials.SecretAccessKey --raw-output)
export AWS_SESSION_TOKEN=$(echo $CREDS | jq .Credentials.SessionToken --raw-output)

echo "[+] Starting rollout polling"

DEPLOYMENT_JSON=$(aws ecs describe-services --cluster core-services --services $2 | jq '.services[0].deployments' --raw-output)
OLD_TASK_DEFINITION=$(echo $DEPLOYMENT_JSON | jq '.[1].taskDefinition' --raw-output)
DESIRED_COUNT=$(echo $DEPLOYMENT_JSON | jq '.[0].desiredCount' --raw-output)

ACCOUNT_ALIAS=$(aws iam list-account-aliases | jq .AccountAliases[0] --raw-output)

if [[ DESIRED_COUNT -eq 0 ]]; then
    if [[ $ACCOUNT_ALIAS == "adimo-aws-production" ]]; then
        echo "[!] Exiting for safety, please contact administrator"
        exit 1
    fi
    echo "[!] Scaling service up from 0 to 1"
    aws ecs update-service --cluster core-services --service $2 --desired-count 1 >/dev/null
    echo "[+] Tracking scale up"
    DEPLOYMENT_JSON=$(aws ecs describe-services --cluster core-services --services $2 | jq '.services[0].deployments' --raw-output)
    track_running_count $2
else
    track_rollout_status $2
fi
