from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config_loader import AppConfig


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def perform_login(page: Page, config: AppConfig) -> None:
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
    log_step("Login enviado")
