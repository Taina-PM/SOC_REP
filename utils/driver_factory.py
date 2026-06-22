from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os
import tempfile
import shutil
import time
import subprocess

from automation.soc_login import realizar_login
from automation.soc_navigation import acessar_programa_232, fechar_popup, selecionar_empresa_por_lupa
from utils.logger import setup_logger

logger = setup_logger()

DOWNLOAD_DIR_PATH = r"C:\SOC_REP\downloads"
_DRIVER_INSTANCE = None
_DRIVER_USE_COUNT = 0
_MAX_USES = 99999
_TEMP_USER_DATA_DIR = None

def reiniciar_driver_existente(driver, usuario, senha, empresa_id, motivo="Erro não especificado"):
    global _DRIVER_INSTANCE, _DRIVER_USE_COUNT

    logger.warning(f"Reiniciando driver devido a: {motivo}")

    if driver:
        try:
            driver.quit()
            time.sleep(1)
            cleanup_temp_dir()
        except Exception:
            logger.warning("Falha ao encerrar driver antigo, prosseguindo assim mesmo.")

    _DRIVER_INSTANCE = None
    _DRIVER_USE_COUNT = 0

    novo_driver = create_driver(headless=False)
    
    try:
        realizar_login(novo_driver, usuario, senha, empresa_id)
        fechar_popup(novo_driver)
        selecionar_empresa_por_lupa(novo_driver)
        acessar_programa_232(novo_driver)
        logger.info("Driver reiniciado com sucesso após erro.")
        return novo_driver
    except Exception as e:
        logger.error(f"Erro fatal ao tentar reiniciar e logar: {e}")
        novo_driver.quit()
        raise e

def cleanup_temp_dir():
    global _TEMP_USER_DATA_DIR
    if _TEMP_USER_DATA_DIR and os.path.exists(_TEMP_USER_DATA_DIR):
        try:
            shutil.rmtree(_TEMP_USER_DATA_DIR, ignore_errors=True)
        except Exception:
            pass
    _TEMP_USER_DATA_DIR = None

def create_driver(headless: bool = True):
    global _DRIVER_INSTANCE, _DRIVER_USE_COUNT, _TEMP_USER_DATA_DIR
    
    try:
        if _DRIVER_INSTANCE and _DRIVER_USE_COUNT < _MAX_USES:
            try:
                _DRIVER_INSTANCE.current_url 
                _DRIVER_USE_COUNT += 1
                return _DRIVER_INSTANCE
            except Exception:
                logger.warning("Driver existente parece morto. Criando novo.")
              
        if _DRIVER_INSTANCE:
            try:
                _DRIVER_INSTANCE.quit()
                time.sleep(1)
            except Exception:
                pass
            cleanup_temp_dir()
            _DRIVER_INSTANCE = None
            _DRIVER_USE_COUNT = 0

        options = EdgeOptions()
        
        options.page_load_strategy = 'eager'

        prefs = {
            "download.default_directory": DOWNLOAD_DIR_PATH,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0,
            "print.always_print_silent": True
        }

        options.add_experimental_option("prefs", prefs)
        options.add_argument("--inprivate")

        if headless:
            options.add_argument("--headless=new")          

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--mute-audio")
        options.add_argument("--ignore-certificate-errors")

        options.add_argument("--disable-3d-apis")
        options.add_argument("--disable-accelerated-2d-canvas")

        _TEMP_USER_DATA_DIR = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={_TEMP_USER_DATA_DIR}")

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        service_args = ["--port=0", "--host=127.0.0.1", "--readable-timestamp"]

        try:
            _DRIVER_INSTANCE = webdriver.Edge(options=options)
        except Exception as primary_exc:
            logger.warning(f"Selenium Manager falhou ao iniciar o driver: {primary_exc}. Tentando fallback com webdriver-manager.")
            driver_path = EdgeChromiumDriverManager().install()
            service = EdgeService(
                executable_path=driver_path,
                log_output='NUL',
                service_args=service_args,
                creationflags=creationflags
            )

            _DRIVER_INSTANCE = webdriver.Edge(service=service, options=options)
        
        _DRIVER_INSTANCE.set_page_load_timeout(60) 
        _DRIVER_INSTANCE.set_script_timeout(60)    

        _DRIVER_USE_COUNT = 1
        return _DRIVER_INSTANCE

    except Exception as e:
        cleanup_temp_dir()
        _DRIVER_INSTANCE = None
        _DRIVER_USE_COUNT = 0
        raise e