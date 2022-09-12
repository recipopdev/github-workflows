import boto3
from deployment_utilities import *
from packaging import version
import logging
import os.path
import argparse
import json
import shutil

def retrieve_service_version(service: str):
  credentials = switch_role(account="management", session_name="IterateVersionSession")
  ssm = get_aws_client("ssm", credentials)
  parameter_path = "/ecs/versions/" + service
  return ssm.get_parameter(Name=parameter_path)["Parameter"]["Value"]

def fetch(service: str, directory: str):
  logging.info("Fetching the version in parameter store for service: " + service)
  if (os.path.isfile("../package.json")):
    logging.info("package.json already exists in the root directory of this repository, using it instead of creating")
    with open("../package.json", "r+") as file:
      package = json.load(file)
      package["version"] = retrieve_service_version(service=service)
      file.seek(0)
      json.dump(package, file, indent=2)
    shutil.copy("../package.json", "package.json")
    logging.info("Successfuly updated package.json")
  else:
    with open((directory + "package.json"), "w") as file:
      package = {}
      package["name"] = service
      package["version"] = retrieve_service_version(service=service)
      json.dump(package, file, indent=2)
    logging.info("Successfuly created package.json")

def save(service: str, directory: str):
  logging.info("Attempting to save the version in parameter store for service: " + service)
  with open((directory + "package.json"), "r") as file:
    local_version = json.load(file)["version"]
    remote_version = retrieve_service_version(service=service)
    if (version.parse(local_version) < version.parse(remote_version)):
      logging.warning("Another pipeline is likely running in a higher environment simultaneously, please try not to do this")
      logging.warning("Skipping version update")
    else:
      credentials = switch_role(account="management", session_name="IterateVersionSession")
      ssm = get_aws_client("ssm", credentials)
      parameter_path = "/ecs/versions/" + service
      ssm.put_parameter(Name=parameter_path, Value=local_version, Overwrite=True)
      logging.info("Successfuly updated version of service: " + service + " from [" + remote_version + "] to [" + local_version + "]")

def main():
  parser = argparse.ArgumentParser(description="AWS ECS Service Versioning Script")

  parser.add_argument("--service", type=str, required=True, help="The name of the service we are interacting with")
  parser.add_argument("--fetch", action="store_true", help="Fetches the version of the service from AWS Parameter Store and store it in package.json format")
  parser.add_argument("--save", action="store_true", help="Saves the version of the service in AWS Parameter Store.")
  parser.add_argument("--directory", nargs='?', const="./", type=str, help="The directory to find package.json in.")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  if (args.fetch):
    fetch(service=args.service, directory=args.directory)
  elif (args.save):
    save(service=args.service, directory=args.directory)
  else:
    print("Error: please use one of either --fetch or --save")

if __name__ == "__main__":
  main()
