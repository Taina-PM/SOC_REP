import os
import pandas as pd
import time
import pyperclip
import urllib3 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
    UnexpectedAlertPresentException, 
)
from automation.socged_modal import (
    baixar_todos_documentos_modal,
)
from automation.soc_navigation import (
    acessar_programa_232,
    fechar_popup,
    selecionar_empresa_por_lupa,
    fechar_alerta_se_existir 
)


from automation.soc_login import realizar_login, verificar_sessao_e_relogar, SessionExpiredException
from utils.logger import setup_logger
from utils.downloads import enviar_e_limpar_arquivos_cpf, limpar_downloads_incompletos_cpf

from utils import driver_factory
from utils.driver_factory import create_driver, cleanup_temp_dir
from automation.socged_actions import abrir_socged, registrar_cpf
from utils.onedrive_uploader import listar_conteudo_pasta_com_zips

logger = setup_logger()


def processar_um_cpf(driver, cpf, matricula_limpa, usuario, senha, empresa_id):

    try:
        if not verificar_sessao_e_relogar(driver, usuario, senha, empresa_id):
            logger.error(f"Sessão expirada e não foi possível restaurar. Pulando CPF {cpf}.")
            registrar_cpf(cpf, tipo="interrompido")
            raise SessionExpiredException("Falha na verificação proativa de sessão.")

        driver.switch_to.default_content()
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "socframe"))
        )

        logger.debug("Switch para iframe 'socframe' realizado com sucesso.")

        for name in ["inativo", "pendente"]:
            try:
                checkbox = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.NAME, name))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                time.sleep(0.2)
                if checkbox.get_attribute("checked"):
                    driver.execute_script("""
                        arguments[0].checked = false;
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, checkbox)
                    logger.info(f"Checkbox '{name}' desmarcado via JS.")
            except TimeoutException:
                logger.warning(f"Checkbox '{name}' não encontrado na página.")
            except Exception as e:
                logger.debug(f"Erro ao manipular checkbox '{name}': {e}")
        
        try:
            radio = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='codigoPesquisaFuncionario' and @value='3']"))
            )
            if not radio.is_selected():
                driver.execute_script("arguments[0].click();", radio)
            logger.debug("Rádio CPF selecionado.")
        except TimeoutException:
            logger.error("Rádio 'CPF' não encontrado — possível mudança no layout.")
            return
        
        try:
            campo_busca = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "nomeSeach"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", campo_busca)
            campo_busca.clear()
            pyperclip.copy(cpf)
            campo_busca.send_keys(Keys.CONTROL, 'v')
            time.sleep(0.5)
            if campo_busca.get_attribute("value").strip() != cpf:
                driver.execute_script("arguments[0].value = arguments[1];", campo_busca, cpf)
            campo_busca.send_keys(Keys.ENTER)
        except Exception as e:
            logger.error(f"Erro na busca do CPF {cpf}: {e}")
            return

        time.sleep(2)

        try:
            codigo_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//td[@class='codigo']/a"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", codigo_link)
            codigo_link.click()
        except TimeoutException:
            logger.warning(f"Nenhum resultado para CPF {cpf}.")
            registrar_cpf(cpf, tipo="inativo")
            return
        
        time.sleep(2)

        if abrir_socged(driver, cpf):
            time.sleep(3)
            

            baixar_todos_documentos_modal(
            driver, 
            cpf=cpf, 
            matricula=matricula_limpa, 
            arquivos_existentes=listar_conteudo_pasta_com_zips(matricula_limpa)
        )
        
            logger.info(f"Processamento de documentos para {cpf} finalizado.")
        
        else:
            logger.warning(f"SOCGED não pôde ser aberto para o CPF {cpf}.")

  
        try:
            driver.switch_to.default_content()
            acessar_programa_232(driver)
        except Exception as e:
            raise e
        
    except UnexpectedAlertPresentException as e_alert:
        logger.error(f"Erro (ALERTA INESPERADO) no CPF {cpf}. Alerta: '{e_alert.alert_text}'")
        registrar_cpf(cpf, tipo="erro")
        fechar_alerta_se_existir(driver, f"Alerta inesperado no CPF {cpf}")
        raise WebDriverException("Alerta inesperado. Driver em estado inválido.")

    except Exception as e:
        logger.exception(f"Erro inesperado ao processar CPF {cpf}: {e}")
        registrar_cpf(cpf, tipo="erro")
        raise e 


def pesquisar_cpfs(driver, usuario, senha, empresa_id, caminho_csv="data/cpfs.csv"):

    MAX_RETRIES_CPF = 3 

    logger.info("Iniciando leitura de CPFs para pesquisa no SOC...")
    
    if not os.path.exists(caminho_csv):
        logger.error(f"Arquivo CSV não encontrado: {caminho_csv}")
        return
    try:
        df = pd.read_csv(caminho_csv, sep=';', dtype=str)
        if df.empty:
            logger.warning(f"O arquivo '{caminho_csv}' está vazio.")
            return
        logger.info(f"{len(df)} registros carregados com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao ler o arquivo CSV '{caminho_csv}': {e}")
        return

    try:
        driver = create_driver(headless=False)
        realizar_login(driver, usuario, senha, empresa_id)
        fechar_popup(driver)
        selecionar_empresa_por_lupa(driver)
        acessar_programa_232(driver)
        logger.info("Login e preparação concluídos.")
    except Exception as e:
        logger.critical(f"Falha crítica na inicialização do driver: {e}", exc_info=True)
        if driver:
            driver.quit()
        return
    
    idx = 0

    while idx < len(df):
        
        if idx > 0 and idx % 200 == 0: 
            logger.info(f"Iniciando reinicialização periódica do driver (item {idx})...")
            try:
                logger.info("Pausando por 30 segundos antes de reiniciar...")
                time.sleep(30) 
                driver = driver_factory.reiniciar_driver_existente(
                    driver, usuario, senha, empresa_id, motivo=f"Reinicialização periódica (item {idx})"
                )
                logger.info("Driver reiniciado periodicamente com sucesso.")
            except Exception as e:
                logger.critical(f"Falha CRÍTICA ao reiniciar driver periodicamente: {e}. Abortando.")
                raise e 
            
        row = df.iloc[idx]
        matricula_raw = (row.get("MATRICULA") or "").strip()
        matricula_limpa = str(matricula_raw).replace('.', '').replace('-', '')
        cpf = (row.get("CPF_PESSOA") or "").strip()

        if not matricula_limpa or not cpf:
             logger.warning(f"Linha {idx + 1}: Matrícula ou CPF vazio, pulando...")
             idx += 1
             continue

        tentativas_cpf = 0
        processado_com_sucesso = False

        while not processado_com_sucesso and tentativas_cpf < MAX_RETRIES_CPF:
            try:
                logger.info(f"Iniciando tentativa {tentativas_cpf + 1}/{MAX_RETRIES_CPF} para CPF {cpf}...")
                processar_um_cpf(driver, cpf, matricula_limpa, usuario, senha, empresa_id)
                
                enviar_e_limpar_arquivos_cpf(matricula_limpa)
                
                processado_com_sucesso = True

            except (
                SessionExpiredException,
                StaleElementReferenceException,
                TimeoutException
            ) as e_sess:
                tentativas_cpf += 1
                logger.warning(f"[{cpf}] FALHA DE SESSÃO (Tentativa {tentativas_cpf}/{MAX_RETRIES_CPF}): {type(e_sess).__name__}.")
                limpar_downloads_incompletos_cpf(matricula_limpa) 
                
                try:
                    logger.info("Sessão perdida. Pausando por 30 segundos antes de reiniciar...")
                    time.sleep(30)
                    driver = driver_factory.reiniciar_driver_existente(
                        driver, usuario, senha, empresa_id, motivo=f"Falha de Sessão (CPF: {cpf})"
                    )
                    logger.info("Driver reiniciado com sucesso. Retentando o mesmo CPF...")
                except Exception as restart_e:
                    logger.critical(f"Falha CRÍTICA ao reiniciar o driver: {restart_e}. Abortando.")
                    raise restart_e
            
            except (
                WebDriverException,
                urllib3.exceptions.MaxRetryError,
                ConnectionRefusedError
            ) as e:
                tentativas_cpf += 1
                logger.error(f"[{cpf}] CONEXÃO PERDIDA (Tentativa {tentativas_cpf}/{MAX_RETRIES_CPF}): {type(e).__name__}.")
                limpar_downloads_incompletos_cpf(matricula_limpa) 
                
                try:
                    logger.info("Conexão perdida. Pausando por 30 segundos antes de reiniciar...")
                    time.sleep(30)
                    driver = driver_factory.reiniciar_driver_existente(
                        driver, usuario, senha, empresa_id, motivo=f"Conexão perdida (CPF: {cpf})"
                    )
                    logger.info("Driver reiniciado com sucesso após falha. Retentando...")
                except Exception as restart_e:
                    logger.critical(f"Falha CRÍTICA ao reiniciar o driver: {restart_e}. Abortando.")
                    raise restart_e 
            
            except Exception as e:
                tentativas_cpf += 1
                logger.exception(f"Erro inesperado (Tentativa {tentativas_cpf}/{MAX_RETRIES_CPF}) para CPF {cpf}: {e}.")
                limpar_downloads_incompletos_cpf(matricula_limpa)
                
                try:
                    logger.info("Erro inesperado. Pausando por 30 segundos antes de reiniciar...")
                    time.sleep(30)

                except Exception as restart_e:
                    logger.critical(f"Falha CRÍTICA ao reiniciar driver: {restart_e}. Abortando.")
                    raise restart_e


        if not processado_com_sucesso:
            logger.error(f"FALHA FINAL: CPF {cpf} (Matrícula {matricula_limpa}) falhou após {MAX_RETRIES_CPF} tentativas. Pulando.")
            registrar_cpf(cpf, tipo="interrompido") 

        idx += 1
            
    
    logger.info("Todas as pesquisas de CPFs foram concluídas com sucesso.")
    try:
        driver.quit()
        cleanup_temp_dir()
        logger.info("Driver encerrado e diretórios temporários limpos.")
    except Exception as e:
        logger.warning(f"Falha ao encerrar driver no final: {e}")

        
