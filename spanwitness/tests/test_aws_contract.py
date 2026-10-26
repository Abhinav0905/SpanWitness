"""SDK contract tests with AWS responses stubbed. No account is contacted."""
import hashlib
from io import BytesIO
import json

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
import pytest

from spanwitness.aws_store import AWSStore


def s3_client():
    return boto3.client("s3", region_name="us-west-2", aws_access_key_id="testing", aws_secret_access_key="testing")


def test_s3_checks_the_saved_image_digest_before_analysis():
    client = s3_client()
    data = b"an altered stored image"
    with Stubber(client) as stub:
        stub.add_response("get_object", {"Body": StreamingBody(BytesIO(data), len(data)),
                                          "Metadata": {"sha256": hashlib.sha256(b"original").hexdigest()}},
                          {"Bucket": "example-evidence", "Key": "images/test.jpg"})
        store = AWSStore("example-evidence", "unused", s3=client, dynamodb=object())
        with pytest.raises(ValueError, match="integrity"):
            store.read_image("test.jpg")


def test_s3_roundtrip_contract_attaches_integrity_and_encryption():
    client = s3_client()
    data = b"jpeg fixture bytes"
    digest = hashlib.sha256(data).hexdigest()
    with Stubber(client) as stub:
        stub.add_response("put_object", {}, {"Bucket": "example-evidence", "Key": "images/test.jpg", "Body": data,
                                               "ContentType": "image/jpeg", "ServerSideEncryption": "AES256", "Metadata": {"sha256": digest}})
        stub.add_response("get_object", {"Body": StreamingBody(BytesIO(data), len(data)), "Metadata": {"sha256": digest}},
                          {"Bucket": "example-evidence", "Key": "images/test.jpg"})
        store = AWSStore("example-evidence", "unused", s3=client, dynamodb=object())
        store.write_image("test.jpg", data)
        assert store.read_image("test.jpg") == data
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("kind", ["observations", "comparisons"])
def test_dynamodb_records_survive_a_fresh_store_instance(kind):
    resource = boto3.resource("dynamodb", region_name="us-west-2", aws_access_key_id="testing", aws_secret_access_key="testing")
    table = resource.Table("example-records")
    record = {"id": "abc", "created_at": "2026-10-25T00:00:00Z", "report": {"physical_clearance": None}}
    payload = json.dumps(record)
    with Stubber(table.meta.client) as stub:
        stub.add_response("put_item", {}, {"TableName": "example-records", "Item": {
            "pk": f"{kind}#abc", "kind": kind, "created": "2026-10-25T00:00:00Z#abc", "payload": payload},
            "ConditionExpression": "attribute_not_exists(pk)"})
        stub.add_response("get_item", {"Item": {"pk": {"S": f"{kind}#abc"}, "payload": {"S": payload}}},
                          {"TableName": "example-records", "Key": {"pk": f"{kind}#abc"}, "ConsistentRead": True})
        AWSStore("unused", "unused", s3=object(), dynamodb=table).save(kind, record)
        assert AWSStore("unused", "unused", s3=object(), dynamodb=table).get(kind, "abc") == record
        stub.assert_no_pending_responses()
