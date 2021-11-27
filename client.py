import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import os
import time
import subprocess as sp

class Client:

    def __init__(self, region:str):

        self.region = region

        if region == 'us-east-1':
            self.img = 'ami-0279c3b3186e54acd'
        
        if region == 'us-east-2':
            self.img = 'ami-020db2c14939a8efb'


        self.aws_config = Config(region_name = region)