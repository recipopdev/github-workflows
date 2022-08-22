#!/bin/bash
set -e

IMAGE_REPOSITORY=$(terraform output -json | jq .image_repository.value --raw-output)
IMAGE_DIGEST=$(terraform output -json | jq .image_digest.value --raw-output)

ACCOUNT_ID=$(aws secretsmanager get-secret-value --secret-id /adimo/terraform --query SecretString --output text | jq $1 --raw-output)
CREDS=$(aws sts assume-role --role-arn "arn:aws:iam::"$ACCOUNT_ID":role/CI" --role-session-name retrieve-ecr-token)
export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq .Credentials.AccessKeyId --raw-output)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq .Credentials.SecretAccessKey --raw-output)
export AWS_SESSION_TOKEN=$(echo $CREDS | jq .Credentials.SessionToken --raw-output)

echo "[+] Starting image scan"

aws ecr start-image-scan --repository-name $IMAGE_REPOSITORY --image-id imageDigest=$IMAGE_DIGEST 2>/dev/null || echo "[-] Error running image scan, likely has already been analysed"

SCAN_STATUS=$(aws ecr describe-image-scan-findings --repository-name $IMAGE_REPOSITORY --image-id imageDigest=$IMAGE_DIGEST | jq .imageScanStatus.status --raw-output)

declare -i i=0

while [[ $SCAN_STATUS != "COMPLETE" ]]
do
    echo "[+] Polling image scan status: $SCAN_STATUS"
    if [[ "$i" == '12' ]]; then
        break
    fi
    i+=1
    sleep 5
    SCAN_STATUS=$(aws ecr describe-image-scan-findings --repository-name $IMAGE_REPOSITORY --image-id imageDigest=$IMAGE_DIGEST | jq .imageScanStatus.status --raw-output)
done

aws ecr describe-image-scan-findings --repository-name $IMAGE_REPOSITORY --image-id imageDigest=$IMAGE_DIGEST | jq .imageScanFindings.findings