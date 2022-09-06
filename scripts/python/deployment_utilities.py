import boto3
import json

def switch_role(account: str, session_name: str):
  sts_client = boto3.client("sts")
  role_arn = "arn:aws:iam::" + fetch_account_number(account) + ":role/CI"
  role_session_name = session_name
  return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)["Credentials"]

def fetch_account_number(account: str):
  sm_client = boto3.client("secretsmanager")
  adimo_config = sm_client.get_secret_value(SecretId="/adimo/terraform")
  adimo_config_json = json.loads(adimo_config["SecretString"])
  return adimo_config_json[(account + "_account")]

def get_aws_client(aws_service: str, credentials: dict):
  return boto3.client(
    aws_service,
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['SessionToken'],
  )