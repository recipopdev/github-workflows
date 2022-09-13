from prometheus_client import Gauge, CollectorRegistry, push_to_gateway
from deployment_utilities import *
import logging
import argparse

registry = CollectorRegistry()
g = Gauge("pipeline_status", "The status of a pipeline", ["environment"], registry=registry)
push_gateway_url = "https://push.mgmt.adimo.co"

def success(service: str, environment: str):
  g.labels(environment=environment).set(1)
  push_to_gateway(push_gateway_url, job=service, registry=registry, handler=push_gateway_handler)

def failure(service: str, environment: str):
  g.labels(environment=environment).set(0)
  push_to_gateway(push_gateway_url, job=service, registry=registry, handler=push_gateway_handler)

def running(service: str, environment: str):
  g.labels(environment=environment).set(2)
  push_to_gateway(push_gateway_url, job=service, registry=registry, handler=push_gateway_handler)

def main():
  parser = argparse.ArgumentParser(description="Pipeline Reporting Script")

  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are interacting with")
  parser.add_argument("--service", type=str, required=True, help="The name of the service we are interacting with")
  parser.add_argument("--success", action="store_true", help="Indicates a successfull pipeline run")
  parser.add_argument("--failure", action="store_true", help="Indicates a failing pipeline run")
  parser.add_argument("--running", action="store_true", help="Indicates a running pipeline")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  if (args.success):
    success(service=args.service, environment=args.environment)
  elif (args.failure):
    failure(service=args.service, environment=args.environment)
  elif (args.running):
    running(service=args.service, environment=args.environment)
  else:
    print("Error: please use one of either --success or --failure or --running")
    exit(1)

if __name__ == "__main__":
  main()