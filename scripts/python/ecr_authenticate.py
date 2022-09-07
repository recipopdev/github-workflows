import boto3
from deployment_utilities import *
import logging
import argparse
import base64

def create_tfvars(environment: str):
  credentials = switch_role(account=environment, session_name="IterateVersionSession")
  ecr = get_aws_client("ecr", credentials)
  auth_token = ecr.get_authorization_token(registryIds=[fetch_account_number(environment)])["authorizationData"][0]["authorizationToken"]
  with open("terraform.tfvars", "w") as file:
    file.write("docker_password = " + auth_token)  

def main():
  parser = argparse.ArgumentParser(description="AWS ECR Authentication Script")

  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are interacting with")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  create_tfvars(environment=args.environment)

if __name__ == "__main__":
  main()
