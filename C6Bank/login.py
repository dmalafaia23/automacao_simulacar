from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

try:
    from .config_loader import AppConfig
except ImportError:
    from config_loader import AppConfig


class LoginFailedError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def perform_login(page: Page, config: AppConfig) -> None:
    mensagens_login_invalido = [
        "usuario ou senha invalid",
        "usuário ou senha inválid",
        "usuario ou senha incorret",
        "usuário ou senha incorret",
        "invalid username or password",
        "senha expirad",
        "senha vencid",
    ]

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
    page.wait_for_timeout(3000)
    try:
        page.get_by_role("button", name="Criar uma nova proposta").wait_for(
            state="visible",
            timeout=8000,
        )
    except PlaywrightTimeoutError:
        texto_pagina = page.locator("body").inner_text().lower()
        if any(mensagem in texto_pagina for mensagem in mensagens_login_invalido):
            raise LoginFailedError("usuario e senha estão incorretos ou expirados")
        raise
    log_step("Login enviado")
