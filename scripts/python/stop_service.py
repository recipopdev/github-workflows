import boto3
from deployment_utilities import *
import logging
import argparse
import time

def main():
  parser = argparse.ArgumentParser(description="AWS ECS Stop Service Script")

  parser.add_argument("--service", type=str, required=True, help="The name of the service we are stopping")
  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are stopping")
  parser.add_argument("--cluster", nargs='?', default="core-services", type=str, help="The name of the environment we are stopping")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  credentials = switch_role(account=args.environment, session_name="StopServiceSession")
  ecs = get_aws_client("ecs", credentials)

  logging.info("Stopping service: " + args.service)
  ecs.update_service(cluster=args.cluster, service=args.service, desiredCount=0)

  logging.info("Service successfully stopped, sleeping for 60 seconds...")

  time.sleep(60)  

if __name__ == "__main__":
  main()