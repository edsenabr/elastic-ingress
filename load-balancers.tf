resource "aws_lb" "nlb" {
  name = "elastic-nlb"
  internal = true
  load_balancer_type = "network"
  subnets = var.alb_subnets
}

resource "aws_lb" "alb" {
  name = "elastic-alb"
  internal = true
  load_balancer_type = "application"
	security_groups = var.alb_sg_arn
  subnets = var.alb_subnets
}

resource "aws_lb_target_group" "nlb" {
  name     = "nlb-to-alb"
  port     = 443
  protocol = "TLS"
  vpc_id   = var.vpc_id
  target_type = "ip"
	deregistration_delay="5"
	health_check {
		interval="10"
		timeout="10"
		path="/healthz"
		protocol="HTTPS"
		healthy_threshold="2"
		unhealthy_threshold="2"
	}
}

resource "aws_lb_listener" "nlb" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = "443"
  protocol          = "TLS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.alb_cert_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb.arn
  }
}

resource "aws_lb_listener" "alb" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "443"
  protocol          = "HTTPS"
  certificate_arn   = var.alb_cert_arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "Error"
      status_code  = "500"
    }
  }
}

resource "aws_lb_listener_rule" "health_check" {
  listener_arn = aws_lb_listener.alb.arn

  action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "OK"
      status_code  = "200"
    }
  }

  condition {
    path_pattern {
      values = ["/healthz"]
    }
  }
}

resource "aws_vpc_endpoint_service" "endpoint_service" {
  acceptance_required        = false
  network_load_balancer_arns = [aws_lb.nlb.arn]
}

resource "aws_vpc_endpoint_service_allowed_principal" "consumer_account" {
  vpc_endpoint_service_id = aws_vpc_endpoint_service.endpoint_service.id
  principal_arn = var.consumer_account_arn
}