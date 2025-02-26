# AWS CloudFormation ALB Dynamic Priority

A Lambda function that serves as a CloudFormation custom resource for dynamically allocating Application Load Balancer (ALB) rule priorities.

## Overview

When creating ALB listener rules in CloudFormation, you need to specify a unique priority for each rule. This can be challenging to manage manually, especially in complex templates with multiple rules or when rules are created across multiple stacks.

This custom resource automatically allocates unique priorities for ALB listener rules, eliminating the need to manually track and assign them.

## Features

- Dynamically allocates unique ALB rule priorities within a specified range (10000-50000 by default)
- Can allocate a single priority or multiple priorities in one request
- Handles CloudFormation Create, Update, and Delete operations
- Packaged as a container image for easy deployment
- Multi-architecture support (arm64 and amd64)

## Installation

The Lambda function is packaged as a container image and published to Amazon ECR Public Gallery. You can deploy it using the provided CloudFormation template.

### Prerequisites

- AWS CLI configured with appropriate permissions
- An existing Application Load Balancer with a listener

### Deployment

1. Create a CloudFormation stack using the example template:

```bash
aws cloudformation create-stack \
  --stack-name alb-dynamic-priority-example \
  --template-body file://example.yml \
  --parameters \
    ParameterKey=ListenerArn,ParameterValue=<your-listener-arn> \
    ParameterKey=LambdaImageUri,ParameterValue=public.ecr.aws/metaphor/aws-cfn-alb-dynamic-priority:latest \
  --capabilities CAPABILITY_IAM
```

## Usage

### Basic Usage

To use the custom resource in your CloudFormation template:

```yaml
Resources:
  ListenerRuleAllocation:
    Type: Custom::ListenerRuleAllocation
    Properties:
      ServiceToken: !GetAtt ListenerRuleAllocationLambda.Arn
      ListenerArn: !Ref YourListenerArn
      # Optional: specify how many priorities you need
      # PriorityCount: 2

  # If PriorityCount is not specified, you can use the single priority:
  YourListenerRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      # ... other properties ...
      ListenerArn: !Ref YourListenerArn
      Priority: !GetAtt ListenerRuleAllocation.Priority
```

### Multiple Priorities

If you need multiple priorities, specify the `PriorityCount` property:

```yaml
Resources:
  ListenerRuleAllocation:
    Type: Custom::ListenerRuleAllocation
    Properties:
      ServiceToken: !GetAtt ListenerRuleAllocationLambda.Arn
      ListenerArn: !Ref YourListenerArn
      PriorityCount: 3

  Rule1:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      # ... other properties ...
      ListenerArn: !Ref YourListenerArn
      Priority: !Select [0, !Split [",", !GetAtt ListenerRuleAllocation.Priorities]]

  Rule2:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      # ... other properties ...
      ListenerArn: !Ref YourListenerArn
      Priority: !Select [1, !Split [",", !GetAtt ListenerRuleAllocation.Priorities]]

  Rule3:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      # ... other properties ...
      ListenerArn: !Ref YourListenerArn
      Priority: !Select [2, !Split [",", !GetAtt ListenerRuleAllocation.Priorities]]
```

## How It Works

1. When CloudFormation creates the custom resource, the Lambda function is invoked.
2. The function queries the ALB listener to get a list of existing rule priorities.
3. It then generates a random priority within the range 10000-50000 that is not already in use.
4. The priority is returned to CloudFormation, which then uses it when creating the listener rule.

## Development

### Prerequisites

- Python 3.13+
- Docker

### Building Locally

```bash
docker build -t aws-cfn-alb-dynamic-priority .
```

### Testing

```bash
docker build --target test -t aws-cfn-alb-dynamic-priority-test .
```

## License

This project is licensed under the terms of the LICENSE.md file in the repository.
