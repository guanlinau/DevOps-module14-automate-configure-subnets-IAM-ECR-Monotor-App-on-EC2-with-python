
# from distutils import command
import boto3
import time
import paramiko
import requests
import schedule

# EXERCISE 3: Automate Running and Monitoring Application on EC2 instance
# 1- Write Python program which automatically creates EC2 instance, install Docker inside and starts Nginx application as Docker container and starts monitoring the application as a scheduled task. Write the program with the following steps:

# 2- Start EC2 instance in default VPC
# 3- Wait until the EC2 server is fully initialized
# 4- Install Docker on the EC2 server
# 5- Start nginx container
# 6- Open port for nginx to be accessible from browser
# 7- Create a scheduled function that sends request to the nginx application and checks the status is OK
# 8- If status is not OK 5 times in a row, it restarts the nginx application

#Get all ec2 instances in default region:sydney
ec2_client = boto3.client('ec2')
ec2_resource = boto3.resource('ec2')

# Set all needed variable values
image_id='ami-0d9f286195031c3d9'
key_name='my-first-key-pair'
instance_type='t2.micro'
security_group='launch-wizard-1'

# the pem file must have restricted 400 permissions: chmod 400 absolute-path/boto3-server-key.pem
ssh_privat_key_path = '/Users/jason/.ssh/my-first-key-pair.pem' 
ssh_user = 'ec2-user'
ssh_host = '' # will be set dynamically below

# Start EC2 instance in default VPC

# check if we have already created this instance using instance name

response = ec2_client.describe_instances(
    Filters =[
        {
            'Name':'tag:Name',
            'Values':[
                'my-server'
            ]
        }
    ]
)

instance_already_exists = len(response["Reservations"]) !=0 and len(response["Reservations"][0]["Instances"]) !=0

instance_id = ''

if not instance_already_exists:
    print("Creating a new ec2 instance")
    ec2_instance_result= ec2_resource.create_instances(
        ImageId=image_id, 
        KeyName=key_name, 
        MinCount=1, 
        MaxCount=1, 
        InstanceType=instance_type,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'my-server'
                    },
                ]
            },
        ],
    )
    instance_id = ec2_instance_result[0].instance_id
else:
    print("Instance already exists")
    instance_id = response['Reservations'][0]['Instances']['InstanceId']

# Wait until the EC2 server is fully initialized

#Method 1
ec2_instance_fully_initialised = False

while not ec2_instance_fully_initialised:
    print("Getting instance status")
    statuses = ec2_client.describe_instance_status(
        InstanceIds = [instance_id]
    )
    if len(statuses['InstanceStatuses']) != 0:
        ec2_status = statuses['InstanceStatuses'][0]

        ins_status = ec2_status['InstanceStatus']['Status']
        sys_status = ec2_status['SystemStatus']['Status']
        state = ec2_status['InstanceState']['Name']
        ec2_instance_fully_initialised = ins_status == 'ok' and sys_status == 'ok' and state == 'running'
        print(ec2_instance_fully_initialised)
    if not ec2_instance_fully_initialised:
        print("waiting for 30 seconds")
        time.sleep(30)

print("Instance fully initialised")
       
#Method2:

# while True:
#     print("Getting instance status, please waiting!")
#     statuses = ec2_client.describe_instance_status(
#         InstanceIds = [instance_id]
#     )
#     if len(statuses['InstanceStatuses']) !=0:
#         print('Continuing waiting!!!')
#         ec2_status = statuses['InstanceStatuses'][0]
#         ins_status = ec2_status['InstanceStatus']['Status']
#         sys_status = ec2_status['SystemStatus']['Status']
#         state = ec2_status['InstanceState']['Name']
#         if ins_status=='ok' and sys_status=='ok' and state=='running':
#             break;

# print("Instance fully initialised")

# get the instance's public ip address
response = ec2_client.describe_instances(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'my-server',
            ]
        },
    ]
) 
instance = response["Reservations"][0]["Instances"][0]
ssh_host = instance["PublicIpAddress"]

# Install Docker on the EC2 server & start nginx container

commands_to_execute = [
    'sudo yum update -y && sudo yum install -y docker',
    'sudo systemctl start docker',
    'sudo chmod -aG docker ec2-user',
    'docker run -d -p 8080:80 --name nginx nginx',
]

# connect to EC2 server

print("Connecting to the server")
print(f"public ip: {ssh_host}")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=ssh_host, username=ssh_user, key_filename=ssh_privat_key_path)

#Install docker & nginx
for command in commands_to_execute:
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.readlines())

ssh.close()

# Open 8080 for nginx server, if not already open
sg_list=ec2_client.describe_security_groups(
    GroupNames=[
        security_group,
    ]
)

port_open=False

for permission in sg_list['SecurityGroups'][0]['IpPermissions']:
    
    if 'FromPort' in permission and permission['FromPort'] == 8080:
        port_open=True
    
if not port_open:
    sg_response=ec2_client.authorize_security_group_ingress(
        FromPort=8080,
        ToPort=8080,
        GroupName=security_group,
        CidrIp='0.0.0.0/0',
        IpProtocol='tcp'
    )

# Scheduled function to check nginx application status and reload if not OK 5x in a row
app_not_accessible_count = 0

def restart_container():
    print('Restarting the application...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ssh_host, username=ssh_user, key_filename=ssh_privat_key_path)
    stdin, stdout, stderr = ssh.exec_command('docker start nginx')
    print(stdout.readlines())
    ssh.close()

     # reset the count
    global app_not_accessible_count
    app_not_accessible_count = 0
    
    print(app_not_accessible_count)

def monitor_application():
    global app_not_accessible_count
    try:
        response = requests.get(f"http://{ssh_host}:8080")
        if response.status_code == 200:
            print('Application is running successfully!')
        else:
            print('Application Down. Fix it!')
            app_not_accessible_count += 1
            if app_not_accessible_count == 5:
                restart_container()
    except Exception as ex:
        print(f'Connection error happened: {ex}')
        print('Application not accessible at all')
        app_not_accessible_count += 1
        if app_not_accessible_count == 5:
            restart_container()
        return "test"

schedule.every(10).seconds.do(monitor_application)  

while True:
    schedule.run_pending()



