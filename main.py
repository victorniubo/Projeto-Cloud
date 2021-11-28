from client import Client

client = Client("us-east-2")
client.killAll()

# client.createKeyPair("vic_key")
# client.createSecurityGroup("SG_Teste", "Descricao blabla", [22, 80, 8080])
# clientIp = client.createInstance("Teste_v", "", sg="SG_Teste")

