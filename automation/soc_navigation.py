from selenium.webdriver.common.by import By
from automation.locators_soc import SocLocators
from utils.wait_utils import wait_for_clickable, wait_for_presence
import time
from utils.logger import setup_logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException,
        StaleElementReferenceException, NoAlertPresentException,UnexpectedAlertPresentException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, WebDriverException
import time
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



# --- 1. SELECIONAR EMPRESA (LIDANDO COM NOVA JANELA/POPUP) ---
def selecionar_empresa_por_lupa(driver, timeout_global=30):
    logger.info("Iniciando seleção de empresa pela lupa...")
    
    try:
        # Garante o foco no frame principal onde a lupa está
        driver.switch_to.default_content()
        WebDriverWait(driver, 15).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "socframe"))
        )

        # Clica na lupa para abrir o modal/área de busca
        lupa = wait_for_clickable(driver, By.ID, "procuraModalBtn", timeout=15)
        driver.execute_script("arguments[0].click();", lupa)
        logger.info("Lupa clicada. Aguardando modal de busca de empresa.")

        # O modal de busca abre no mesmo contexto (frame), não em uma nova janela.
        # Aguarda o link da empresa estar visível e clicável.
        # O XPath é baseado no HTML fornecido, buscando um link que contenha o texto da empresa.
        empresa_locator = (By.XPATH, "//a[contains(text(), 'PAGUE MENOS COMERCIO DE PRODUTOS ALIMENTICIOS LTDA')]")
        empresa_element = wait_for_clickable(driver, *empresa_locator, timeout=timeout_global)

        if not empresa_element:
            # Se o wait_for_clickable retornar None, o elemento não foi encontrado.
            logger.error("Não foi possível localizar o link da empresa 'PAGUE MENOS' na lista.")
            raise TimeoutException("O link da empresa 'PAGUE MENOS' não foi encontrado após clicar na lupa.")

        logger.info("Empresa 'PAGUE MENOS' localizada. Clicando...")

        # Usa JavaScript para garantir o clique e a rolagem, o que é mais confiável.
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", empresa_element)
        try:
            empresa_element.click()
        except ElementClickInterceptedException:
            logger.warning("Clique na empresa foi interceptado, tentando com JavaScript.")
            driver.execute_script("arguments[0].click();", empresa_element)

        # Após o clique, o SOC atualiza a página principal.
        # É uma boa prática garantir que o driver volte ao contexto padrão.
        driver.switch_to.default_content()
        
        fechar_popup(driver)
        logger.info("Empresa selecionada com sucesso!")
        return True

    except Exception as e:
        logger.error(f"Falha crítica ao selecionar empresa: {e}")
        driver.switch_to.default_content() # Garante a saída de qualquer frame em caso de erro
        raise RuntimeError("Erro ao tentar selecionar a empresa 'PAGUE MENOS'.") from e  


# --- 2. ACESSAR PROGRAMA 232 (SIMULANDO DIGITAÇÃO REAL) ---
def acessar_programa_232(driver, timeout=15, max_tentativas=2):
    logger.info("Iniciando acesso ao programa 232...")

    for tentativa in range(1, max_tentativas + 1):
        try:
            logger.debug(f"Tentativa {tentativa}/{max_tentativas} para acessar o programa 232.")
            # Garante que está fora de qualquer iframe
            driver.switch_to.default_content() 

            campo = wait_for_clickable(driver, By.ID, "cod_programa", timeout)
            driver.execute_script("arguments[0].scrollIntoView(true);", campo)
            
            # Em vez de injetar JS puro, clicamos e digitamos para disparar o 'onkeyup' do SOC
            campo.click()
            campo.clear()
            time.sleep(0.2)
            campo.send_keys("232")
            time.sleep(0.3)

            # VERIFICAÇÃO E CORREÇÃO: Garante que o valor "232" foi inserido corretamente.
            valor_no_campo = campo.get_attribute("value")
            if valor_no_campo != "232":
                logger.warning(f"O valor no campo era '{valor_no_campo}' em vez de '232'. Corrigindo com JS.")
                driver.execute_script("arguments[0].value = '232';", campo)

            campo.send_keys(Keys.TAB) # Dispara o 'onblur' de validação
            
            logger.info(f"Código '232' inserido e validado. Valor final no campo: '{campo.get_attribute('value')}'")

            # Localiza e clica no botão OK
            btn = wait_for_clickable(driver, By.ID, "btn_programa", timeout)
            try:
                btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", btn)

            # Espera o SOC processar e carregar o novo iframe interno
            logger.debug("Aguardando 'socframe' carregar pós-redirecionamento...")
            WebDriverWait(driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "socframe"))
            )

            # VERIFICAÇÃO: Confirma se um elemento da tela de pesquisa está presente
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "nomeSeach")))
            logger.info("Programa 232 acessado e verificado com sucesso.")
            return True
            
        except Exception as e:
            logger.warning(f"Falha na tentativa {tentativa} de acessar o programa 232: {e}")
            if tentativa == max_tentativas:
                logger.error("Todas as tentativas de acessar o programa 232 falharam.")
                raise WebDriverException(f"Erro final ao acessar Prog 232: {e}") from e
            time.sleep(2) # Pausa antes de tentar novamente
        
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