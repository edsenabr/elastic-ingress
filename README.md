# elastic-ingress

this project has the objective of implementing the following topology:

![Topology](static/vpc-endpoints.drawio.png)

in order to deploy it, you'll need the following pre-requisites:

- terraform
- pyhton 3.6
- pip

> **DISCLAIMER**: This not a production ready system. It is meant only to educate in terms of what can be achieved with the components aforementioned. In order to understand AWS best practices to production topologies, please refer to [AWS Well Architected Framework](https://aws.amazon.com/architecture/well-architected/)


for deploying the solution, follow these simple steps:

1. clone this repo
1. edit the file [variables.tf](variables.tf) for setting the right required values
2. create a python virtualenv inside the [lambda](lambda) folder and activate it
1. execute a `terraform apply`

the terraform script will deploy the basic infrastructure, including a lambda function written in python that will configure the target groups of both load balancers to the right ips, discovering the private endpoints of all Elasticsearch clusters deployed to the same account. This function will be invoked every minute. 

In order to create the endpoint component on the transit VPC, use the 'service_endpoint' output value of the terraform script. 