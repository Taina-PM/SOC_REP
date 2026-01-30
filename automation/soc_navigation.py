from selenium.webdriver.common.by import By
from automation.locators_soc import SocLocators
from utils.wait_utils import wait_for_clickable, wait_for_presence
import time
from utils.logger import setup_logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException,
        StaleElementReferenceException, NoAlertPresentException,UnexpectedAlertPresentException)

logger = setup_logger()


def fechar_popup(driver, timeout: int = 5, tentativas: int = 2):
    logger.debug("Verificando se há pop-up para fechar...")

    for tentativa in range(1, tentativas + 1):
        logger.debug(f"Tentativa {tentativa}/{tentativas} para fechar pop-up...")
        try:
            el = wait_for_clickable(driver, By.XPATH, SocLocators.BOTAO_FECHAR_POPUP, timeout)
            
            if not el:
                logger.debug("Botão de fechar não encontrado (wait retornou None).")
                continue 

            el.click()
            logger.info(f"Pop-up fechado com sucesso (tentativa {tentativa}/{tentativas}).")
            time.sleep(0.5)
            return True

        except ElementClickInterceptedException:
            logger.warning("Clique no pop-up interceptado — tentando via JavaScript.")
            try:
                driver.execute_script("arguments[0].click();", el)
                logger.info(f"Pop-up fechado via JavaScript (tentativa {tentativa}/{tentativas}).")
                time.sleep(0.5) 
                return True
            except Exception as e_js:
                logger.error(f"Falha ao tentar clique via JavaScript: {e_js}")
                continue 

        except (TimeoutException, NoSuchElementException):
            logger.debug(f"Pop-up não apareceu dentro de {timeout}s (tentativa {tentativa}).")
            return False 

        except StaleElementReferenceException:
            logger.warning(f"Elemento do pop-up ficou obsoleto (tentativa {tentativa}). Relocalizando...")
            time.sleep(0.5) 
            continue 

        except Exception as e:
            logger.error(f"Erro inesperado ao tentar fechar o pop-up (tentativa {tentativa}): {e}")
            time.sleep(0.5)
            continue 

    logger.warning("Todas as tentativas de fechamento do pop-up falharam.")
    return False


def acessar_programa_232(driver, timeout=10):
   
    logger.info("Iniciando acesso ao programa 232...")

    try:
    
        logger.debug("Garantindo que o driver está no default_content...")
        driver.switch_to.default_content() 

        logger.debug("Aguardando campo do código estar clicável...")
        campo = wait_for_clickable(driver, By.XPATH, SocLocators.COD_PROGRAMA, timeout)

        driver.execute_script("arguments[0].scrollIntoView(true);", campo)

        driver.execute_script(
            "arguments[0].value = '232'; arguments[0].dispatchEvent(new Event('change'));", campo
        )
        valor = campo.get_attribute("value")
        logger.info(f"Campo de código definido. Valor atual: '{valor}'")

        try:
            btn = wait_for_clickable(driver, By.XPATH, SocLocators.BTN_OK_PROGRAMA, timeout)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)

            try:
                btn.click()
            except ElementClickInterceptedException:
                logger.warning("Clique no botão OK interceptado. Tentando via JavaScript...")
                driver.execute_script("arguments[0].click();", btn)
            except WebDriverException as e:
                logger.warning(f"Erro ao clicar no botão OK: {e}. Tentando via JavaScript...")
                driver.execute_script("arguments[0].click();", btn)

        except (TimeoutException, NoSuchElementException) as e_btn:
            logger.error(f"Botão OK do programa 232 não encontrado: {e_btn}")
            raise TimeoutException("Botão OK do programa 232 não foi encontrado.") from e_btn
        
        logger.debug("Aguardando 'socFrame' carregar" )
        WebDriverWait(driver, 15).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "socframe"))
        )

        logger.info("Programa 232 acessado e 'socframe' verificado com sucesso.")
        
        driver.switch_to.default_content() 
        return True
    except (TimeoutException, NoSuchElementException) as e_campo:
        logger.error(f"Campo do código do programa 232 não encontrado: {e_campo}")
        raise TimeoutException("Campo do código do programa 232 não foi encontrado.") from e_campo
    
    except WebDriverException as e_wd:
        logger.error(f"Erro inesperado de WebDriver ao acessar o programa 232: {e_wd}")
        raise WebDriverException(f"Erro de WebDriver ao acessar Prog 232: {e_wd}") from e_wd
    
    except Exception as e:
        logger.exception(f"Erro geral inesperado ao acessar o programa 232: {e}")
        raise WebDriverException(f"Erro inesperado ao acessar Prog 232: {e}") from e
    
    
def selecionar_empresa_por_lupa(driver):
    try:
        logger.info("Aguardando carregamento da tela principal do SOC...")
        wait_for_presence(driver, By.XPATH, '//*[@id="cod_programa"]', timeout=90)
        logger.info("Tela principal carregada. Aguardando estabilização...")
        time.sleep(2) 
    except Exception as e:
        logger.error(f"Erro ao carregar a tela principal: {e}")
        raise RuntimeError("Falha ao carregar a tela principal antes de abrir a lupa.") from e

    try:
        driver.switch_to.default_content()
        WebDriverWait(driver, 15).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "socframe"))
        )
        logger.info("Alternado para o iframe 'socframe'.")

        lupa = wait_for_clickable(driver, By.ID, "procuraModalBtn", timeout=30)
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", lupa)
        time.sleep(0.5)

        try:
            logger.info("Tentando clicar na lupa...")
            lupa.click()
        except (ElementClickInterceptedException, WebDriverException):
            logger.warning("Clique convencional na lupa falhou/interceptado. Forçando via JavaScript.")
            driver.execute_script("arguments[0].click();", lupa)
        
        logger.info("Lupa clicada com sucesso.")

    except Exception as e:
        logger.error(f"Falha ao localizar ou clicar na lupa: {e}")
        driver.switch_to.default_content()
        raise RuntimeError("Erro ao tentar clicar na lupa para selecionar a empresa.") from e

    try:
        driver.switch_to.default_content()
        logger.info("Aguardando os iframes do modal da lupa ficarem disponíveis...")
        
        time.sleep(2) 
        
        iframes = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )
        logger.info(f"{len(iframes)} iframes detectados após clicar na lupa.")

        empresa_element = None
        found = False
        
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)

                if wait_for_presence(driver, By.XPATH, SocLocators.EMPRESA_PAGUE_MENOS, timeout=2):
                    logger.info(f"Empresa 'PAGUE MENOS' encontrada no iframe {i}.")
                    empresa_element = driver.find_element(By.XPATH, SocLocators.EMPRESA_PAGUE_MENOS)
                    found = True
                    break
            except Exception:
                continue

        if not found or not empresa_element:
            raise RuntimeError("Empresa 'PAGUE MENOS' não encontrada em nenhum iframe.")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", empresa_element)
        time.sleep(0.5)
        try:
            empresa_element.click()
        except ElementClickInterceptedException:
             driver.execute_script("arguments[0].click();", empresa_element)
             
        logger.info("Empresa 'PAGUE MENOS' selecionada com sucesso.")

        driver.switch_to.default_content()
        fechar_popup(driver)
        logger.info("Pop-up de empresa fechado com sucesso.")

    except Exception as e:
        logger.error(f"Erro durante a seleção da empresa: {e}")
        driver.switch_to.default_content()
        raise RuntimeError("Falha ao selecionar empresa 'PAGUE MENOS' no modal.") from e
    
def fechar_alerta_se_existir(driver, contexto=""):
    try:
        alert = driver.switch_to.alert
        texto = alert.text
        logger.warning(f"[ALERTA DETECTADO] {texto} | Contexto: {contexto}")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False
    except UnexpectedAlertPresentException as e:
        logger.warning(f"Alerta inesperado persistente ({contexto}): {str(e)}")
        try:
            driver.switch_to.alert.accept()
        except Exception:
            pass
        return True