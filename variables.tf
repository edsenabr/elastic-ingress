variable "aws_region" {
    default = "sa-east-1"
}

variable "aws_profile" {
    default = "provedora"
}

variable "vpc_id" {
    default = "vpc-XXXXXXXXXXXXXXXXX"
}

variable "alb_sg_arn" {
	type    = list(string)
    default = ["sg-XXXXXXXXXXXXXXXXX"]	
}

variable "alb_subnets" {
	type    = list(string)
    default = ["subnet-XXXXXXXXXXXXXXXXX","subnet-XXXXXXXXXXXXXXXXX"]	
}

variable "alb_cert_arn" {
    default = "arn:aws:acm:sa-east-1:XXXXXXXXXXXX:certificate/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}

variable "lambda_role_arn" {
    default = ""
}

variable "consumer_account_arn" {
    default = "arn:aws:iam::XXXXXXXXXXXX:root"
}