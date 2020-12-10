module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"
  function_name = "elastic-ingress"
  handler       = "update_targets.lambda_handler"
  runtime       = "python3.6"
	create_role   = false
	lambda_role   = aws_iam_role.lambda.arn
	create_current_version_allowed_triggers = false
  source_path = {
    path        = "lambda",
    pip_requirements = true,
		patterns = [
      "!requirements.txt",
      "!.gitignore"
    ]		
  }

	allowed_triggers = {
    OneRule = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.schedule.arn
    }
  }

	depends_on = [
		aws_lb_target_group.nlb,
		aws_lb_listener.alb
	]

}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "elastic-ingress"
	schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  arn       = module.lambda_function.this_lambda_function_arn
}