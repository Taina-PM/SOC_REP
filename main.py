import os
import time
from pathlib import Path
from dotenv import load_dotenv
from automation.cpf_searcher import pesquisar_cpfs

from utils.logger import setup_logger
from utils.driver_factory import create_driver

logger = setup_logger()


def main():
    current_dir = Path(__file__).resolve().parent
    dotenv_path = current_dir / "config" / ".env"

    print(f" Procurando .env em: {dotenv_path}")

    if not dotenv_path.exists():
        print(" Arquivo .env não encontrado!")
        raise FileNotFoundError(f"Arquivo .env não encontrado em: {dotenv_path}")
    else:
        print(" Arquivo .env encontrado!")

    load_dotenv(dotenv_path=dotenv_path)

    print("CLIENT_ID:", os.getenv("CLIENT_ID"))
    print("TENANT_ID:", os.getenv("TENANT_ID"))
    print("CLIENT_SECRET:", (os.getenv("CLIENT_SECRET") or "")[:5] + "...")
    print("DRIVE_ID:", os.getenv("DRIVE_ID"))

    base_url = os.getenv("SOC_BASE_URL")
    usuario = os.getenv("SOC_USER")
    senha = os.getenv("SOC_PASSWORD")
    empresa_id = os.getenv("SOC_EMPRESA_ID")

    if not usuario or not empresa_id or base_url is None:
        print("---  ERRO CRÍTICO DE CONFIGURAÇÃO ---")
        raise ValueError("Verifique se SOC_USER, SOC_EMPRESA_ID e SOC_BASE_URL estão definidos no config/.env")

    driver = None
    try:
        driver = create_driver(headless=False)

        pesquisar_cpfs(driver, usuario, senha, empresa_id, caminho_csv="data/cpfs.csv")

        logger.info("Fluxo de navegação concluído com sucesso.")

    except Exception as e:
        logger.exception("Erro crítico na execução: %s", e)

    finally:
        if driver:
            time.sleep(2)
            driver.quit()
            logger.info("Driver encerrado.")


if __name__ == "__main__":
    main()
