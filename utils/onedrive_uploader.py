import os
import time
import msal
import json 
import zipfile
import tempfile
import requests

from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote
from utils.logger import setup_logger
from config.settings import GRAPH_CLIENT

from utils.logger import setup_logger


logger = setup_logger()

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / 'config' / '.env' 

load_dotenv(dotenv_path=DOTENV_PATH)

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DRIVE_ID = os.getenv("DRIVE_ID")

logger.debug(f"DEBUG: TENANT_ID lido: {TENANT_ID}")
logger.debug(f"DEBUG: DRIVE_ID lido: {DRIVE_ID}")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = ["https://graph.microsoft.com/.default"]

RETRYABLE_STATUS_CODES = [
    400, 
    429,  
    500,  
    503,
    504  
]

BASE_FOLDER_SHAREPOINT = "104 - Arquivos Migração/Medicina e Segurança/Documentos Físicos"

def get_access_token():
    """Gera o token de acesso para o Microsoft Graph API"""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        return result["access_token"]
    else:
        logger.error(f"Erro ao obter token: {result.get('error_description')}")
        raise Exception("Falha na autenticação com o SharePoint")


def upload_folder_to_sharepoint(local_folder_path, remote_folder_name):
    """
    Faz upload de todos os arquivos de uma pasta local para o SharePoint.
    """
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    full_remote_path = f"{BASE_FOLDER_SHAREPOINT}/{remote_folder_name}" if BASE_FOLDER_SHAREPOINT else remote_folder_name
    
    sucesso_total = True
    
    for root, _, files in os.walk(local_folder_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            file_name = os.path.basename(local_file_path)

            file_path_encoded = quote(f"{full_remote_path}/{file_name}")
            url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{file_path_encoded}:/content"
            
            logger.info(f"Enviando: {file_name}...")
            
            try:
                with open(local_file_path, 'rb') as f:
                    file_content = f.read()
                
                response = requests.put(url, headers=headers, data=file_content)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Upload sucesso: {file_name}")
                else:
                    logger.error(f"Erro upload {file_name}: {response.status_code} - {response.text}")
                    sucesso_total = False
            except Exception as e:
                logger.error(f"Exceção no upload de {file_name}: {e}")
                sucesso_total = False
                
    return sucesso_total


def listar_conteudo_pasta_com_zips(matricula):
  
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    caminho_pasta = f"{BASE_FOLDER_SHAREPOINT}/{matricula}" if BASE_FOLDER_SHAREPOINT else matricula
    caminho_encoded = quote(caminho_pasta) 
    
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{caminho_encoded}:/children"
    
    logger.info(f"[{matricula}] Consultando SharePoint: {caminho_pasta} ...")
    
    response = requests.get(url, headers=headers)
    
    lista_final = []
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        logger.info(f"[{matricula}] Encontrados {len(items)} itens na pasta remota.")
        
        for item in items:
            nome = item['name']
            download_url = item.get('@microsoft.graph.downloadUrl')
            
            if nome.lower().endswith('.zip') and download_url:
                logger.info(f"[{matricula}] Inspecionando ZIP: {nome}...")
                try:
                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                        with requests.get(download_url, stream=True) as r:
                            r.raise_for_status()
                            for chunk in r.iter_content(chunk_size=8192):
                                tmp_file.write(chunk)
                        tmp_path = tmp_file.name
                    
                    with zipfile.ZipFile(tmp_path, 'r') as zf:
                        conteudo_zip = zf.namelist()
                        logger.info(f"   -> Conteúdo de {nome}: {conteudo_zip}")
                        lista_final.extend(conteudo_zip)
                        lista_final.append(nome)
                    
                    os.remove(tmp_path)
                    
                except Exception as e:
                    logger.error(f"Erro ao ler ZIP {nome}: {e}")
                    lista_final.append(nome)
            else:
                lista_final.append(nome)
                
    elif response.status_code == 404:
        logger.info(f"[{matricula}] Pasta não encontrada no SharePoint (será criada no upload).")
    else:
        logger.error(f"Erro API SharePoint ({response.status_code}): {response.text}")

    return lista_final


def listar_arquivos_simples(matricula):
    
    if not GRAPH_CLIENT:
        print("Erro: GRAPH_CLIENT não foi iniciado.")
        return []

    try:
     
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/downloads/{matricula}:/children"
        
        resposta = GRAPH_CLIENT.get(url)
        
        if resposta.status_code == 200:
            return resposta.json().get('value', [])
        elif resposta.status_code == 404:
            return []
        else:
            print(f"Erro na API Graph: {resposta.status_code} - {resposta.text}")
            return []
            
    except Exception as e:
        print(f"Exceção ao listar arquivos: {e}")
        return []