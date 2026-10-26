"""AWS persistence for the same inspection workflow used locally."""
from __future__ import annotations

import hashlib
import json

import boto3
from boto3.dynamodb.conditions import Key

from .store import Store


class AWSStore:
    backend = "aws_s3_dynamodb"

    def __init__(self, bucket: str, table: str, *, s3=None, dynamodb=None):
        self.bucket = bucket
        self.s3 = s3 if s3 is not None else boto3.client("s3")
        self.table = dynamodb if dynamodb is not None else boto3.resource("dynamodb").Table(table)

    def write_image(self, name: str, data: bytes):
        self.s3.put_object(Bucket=self.bucket, Key=f"images/{name}", Body=data,
                           ContentType="image/jpeg", ServerSideEncryption="AES256",
                           Metadata={"sha256": hashlib.sha256(data).hexdigest()})

    def read_image(self, name: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket, Key=f"images/{name}")
        body = response["Body"]
        try:
            data = body.read()
        finally:
            body.close()
        expected = response.get("Metadata", {}).get("sha256")
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Stored image integrity check failed.")
        return data

    def save(self, kind: str, record: dict):
        Store._table(kind)
        self.table.put_item(Item={"pk": f"{kind}#{record['id']}", "kind": kind,
                                  "created": f"{record['created_at']}#{record['id']}",
                                  "payload": json.dumps(record)},
                            ConditionExpression="attribute_not_exists(pk)")

    def get(self, kind: str, identifier: str) -> dict | None:
        Store._table(kind)
        item = self.table.get_item(Key={"pk": f"{kind}#{identifier}"}, ConsistentRead=True).get("Item")
        return json.loads(item["payload"]) if item else None

    def list(self, kind: str, limit: int = 100) -> list[dict]:
        Store._table(kind)
        response = self.table.query(IndexName="kind-created", KeyConditionExpression=Key("kind").eq(kind),
                                    ScanIndexForward=False, Limit=limit)
        return [json.loads(item["payload"]) for item in response.get("Items", [])]
