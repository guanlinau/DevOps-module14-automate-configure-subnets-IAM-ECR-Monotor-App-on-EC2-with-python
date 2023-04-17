import boto3


#Exercise 1:Working with Subnets in AWS
# 1- Get all the subnets in your default region
# 2- Print the subnet Ids
# Get all ec2 instances from default region, should not define second parameter in the client()
ec2 = boto3.client('ec2')
subnets = ec2.describe_subnets()
for subnet in subnets['Subnets']:
    print(subnet['SubnetId'])
    print(subnet['DefaultForAz'])
