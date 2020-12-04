variable "aws_region" {
    default = "sa-east-1"
}

variable "aws_profile" {
    default = "provedora"
}

variable "vpc_id" {
    default = "vpc-0c615fe09521a0a6d"
}

variable "alb_sg_arn" {
	type    = list(string)
  default = ["sg-02e3e7a269dd70fed"]	
}

variable "alb_subnets" {
	type    = list(string)
  default = ["subnet-07e27b8af73f71d71","subnet-08f790884bd2dd109"]	
}

variable "alb_cert_arn" {
    default = "arn:aws:acm:sa-east-1:279835290717:certificate/03782419-31b2-495a-94f4-a9e0874b2917"
}

variable "lambda_role_arn" {
    default = ""
}

variable "consumer_account_arn" {
    default = "arn:aws:iam::837108680928:root"
}