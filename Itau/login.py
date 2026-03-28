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
    mensagem_login_invalido = "Nome de usuário ou senha inválida."
    mensagem_login_expirado = "expirada"

    log_step("Iniciando login")
    frame = page.frame_locator("iframe")
    try:
        log_step("Acessando campo e-mail")
        frame.get_by_role("textbox", name="e-mail").click()
    except PlaywrightTimeoutError:
        log_step("Iframe não respondeu, recarregando página")
        page.reload()
        page.wait_for_selector("iframe", state="visible", timeout=60000)
        frame = page.frame_locator("iframe")
        log_step("Acessando campo e-mail (após reload)")
        frame.get_by_role("textbox", name="e-mail").click()
    page.wait_for_timeout(500)
    log_step("Preenchendo e-mail")
    frame.get_by_role("textbox", name="e-mail").fill(config.email)
    page.wait_for_timeout(500)
    log_step("Acessando campo senha")
    frame.get_by_role("textbox", name="senha").click()
    page.wait_for_timeout(500)
    log_step("Preenchendo senha")
    frame.get_by_role("textbox", name="senha").fill(config.senha)
    page.wait_for_timeout(1000)
    log_step("Enviando login")
    frame.get_by_role("button", name="entrar").click()
    page.wait_for_timeout(3000)
    try:
        page.get_by_role("button", name="Novo Simulador PF").wait_for(
            state="visible",
            timeout=8000,
        )
    except PlaywrightTimeoutError:
        texto_iframe = frame.locator("body").inner_text()
        if (
            mensagem_login_invalido in texto_iframe
            or mensagem_login_expirado in texto_iframe.lower()
        ):
            raise LoginFailedError("usuario e senha estão incorretos ou expirados")
        raise
    log_step("Login enviado")
