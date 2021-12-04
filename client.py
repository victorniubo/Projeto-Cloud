import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import sys, os, stat
import subprocess as sp
from cores import bcolors
import time

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

        self.loadbalancer = boto3.client('elbv2', config=self.aws_config)

        self.autoscaling = boto3.client("autoscaling", config=self.aws_config)

    
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

            print(f"{self.color.OKCYAN}Key Pair {name} deletada{self.color.ENDC}")
    
        print(f"{self.color.HEADER}Gerando nova Key Pair de nome: {name}{self.color.ENDC}")
        response = self.client.create_key_pair(KeyName=name)

        if os.path.exists(file):
            os.remove(file)

        f = open(file, "x")
        f.write(response['KeyMaterial'])
        f.close()

        os.chmod(file, stat.S_IREAD)

        print(f"{self.color.OKGREEN}Key Pair criada com sucesso{self.color.ENDC}")

        return name

    def createSecurityGroup(self, name:str, description:str, port_list:list):

        response = self.client.describe_security_groups(Filters = [
            {
                'Name' : 'group-name',
                'Values' : [name]
            }

        ])

        if response['SecurityGroups']:
            print(f"{self.color.WARNING}Apagando Security Group existente{self.color.ENDC}")

            response = self.client.delete_security_group(GroupName = name)
            print(f"{self.color.OKCYAN}Security Group {name} deletado{self.color.ENDC}")

        print(f"{self.color.HEADER}Criando novo Security Group de nome: {name}{self.color.ENDC}")
        response = self.client.create_security_group(GroupName = name, Description = description)

        sg_id = response['GroupId']

        permissions = []

        for port in port_list:
            permissions.append({'IpProtocol': 'tcp',
                                 'FromPort': port,
                                 'ToPort': port,
                                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})
        
        response = self.client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=permissions)

        waiter = self.client.get_waiter('security_group_exists')
        waiter.wait(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [
                        name,
                    ]
                },
            ]
            
        )

        print(f"{self.color.OKGREEN}Security Group criado com sucesso{self.color.ENDC}")
        print(f"Name: {name} \n ID: {sg_id} \n Ports: {port_list}")

        return sg_id


    def createInstance(self, name:str, initial_script:str, InstType = 't2.micro', key = 'victor_key', sg = 'default'):

        
        
        response = self.client.allocate_address()
        instance_ip = response['PublicIp']

        response = self.client.run_instances(
            ImageId = self.imgId,
            InstanceType = InstType,
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

        print(f"{self.color.HEADER}Criando nova Instância de nome: {name}{self.color.ENDC}")

        waiter = self.client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[instance_id])

        response = self.client.associate_address(InstanceId=instance_id, PublicIp=instance_ip)

        print(f"{self.color.OKGREEN}Instância criada e funcionando com sucesso{self.color.ENDC}")
        print(f"Name: {name} \n ID: {instance_id} \n IP: {instance_ip}")

        return instance_ip, instance_id
    
    def killAll (self):

        if self.region == 'us-east-1':
            response = self.client.describe_instances(Filters = [
                {
                    'Name' : 'tag:Name',
                    'Values' : ['autoscaled_v']
                },
            ])

            if response['Reservations']:

                as_ids = []
                for inst in response['Reservations']:
                    
                    as_ids.append(inst['Instances'][0]['InstanceId'])

                for id in as_ids:

                    response = self.client.terminate_instances(InstanceIds = [id])

                    print(f"{self.color.WARNING}Terminando Instância AS{id}{self.color.ENDC}")


            self.autoscaling.delete_auto_scaling_group(AutoScalingGroupName='autoscalingV', ForceDelete=True)

            # self.autoscaling.delete_launch_configuration(LaunchConfigurationName='launchconfigV')



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
        
        if response['Reservations']:

            inst_ips = []
            inst_ids = []

            for inst in response['Reservations']:
                inst_ips.append(inst['Instances'][0]['PublicIpAddress'])
                inst_ids.append(inst['Instances'][0]['InstanceId'])
            
            for ip in inst_ips:
                response = self.client.describe_addresses(PublicIps = [ip])

                allocation = response['Addresses'][0]['AllocationId']

                response = self.client.release_address(AllocationId = allocation)
            
            print(f"{self.color.OKCYAN}Endereços liberados: \n {inst_ips}{self.color.ENDC}")

            for id in inst_ids:
                response = self.client.terminate_instances(InstanceIds = [id])

                print(f"{self.color.WARNING}Terminando Instância {id}{self.color.ENDC}")

                waiter = self.client.get_waiter('instance_terminated')
                waiter.wait(InstanceIds=[id])

                print(f"{self.color.OKCYAN}Instância {id} terminada{self.color.ENDC}")
            
            print(f"{self.color.OKGREEN}Todas as Instâncias de {self.region} foram terminadas{self.color.ENDC}")

        else:
            print(f"{self.color.WARNING}Não existe nenhuma instância sua em {self.region}{self.color.ENDC}")
        
        

        # try:
        #     response = self.loadbalancer.describe_load_balancers(
                
        #         Names=[
        #             'loadbalancerV'
        #         ]
        #     )
        #     if response['LoadBalancers']:
        #         print(f"{self.color.WARNING}Apagando Load Balancer: {'loadbalancerV'}{self.color.ENDC}")
        #         lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
        #         response = self.loadbalancer.delete_load_balancer(
        #             LoadBalancerArn = lb_arn
        #         )
        # except:
        #     pass

    def killDjango(self):
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
        
        if response['Reservations']:

            inst_ips = []
            inst_ids = []

            for inst in response['Reservations']:
                inst_ips.append(inst['Instances'][0]['PublicIpAddress'])
                inst_ids.append(inst['Instances'][0]['InstanceId'])
            
            for ip in inst_ips:
                response = self.client.describe_addresses(PublicIps = [ip])

                allocation = response['Addresses'][0]['AllocationId']

                response = self.client.release_address(AllocationId = allocation)
            
            print(f"{self.color.OKCYAN}Endereços liberados: \n {inst_ips}{self.color.ENDC}")

            for id in inst_ids:
                response = self.client.terminate_instances(InstanceIds = [id])

                print(f"{self.color.WARNING}Terminando Instância {id}{self.color.ENDC}")

                waiter = self.client.get_waiter('instance_terminated')
                waiter.wait(InstanceIds=[id])

                print(f"{self.color.OKCYAN}Instância {id} terminada{self.color.ENDC}")
            
            print(f"{self.color.OKGREEN}Todas as Instâncias de {self.region} foram terminadas{self.color.ENDC}")

    def createIMG (self, name:str, description:str, instanceID: str):

        response = self.client.describe_images(
         
            Filters=[
                {
                    'Name': 'name',
                    'Values': [
                        name
                    ]
                },
            ]
        )
        if response['Images']:
            print(f"{self.color.WARNING}Apagando Imagem: {name}{self.color.ENDC}")
            response = self.client.deregister_image(ImageId=response['Images'][0]['ImageId'])
            print(f"{self.color.OKCYAN}Imagem {name} deletada{self.color.ENDC}")

        print(f"{self.color.HEADER}Criando nova Imagem de nome: {name}{self.color.ENDC}")

        response = self.client.create_image(
       
            Description= description,

            InstanceId = instanceID,

            Name = name,
    
            TagSpecifications=[
                {
                    'ResourceType':'image',
                    'Tags': [
                        {
                            'Key': 'Criador',
                            'Value': 'Victor'
                        },
                    ]
                },
            ]
        )
        # self.ec2_resource.Image(response["ImageId"]).wait_until_exists()
        waiter = self.client.get_waiter("image_available")
        waiter.wait(ImageIds=[response["ImageId"]])
        print(f"{self.color.OKGREEN}Imagem criada com sucesso{self.color.ENDC}")

        return response['ImageId']
    
    def createTargetGroup (self, tg_name:str):
        try:
            response = self.loadbalancer.describe_target_groups(
                
                Names=[
                    tg_name
                ]
            )
            if response['TargetGroups']:
                print(f"{self.color.WARNING}Apagando Target Group: {tg_name}{self.color.ENDC}")
                tg_arn = response['TargetGroups'][0]['TargetGroupArn']
                response = self.loadbalancer.delete_target_group(
                    TargetGroupArn = tg_arn
                )
                print(f"{self.color.OKCYAN}Target Group {tg_name} deletado{self.color.ENDC}")
            else:
                print(f"{self.color.WARNING}Não existe nenhum Target Group com nome: {tg_name}{self.color.ENDC}")
        except:
            print(f"{self.color.WARNING}Não existe nenhum Target Group com nome: {tg_name}{self.color.ENDC}")
            pass
        
        

        print(f"{self.color.HEADER}Criando novo Target Group de nome: {tg_name}{self.color.ENDC}")


        response = self.loadbalancer.create_target_group(
            Name=tg_name,
            Protocol='HTTP',
            ProtocolVersion='HTTP1',
            Port=8080,
            VpcId='vpc-40ea2a3a',
            
            TargetType='instance',
            Tags=[
                {
                    'Key': 'Criador',
                    'Value': 'Victor'
                },
            ],
        )

        print(f"{self.color.OKGREEN}Target Group {tg_name} criado com sucesso{self.color.ENDC}")

        response = self.loadbalancer.describe_target_groups(
                
                Names=[
                    tg_name
                ]
            )
        if response['TargetGroups']:
            
            tg_arn_real = response['TargetGroups'][0]['TargetGroupArn']
            print(tg_arn_real)


        return tg_arn_real


    def createLoadBalancer (self, lb_name:str, scrt_group_id: str):
        
        
        try:
            response = self.loadbalancer.describe_load_balancers(
                
                Names=[
                    lb_name
                ]
            )
            if response['LoadBalancers']:
                print(f"{self.color.WARNING}Apagando Load Balancer: {lb_name}{self.color.ENDC}")
                lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
                response = self.loadbalancer.delete_load_balancer(
                    LoadBalancerArn = lb_arn
                )
                print(f"{self.color.OKCYAN}Load Balancer {lb_name} deletado{self.color.ENDC}")
            else:
                print(f"{self.color.WARNING}Não existe nenhum LoadBalancer com nome: {lb_name}{self.color.ENDC}")
        except:
            print(f"{self.color.WARNING}Não existe nenhum Load Balancer com nome: {lb_name}{self.color.ENDC}")
            pass


        
        
        print(f"{self.color.HEADER}Criando novo Load Balancer de nome: {lb_name}{self.color.ENDC}")

        response = self.loadbalancer.create_load_balancer(
            Name = lb_name,
            Subnets=[
                'subnet-9b93d2d1', 'subnet-9d8230c1', 'subnet-52d46435', 'subnet-0758e429', 'subnet-5da66163', 'subnet-7b196e74'
            ],
            
            SecurityGroups=[
                scrt_group_id,
            ],
            Scheme='internet-facing',
            Tags=[
                {
                    'Key': 'Criador',
                    'Value': 'Victor'
                },
            ],
            Type='application',
            IpAddressType='ipv4',
        )
        response = self.loadbalancer.describe_load_balancers(
                
            Names=[
                lb_name
            ]
        )
        if response['LoadBalancers']:
            
            lb_arn_real = response['LoadBalancers'][0]['LoadBalancerArn']
            dns = response['LoadBalancers'][0]['DNSName']

        waiter = self.loadbalancer.get_waiter("load_balancer_available")
        waiter.wait(
            Names=[
                lb_name
            ]
        )

        print(f"{self.color.OKGREEN}Load Balancer criado com sucesso: \n {dns}{self.color.ENDC}")

        return lb_arn_real
    
    def deleteLoadBalancer(self, lb_name:str):
        try:
            response = self.loadbalancer.describe_load_balancers(
                
                Names=[
                    lb_name
                ]
            )
            if response['LoadBalancers']:
                print(f"{self.color.WARNING}Apagando Load Balancer: {lb_name}{self.color.ENDC}")
                lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
                response = self.loadbalancer.delete_load_balancer(
                    LoadBalancerArn = lb_arn
                )
                print(f"{self.color.OKCYAN}Load Balancer {lb_name} deletado{self.color.ENDC}")
            else:
                print(f"{self.color.WARNING}Não existe nenhum LoadBalancer com nome: {lb_name}{self.color.ENDC}")
        except:
            print(f"{self.color.WARNING}Não existe nenhum Load Balancer com nome: {lb_name}{self.color.ENDC}")
            pass

        waiter = self.loadbalancer.get_waiter('load_balancers_deleted')
        waiter.wait(
            Names=[
                lb_name
            ]
        )
        time.sleep(60)
        print(f"{self.color.OKCYAN}Load Balancer {lb_name} deletado{self.color.ENDC}")

    def createListener(self, lb_arn, tg_arn):

        try:
            response = self.loadbalancer.describe_listeners(LoadBalancerArn=lb_arn)['Listeners'][0]['ListenerArn']
            if response:
                print(f"{self.color.WARNING}Apagando Listener{self.color.ENDC}")
                self.loadbalancer.delete_listener(ListenerArn=response)

        except:
            print(f"{self.color.WARNING}Não existe nenhum Listener ativo{self.color.ENDC}")
            pass

        print(f"{self.color.HEADER}Criando novo Listener{self.color.ENDC}")

        response = self.loadbalancer.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=80,
            
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': tg_arn,
                },
            ],    
        )
        print(f"{self.color.OKGREEN}Listener criado com sucesso{self.color.ENDC}")

        
    
    def createAutoScaling(self, AS_name:str, LC_name:str, img_id:str, key:str, scrt_group_name:str, tg_arn:str):

        try:


            self.autoscaling.delete_launch_configuration(LaunchConfigurationName='launchconfigV')

        except:
            print(f"{self.color.WARNING}Não existe nenhum Launch Configuration ou AutoScaling com nomes: {LC_name} e {AS_name}{self.color.ENDC}")
            pass

        print(f"{self.color.HEADER}Criando Launch Configuration de nome: {LC_name}{self.color.ENDC}")
        
        response = self.autoscaling.create_launch_configuration(
            LaunchConfigurationName=LC_name,
            ImageId=img_id,
            KeyName=key,
            SecurityGroups=[
                scrt_group_name,
            ],
            InstanceType='t2.micro'
        )
        print(f"{self.color.OKCYAN}Launch Configuration {LC_name} criada{self.color.ENDC}")

        print(f"{self.color.HEADER}Criando AutoScaling de nome: {AS_name}{self.color.ENDC}")

        response = self.autoscaling.create_auto_scaling_group(
            AutoScalingGroupName = AS_name,
            LaunchConfigurationName=LC_name,
            
            MinSize=1,
            MaxSize=5,
            
            AvailabilityZones=[
                'us-east-1d', 'us-east-1c', 'us-east-1e', 'us-east-1f', 'us-east-1a', 'us-east-1b'
            ],
            TargetGroupARNs=[
                tg_arn,
            ],
            
            Tags=[
                
                {
                    'Key': 'Name',
                    'Value': 'austoscaled_v'
                },
              
             
            ],
            
        )

        print(f"{self.color.OKCYAN}AutoScaling {AS_name} criada{self.color.ENDC}")