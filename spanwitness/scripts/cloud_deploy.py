"""Deploy through the owner's existing CloudShell session. Never print credentials."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess

import boto3
from botocore.exceptions import ClientError, WaiterError
import docker
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
RECEIPT = WORKSPACE / "deployment-receipt.json"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    if suffix == "GetAtt" and isinstance(value, str):
        value = value.split(".", 1)
    return {suffix if suffix == "Ref" else f"Fn::{suffix}": value}


CloudFormationLoader.add_multi_constructor("!", intrinsic)


def save(receipt):
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")


def prepare(session, args, account):
    if not 0 < args.approved_budget <= 5:
        raise ValueError("This deployment requires the owner's approved budget, at most $5.")
    manifest = WORKSPACE / "SOURCE_MANIFEST.json"
    source_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    tag = f"source-{source_digest[:16]}"
    repository_name = args.stack
    ecr = session.client("ecr")
    try:
        repository = ecr.describe_repositories(repositoryNames=[repository_name])["repositories"][0]
    except ecr.exceptions.RepositoryNotFoundException:
        repository = ecr.create_repository(repositoryName=repository_name, imageTagMutability="IMMUTABLE",
                                             encryptionConfiguration={"encryptionType": "AES256"},
                                             tags=[{"Key": "Application", "Value": "SpanWitness"}])["repository"]
    function_arn = f"arn:aws:lambda:{args.region}:{account}:function:{args.stack}-inspection"
    ecr.set_repository_policy(repositoryName=repository_name, policyText=json.dumps({
        "Version": "2012-10-17", "Statement": [{"Sid": "SpanWitnessLambdaPull", "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"}, "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
            "Condition": {"ArnLike": {"aws:SourceArn": function_arn}}}]}))
    uri = repository["repositoryUri"]
    try:
        digest = ecr.describe_images(repositoryName=repository_name, imageIds=[{"imageTag": tag}])["imageDetails"][0]["imageDigest"]
        print(json.dumps({"image": "already_uploaded", "tag": tag}), flush=True)
    except ecr.exceptions.ImageNotFoundException:
        local_tag = "spanwitness:deploy"
        subprocess.run(["docker", "build", "--platform", "linux/amd64", "-f", str(ROOT / "Dockerfile"),
                        "-t", local_tag, str(WORKSPACE)], check=True)
        client = docker.from_env()
        client.images.get(local_tag).tag(uri, tag=tag)
        auth = ecr.get_authorization_token()["authorizationData"][0]
        username, password = base64.b64decode(auth["authorizationToken"]).decode().split(":", 1)
        # SDK auth_config stays in memory. No docker-login credential file is created.
        for update in client.images.push(uri, tag=tag, auth_config={"username": username, "password": password,
                                                                   "serveraddress": auth["proxyEndpoint"]}, stream=True, decode=True):
            if update.get("error"):
                raise RuntimeError(update["error"])
            if update.get("status") in {"Pushed", "Layer already exists"}:
                print(json.dumps({"image_layer": update.get("id"), "status": update["status"]}), flush=True)
        client.close()
        digest = ecr.describe_images(repositoryName=repository_name, imageIds=[{"imageTag": tag}])["imageDetails"][0]["imageDigest"]
    secret_name = f"/spanwitness/{args.stack}/preview-access"
    ssm = session.client("ssm")
    try:
        preview_code = ssm.get_parameter(Name=secret_name, WithDecryption=True)["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        preview_code = secrets.token_urlsafe(24)
        ssm.put_parameter(Name=secret_name, Value=preview_code, Type="SecureString",
                          Description="SpanWitness private preview access code. Username: judge.",
                          Tags=[{"Key": "Application", "Value": "SpanWitness"}])
    template = yaml.load((ROOT / "template.yaml").read_text(), Loader=CloudFormationLoader)
    function = template["Resources"]["InspectionFunction"]
    function.pop("Metadata", None)
    function["Properties"]["ImageUri"] = f"{uri}@{digest}"
    cloudformation = session.client("cloudformation")
    try:
        stack = cloudformation.describe_stacks(StackName=args.stack)["Stacks"][0]
        change_type = "UPDATE"
        if stack["StackStatus"].endswith("IN_PROGRESS"):
            raise RuntimeError(f"Stack currently {stack['StackStatus']}; do not start a second deployment.")
    except ClientError as error:
        if "does not exist" not in error.response["Error"].get("Message", ""):
            raise
        change_type = "CREATE"
    name = f"preview-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{source_digest[:8]}"
    change = cloudformation.create_change_set(StackName=args.stack, ChangeSetName=name, ChangeSetType=change_type,
        TemplateBody=json.dumps(template), Capabilities=["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"],
        Parameters=[{"ParameterKey": "PreviewAccessCode", "ParameterValue": preview_code}],
        Tags=[{"Key": "Application", "Value": "SpanWitness"}])
    receipt = {"stack_name": args.stack, "region": args.region, "account_suffix": account[-4:],
               "source_manifest_sha256": source_digest, "image_uri": f"{uri}@{digest}", "change_set_id": change["Id"],
               "preview_access_parameter": secret_name, "approved_budget_usd": args.approved_budget,
               "status": "change_set_preparing", "prepared_at": datetime.now(timezone.utc).isoformat()}
    save(receipt)
    cloudformation.get_waiter("change_set_create_complete").wait(StackName=args.stack, ChangeSetName=change["Id"],
                                                                WaiterConfig={"Delay": 5, "MaxAttempts": 60})
    details = cloudformation.describe_change_set(StackName=args.stack, ChangeSetName=change["Id"])
    receipt.update(status="change_set_ready", changes=[{"action": c["ResourceChange"]["Action"],
        "logical_id": c["ResourceChange"]["LogicalResourceId"], "type": c["ResourceChange"]["ResourceType"],
        "replacement": c["ResourceChange"].get("Replacement")} for c in details["Changes"]])
    save(receipt)
    print(json.dumps(receipt), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "execute", "status"])
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--stack", default="spanwitness-demo")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--approved-budget", type=float, default=0)
    args = parser.parse_args()
    session = boto3.Session(region_name=args.region)
    account = session.client("sts").get_caller_identity()["Account"]
    if account != args.expected_account:
        raise RuntimeError("Signed-in account does not match the owner's selected account. No changes made.")
    if args.action == "prepare":
        prepare(session, args, account)
        return
    cloudformation = session.client("cloudformation")
    receipt = json.loads(RECEIPT.read_text())
    if args.action == "execute":
        if receipt["status"] != "change_set_ready":
            raise RuntimeError("A reviewed, prepared change set is required.")
        cloudformation.execute_change_set(StackName=args.stack, ChangeSetName=receipt["change_set_id"])
        receipt["status"] = "deployment_started"
        save(receipt)
        print(json.dumps({"status": "deployment_started", "stack": args.stack}), flush=True)
    else:
        stack = cloudformation.describe_stacks(StackName=args.stack)["Stacks"][0]
        receipt["status"] = stack["StackStatus"]
        receipt["outputs"] = {value["OutputKey"]: value["OutputValue"] for value in stack.get("Outputs", [])}
        events = cloudformation.describe_stack_events(StackName=args.stack)["StackEvents"][:12]
        receipt["recent_events"] = [{"resource": e["LogicalResourceId"], "status": e["ResourceStatus"],
                                     "reason": e.get("ResourceStatusReason", "")} for e in events]
        save(receipt)
        print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
