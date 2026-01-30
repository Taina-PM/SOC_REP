import time
import re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, UnexpectedAlertPresentException, NoAlertPresentException

from utils.downloads import garantir_pasta_download, renomear_e_mover_arquivo, PASTA_DOWNLOAD_PADRAO
from utils.logger import setup_logger
from automation.socged_actions import registrar_cpf
from utils.alert_handler import wait_for_alert_and_handle

logger = setup_logger()

def limpar_string_comparacao(nome):

    if not nome:
        return ""
    
    nome = nome.lower()
    nome = re.sub(r'[^a-z0-9]', '', nome)
    
 
    extensoes = ['pdf', 'jpg', 'jpeg', 'png', 'zip', 'rar', '7z']
   
    mudou = True
    while mudou:
        mudou = False
        for ext in extensoes:
            if nome.endswith(ext):
                nome = nome[:-len(ext)]
                mudou = True 
    
    return nome

def limpar_nome_arquivo_windows(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def baixar_todos_documentos_modal(driver, cpf, matricula, arquivos_existentes=None, tempo_espera=20):
    
    if arquivos_existentes is None:
        arquivos_existentes = []

    lista_existentes_limpa = [limpar_string_comparacao(f) for f in arquivos_existentes]
    
    logger.debug(f"[{cpf}] Lista SharePoint Limpa para Comparação: {lista_existentes_limpa}")

    pasta_destino_matricula = os.path.join(PASTA_DOWNLOAD_PADRAO, str(matricula))

    garantir_pasta_download()
    driver.switch_to.default_content()

    tabela_iframe = None
    arquivos_baixados_sessao = 0
    icones = []

    for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
        driver.switch_to.default_content()
        driver.switch_to.frame(iframe)
        try:
            icones = WebDriverWait(driver, 1).until(
                EC.presence_of_all_elements_located((By.XPATH, "//td[@class='campo']/a[contains(@href, 'listarArquivosModal')]"))
            )
            tabela_iframe = iframe
            break
        except Exception:
            driver.switch_to.default_content()
            continue

    if not tabela_iframe or not icones:
        logger.info(f"[{cpf}] Nenhum ícone de importação encontrado. Registrando como sem ícone.")
        registrar_cpf(cpf, tipo="sem_icone")
        return

    for idx_icone, icone in enumerate(icones, start=1):
        try:
            driver.switch_to.default_content()
            WebDriverWait(driver, tempo_espera).until(EC.frame_to_be_available_and_switch_to_it(tabela_iframe))
            
            icone_atualizado = driver.find_elements(By.XPATH, "//td[@class='campo']/a[contains(@href, 'listarArquivosModal')]")[idx_icone - 1]
            driver.execute_script("arguments[0].scrollIntoView(true);", icone_atualizado)
            driver.execute_script("arguments[0].click();", icone_atualizado)
            time.sleep(2)

            iframe_modal = None
            driver.switch_to.default_content()
            for frame in driver.find_elements(By.TAG_NAME, "iframe"):
                driver.switch_to.frame(frame)
                if driver.find_elements(By.ID, "tabelaListaArquivos"):
                    iframe_modal = frame
                    break
                driver.switch_to.default_content()

            if not iframe_modal:
                try: 
                    driver.switch_to.alert.accept() 
                except: pass
                continue

            links = driver.find_elements(By.XPATH, "//td[contains(@class, 'td-nome-arquivo')]//a[starts-with(@href, 'javascript:download')]")
            
            if not links:
                try: driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(@href, 'fechar')]"))
                except: pass
                driver.switch_to.default_content()
                continue

            lista_downloads = []
            for i, link in enumerate(links):
                lista_downloads.append({"index": i, "nome_raw": link.text.strip()})

            for item in lista_downloads:
                nome_original = item["nome_raw"]
                
                nome_limpo_windows = limpar_nome_arquivo_windows(nome_original)
                if not nome_limpo_windows.lower().endswith('.pdf'):
                    nome_final = f"{nome_limpo_windows}.pdf"
                else:
                    nome_final = nome_limpo_windows
                
              
                nome_comparacao = limpar_string_comparacao(nome_final)
                
                if nome_comparacao in lista_existentes_limpa:
                    logger.info(f" >> [PULANDO] '{nome_final}' já identificado no SharePoint (Match: {nome_comparacao}).")
                    continue

                sucesso = False
                for tentativa in range(1, 4):
                    try:
                        logger.info(f"[{cpf}] Baixando: {nome_final}")
                        
                        link_click = WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, "//td[contains(@class, 'td-nome-arquivo')]//a[starts-with(@href, 'javascript:download')]")
                            )
                        )[item["index"]]

                        driver.execute_script("arguments[0].scrollIntoView(true);", link_click)
                        driver.execute_script("arguments[0].click();", link_click)
                        
                        wait_for_alert_and_handle(driver)
                        time.sleep(5) 

                        renomear_e_mover_arquivo(nome_final, pasta_destino_matricula)
                        
                        arquivos_baixados_sessao += 1
                        sucesso = True
                        break

                    except Exception as e:
                        logger.warning(f"Erro ao baixar (Tentativa {tentativa}): {e}")
                        driver.switch_to.default_content()
                        try:
                            WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it(iframe_modal))
                        except: pass
                
                if not sucesso:
                    logger.error(f"[{cpf}] Falha ao baixar {nome_final}.")
                    registrar_cpf(cpf, tipo="erro")

            try:
                driver.switch_to.default_content()
                WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe_modal))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(@href, 'fechar')]"))
            except: pass

        except Exception as e:
            logger.error(f"Erro no loop de ícones: {e}")
            continue
        finally:
            driver.switch_to.default_content()

    logger.info(f"[{cpf}] Download finalizado. {arquivos_baixados_sessao} novos arquivos.")

