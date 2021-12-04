from client import Client

client_postgres = Client("us-east-2")
client_postgres.killAll()

client_django = Client("us-east-1")
client_django.killAll()

client_postgres.createKeyPair("postgres_key_v")
client_postgres.createSecurityGroup("Postgres_SG", "Security Group do Postgres", [22, 80, 8080, 5432])
postgresIp, postgresId = client_postgres.createInstance(name="Postgres_v", initial_script=open("postgres.sh", "r").read(), sg="Postgres_SG", key='postgres_key_v')

key_name = client_django.createKeyPair("django_key_v")
client_django.createSecurityGroup("Django_SG", "Security Group do Django", [22, 80, 8080])
djangoIp, djangoId = client_django.createInstance(name="Django_v", initial_script=open("django.sh", "r").read().replace("postgresIp", postgresIp), sg="Django_SG", key='django_key_v')
img_id = client_django.createIMG('DjangoIMG', "Imagem de instancia com Django instalado", djangoId)
client_django.killDjango()

tg_arn = client_django.createTargetGroup('targetgroupV')
client_django.deleteLoadBalancer('loadbalancerV')
sg_id = client_django.createSecurityGroup('LoadBalancer_SG', "Security Group do Load Balancer", [22, 80, 8080])
lb_arn = client_django.createLoadBalancer('loadbalancerV', sg_id)

client_django.createListener(lb_arn, tg_arn)
client_django.createSecurityGroup('AutoScaling_SG', 'Security Group do AutoScaler', [80, 8080])
client_django.createAutoScaling('autoscalingV', 'launchconfigV', img_id, key_name, 'AutoScaling_SG', tg_arn)