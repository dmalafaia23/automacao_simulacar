from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config_loader import AppConfig


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def perform_login(page: Page, config: AppConfig) -> None:
    log_step("Iniciando login")
    try:
        log_step("Aguardando botao iniciar login")
        page.wait_for_timeout(10000)
        log_step("Clicando em iniciar login")
        page.get_by_role("button", name="Iniciar Login").click()
    except PlaywrightTimeoutError:
        log_step("Pagina/elemento nao respondeu, recarregando")
        page.reload()
        page.wait_for_selector("iframe", state="visible", timeout=60000)
        log_step("Clicando em iniciar login (apos reload)")
        page.get_by_role("button", name="Iniciar Login").click()

    page.wait_for_timeout(500)
    log_step("Acessando campo CPF")
    page.get_by_role("textbox", name="CPF").click()
    page.wait_for_timeout(500)
    log_step("Preenchendo CPF")
    page.get_by_role("textbox", name="CPF").fill(config.email)
    page.wait_for_timeout(500)

    page.wait_for_timeout(500)
    log_step("Acessando campo senha")
    page.get_by_role("textbox", name="Senha").click()
    page.wait_for_timeout(500)
    log_step("Preenchendo senha")
    page.get_by_role("textbox", name="Senha").fill(config.senha)
    page.wait_for_timeout(500)

    log_step("Clicando em acessar")
    page.get_by_role("button", name="Acessar").click()
    page.wait_for_timeout(8000)
    log_step("Login enviado")
