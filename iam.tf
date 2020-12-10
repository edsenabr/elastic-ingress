resource "aws_iam_role" "lambda" {
  name = "ElasticIngressRole"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "lambda" {
  name        = "ElasticIngressPolicy"
  path        = "/"
  description = "IAM policy for managing the "

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Targets",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:RegisterTargets",
                "elasticloadbalancing:DeregisterTargets"
            ],
            "Resource": [
                "arn:aws:elasticloadbalancing:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:targetgroup/elastic-*/*",
                "${aws_lb_target_group.nlb.arn}"
            ]
        },
        {
            "Sid": "TargetGroup",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:CreateTargetGroup",
                "elasticloadbalancing:DeleteTargetGroup"
            ],
            "Resource": [
                "arn:aws:elasticloadbalancing:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:targetgroup/elastic-*/*"
            ]
        },
        {
            "Sid": "Rules",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:CreateRule",
                "elasticloadbalancing:DeleteRule"
            ],
            "Resource": [
                "${aws_lb_listener.alb.arn}",
                "${replace(aws_lb_listener.alb.arn, "listener", "listener-rule")}/*"
            ]
        },
        {
            "Sid": "ReadOnly",
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:DescribeLoadBalancers",
                "es:ListDomainNames",
                "es:DescribeElasticsearchDomains",
                "ec2:DescribeNetworkInterfaces",
                "elasticloadbalancing:DescribeListeners",
                "elasticloadbalancing:DescribeTargetHealth",
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeRules"
            ],
            "Resource": "*"
        },
				{
            "Sid": "Logs",
            "Effect": "Allow",
            "Action": [
                "logs:PutLogEvents",
                "logs:CreateLogStream"
            ],
            "Resource": [
                "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/elastic-ingress:*:*",
                "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/elastic-ingress:*"
            ]
        }				
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}