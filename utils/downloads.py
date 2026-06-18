import os
import shutil 
from pathlib import Path
import time
import re
from utils.logger import setup_logger
import zipfile 
from utils.onedrive_uploader import upload_folder_to_sharepoint

logger = setup_logger()


PASTA_DOWNLOAD_PADRAO = r"C:\Users\taina.ribeiro\OneDrive - Pague Menos Comercio de Produtos Alimenticios Ltda\Documentos\Dev\Automações\SOC_REP\downloads"
DOWNLOAD_DIR = Path(PASTA_DOWNLOAD_PADRAO)

def garantir_pasta_download():
    if not DOWNLOAD_DIR.exists():
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR

def esperar_download_e_mover(nome_final_com_extensao: str, pasta_destino_matricula: str, timeout_segundos=120):

    if not os.path.exists(pasta_destino_matricula):
        os.makedirs(pasta_destino_matricula, exist_ok=True)

    caminho_final = Path(pasta_destino_matricula) / nome_final_com_extensao
    
    if caminho_final.exists():
        logger.warning(f"Arquivo '{caminho_final.name}' já existe. Gerando nome alternativo.")
        base, ext = os.path.splitext(nome_final_com_extensao)
        contador = 1
        while True:
            novo_nome = f"{base} ({contador}){ext}"
            novo_caminho = Path(pasta_destino_matricula) / novo_nome
            if not novo_caminho.exists():
                caminho_final = novo_caminho
                break
            contador += 1
        logger.info(f"Arquivo será salvo como '{caminho_final.name}'.")

    caminho_zip_esperado = DOWNLOAD_DIR / "consulta.zip"
    tempo_inicio = time.time()
    download_concluido = False
    
    logger.info("Aguardando download do arquivo 'consulta.zip'...")
    while time.time() - tempo_inicio < timeout_segundos:
        if caminho_zip_esperado.exists():
            time.sleep(1) # Pausa para garantir que o arquivo foi completamente escrito
            logger.info(f"Arquivo '{caminho_zip_esperado.name}' detectado.")
            download_concluido = True
            break
        time.sleep(0.3)
    
    if not download_concluido:
        raise FileNotFoundError(f"Timeout: O arquivo 'consulta.zip' não foi encontrado em {timeout_segundos}s.")
    
    # 2. Processa o arquivo 'consulta.zip'
    try:
        logger.info(f"Processando '{caminho_zip_esperado.name}'...")
        with zipfile.ZipFile(caminho_zip_esperado, 'r') as zip_ref:
            lista_arquivos_zip = zip_ref.namelist()
            if not lista_arquivos_zip:
                raise zipfile.BadZipFile("Arquivo ZIP está vazio.")
            
            nome_arquivo_interno = lista_arquivos_zip[0]
            logger.info(f"Extraindo '{nome_arquivo_interno}' do ZIP...")
            
            # Extrai o arquivo para a pasta de downloads principal temporariamente
            caminho_extraido_temp = Path(zip_ref.extract(nome_arquivo_interno, path=DOWNLOAD_DIR))
        
        # Move o arquivo extraído para a pasta de destino da matrícula com o nome final correto
        shutil.move(str(caminho_extraido_temp), str(caminho_final))
        logger.info(f"Arquivo extraído e salvo em: {caminho_final}")
        
        # Remove o arquivo .zip após o sucesso
        os.remove(caminho_zip_esperado)
        logger.info(f"Arquivo '{caminho_zip_esperado.name}' removido.")
        
        return str(caminho_final)
    
    except Exception as e:
        logger.error(f"Falha ao processar o arquivo ZIP: {e}")
        # Tenta limpar o zip mesmo em caso de erro de extração
        if caminho_zip_esperado.exists():
            os.remove(caminho_zip_esperado)
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
