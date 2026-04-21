import re
from dataclasses import dataclass
from typing import Dict, List

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

try:
    from .config_loader import AppConfig
    from .client_data_loader import ClientData
    from .login import LoginFailedError, perform_login
except ImportError:
    from config_loader import AppConfig
    from client_data_loader import ClientData
    from login import LoginFailedError, perform_login


class SiteLentoError(RuntimeError):
    pass


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def normalizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def somente_digitos(valor: str) -> str:
    return "".join(ch for ch in valor if ch.isdigit())


def digitos_monetarios(valor: str) -> str:
    digitos = somente_digitos(valor)
    if not digitos or int(digitos) == 0:
        return "0"
    return digitos


def extrair_numero_proposta(texto: str) -> str:
    match = re.search(r"Prop\.\s*(\d+)", texto, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def extrair_prazo_parcela(texto: str) -> str:
    match = re.search(r"(\d+\s*x\s*de\s*R\$\s*[\d\.\,]+)", texto, flags=re.IGNORECASE)
    if match:
        return normalizar_texto(match.group(1))
    return ""


def separar_parcela(parcela_texto: str) -> Dict[str, str]:
    match = re.search(r"(\d+)\s*x\s*(?:de\s*)?(R\$\s*[\d\.\,]+)", parcela_texto, flags=re.IGNORECASE)
    if not match:
        return {"quantidade_parcelas": "", "valor_parcela": ""}
    return {
        "quantidade_parcelas": match.group(1),
        "valor_parcela": normalizar_texto(match.group(2)),
    }


@dataclass
class Simulator:
    config: AppConfig
    client_data: ClientData

    def run(self) -> List[Dict[str, str]]:
        log_step("Iniciando execucao do simulador Santander")
        with sync_playwright() as p:
            log_step("Abrindo navegador")
            browser = p.chromium.launch(headless=self.config.headless)
            page = browser.new_page()
            page.set_default_timeout(self.config.timeout_ms)
            try:
                log_step(f"Acessando URL base: {self.config.base_url}")
                page.goto(self.config.base_url)
                page.wait_for_timeout(2500)

                log_step("Executando login")
                perform_login(page, self.config)

                resultados = self.simulador_pf(
                    page,
                    cpf=self.client_data.cpf,
                    timeout_ms=self.config.timeout_ms,
                )
                log_step("Execucao Santander finalizada")
                return resultados
            except LoginFailedError as exc:
                log_step("Falha de login detectada; finalizando automacao")
                return [{"status": "login_invalido", "mensagem": exc.message}]
            finally:
                browser.close()

    def simulador_pf(self, page: Page, cpf: str, timeout_ms: int) -> List[Dict[str, str]]:
        log_step("Selecionando produto Financiamento")
        self._selecionar_financiamento(page, timeout_ms)

        log_step("Aguardando tela de dados do cliente")
        page.locator('input[formcontrolname="documentNumber"]').first.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

        log_step("Preenchendo CPF do cliente")
        campo_cpf = page.locator('input[formcontrolname="documentNumber"]').first
        self._digitar_e_tab(page, campo_cpf, cpf, espera_apos_tab_ms=2500)
        self._aguardar_pos_cpf(page, timeout_ms)

        log_step("Preenchendo data de nascimento")
        campo_data = page.locator('input[formcontrolname="dateOfBirth"]').first
        campo_data.wait_for(state="visible", timeout=timeout_ms)
        self._digitar_e_tab(
            page,
            campo_data,
            somente_digitos(self.client_data.data_nascimento),
            espera_apos_tab_ms=1500,
        )

        log_step("Selecionando busca por placa")
        self._selecionar_radio_por_texto(page, "Busca por placa", timeout_ms)
        page.wait_for_timeout(1000)

        log_step("Preenchendo placa do veiculo")
        campo_placa = page.locator('input[formcontrolname="searchPlate"]').first
        campo_placa.wait_for(state="visible", timeout=timeout_ms)
        self._digitar_e_tab(
            page,
            campo_placa,
            self.client_data.placa_veiculo.upper(),
            espera_apos_tab_ms=4500,
        )

        log_step("Aguardando carregamento do veiculo")
        campo_valor = page.locator('input[formcontrolname="vehicleAmount"]').first
        campo_valor.wait_for(state="visible", timeout=timeout_ms)
        page.wait_for_timeout(1500)

        log_step("Preenchendo valor do veiculo")
        self._digitar_e_tab(
            page,
            campo_valor,
            digitos_monetarios(self.client_data.valor_financiamento),
            espera_apos_tab_ms=1500,
        )

        log_step("Concordando com termos")
        botao_termos = page.get_by_role("button", name="Concordar e continuar").first
        botao_termos.scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        self._clicar_botao_por_texto(page, "Concordar e continuar")

        log_step("Confirmando licenciamento quando solicitado")
        self._confirmar_licenciamento_se_aparecer(page)

        log_step("Aguardando ofertas da simulacao")
        self._aguardar_tela_ofertas(page, timeout_ms)

        log_step("Coletando ofertas com debito em conta Santander")
        ofertas_debito = self._coletar_ofertas_por_pagamento(
            page,
            codigo_pagamento="DC",
            nome_pagamento="Debito em conta Santander",
            timeout_ms=timeout_ms,
        )

        log_step("Coletando ofertas com boleto")
        ofertas_boleto = self._coletar_ofertas_por_pagamento(
            page,
            codigo_pagamento="CA",
            nome_pagamento="Boleto",
            timeout_ms=timeout_ms,
        )

        if not ofertas_debito and not ofertas_boleto:
            return [
                {
                    "status": "nao_aprovado_credito",
                    "mensagem": "Nenhuma parcela foi encontrada no Santander.",
                }
            ]

        if self._ofertas_iguais(ofertas_debito, ofertas_boleto):
            return ofertas_debito or ofertas_boleto
        return ofertas_debito + ofertas_boleto

    def _digitar_e_tab(self, page: Page, campo: Locator, valor: str, espera_apos_tab_ms: int = 900) -> None:
        self._aguardar_loading_sumir(page, 10000)
        try:
            campo.click()
        except PlaywrightTimeoutError:
            self._fechar_simulacoes_anteriores(page)
            self._aguardar_loading_sumir(page, 10000)
            campo.click()
        page.wait_for_timeout(400)
        campo.fill("")
        page.wait_for_timeout(300)
        campo.type(valor, delay=90)
        page.wait_for_timeout(700)
        page.keyboard.press("Tab")
        page.wait_for_timeout(espera_apos_tab_ms)

    def _selecionar_financiamento(self, page: Page, timeout_ms: int) -> None:
        try:
            page.wait_for_url(lambda url: "/showcase" in url, timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

        financiamento = page.get_by_text("Financiamento", exact=True).first
        try:
            if financiamento.is_visible(timeout=5000):
                financiamento.click()
                page.wait_for_timeout(800)
        except PlaywrightTimeoutError:
            pass

        self._clicar_botao_por_texto(page, "Continuar")
        page.wait_for_timeout(2500)
        page.wait_for_url(lambda url: "/proposal/step-personal" in url, timeout=timeout_ms)

    def _selecionar_radio_por_texto(self, page: Page, texto: str, timeout_ms: int) -> None:
        radio = page.locator("mat-radio-button").filter(has_text=texto).first
        radio.wait_for(state="visible", timeout=timeout_ms)
        radio.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        radio.click()
        page.wait_for_timeout(900)

    def _aguardar_loading_sumir(self, page: Page, timeout_ms: int) -> None:
        for selector in (".loading-indicator__overlay", "app-loading-indicator"):
            try:
                page.locator(selector).first.wait_for(state="hidden", timeout=timeout_ms)
            except PlaywrightTimeoutError:
                pass

    def _aguardar_pos_cpf(self, page: Page, timeout_ms: int) -> None:
        tempo_total = 0
        intervalo = 1000
        while tempo_total < timeout_ms:
            self._aguardar_loading_sumir(page, 3000)
            self._fechar_simulacoes_anteriores(page)
            campo_data = page.locator('input[formcontrolname="dateOfBirth"]').first
            try:
                if campo_data.is_visible(timeout=1000) and self._overlay_vazio(page):
                    return
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(intervalo)
            tempo_total += intervalo

    def _fechar_simulacoes_anteriores(self, page: Page) -> None:
        try:
            overlay_texto = normalizar_texto(page.locator(".cdk-overlay-container").inner_text(timeout=2000))
            if "simula" not in overlay_texto.lower():
                return
        except PlaywrightTimeoutError:
            return

        log_step("Fechando aviso de simulacoes anteriores")
        fechou = bool(
            page.evaluate(
                r"""() => {
                    const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                    const overlay = document.querySelector('.cdk-overlay-container');
                    if (!overlay) return false;
                    const buttons = [...overlay.querySelectorAll('button')];
                    const button = buttons.find((item) => normalize(item.innerText) === 'Fechar')
                        || buttons.find((item) => normalize(item.innerText).includes('close'));
                    if (!button) return false;
                    button.click();
                    return true;
                }"""
            )
        )
        if not fechou:
            self._clicar_botao_por_texto(page, "Fechar")
        page.wait_for_timeout(1200)

    def _overlay_vazio(self, page: Page) -> bool:
        try:
            return not normalizar_texto(page.locator(".cdk-overlay-container").inner_text(timeout=500))
        except PlaywrightTimeoutError:
            return True

    def _clicar_botao_por_texto(self, page: Page, texto: str) -> bool:
        botao = page.get_by_role("button", name=texto).first
        try:
            if botao.is_visible(timeout=2500):
                botao.click()
                return True
        except Exception:
            pass

        return bool(
            page.evaluate(
                r"""(text) => {
                    const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                    const buttons = [...document.querySelectorAll('button')];
                    const button = buttons.find((item) => normalize(item.innerText) === text);
                    if (!button) return false;
                    button.click();
                    return true;
                }""",
                texto,
            )
        )

    def _confirmar_licenciamento_se_aparecer(self, page: Page) -> None:
        for _ in range(20):
            page.wait_for_timeout(500)
            overlay_texto = ""
            try:
                overlay_texto = normalizar_texto(page.locator(".cdk-overlay-container").inner_text(timeout=1000))
            except PlaywrightTimeoutError:
                pass

            if "licenciamento" in overlay_texto.lower():
                page.evaluate(
                    r"""() => {
                        const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                        const overlay = document.querySelector('.cdk-overlay-container');
                        const buttons = [...(overlay || document).querySelectorAll('button')];
                        const continuar = buttons.reverse()
                            .find((button) => normalize(button.innerText) === 'Continuar');
                        if (continuar) continuar.click();
                    }"""
                )
                page.wait_for_timeout(1500)
                return

            if "/proposal/step-offers" in page.url or "Por favor, aguarde" in page.locator("body").inner_text(timeout=1000):
                return

    def _aguardar_tela_ofertas(self, page: Page, timeout_ms: int) -> None:
        page.wait_for_url(lambda url: "/proposal/step-offers" in url, timeout=max(timeout_ms, 120000))
        self._aguardar_recalculo(page, timeout_ms=max(timeout_ms, 120000))
        self._aguardar_cards_parcela(page, timeout_ms)

    def _aguardar_recalculo(self, page: Page, timeout_ms: int) -> None:
        page.wait_for_timeout(1200)
        try:
            page.wait_for_function(
                """() => {
                    const text = document.body.innerText || '';
                    return !text.includes('Por favor, aguarde') &&
                           !text.includes('Encontrando ofertas');
                }""",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            log_step("Recalculo ainda exibe loader; seguindo com os dados visiveis")

    def _aguardar_cards_parcela(self, page: Page, timeout_ms: int) -> None:
        page.wait_for_function(
            r"""() => {
                const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                return [...document.querySelectorAll('.card-installment')]
                    .some((item) => /\d+x\s+de\s+R\$/.test(normalize(item.innerText)));
            }""",
            timeout=max(timeout_ms, 60000),
        )

    def _coletar_ofertas_por_pagamento(
        self,
        page: Page,
        codigo_pagamento: str,
        nome_pagamento: str,
        timeout_ms: int,
    ) -> List[Dict[str, str]]:
        self._selecionar_forma_pagamento(page, codigo_pagamento, timeout_ms)
        proposta = extrair_numero_proposta(page.locator("body").inner_text(timeout=5000))
        entrada = self._valor_input(page, "entryValue")
        financiado = self._valor_input(page, "releasedAmount")
        valor_venda = self._valor_input(page, "purchaseValue")

        resultados: List[Dict[str, str]] = []
        cards = page.locator(".card-installment")
        for index in range(cards.count()):
            texto_card = normalizar_texto(cards.nth(index).inner_text())
            parcela = extrair_prazo_parcela(texto_card)
            if not parcela:
                continue
            detalhes_parcela = separar_parcela(parcela)
            resultados.append(
                {
                    "quantidade_parcelas": detalhes_parcela["quantidade_parcelas"],
                    "valor_parcela": detalhes_parcela["valor_parcela"],
                    "parcela": parcela,
                    "taxa": "",
                    "entrada": entrada,
                    "financiado": financiado,
                    "valor_venda": valor_venda,
                    "proposta": proposta,
                    "forma_pagamento": nome_pagamento,
                    "status": "aprovado",
                }
            )

        parcelas_log = ", ".join(oferta["parcela"] for oferta in resultados) or "nenhuma parcela"
        log_step(f"{nome_pagamento}: {parcelas_log}")
        return resultados

    def _selecionar_forma_pagamento(self, page: Page, codigo_pagamento: str, timeout_ms: int) -> None:
        cards_antes = "|".join(self._textos_cards(page))
        texto_pagamento = "Boleto" if codigo_pagamento == "CA" else "Debito em conta Santander"
        esta_selecionado = bool(
            page.evaluate(
                """(value) => {
                    const input = [...document.querySelectorAll('input[type="radio"]')]
                        .find((item) => item.value === value);
                    return Boolean(input && input.checked);
                }""",
                codigo_pagamento,
            )
        )
        if esta_selecionado:
            return

        if codigo_pagamento == "CA":
            page.locator("mat-radio-button").filter(has_text="Boleto").first.click()
        else:
            page.locator("mat-radio-button").filter(has_text="bito em conta Santander").first.click()
        log_step(f"Selecionando forma de pagamento: {texto_pagamento}")
        page.wait_for_timeout(1500)
        try:
            page.wait_for_function(
                """(value) => {
                    const input = [...document.querySelectorAll('input[type="radio"]')]
                        .find((item) => item.value === value);
                    return Boolean(input && input.checked);
                }""",
                arg=codigo_pagamento,
                timeout=max(timeout_ms, 60000),
            )
        except PlaywrightTimeoutError:
            log_step("Forma de pagamento demorou para marcar; aguardando recalculo")

        if cards_antes:
            try:
                page.wait_for_function(
                    r"""(previousCards) => {
                        const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                        const currentCards = [...document.querySelectorAll('.card-installment')]
                            .map((item) => normalize(item.innerText))
                            .join('|');
                        return currentCards && currentCards !== previousCards;
                    }""",
                    arg=cards_antes,
                    timeout=max(timeout_ms, 60000),
                )
            except PlaywrightTimeoutError:
                log_step("Parcelas nao mudaram apos troca de pagamento; seguindo se o loader terminou")

        self._aguardar_recalculo(page, timeout_ms=max(timeout_ms, 60000))
        self._aguardar_cards_parcela(page, timeout_ms=max(timeout_ms, 60000))

    def _textos_cards(self, page: Page) -> List[str]:
        return [
            normalizar_texto(texto)
            for texto in page.locator(".card-installment").all_inner_texts()
        ]

    def _valor_input(self, page: Page, formcontrolname: str) -> str:
        valor = page.evaluate(
            """(name) => {
                const inputs = [...document.querySelectorAll(`input[formcontrolname="${name}"]`)];
                const input = inputs.find((item) => item.type === 'text') || inputs[0];
                return input ? input.value : '';
            }""",
            formcontrolname,
        )
        return normalizar_texto(str(valor))

    def _ofertas_iguais(self, ofertas_a: List[Dict[str, str]], ofertas_b: List[Dict[str, str]]) -> bool:
        if not ofertas_a or not ofertas_b or len(ofertas_a) != len(ofertas_b):
            return False

        def assinatura(ofertas: List[Dict[str, str]]) -> list[tuple[str, str, str, str]]:
            return [
                (
                    oferta.get("parcela", ""),
                    oferta.get("entrada", ""),
                    oferta.get("financiado", ""),
                    oferta.get("valor_venda", ""),
                )
                for oferta in ofertas
            ]

        return assinatura(ofertas_a) == assinatura(ofertas_b)
