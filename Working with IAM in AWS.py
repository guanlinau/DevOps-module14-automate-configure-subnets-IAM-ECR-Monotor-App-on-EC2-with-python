import boto3


#Exercise 2 Working with IAM in AWS
# 1- Get all the IAM users in your AWS account
# 2- For each user, print out the name of the user and when they were last active (hint: Password Last Used attribute)
# 3 -Print out the user ID and name of the user who was active the most recently

#Get all IAM users in the default region
iam= boto3.client('iam')
users = iam.list_users()

last_active_user = users['Users'][0]
for user in users['Users']:
    print(f"The user {user['UserName']} with last active time {user['PasswordLastUsed']}")
    if(last_active_user['PasswordLastUsed'] < user['PasswordLastUsed']):
        last_active_user=user

print(f"Last_active_user is{last_active_user['UserName']} with user_id {last_active_user['UserId']} ")