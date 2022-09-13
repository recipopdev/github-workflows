import boto3
from deployment_utilities import *
from prometheus_client import Gauge, CollectorRegistry, push_to_gateway
import logging
import argparse
import base64
import time
import math

def image_scan(service:str, environment: str):
  credentials = switch_role(account=environment, session_name="IterateVersionSession")
  ecr = get_aws_client("ecr", credentials)
  logging.info("Retrieving latest image to scan")
  image_details = ecr.describe_images(repositoryName=service)["imageDetails"]
  image_details.sort(key = lambda x:x["imagePushedAt"], reverse=True)
  image_digest = image_details[0]["imageDigest"]
  if "imageScanStatus" in image_details[0]:
    if "status" in image_details[0]["imageScanStatus"]:
      if image_details[0]["imageScanStatus"]["status"] == "COMPLETE":
        logging.warning("Image scan already completed")
        exit(0)
      elif image_details[0]["imageScanStatus"]["status"] == "IN_PROGRESS":
        logging.warning("Image scan was already started")
      else:
        logging.error("Image scan status error")
        logging.error("Image scan status: (" + image_details[0]["imageScanStatus"]["status"] + ")")
        exit(1)

  imageId = {}
  imageId["imageDigest"] = image_digest
  result = ecr.start_image_scan(repositoryName=service, imageId=imageId)
  scan_status = retrieve_image_scan_status(ecr=ecr, service=service)
  i = 0
  while(scan_status != "COMPLETE"):
    logging.info("Polling image scan state [" + str(math.floor((i*5)/60)) + "m" + str((i*5)%60) + "s]")
    time.sleep(5)
    scan_status = retrieve_image_scan_status(ecr=ecr, service=service)
    if ((scan_status != "COMPLETE") and (scan_status != "IN_PROGRESS")):
      logging.error("Failure scanning image, reason: " + scan_status)
      exit(1)
    i = i + 1
  logging.info("Image scan complete, results are as follows")
  print_image_scan_findings(ecr=ecr, service=service, environment=environment)
  
def retrieve_image_scan_status(ecr:boto3.client, service:str) -> str:
  image_details = ecr.describe_images(repositoryName=service)["imageDetails"]
  image_details.sort(key = lambda x:x["imagePushedAt"], reverse=True)
  if "imageScanStatus" in image_details[0]:
    if "status" in image_details[0]["imageScanStatus"]:
      return image_details[0]["imageScanStatus"]["status"]
  return "ERROR"

def print_image_scan_findings(ecr:boto3.client, service:str, environment: str):
  image_details = ecr.describe_images(repositoryName=service)["imageDetails"]
  image_details.sort(key = lambda x:x["imagePushedAt"], reverse=True)
  if "imageScanFindingsSummary" in image_details[0]:
    if "findingSeverityCounts" in image_details[0]["imageScanFindingsSummary"]:
      print(image_details[0]["imageScanFindingsSummary"]["findingSeverityCounts"])
      push_results(service=service, environment=environment, results=image_details[0]["imageScanFindingsSummary"]["findingSeverityCounts"])

def push_results(service: str, environment: str, results: dict):
  for category in ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNDEFINED"]:
    registry = CollectorRegistry()
    g = Gauge(("image_scan_" + category.lower()), "The vulnerabilities contained in an image", ["instance"], registry=registry)
    g.labels(instance=environment).set(get_result(category=category, results=results))
    push_to_gateway(push_gateway_url, job=(service + "_" + environment), registry=registry, handler=push_gateway_handler)
  
  
def get_result(category: str, results: dict) -> int:
  if (category in results):
    return results[category]
  else:
    return 0


def main():
  parser = argparse.ArgumentParser(description="AWS ECR Authentication Script")

  parser.add_argument("--service", type=str, required=True, help="The name of the service we are interacting with")
  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are interacting with")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  image_scan(service=args.service, environment=args.environment)

if __name__ == "__main__":
  main()
