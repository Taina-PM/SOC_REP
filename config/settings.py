import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

BASE_URL = os.getenv("SOC_BASE_URL", "https://sistema.soc.com.br/WebSoc/")
USER = os.getenv("SOC_USER")
PASSWORD = os.getenv("SOC_PASSWORD")
EMPRESA_ID = os.getenv("SOC_EMPRESA_ID", "6263")

DEFAULT_WAIT = int(os.getenv("DEFAULT_WAIT", "15"))

import os
import requests
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential


# --- NOVA CONFIGURAÇÃO: MICROSOFT GRAPH ---
MS_CLIENT_ID = os.getenv("CLIENT_ID")
MS_TENANT_ID = os.getenv("TENANT_ID")
MS_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DRIVE_ID = os.getenv("DRIVE_ID") # Note que aqui definimos o DRIVE_ID que seu código pede

GRAPH_CLIENT = None

# Lógica de Autenticação Automática
if MS_CLIENT_ID and MS_CLIENT_SECRET and MS_TENANT_ID:
    try:
        print("Autenticando no Microsoft Graph...")
        # 1. Cria a credencial
        credential = ClientSecretCredential(
            tenant_id=MS_TENANT_ID,
            client_id=MS_CLIENT_ID,
            client_secret=MS_CLIENT_SECRET
        )
        
        # 2. Pega o Token
        token_object = credential.get_token('https://graph.microsoft.com/.default')
        
        # 3. Cria a sessão HTTP pronta para uso
        GRAPH_CLIENT = requests.Session()
        GRAPH_CLIENT.headers.update({
            'Authorization': f'Bearer {token_object.token}',
            'Content-Type': 'application/json'
        })
        print("Graph API: Conectado com sucesso.")
    except Exception as e:
        print(f"AVISO: Falha ao conectar no Graph API: {e}")
        GRAPH_CLIENT = None
else:
    print("AVISO: Credenciais do Microsoft Graph não encontradas no .env")