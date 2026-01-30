import os
import shutil 
from pathlib import Path
import time
import re
from utils.logger import setup_logger
from utils.onedrive_uploader import upload_folder_to_sharepoint

logger = setup_logger()


PASTA_DOWNLOAD_PADRAO = r"C:\Users\taina.ribeiro\OneDrive - Pague Menos Comercio de Produtos Alimenticios Ltda\Documentos\Dev\Automações\SOC_REP\downloads"
DOWNLOAD_DIR = Path(PASTA_DOWNLOAD_PADRAO)

def garantir_pasta_download():
    if not DOWNLOAD_DIR.exists():
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR

def renomear_e_mover_arquivo(nome_final_com_extensao: str, pasta_destino_matricula: str):

    try:
        if not os.path.exists(pasta_destino_matricula):
            os.makedirs(pasta_destino_matricula, exist_ok=True)

        extensoes_temp = [".crdownload", ".tmp", ".part", ".inprogress", ".download"]
        
        ultimo_arquivo = None
        for _ in range(10):
            arquivos = [
                f for f in DOWNLOAD_DIR.glob("*") 
                if f.is_file() and f.suffix.lower() not in extensoes_temp
            ]
            if arquivos:
                ultimo_arquivo = max(arquivos, key=os.path.getmtime)
                break
            time.sleep(1)
        
        if not ultimo_arquivo:
            raise Exception(f"Nenhum arquivo encontrado em {DOWNLOAD_DIR} após o download.")

        caminho_final = Path(pasta_destino_matricula) / nome_final_com_extensao

        if caminho_final.exists():
            os.remove(caminho_final)

        shutil.move(str(ultimo_arquivo), str(caminho_final))
        
        logger.info(f"Arquivo organizado em: {caminho_final}")
        return str(caminho_final)

    except Exception as e:
        logger.error(f"Erro ao mover/renomear arquivo: {e}")
        raise e

def limpar_downloads_incompletos_cpf(matricula: str):
    subpasta_local = DOWNLOAD_DIR / str(matricula)
    if subpasta_local.exists():
        shutil.rmtree(subpasta_local, ignore_errors=True)

def enviar_e_limpar_arquivos_cpf(matricula: str):
    subpasta_local = DOWNLOAD_DIR / str(matricula)
    
    if not subpasta_local.exists():
         logger.info(f"Nenhum arquivo local baixado para a matrícula {matricula}. Nada a enviar.")
         return True

    arquivos_locais = list(subpasta_local.glob("*.*"))

    if not arquivos_locais:
        logger.info(f"A pasta {subpasta_local} existe mas está vazia. Nada para enviar.")
        shutil.rmtree(subpasta_local, ignore_errors=True)
        return True

    logger.info(f"*** INICIANDO UPLOAD PARA A MATRÍCULA: {matricula} ***")
    logger.info(f"Enviando {len(arquivos_locais)} arquivos de {subpasta_local}...")
    sucesso = upload_folder_to_sharepoint(str(subpasta_local), str(matricula))

    if sucesso:
        logger.info(f"Upload concluído. Limpando pasta local...")
        shutil.rmtree(subpasta_local, ignore_errors=True)
    else:
        logger.error(f"Falha no upload da Matrícula {matricula}.")

    return sucesso

