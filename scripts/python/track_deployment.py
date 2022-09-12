import boto3
from deployment_utilities import *
from datetime import datetime, timedelta
import logging
import argparse
import json
import time
import math

cluster="core-services"

def track_rollout(deployment_id: str, environment: str, service: str) -> bool:
  logging.info("Starting the tracking of service rollout")
  credentials = switch_role(account=environment, session_name="TrackDeploymentSession")
  ecs = get_aws_client("ecs", credentials)
  deployments = ecs.describe_services(cluster=cluster, services=[service])["services"][0]["deployments"]
  rollout_state = parse_deployment_state(deployments=deployments, deployment_id=deployment_id)
  running_count = parse_running_count(deployments=deployments, deployment_id=deployment_id)
  pending_count = parse_pending_count(deployments=deployments, deployment_id=deployment_id)
  failed_tasks = parse_failed_tasks(deployments=deployments, deployment_id=deployment_id)
  i = 0
  while ((rollout_state != "COMPLETED") or (running_count == 0) or (pending_count > 0)):
    logging.info("Polling service rollout state [" + str(math.floor((i*30)/60)) + "m" + str((i*30)%60) + "s]")
    logging.info("rollout_state(" + rollout_state + ") running_count(" + str(running_count) + ") pending_count(" + str(pending_count) + ") failed_tasks(" + str(failed_tasks) + ")")
    time.sleep(30)
    deployments = ecs.describe_services(cluster=cluster, services=[service])["services"][0]["deployments"]
    running_count = parse_running_count(deployments=deployments, deployment_id=deployment_id)
    rollout_state = parse_deployment_state(deployments=deployments, deployment_id=deployment_id)
    pending_count = parse_pending_count(deployments=deployments, deployment_id=deployment_id)
    if (rollout_state == "FAILED"):
      logging.error("Rollout failed, if possible a revert to the last healthy deployment will be attempted")
      return False
    failed_tasks = parse_failed_tasks(deployments=deployments, deployment_id=deployment_id)
    if (failed_tasks > 0):
      logging.error("Rollout failed due to a failed task, if possible a revert to the last healthy deployment will be attempted")
      return False
    if (i > 80):
      logging.error("Timed out waiting for rollout")
      exit(1)
    i = i + 1
  logging.info("Rollout completed successfully")
  return True

def revert_rollout(task_definition: str, environment: str, service: str):
  logging.warning("Reverting rollout to last healthy task definition")
  credentials = switch_role(account=environment, session_name="TrackDeploymentSession")
  ecs = get_aws_client("ecs", credentials)
  deployments = sort_deployments(ecs.update_service(cluster=cluster, service=service, taskDefinition=task_definition)["service"]["deployments"])
  deployment_id = deployments[0]["id"]
  if (track_rollout(deployment_id=deployment_id, environment=environment, service=service)):
    logging.warning("Revert completed successfully")
    exit(1)
  else:
    logging.error("Revert failed, please contact administrator")
    exit(1)


def sort_deployments(deployments: dict) -> dict:
  deployments.sort(key = lambda x:x["createdAt"], reverse=True)
  return deployments

def check_edge_cases(deployments: dict, environment: str, service: str) -> dict:
  if (len(deployments) == 1):
    if (deployments[0]["rolloutState"] == "COMPLETED"):
      if ((environment == "production")):
        logging.error("No deployment to environment: " + environment + " has been found to track for service: " + service)
        exit(1)
      elif (deployments[0]["desiredCount"] != 0):
        logging.error("No deployment to environment: " + environment + " has been found to track for service: " + service)
        exit(1)
  if (len(deployments) > 2):
    logging.warning("More than 1 deployment is currently being deployed at once, will track the most recent")
    logging.warning("Try not to run one more pipeline per environment at a time")

def parse_deployment_state(deployments: dict, deployment_id: str) -> str:
  for deployment in deployments:
    if (deployment["id"] == deployment_id):
      return deployment["rolloutState"]

def parse_failed_tasks(deployments: dict, deployment_id: str) -> int:
  for deployment in deployments:
    if (deployment["id"] == deployment_id):
      return deployment["failedTasks"]

def parse_running_count(deployments: dict, deployment_id: str) -> int:
  for deployment in deployments:
    if (deployment["id"] == deployment_id):
      return deployment["runningCount"]

def parse_pending_count(deployments: dict, deployment_id: str) -> int:
  for deployment in deployments:
    if (deployment["id"] == deployment_id):
      return deployment["pendingCount"]

def parse_service_state(events: dict, success: str) -> bool:
  if success in events[0]["message"]:
    return True
  else:
    return False


def main():
  parser = argparse.ArgumentParser(description="AWS ECS Track Deployment Script")

  parser.add_argument("--service", type=str, required=True, help="The name of the service we are interacting with")
  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are interacting with")
  parser.add_argument("--cluster", nargs='?', const="core-services", type=str, help="The name of the environment we are interacting with")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  global cluster
  cluster = args.cluster

  credentials = switch_role(account=args.environment, session_name="TrackDeploymentSession")
  ecs = get_aws_client("ecs", credentials)
  services = ecs.describe_services(cluster=cluster, services=[args.service])

  if (len(services["services"]) > 1):
    logging.error("More than one service was matched, please contact administrator")
    exit(1)
  
  deployments = sort_deployments(services["services"][0]["deployments"])
  check_edge_cases(deployments=deployments, environment=args.environment, service=args.service)

  healthy_task_definition = None
  if (deployments[-1]["rolloutState"] == "COMPLETED"):
    healthy_task_definition = deployments[-1]["taskDefinition"]
  else:
    logging.warning("No healthy rollout state to revert to in case of failure")

  if (args.environment != "production"):
    if (deployments[0]["desiredCount"] == 0):
      if (deployments[-1]["desiredCount"] == 0):
        logging.warning("Service is currently scaled down, will try to scale the most recent deployment up")
        deployments = sort_deployments(ecs.update_service(cluster=cluster, service=args.service, desiredCount=1)["service"]["deployments"])

  deployment_id = deployments[0]["id"]

  if (not track_rollout(deployment_id=deployment_id, environment=args.environment, service=args.service)):
    if (healthy_task_definition != None):
      revert_rollout(task_definition=healthy_task_definition, environment=args.environment, service=args.service)
    else:
      logging.error("No past healthy deployment to revert to")
      exit(1)

if __name__ == "__main__":
  main()