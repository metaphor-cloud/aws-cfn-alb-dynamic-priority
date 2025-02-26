import json
import os
import random
import uuid
from urllib.parse import urlparse
import http.client

import boto3

SUCCESS = "SUCCESS"
FAILED = "FAILED"
ALB_RULE_PRIORITY_RANGE = 10000, 50000
ALLOCATING = []


def handler(event, context):
    try:
        _lambda_handler(event, context)
    except Exception as e:
        send(event, context, response_status=FAILED if event['RequestType'] != 'Delete' else SUCCESS, response_data=None, physical_resource_id=str(uuid.uuid4()), reason=str(e))
        raise


def get_alb_rule_priority(listener_arn):
    global ALLOCATING
    elbv2_client = boto3.client('elbv2')

    result = elbv2_client.describe_rules(ListenerArn=listener_arn)
    in_use = list(filter(lambda s: s.isdecimal(), [r['Priority'] for r in result['Rules']]))

    priority = None
    while not priority:
        new_priority = str(random.randint(*ALB_RULE_PRIORITY_RANGE))
        if new_priority and new_priority not in in_use and new_priority not in ALLOCATING:
            ALLOCATING.append(priority)
            priority = new_priority

    return priority


def _lambda_handler(event, context):
    """Process CloudFormation custom resource events for ALB rule priority allocation.

    This Lambda handler manages the allocation of Application Load Balancer (ALB) rule priorities
    through CloudFormation custom resources. It supports Create, Update and Delete operations.

    Args:
        event (dict): CloudFormation custom resource event containing:
            - RequestType: Create, Update or Delete
            - ResourceProperties: Dictionary containing:
                - ListenerArn: ARN of the ALB listener
                - PriorityCount: Number of priorities to allocate (optional)
            - PhysicalResourceId: Resource identifier (optional)
        context (LambdaContext): AWS Lambda context object

    Returns:
        dict: CloudFormation custom resource response containing:
            - Status: SUCCESS or FAILED
            - Data: Dictionary containing allocated priorities:
                - If PriorityCount specified: {'Priorities': "comma,separated,list", 'ListenerArn': listener_arn}
                - If no count specified: {'Priority': priority, 'ListenerArn': listener_arn}
            - PhysicalResourceId: Resource identifier

    Raises:
        None: Failures are handled by returning FAILED status to CloudFormation
    """
    print("Received event: " + json.dumps(event, indent=2))

    physical_resource_id = event.get('PhysicalResourceId', str(uuid.uuid4()))
    response_data = {}

    request_type = event['RequestType']
    print(f"Request type is {request_type}")
    print(f"Allocation cache state: {ALLOCATING}")

    request_properties = event.get('ResourceProperties', {})

    if request_type in ['Create', 'Update']:
        listener_arn = request_properties.get('ListenerArn')
        request_priority_count = request_properties.get('PriorityCount')
        print(request_properties, listener_arn, request_priority_count)

        if listener_arn and request_priority_count:
            print(f"Allocating {request_priority_count} priorities for {listener_arn}")
            priorities = []
            response_data['Priorities'] = ""
            for _ in range(int(request_priority_count)):
                priority = get_alb_rule_priority(listener_arn)
                priorities.append(priority)
            priorities.sort()
            response_data['Priorities'] = ",".join(priorities)
            response_data['ListenerArn'] = listener_arn
            print(f"Allocated priorities: {response_data['Priorities']}")
            return send(event, context, SUCCESS, response_data, physical_resource_id)
        elif listener_arn:
            print("No priority count specified, allocating one")
            priority = get_alb_rule_priority(listener_arn)
            response_data['Priority'] = priority
            response_data['ListenerArn'] = listener_arn
            print(f"Allocated: {response_data}")
            return send(event, context, SUCCESS, response_data, physical_resource_id)

    if request_type == 'Delete':
        return send(event, context, SUCCESS, request_properties, physical_resource_id)

    return send(event, context, FAILED, response_data, physical_resource_id, reason='No response data')


def send(event, context, response_status, response_data, physical_resource_id, reason=None):
    response_url = event['ResponseURL']
    parsed_url = urlparse(response_url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)

    response_body = {
        'Status': response_status,
        'Reason': reason if reason else 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
        'PhysicalResourceId': physical_resource_id,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data,
    }

    json_response_body = json.dumps(response_body)
    conn.request('PUT', f"{parsed_url.path}?{parsed_url.query}", body=json_response_body, headers={'Content-Length': str(len(json_response_body))})

    response = conn.getresponse()
    if response.status != 200:
        print(f"Failed to send message to CloudFormation. HTTP status code: {response.status}")
        print("Response: ", response.read().decode())