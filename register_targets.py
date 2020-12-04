import re
import boto3
ec2 = boto3.client('ec2')
elbv2 = boto3.client('elbv2')
es = boto3.client('es')

def get_alb_arn():
	return elbv2.describe_load_balancers(
		Names=["elastic-alb"]
	)["LoadBalancers"][0]["LoadBalancerArn"]

def get_alb_listener_arn(arn):
	return elbv2.describe_listeners(
		LoadBalancerArn=arn,
	)["Listeners"][0]["ListenerArn"]

def get_nlb_target_group_arn():
	return elbv2.describe_target_groups(
		Names=["elastic-alb"]
	)["TargetGroups"][0]["TargetGroupArn"]


def list_clusters(): 
	names = [Domain['DomainName'] for Domain in es.list_domain_names()['DomainNames']]
	DomainStatusList = es.describe_elasticsearch_domains(
		DomainNames=names
	)
	domains = [
		{
			"DomainName": DomainStatus['DomainName'], 
			"Endpoint": DomainStatus['DomainEndpointOptions']['CustomEndpoint'],
			"PrivateIpAddress": list_cluster_current_ips(DomainStatus['DomainName']),
			"VPCId": DomainStatus["VPCOptions"]["VPCId"]
		}
		for DomainStatus in 
		DomainStatusList['DomainStatusList']
	]
	return domains

def list_cluster_current_ips(cluster):
	response = ec2.describe_network_interfaces(
		Filters=[
				{
						'Name': 'requester-id',
						'Values': ['amazon-elasticsearch']
				},
				{
						'Name': 'attachment.status',
						'Values': [ 'attached' ]
				},
				{
						'Name': 'status',
						'Values': [ 'in-use' ]
				},
				{
						'Name': 'description',
						'Values': [ ('ES %s' % cluster) ]
				}
		],
		DryRun=False
	)
	return [ NetworkInterface['PrivateIpAddress'] for NetworkInterface in response['NetworkInterfaces'] ]

def list_alb_current_ips(arn):
	items = re.match(
		'arn:aws:elasticloadbalancing:.+:.+:loadbalancer/app/(.+)',
		arn	
	)
	id = items.group(1)
	response = ec2.describe_network_interfaces(
		Filters=[
				{
						'Name': 'requester-id',
						'Values': ['amazon-elb']
				},
				{
						'Name': 'attachment.status',
						'Values': [ 'attached' ]
				},
				{
						'Name': 'status',
						'Values': [ 'in-use' ]
				},
				{
						'Name': 'description',
						'Values': [ ('ELB app/%s' % id) ]
				}
		],
		DryRun=False
	)
	return [ NetworkInterface['PrivateIpAddress'] for NetworkInterface in response['NetworkInterfaces'] ]

def register_targets (arn, ips): 
	print("... registering IPS %s on target group %s" % (ips, arn))
	if len(ips) > 0: 
		elbv2.register_targets(
			TargetGroupArn=arn,
			Targets=[ {'Id': ip} for ip in ips ]
		)	

def create_target_group(domain):
	print("... creating target group elastic-%s" % domain['DomainName'])
	arn = elbv2.create_target_group(
		Name='elastic-%s' % domain['DomainName'],
		Protocol='HTTPS',
		Port=443,
		VpcId=domain['VPCId'],
		HealthCheckProtocol='HTTPS',
		HealthCheckEnabled=True,
		HealthCheckIntervalSeconds=5,
		HealthCheckTimeoutSeconds=2,
		HealthyThresholdCount=5,
		UnhealthyThresholdCount=2,
		Matcher={
				'HttpCode': '401'
		},
		TargetType='ip'
	)['TargetGroups'][0]['TargetGroupArn']
	register_targets(arn, domain['PrivateIpAddress'])
	return arn

def count_listener_rules(arn):
	return len(elbv2.describe_rules(
		ListenerArn=arn
	)['Rules'])

def create_listener_rule(listener_arn, target_group_arn, domain):
	print("... creating listener rule for cluster %s on %s pointing to %s" % (domain['DomainName'], listener_arn, target_group_arn))
	elbv2.create_rule(
		ListenerArn=listener_arn,
		Priority=count_listener_rules(listener_arn),
		Conditions=[{
			'Field': 'host-header',
			'Values': [
					domain['Endpoint']
			]
		}],
		Actions=[{
			'Type': 'forward',
			'TargetGroupArn': target_group_arn
		}]
	)

if __name__ == "__main__":
	alb_arn = get_alb_arn()
	alb_listener_arn = get_alb_listener_arn(alb_arn)

	domains = list_clusters()
	for domain in domains:
		target_group_arn = create_target_group(domain)
		create_listener_rule(alb_listener_arn, target_group_arn, domain)

	nlb_tg_arn = get_nlb_target_group_arn()
	alb_ips = list_alb_current_ips(alb_arn)
	register_targets(nlb_tg_arn, alb_ips)