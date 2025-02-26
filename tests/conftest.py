import json
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_context():
    """Mock AWS Lambda context object."""
    context = MagicMock()
    context.log_stream_name = "test-log-stream"
    context.function_name = "test-function"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id"
    return context

@pytest.fixture
def create_event():
    """Generate a CloudFormation Create event."""
    return {
        "RequestType": "Create",
        "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/response",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/test-stack-id",
        "RequestId": "test-request-id",
        "ResourceType": "Custom::ListenerRuleAllocation",
        "LogicalResourceId": "ListenerRuleAllocation",
        "ResourceProperties": {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-lb/test-lb-id/test-listener-id",
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        }
    }

@pytest.fixture
def create_event_with_count():
    """Generate a CloudFormation Create event with PriorityCount."""
    return {
        "RequestType": "Create",
        "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/response",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/test-stack-id",
        "RequestId": "test-request-id",
        "ResourceType": "Custom::ListenerRuleAllocation",
        "LogicalResourceId": "ListenerRuleAllocation",
        "ResourceProperties": {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-lb/test-lb-id/test-listener-id",
            "PriorityCount": "2",
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        }
    }

@pytest.fixture
def update_event():
    """Generate a CloudFormation Update event."""
    return {
        "RequestType": "Update",
        "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/response",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/test-stack-id",
        "RequestId": "test-request-id",
        "PhysicalResourceId": "test-physical-id",
        "ResourceType": "Custom::ListenerRuleAllocation",
        "LogicalResourceId": "ListenerRuleAllocation",
        "ResourceProperties": {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-lb/test-lb-id/test-listener-id",
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        },
        "OldResourceProperties": {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-lb/test-lb-id/test-listener-id",
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        }
    }

@pytest.fixture
def delete_event():
    """Generate a CloudFormation Delete event."""
    return {
        "RequestType": "Delete",
        "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/response",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/test-stack-id",
        "RequestId": "test-request-id",
        "PhysicalResourceId": "test-physical-id",
        "ResourceType": "Custom::ListenerRuleAllocation",
        "LogicalResourceId": "ListenerRuleAllocation",
        "ResourceProperties": {
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-lb/test-lb-id/test-listener-id",
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        }
    }

@pytest.fixture
def mock_elbv2_client():
    """Mock boto3 elbv2 client."""
    with patch("boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        
        # Mock describe_rules response
        mock_client.describe_rules.return_value = {
            "Rules": [
                {"Priority": "default"},
                {"Priority": "1"},
                {"Priority": "5"},
                {"Priority": "10"}
            ]
        }
        
        yield mock_client

@pytest.fixture
def mock_http_client():
    """Mock http.client for CloudFormation responses."""
    with patch("http.client.HTTPSConnection") as mock_https:
        mock_conn = MagicMock()
        mock_https.return_value = mock_conn
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_conn.getresponse.return_value = mock_response
        
        yield mock_conn
