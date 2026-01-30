import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    ElementClickInterceptedException,
    TimeoutException,
    StaleElementReferenceException
)
from utils.logger import setup_logger

logger = setup_logger()

OUTPUT_DIR = "output"

def abrir_socged(driver, cpf, max_tentativas=3):
 
    wait = WebDriverWait(driver, 15)

    for tentativa in range(1, max_tentativas + 1):
        try:
            logger.info(f"[{cpf}] Tentativa {tentativa}/{max_tentativas} de abrir o SOCGED...")

            icone_ged = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//img[contains(@src, 'ged.png') or contains(@src, 'importt.png') or contains(@src, 'importar.png')]"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", icone_ged)
            time.sleep(0.3) 

            try:
                icone_ged.click() 
            except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
                logger.warning(f"[{cpf}] Clique normal no ícone GED falhou, tentando via JS.")
                driver.execute_script("arguments[0].click();", icone_ged)
            
            logger.info(f"[{cpf}] Ícone SOCGED clicado.")

            link_socged = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//h4[@id='socged']/a"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", link_socged)
            time.sleep(0.3)

            try:
                link_socged.click()
            except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
                logger.warning(f"[{cpf}] Clique normal no link SOCGED falhou, tentando via JS.")
                driver.execute_script("arguments[0].click();", link_socged)
            
            logger.info(f"[{cpf}] Link 'SOCGED' clicado com sucesso.")
            
            return True

        except TimeoutException:
            logger.warning(f"[{cpf}] Falha (Timeout) ao tentar abrir SOCGED na tentativa {tentativa}.")
            if tentativa == max_tentativas:
                logger.error(f"[{cpf}] Todas as tentativas (Timeout) de abrir o SOCGED falharam. Provavelmente sem ícone.")
                registrar_cpf(cpf, tipo="sem_icone") 
                return False
        
        except Exception as e:
            logger.warning(f"[{cpf}] Falha (Geral) ao abrir SOCGED na tentativa {tentativa}: {e}")
            if tentativa == max_tentativas:
                logger.error(f"[{cpf}] Todas as tentativas (Geral) de abrir o SOCGED falharam.")
                registrar_cpf(cpf, tipo="erro")
                return False

        time.sleep(2)

    return False


def registrar_cpf(cpf, tipo="erro", arquivos_baixados=0, total_arquivos=None):
  
    arquivos_map = {
        "sem_icone": "cpfs_sem_icone.txt",
        "inativo": "cpfs_inativos.txt",
        "erro": "cpfs_erros.txt",
        "interrompido": "cpfs_interrompidos_sessao.txt"
    }

    mensagens_map = {
        "sem_icone": f"{cpf} - CPF Não possui arquivos para baixar",
        "inativo": f"{cpf} - CPF Inativo ou não encontrado",
        "erro": f"{cpf} - CPF não enviado ao sharepoint",
    }

    caminho_arquivo_log = arquivos_map.get(tipo)
    if not caminho_arquivo_log:
        logger.error(f"Tipo de registro inválido: {tipo}")
        return

    caminho_completo = os.path.join(OUTPUT_DIR, caminho_arquivo_log)

    if tipo == "interrompido":
        if total_arquivos is not None and total_arquivos > 0:
            mensagem = f"CPF: {cpf} - Sessão expirada durante o download ({arquivos_baixados}/{total_arquivos} arquivos baixados)"
        else:
            mensagem = f"CPF: {cpf} - Sessão expirada durante o download (contagem indisponível)"
        logger_func = logger.error
    else:
        mensagem = mensagens_map.get(tipo, f"{cpf} - Status: {tipo}") # Fallback
        logger_func = logger.info

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(caminho_completo, "a", encoding="utf-8") as arquivo:
            arquivo.write(mensagem + "\n")
        
        logger_func(f"[{cpf}] Registrado: {mensagem}")
        
    except (IOError, OSError) as e:
        logger.error(f"[{cpf}] FALHA AO ESCREVER NO ARQUIVO DE LOG {caminho_completo}: {e}")
        logger.error(f"[{cpf}] Mensagem que falhou ao registrar: {mensagem}")