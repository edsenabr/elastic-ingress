import re
import boto3
ec2 = boto3.client('ec2')
elbv2 = boto3.client('elbv2')
es = boto3.client('es')

def get_alb_arn():
	return elbv2.describe_load_balancers(
		Names=["elastic-alb"]
	)["LoadBalancers"][0]["LoadBalancerArn"]



def get_alb_listener_arn(alb_arn):
	return elbv2.describe_listeners(
		LoadBalancerArn=alb_arn,
	)["Listeners"][0]["ListenerArn"]



def get_nlb_target_group_arn():
	return elbv2.describe_target_groups(
		Names=["nlb-to-alb"]
	)["TargetGroups"][0]["TargetGroupArn"]



def list_es_domains(): 
	names = [Domain['DomainName'] for Domain in es.list_domain_names()['DomainNames']]
	DomainStatusList = es.describe_elasticsearch_domains(
		DomainNames=names
	)
	domains = {}
	for DomainStatus in DomainStatusList['DomainStatusList']: 
		domains[DomainStatus['DomainName']] = {
			"DomainName": DomainStatus['DomainName'], 
			"Endpoint": DomainStatus['DomainEndpointOptions']['CustomEndpoint'],
			"PrivateIpAddress": list_es_domain_current_ips(DomainStatus['DomainName']),
			"VPCId": DomainStatus["VPCOptions"]["VPCId"]
		}
	return domains


def list_tg_registrations(tg_arn): 
	response = elbv2.describe_target_health(
		TargetGroupArn=tg_arn,
	)
	return [ Target['Target']['Id'] for Target in response['TargetHealthDescriptions'] ]



def list_target_groups(existing_domains):
	groups = {}
	for TargetGroup in elbv2.describe_target_groups()['TargetGroups']:
		if TargetGroup['TargetGroupName'].startswith('elastic-'): 
					
			groups[TargetGroup['TargetGroupName']] = {
				'TargetGroupArn': TargetGroup['TargetGroupArn']
			}

			try:
				domain = existing_domains[TargetGroup['TargetGroupName'][8:]]
				print("found %s on %s" % (domain['DomainName'], TargetGroup['TargetGroupArn']))
				domain['TargetGroupArn'] = TargetGroup['TargetGroupArn']
				groups[TargetGroup['TargetGroupName']]['DomainName'] = domain['DomainName']
			except KeyError:
				pass

	return groups

def list_interfaces_ips(requester, description):
	response = ec2.describe_network_interfaces(
		Filters=[
				{'Name': 'requester-id', 'Values': [requester]},
				{'Name': 'attachment.status', 'Values': [ 'attached' ]},
				{'Name': 'status', 'Values': [ 'in-use' ]},
				{'Name': 'description', 'Values': [ description ]}
		],
		DryRun=False
	)
	return [ NetworkInterface['PrivateIpAddress'] for NetworkInterface in response['NetworkInterfaces'] ]


def list_es_domain_current_ips(domain_name):
	return list_interfaces_ips('amazon-elasticsearch', ('ES %s' % domain_name))

def list_alb_current_ips(alb_arn):
	id = re.match(
		'arn:aws:elasticloadbalancing:.+:.+:loadbalancer/app/(.+)',
		alb_arn	
	).group(1)
	return list_interfaces_ips('amazon-elb', ('ELB app/%s' % id))

def register_tg_targets (tg_arn, ips): 
	if len(ips) > 0: 
		print("... registering IPS %s on target group %s" % (ips, tg_arn))
		elbv2.register_targets(
			TargetGroupArn=tg_arn,
			Targets=[ {'Id': ip} for ip in ips ]
		)	

def deregister_tg_targets (tg_arn, ips): 
	if len(ips) > 0: 
		print("... deregistering IPS %s from target group %s" % (ips, tg_arn))
		elbv2.deregister_targets(
			TargetGroupArn=tg_arn,
			Targets=[{'Id': ip} for ip in ips]
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
	return arn



def count_alb_listener_rules(alb_listener_arn):
	return len(elbv2.describe_rules(
		ListenerArn=alb_listener_arn
	)['Rules'])



def create_alb_listener_rule(alb_listener_arn, target_group_arn, domain):
	print("... creating listener rule for cluster %s on %s pointing to %s" % (domain['DomainName'], alb_listener_arn, target_group_arn))
	elbv2.create_rule(
		ListenerArn=alb_listener_arn,
		Priority=count_alb_listener_rules(alb_listener_arn),
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


def list_alb_listener_rules(alb_listener_arn):
	rules = {}
	for Rule in elbv2.describe_rules(ListenerArn=alb_listener_arn)['Rules']:
		if len(Rule['Conditions']) > 0 and Rule['Conditions'][0]['Field'] == 'host-header' :
			rules[Rule['Actions'][0]['TargetGroupArn']] = Rule['RuleArn']
	return rules



def delete_alb_listener_rule(alb_listener_rules, group):
	try:
		alb_rule_arn = alb_listener_rules[group['TargetGroupArn']]
		print("... deleting listener rule %s for group %s" % (alb_rule_arn, group['TargetGroupArn']))
		elbv2.delete_rule(
			RuleArn=alb_rule_arn
		)
	except KeyError:
		pass



def delete_target_group(group):
	print("... deleting target group %s " % group['TargetGroupArn'])
	elbv2.delete_target_group(
    TargetGroupArn=group['TargetGroupArn']
	)



def update_tg_registrations(target_group_arn, current_ips):
		registered_ips = list_tg_registrations(target_group_arn)
		to_register = set(current_ips) - set(registered_ips)
		to_deregister = set(registered_ips) - set(current_ips)
		register_tg_targets(target_group_arn, to_register)
		deregister_tg_targets(target_group_arn, to_deregister)



def update_alb(alb_arn):
	domains = list_es_domains()
	target_groups = list_target_groups(domains)
	alb_listener_arn = get_alb_listener_arn(alb_arn)
	alb_listener_rules = list_alb_listener_rules(alb_listener_arn)

	for DomainName, domain in domains.items():
		if 'TargetGroupArn' in domain:
			update_tg_registrations(
				domain['TargetGroupArn'], 
				domain['PrivateIpAddress']
			)
		else:
			print("will create TG for domain %s" % (DomainName))
			target_group_arn = create_target_group(domain)
			register_tg_targets(target_group_arn, domain['PrivateIpAddress'])
			create_alb_listener_rule(alb_listener_arn, target_group_arn, domain)

	for group in target_groups.values():
		if 'DomainName' not in group:
			delete_alb_listener_rule(alb_listener_rules, group)
			delete_target_group(group)



def update_nlb(alb_current_ips):
	nlb_tg_arn = get_nlb_target_group_arn()
	update_tg_registrations(
		nlb_tg_arn,
		alb_current_ips
	)


def lambda_handler(event, context):
	alb_arn = get_alb_arn()
	update_alb(alb_arn)

	alb_current_ips = list_alb_current_ips(alb_arn)
	update_nlb(alb_current_ips)



if __name__ == "__main__":
	lambda_handler(None, None)