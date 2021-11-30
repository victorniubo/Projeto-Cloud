from client import Client

client_postgres = Client("us-east-2")
client_postgres.killAll()

# client_django = Client("us-east-1")
# client_django.killAll()

# client_postgres.createKeyPair("postgres_key_v")
client_postgres.createSecurityGroup("Postgres_SG", "Security Group do Postgres", [22, 80, 8080, 5432])
# postgresIp = client_postgres.createInstance(name="Postgres_v", initial_script=open("postgres.sh", "r").read(), sg="Postgres_SG", key='postgres_key_v')

# client_django.createKeyPair("django_key_v")
# client_django.createSecurityGroup("Django_SG", "Security Group do Django", [22, 80, 8080])
# djangoIp = client_django.createInstance(name="Django_v", initial_script=open("django.sh", "r").read().replace("postgresIp", postgresIp), sg="Django_SG", key='django_key_v')

