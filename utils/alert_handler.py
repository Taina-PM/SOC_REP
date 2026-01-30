import os
import time
import requests

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException

from utils.logger import setup_logger
from azure.identity import ClientSecretCredential



CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REMETENTE = os.getenv("REMETENTE")
DESTINATARIO = os.getenv("DESTINATARIO")

DRIVE_ID = os.getenv("DRIVE_ID") 

logger = setup_logger()

def check_and_handle_alert(driver: WebDriver) -> bool:
    try:
        alert = driver.switch_to.alert
        
        alert_text = alert.text
        logger.warning(f"[ALERTA DETECTADO] Texto do alerta: '{alert_text}'")
        
        alert.dismiss()
        logger.info("[ALERTA DETECTADO] Alerta dispensado (dismissed).")
        
        time.sleep(1) 
        return True
        
    except NoAlertPresentException:
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao tentar manipular alerta: {e}")
        try:
            driver.switch_to.default_content()
        except:
            pass
        return False 

def wait_for_alert_and_handle(driver: WebDriver, timeout: int = 3) -> bool:

    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        
        alert = driver.switch_to.alert
        alert_text = alert.text
        logger.warning(f"[ALERTA DETECTADO] Um alerta apareceu após a ação: '{alert_text}'")
        
        alert.dismiss()
        logger.info("[ALERTA DETECTADO] Alerta dispensado (dismissed).")
        time.sleep(1)
        return True

    except UnexpectedAlertPresentException:
        logger.warning("[ALERTA DETECTADO] Um Alerta Inesperado já estava presente.")
        return check_and_handle_alert(driver)

    except Exception:
        return False


def enviar_email_alerta():
   
    logger.info("Tentando enviar e-mail de alerta sobre Captcha...")
    
    try:

        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        token_object = credential.get_token('https://graph.microsoft.com/.default')
        access_token = token_object.token

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        url = f"https://graph.microsoft.com/v1.0/users/{REMETENTE}/sendMail"

        email_body = {
            "message": {
                "subject": " AÇÃO NECESSÁRIA: Robô SOC Parado no Captcha",
                "body": {
                    "contentType": "HTML",
                    "content": """
                    <h3>O Robô do SOC encontrou um Captcha!</h3>
                    <p>A automação entrou em modo de espera.</p>
                    <p><b>Por favor, acesse o servidor/máquina e resolva o Captcha manualmente para que o robô continue.</b></p>
                    <p><i>Atenciosamente,<br>Seu Robô RPA</i></p>
                    """
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": DESTINATARIO
                        }
                    }
                ]
            },
            "saveToSentItems": "false"
        }

        response = requests.post(url, headers=headers, json=email_body)

        if response.status_code == 202:
            logger.info("E-mail de alerta enviado com sucesso!")
        else:
            logger.error(f"Falha ao enviar e-mail. Código: {response.status_code}. Erro: {response.text}")

    except Exception as e:
        logger.error(f"Erro ao tentar enviar e-mail: {e}")