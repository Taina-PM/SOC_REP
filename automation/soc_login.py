import time
import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException,
)

from automation.soc_navigation import acessar_programa_232, selecionar_empresa_por_lupa, fechar_popup

from utils.alert_handler import enviar_email_alerta
from utils.logger import setup_logger

logger = setup_logger()

class SessionExpiredException(Exception):
    pass


def verificar_e_aguardar_captcha(driver):
    logger.info("Verificando se o SOC pediu Captcha...")
    
    try:
        captcha_frame = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha') or contains(@src, 'google.com/recaptcha')]")
        texto_bloqueio = driver.find_elements(By.XPATH, "//*[contains(text(), 'Select all images') or contains(text(), 'Selecione todas as imagens')]")

        if captcha_frame or texto_bloqueio:
            logger.warning("CAPTCHA DETECTADO! O robô entrou em modo de espera.")
            logger.warning("POR FAVOR, RESOLVA O CAPTCHA MANUALMENTE NA TELA DO NAVEGADOR.")
            
            enviar_email_alerta()
            
            tempo_limite_minutos = 30  
            tempo_inicio = time.time()
            
            while True:
                tempo_decorrido = (time.time() - tempo_inicio) / 60
                if tempo_decorrido > tempo_limite_minutos:
                    logger.error(f"Tempo limite de {tempo_limite_minutos} minutos excedido aguardando o Captcha.")
                    raise Exception("Timeout: Captcha não foi resolvido a tempo.")

                if "Main" in driver.current_url or "Principal" in driver.current_url or "sistema.soc.com.br/WebSoc/Principal" in driver.current_url:
                    logger.info("Captcha resolvido! Retomando automação...")
                    break
                
                if len(driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")) == 0:
                     time.sleep(2)
                     if "login" not in driver.current_url.lower():
                         logger.info("Parece que o Captcha sumiu. Tentando prosseguir...")
                         break

                logger.info(f"Aguardando resolução... ({int(tempo_decorrido)}/{tempo_limite_minutos} min)")
                time.sleep(10) 

        else:
            logger.info("Nenhum Captcha detectado. Seguindo fluxo normal.")

    except Exception as e:
        logger.error(f"Erro na verificação de Captcha: {e}")
        if "Timeout" in str(e):
            raise e

def realizar_login(driver, usuario: str, senha: str, empresa_id: str):
    
    url = "https://sistema.soc.com.br/WebSoc/"
    logger.info("Iniciando processo de login no SOC...")

    try:
        driver.get(url)
        logger.debug(f"Acessando URL: {url}")
    except WebDriverException as e:
        logger.error(f"Falha ao acessar a URL do SOC: {e}")
        return False

    wait = WebDriverWait(driver, 20)

    try:
        campo_usuario = wait.until(EC.presence_of_element_located((By.ID, "usu")))
        campo_senha = wait.until(EC.presence_of_element_located((By.ID, "senha")))
        campo_id = wait.until(EC.element_to_be_clickable((By.ID, "empsoc")))

        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
        campo_senha.clear()
        campo_senha.send_keys(senha)
        logger.debug("Campos de usuário e senha preenchidos.")

        pyperclip.copy(empresa_id)
        campo_id.click()
        time.sleep(0.4)
        campo_id.send_keys(Keys.CONTROL, 'v')
        time.sleep(0.6)

        tentativas = 0
        while campo_id.get_attribute("value").strip() != empresa_id and tentativas < 3:
            driver.execute_script("arguments[0].value = arguments[1];", campo_id, empresa_id)
            time.sleep(0.5)
            tentativas += 1

        if campo_id.get_attribute("value").strip() == empresa_id:
            logger.info(f"Empresa selecionada com sucesso: {empresa_id}")
        else:
            logger.warning(f"Falha ao definir o ID da empresa. Valor atual: {campo_id.get_attribute('value')}")

        botao_entrar = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Entrar")]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", botao_entrar)
        time.sleep(0.3)

        try:
            botao_entrar.click()
        except ElementClickInterceptedException:
            logger.warning("Clique interceptado — tentando via JavaScript.")
            driver.execute_script("arguments[0].click();", botao_entrar)

        logger.info("Botão 'Entrar' clicado. Aguardando processamento...")
        
        time.sleep(2) 
        verificar_e_aguardar_captcha(driver)
    except TimeoutException as e:
        logger.error(f"Tempo limite ao localizar campos de login: {e}")
        return False
    except NoSuchElementException as e:
        logger.error(f"Elemento esperado não encontrado durante o login: {e}")
        return False
    except WebDriverException as e:
        logger.error(f"Erro inesperado do WebDriver durante o login: {e}")
        return False
    except Exception as e:
        logger.exception(f"Erro inesperado ao tentar realizar login: {e}")
        return False

    return True 

def verificar_sessao_e_relogar(driver, usuario, senha, empresa_id, timeout=10):
    
    try:
        try:
            alerta_sessao_span = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "alertaSessaoIdc"))
            )
            if "Salve seu trabalho, sua sessão irá expirar em 05 minutos." in alerta_sessao_span.text:
                logger.warning("Pop-up de aviso de sessão (5 minutos) detectado.")
                
                btn_ok_aviso = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//p[@class='modalAlertaBotoes']/a[text()='OK']"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", btn_ok_aviso)
                btn_ok_aviso.click()
                logger.info("Botão OK do aviso clicado.")
                time.sleep(1)
                return True 
        except TimeoutException:
            pass

    except Exception as e:
        pass 

    try:
        if "nosession/sessao.jsp" in driver.current_url:
            logger.warning("Sessão expirada detectada na URL.")

            try:
                btn_ok_expiracao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "btn_ok"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", btn_ok_expiracao)
                btn_ok_expiracao.click()
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Não foi possível clicar no OK do alerta de expiração: {e}")
                
            sucesso_login = realizar_login(driver, usuario, senha, empresa_id)
            if not sucesso_login:
                logger.error("Falha ao realizar login após expiração de sessão.")
                return False

            try:
                fechar_popup(driver)
            except Exception as e:
                logger.error(f"Erro ao fechar popup no relogin: {e}")

            try:
                selecionar_empresa_por_lupa(driver)
            except Exception as e:
                logger.error(f"Erro ao selecionar empresa após relogin: {e}")
                return False

            if not acessar_programa_232(driver, timeout):
                logger.error("Erro ao acessar o programa 232 após relogin.")
                return False

            logger.info("Sessão restaurada com sucesso.")
            return True

    except Exception as e:
        logger.error(f"Erro inesperado ao verificar sessão: {e}")
        return False

    return True