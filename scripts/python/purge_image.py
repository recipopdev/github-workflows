import boto3
from deployment_utilities import *
import logging
import argparse
import time

def main():
  parser = argparse.ArgumentParser(description="AWS ECR Purge Old Images Script")

  parser.add_argument("--service", type=str, required=True, help="The name of the service we are stopping")
  parser.add_argument("--environment", type=str, required=True, help="The name of the environment we are stopping")

  args = parser.parse_args()

  logging.getLogger().setLevel("INFO")

  credentials = switch_role(account=args.environment, session_name="PurgeImageSession")
  ecr = get_aws_client("ecr", credentials)

  logging.info("Purging images for: " + args.service)
  images = ecr.list_images(repositoryName=args.service, maxResults=1000)
  descriptions = ecr.describe_images(repositoryName=args.service, imageIds=images["imageIds"])["imageDetails"]
  descriptions.sort(key=extract_time, reverse=True)

  if (len(descriptions) <= 5):
    logging.info("No images need to be deleted")
    exit(0)
  
  old_image_descriptions = descriptions[5:]

  image_ids = []

  for description in old_image_descriptions:
    image_id = {}
    image_id["imageDigest"] = description["imageDigest"]
    image_id["imageTag"] = description["imageTags"][0]
    image_ids.append(image_id)

  response = ecr.batch_delete_image(repositoryName=args.service, imageIds=image_ids)

  if (len(response["failures"]) > 0):
    logging.error("Failed to delete (" + str(len(response["failures"])) + ") images")

  logging.info("Deleted (" + str(len(old_image_descriptions)) + ") old images")


def extract_time(descriptions):
  try:
    return descriptions["imagePushedAt"]
  except KeyError:
    return 0


if __name__ == "__main__":
  main()