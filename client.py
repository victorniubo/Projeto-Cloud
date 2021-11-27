import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import sys, os, stat
import subprocess as sp
from cores import bcolors

class Client:

    def __init__(self, region:str):

        self.region = region

        self.color = bcolors()

        if region == 'us-east-1':
            self.imgId = 'ami-0279c3b3186e54acd'
        
        elif region == 'us-east-2':
            self.imgId = 'ami-020db2c14939a8efb'
        
        else:
            print(f"{self.color.FAIL}Região não suportada{self.color.ENDC}")
        

        self.aws_config = Config(region_name = region)

        self.client = boto3.client("ec2", config=self.aws_config)

    
    def createKeyPair (self, name:str):

        file = 'keys/' + name + '.pem'

        response = self.client.describe_key_pairs(Filters = [
            {
                'Name' : 'key-name',
                'Values' : [name]
            }
        ])

        if response['KeyPairs']:
            print(f"{self.color.WARNING}Apagando Key Pair existente{self.color.ENDC}")

            response = self.client.delete_key_pair(KeyName=name)

    
        print(f"{self.color.OKCYAN}Gerando nova Key Pair de nome: {name}{self.color.ENDC}")
        response = self.client.create_key_pair(KeyName=name)

        if os.path.exists(file):
            os.remove(file)

        f = open(file, "x")
        f.write(response['KeyMaterial'])
        f.close()

        os.chmod(file, stat.S_IREAD)

        print(f"{self.color.OKGREEN}Key Pair criada com sucesso{self.color.ENDC}")

    def createSecurityGroup(self, name:str, description:str, port_list:list):

        response = self.client.describe_secutity_groups(Filters = [
            {
                'Name' : 'group-name',
                'Values' : [name]
            }

        ])

        if response['SecurityGroups']:
            print(f"{self.color.WARNING}Apagando Security Group existente{self.color.ENDC}")

            response = self.client.delete_security_group(GroupName = name)

        print(f"{self.color.OKCYAN}Criando novo Security Group de nome: {name}{self.color.ENDC}")
        response = self.client.create_security_group(GroupName = name, Description = description)

        sg_id = response['GroupId']

        permissions = []

        for port in port_list:
            permissions.append({'IpProtocol': 'tcp',
                                 'FromPort': port,
                                 'ToPort': port,
                                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})
        
        response = self.client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=permissions)

        print(f"{self.color.OKGREEN}Security Group criado com sucesso{self.color.ENDC}")
        print(f"Name: {name} \n ID: {sg_id} \n Ports: {port_list}")

        return sg_id


    def createInstance(self, name:str, initial_script:str, Type: 't2.micro', key='victor_key', sg='default'):

        
        
        response = self.client.allocate_adress()
        instance_ip = response['PublicIp']

        response = self.client.run_instance(
            ImageId = self.imgId,
            InstanceType = Type,
            MinCount = 1,
            MaxCount = 1,
            KeyName = key,
            SecurityGroups = [sg],
            UserData = initial_script,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key'  : 'Name',
                        'Value':  name
                    },
                    {
                        'Key'  : 'Criador',
                        'Value': 'Victor'
                    }
                ]
            }]
        )

        instance_id = response['Instances'][0]["InstanceId"]

        print(f"{self.color.OKCYAN}Criando nova Instância de nome: {name}{self.color.ENDC}")

        waiter = self.client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        response = self.client.associate_address(InstanceId=instance_id, PublicIp=instance_ip)

        print(f"{self.color.OKGREEN}Instância criada com sucesso{self.color.ENDC}")
        print(f"Name: {name} \n ID: {instance_id} \n IP: {instance_ip}")

        return instance_ip
    
    def killAll (self):

        response = self.client.describe_instances(Filters = [
            {
                'Name' : 'tag:Criador',
                'Values' : ['Victor']
            },
            {
                'Name' : 'instance-state-name',
                'Values' : ['running']
            }
        ])

        inst_ips = []
        inst_ids = []

        for i in response['Reservations']:
            inst_ids.append(i['Instances'][0]['InstanceId'])
            inst_ips.append(i['Instances'][0]['PublicIpAddress'])
        
        for ip in inst_ips:
            response = self.client.describe_adresses(PublicIps = [ip])

            allocation = response['Adresses'][0]['AllocationId']

            response = self.client.release_adresses(AllocationId = allocation)
        
        print(f"{self.color.OKCYAN}Endereços liberados: \n {inst_ips}{self.color.ENDC}")

        for id in inst_ids:
            response = self.client.terminate_instances(InstanceId = [id])

            print(f"{self.color.WARNING}Terminando Instância {id}{self.color.ENDC}")

            waiter = self.client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[id])

            print(f"{self.color.OKCYAN}Instância {id} terminada{self.color.ENDC}")
        
        print(f"{self.color.OKGREEN}Todas as Instâncias de {self.region} foram terminadas{self.color.ENDC}")

