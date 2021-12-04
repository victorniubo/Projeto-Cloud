import requests
from client import Client
import click
import json
import datetime
import sys

client = Client("us-east-1")
response = client.loadbalancer.describe_load_balancers(
                
            Names=[
                'loadbalancerV'
            ]
        )
if response['LoadBalancers']:
    
    dns = response['LoadBalancers'][0]['DNSName']

url = 'http://{}/tasks'.format(dns)

instruction =  sys.argv[1]

if instruction == "get":
    r = requests.get(url + "/get")
    print("\n Log: ", r.text)



if instruction == "post":
    titulo = str(input("Título da Task: "))
    date=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    desc = str(input("Descrição da Task: "))
    payload = {
        "title":titulo,
        "pub_date":date,
        "description":desc
    }
    r = requests.post(url + "/post", json=payload)
    print("\n Log: ", r.text)

if instruction == "delete":
    r = requests.delete(url + "/delete")
    print("\n Log: ", r.text)