import re
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


def _first_visible_text(page: Page, patterns: list[str]) -> Optional[str]:
    body_text = page.locator("body").inner_text(timeout=5000)
    normalized = re.sub(r"\s+", " ", body_text).strip()
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _capturar_aviso_senha_expirando(page: Page) -> Optional[str]:
    patterns = [
        r"sua senha expira em \d+\s+dia\(s\)\.?",
        r"sua senha vence em \d+\s+dia\(s\)\.?",
        r"[^.?!]*(?:senha)[^.?!]*(?:expir|venc)[^.?!]*[.?!]?",
        r"[^.?!]*(?:expir|venc)[^.?!]*(?:senha)[^.?!]*[.?!]?",
    ]
    mensagem = _first_visible_text(page, patterns)
    if not mensagem:
        return None

    for button_name in ("Continuar", "Entendi", "OK", "Ok", "Fechar"):
        button = page.get_by_role("button", name=button_name)
        try:
            if button.is_visible(timeout=1000):
                button.click()
                page.wait_for_timeout(1000)
                break
        except PlaywrightTimeoutError:
            continue

    return mensagem


def perform_login(page: Page, config: AppConfig) -> LoginResult:
    mensagens_login_invalido = [
        "usuario ou senha invalid",
        "usuário ou senha inválid",
        "usuario ou senha incorret",
        "usuário ou senha incorret",
        "login ou senha inválid",
        "senha expirad",
        "senha vencid",
    ]

    log_step("Iniciando login Banco PAN")
    aceitar_cookies = page.locator("#onetrust-accept-btn-handler")
    try:
        if aceitar_cookies.is_visible(timeout=3000):
            log_step("Aceitando cookies")
            aceitar_cookies.click()
            page.wait_for_timeout(500)
    except PlaywrightTimeoutError:
        pass

    log_step("Aguardando campo Usuario")
    campo_usuario = page.locator("#login")
    campo_usuario.wait_for(state="visible", timeout=config.timeout_ms)
    log_step("Preenchendo Usuario")
    campo_usuario.click()
    campo_usuario.fill(config.email)
    page.wait_for_timeout(500)

    log_step("Aguardando campo Senha")
    campo_senha = page.locator("#password")
    campo_senha.wait_for(state="visible", timeout=config.timeout_ms)
    log_step("Preenchendo Senha")
    campo_senha.click()
    campo_senha.fill(config.senha)
    page.wait_for_timeout(500)

    log_step("Enviando login")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(3000)

    aviso_senha = _capturar_aviso_senha_expirando(page)

    try:
        page.locator("#combo__input").wait_for(state="visible", timeout=config.timeout_ms)
    except PlaywrightTimeoutError as exc:
        texto_pagina = page.locator("body").inner_text(timeout=5000).lower()
        if any(mensagem in texto_pagina for mensagem in mensagens_login_invalido):
            raise LoginFailedError("usuario e senha estao incorretos ou expirados")
        raise LoginFailedError("login realizado, mas tela inicial do Banco PAN nao carregou") from exc

    log_step("Login Banco PAN concluido")
    return LoginResult(senha_expirando_mensagem=aviso_senha)
