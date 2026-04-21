from dataclasses import dataclass
from typing import Optional

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


@dataclass(frozen=True)
class LoginResult:
    senha_expirando_mensagem: Optional[str] = None


def _digitar_e_tab(page: Page, campo, valor: str, espera_apos_tab_ms: int = 900) -> None:
    campo.click()
    page.wait_for_timeout(400)
    campo.fill("")
    page.wait_for_timeout(300)
    campo.type(valor, delay=85)
    page.wait_for_timeout(700)
    page.keyboard.press("Tab")
    page.wait_for_timeout(espera_apos_tab_ms)


def _clicar_botao_por_texto(page: Page, texto: str) -> bool:
    botao = page.get_by_role("button", name=texto).first
    try:
        if botao.is_visible(timeout=2000):
            botao.click()
            return True
    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass

    return bool(
        page.evaluate(
            r"""(text) => {
                const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                const button = [...document.querySelectorAll('button')]
                    .find((item) => normalize(item.innerText) === text);
                if (!button) return false;
                button.click();
                return true;
            }""",
            texto,
        )
    )


def _tratar_selecao_loja(page: Page, timeout_ms: int) -> None:
    if "select-store" not in page.url:
        return

    log_step("Selecionando loja padrao Santander")
    try:
        page.locator("mat-select").first.click(timeout=5000)
        page.wait_for_timeout(800)
        page.locator("mat-option").first.click(timeout=5000)
        page.wait_for_timeout(800)
        _clicar_botao_por_texto(page, "Continuar")
        page.wait_for_timeout(2000)
        page.wait_for_url(lambda url: "/showcase" in url, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        log_step("Tela de loja nao exigiu selecao manual")


def perform_login(page: Page, config: AppConfig) -> LoginResult:
    mensagens_login_invalido = [
        "cpf e senha",
        "senha incorreta",
        "usuario ou senha",
        "usuário ou senha",
        "login invalido",
        "login inválido",
    ]

    log_step("Iniciando login Santander")
    campo_usuario = page.locator('input[formcontrolname="documentNumber"]').first
    campo_senha = page.locator('input[formcontrolname="password"]').first

    log_step("Aguardando campo CPF do lojista")
    campo_usuario.wait_for(state="visible", timeout=config.timeout_ms)

    log_step("Preenchendo CPF do lojista")
    _digitar_e_tab(page, campo_usuario, config.email)

    log_step("Preenchendo senha")
    campo_senha.wait_for(state="visible", timeout=config.timeout_ms)
    _digitar_e_tab(page, campo_senha, config.senha)

    log_step("Enviando login Santander")
    _clicar_botao_por_texto(page, "Entrar")
    page.wait_for_timeout(3000)

    try:
        page.wait_for_url(
            lambda url: "/showcase" in url or "/select-store" in url,
            timeout=config.timeout_ms,
        )
    except PlaywrightTimeoutError as exc:
        texto_pagina = page.locator("body").inner_text(timeout=5000).lower()
        if any(mensagem in texto_pagina for mensagem in mensagens_login_invalido):
            raise LoginFailedError("usuario e senha estao incorretos ou expirados")
        raise LoginFailedError("login realizado, mas o portal Santander nao carregou") from exc

    _tratar_selecao_loja(page, config.timeout_ms)

    try:
        page.locator("body").filter(has_text="Escolha o tipo de simulacao").wait_for(
            state="visible",
            timeout=5000,
        )
    except PlaywrightTimeoutError:
        # Alguns ambientes renderizam os acentos corretamente; a URL ja confirma o acesso.
        pass

    log_step("Login Santander concluido")
    return LoginResult()
