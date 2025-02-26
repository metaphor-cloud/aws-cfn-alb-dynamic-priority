import json
import random
import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from src import index


class TestLambdaHandler:
    """Tests for the main lambda_handler function."""

    def test_lambda_handler_success(self, create_event, mock_context, mock_elbv2_client, mock_http_client):
        """Test that lambda_handler successfully calls _lambda_handler."""
        with patch("src.index._lambda_handler") as mock_internal_handler:
            index.lambda_handler(create_event, mock_context)
            mock_internal_handler.assert_called_once_with(create_event, mock_context)

    def test_lambda_handler_error_handling_create(self, create_event, mock_context, mock_http_client):
        """Test that lambda_handler handles exceptions for Create events."""
        with patch("src.index._lambda_handler") as mock_internal_handler:
            mock_internal_handler.side_effect = Exception("Test error")
            with patch("uuid.uuid4", return_value="test-uuid"):
                with patch("src.index.send") as mock_send:
                    with pytest.raises(Exception, match="Test error"):
                        index.lambda_handler(create_event, mock_context)
                    
                    # Verify send was called with FAILED status
                    mock_send.assert_called_once()
                    args, kwargs = mock_send.call_args
                    assert args[0] == create_event
                    assert args[1] == mock_context
                    assert kwargs['response_status'] == index.FAILED
                    assert kwargs['response_data'] is None
                    assert kwargs['physical_resource_id'] == "test-uuid"
                    assert kwargs['reason'] == "Test error"

    def test_lambda_handler_error_handling_delete(self, delete_event, mock_context, mock_http_client):
        """Test that lambda_handler handles exceptions for Delete events."""
        with patch("src.index._lambda_handler") as mock_internal_handler:
            mock_internal_handler.side_effect = Exception("Test error")
            with patch("uuid.uuid4", return_value="test-uuid"):
                with patch("src.index.send") as mock_send:
                    with pytest.raises(Exception, match="Test error"):
                        index.lambda_handler(delete_event, mock_context)
                    
                    # Verify send was called with SUCCESS status for Delete events
                    mock_send.assert_called_once()
                    args, kwargs = mock_send.call_args
                    assert args[0] == delete_event
                    assert args[1] == mock_context
                    assert kwargs['response_status'] == index.SUCCESS  # Delete events should return SUCCESS even on error
                    assert kwargs['response_data'] is None
                    assert kwargs['physical_resource_id'] == "test-uuid"
                    assert kwargs['reason'] == "Test error"


class TestInternalLambdaHandler:
    """Tests for the _lambda_handler function."""

    def test_create_with_single_priority(self, create_event, mock_context, mock_elbv2_client, mock_http_client):
        """Test Create operation with a single priority."""
        with patch("src.index.get_alb_rule_priority", return_value="12345") as mock_get_priority:
            with patch("src.index.send") as mock_send:
                index._lambda_handler(create_event, mock_context)
                
                # Verify get_alb_rule_priority was called
                listener_arn = create_event["ResourceProperties"]["ListenerArn"]
                mock_get_priority.assert_called_once_with(listener_arn)
                
                # Verify send was called with correct data
                mock_send.assert_called_once()
                args = mock_send.call_args[0]
                assert args[0] == create_event
                assert args[1] == mock_context
                assert args[2] == index.SUCCESS
                assert args[3] == {
                    "Priority": "12345",
                    "ListenerArn": listener_arn
                }

    def test_create_with_multiple_priorities(self, create_event_with_count, mock_context, mock_elbv2_client, mock_http_client):
        """Test Create operation with multiple priorities."""
        # Mock get_alb_rule_priority to return different values on each call
        priorities = ["12345", "23456"]
        with patch("src.index.get_alb_rule_priority", side_effect=priorities) as mock_get_priority:
            with patch("src.index.send") as mock_send:
                index._lambda_handler(create_event_with_count, mock_context)
                
                # Verify get_alb_rule_priority was called twice
                listener_arn = create_event_with_count["ResourceProperties"]["ListenerArn"]
                assert mock_get_priority.call_count == 2
                mock_get_priority.assert_has_calls([call(listener_arn), call(listener_arn)])
                
                # Verify send was called with correct data
                mock_send.assert_called_once()
                args = mock_send.call_args[0]
                assert args[0] == create_event_with_count
                assert args[1] == mock_context
                assert args[2] == index.SUCCESS
                assert args[3] == {
                    "Priorities": "12345,23456",
                    "ListenerArn": listener_arn
                }

    def test_update_operation(self, update_event, mock_context, mock_elbv2_client, mock_http_client):
        """Test Update operation."""
        with patch("src.index.get_alb_rule_priority", return_value="12345") as mock_get_priority:
            with patch("src.index.send") as mock_send:
                index._lambda_handler(update_event, mock_context)
                
                # Verify get_alb_rule_priority was called
                listener_arn = update_event["ResourceProperties"]["ListenerArn"]
                mock_get_priority.assert_called_once_with(listener_arn)
                
                # Verify send was called with correct data
                mock_send.assert_called_once()
                args = mock_send.call_args[0]
                assert args[0] == update_event
                assert args[1] == mock_context
                assert args[2] == index.SUCCESS
                assert args[3] == {
                    "Priority": "12345",
                    "ListenerArn": listener_arn
                }

    def test_delete_operation(self, delete_event, mock_context, mock_http_client):
        """Test Delete operation."""
        with patch("src.index.send") as mock_send:
            index._lambda_handler(delete_event, mock_context)
            
            # Verify send was called with SUCCESS and the request properties
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == delete_event
            assert args[1] == mock_context
            assert args[2] == index.SUCCESS
            assert args[3] == delete_event["ResourceProperties"]

    def test_invalid_request(self, mock_context, mock_http_client):
        """Test handling of invalid requests."""
        # Create an event with missing ListenerArn
        invalid_event = {
            "RequestType": "Create",
            "ResponseURL": "https://example.com/response",
            "StackId": "test-stack-id",
            "RequestId": "test-request-id",
            "LogicalResourceId": "test-resource-id",
            "ResourceProperties": {
                "ServiceToken": "test-service-token"
                # Missing ListenerArn
            }
        }
        
        with patch("src.index.send") as mock_send:
            index._lambda_handler(invalid_event, mock_context)
            
            # Verify send was called with FAILED
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert args[0] == invalid_event
            assert args[1] == mock_context
            assert args[2] == index.FAILED
            assert args[3] == {}
            assert kwargs.get('reason') == "No response data"


class TestGetAlbRulePriority:
    """Tests for the get_alb_rule_priority function."""

    def test_priority_in_range(self, mock_elbv2_client):
        """Test that the generated priority is within the specified range."""
        priority = index.get_alb_rule_priority("test-listener-arn")
        
        # Verify the priority is within the specified range
        assert priority.isdigit()
        priority_int = int(priority)
        assert index.ALB_RULE_PRIORITY_RANGE[0] <= priority_int <= index.ALB_RULE_PRIORITY_RANGE[1]

    def test_priority_not_in_use(self, mock_elbv2_client):
        """Test that the generated priority is not already in use."""
        # Set up the mock to return priorities that are already in use
        in_use_priorities = ["10000", "10001", "10002"]
        mock_elbv2_client.describe_rules.return_value = {
            "Rules": [{"Priority": p} for p in in_use_priorities]
        }
        
        with patch("random.randint") as mock_randint:
            # First return a priority that's in use, then one that's not
            mock_randint.side_effect = [10000, 10003]
            
            priority = index.get_alb_rule_priority("test-listener-arn")
            
            # Verify the priority is not in the in-use list
            assert priority not in in_use_priorities
            assert priority == "10003"

    def test_priority_not_in_allocating(self, mock_elbv2_client):
        """Test that the generated priority is not in the ALLOCATING list."""
        # Add a priority to the ALLOCATING list
        index.ALLOCATING = ["20000"]
        
        with patch("random.randint") as mock_randint:
            # First return a priority that's in ALLOCATING, then one that's not
            mock_randint.side_effect = [20000, 20001]
            
            priority = index.get_alb_rule_priority("test-listener-arn")
            
            # Verify the priority is not in the ALLOCATING list
            assert priority not in index.ALLOCATING
            assert priority == "20001"
            
            # Clean up
            index.ALLOCATING = []


class TestSendResponse:
    """Tests for the send function."""

    def test_send_success_response(self, create_event, mock_context, mock_http_client):
        """Test sending a SUCCESS response."""
        physical_id = str(uuid.uuid4())
        response_data = {"Priority": "12345"}
        
        index.send(create_event, mock_context, index.SUCCESS, response_data, physical_id)
        
        # Verify the HTTP request was made with the correct data
        mock_http_client.request.assert_called_once()
        args = mock_http_client.request.call_args
        
        # Check HTTP method and URL
        assert args[0][0] == "PUT"
        assert args[0][1].startswith("/")  # Just check that the path starts with /
        
        # Parse the body JSON and check its contents
        body = json.loads(args[1]["body"])
        assert body["Status"] == index.SUCCESS
        assert body["PhysicalResourceId"] == physical_id
        assert body["StackId"] == create_event["StackId"]
        assert body["RequestId"] == create_event["RequestId"]
        assert body["LogicalResourceId"] == create_event["LogicalResourceId"]
        assert body["Data"] == response_data
        assert "Reason" in body  # Reason should be present

    def test_send_failure_response(self, create_event, mock_context, mock_http_client):
        """Test sending a FAILED response with a reason."""
        physical_id = str(uuid.uuid4())
        response_data = {}
        reason = "Test failure reason"
        
        index.send(create_event, mock_context, index.FAILED, response_data, physical_id, reason)
        
        # Verify the HTTP request was made with the correct data
        mock_http_client.request.assert_called_once()
        args = mock_http_client.request.call_args
        
        # Parse the body JSON and check its contents
        body = json.loads(args[1]["body"])
        assert body["Status"] == index.FAILED
        assert body["Reason"] == reason
        assert body["PhysicalResourceId"] == physical_id
        assert body["Data"] == response_data

    def test_http_error_handling(self, create_event, mock_context):
        """Test handling of HTTP errors when sending the response."""
        # Mock HTTPSConnection to simulate an error
        with patch("http.client.HTTPSConnection") as mock_https:
            mock_conn = MagicMock()
            mock_https.return_value = mock_conn
            
            # Mock response with a non-200 status
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.read.return_value = b"Internal Server Error"
            mock_conn.getresponse.return_value = mock_response
            
            # Mock print to capture the error message
            with patch("builtins.print") as mock_print:
                physical_id = str(uuid.uuid4())
                response_data = {"Priority": "12345"}
                
                index.send(create_event, mock_context, index.SUCCESS, response_data, physical_id)
                
                # Verify error was logged
                mock_print.assert_any_call("Failed to send message to CloudFormation. HTTP status code: 500")
