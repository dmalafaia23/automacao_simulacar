import re
from dataclasses import dataclass
from typing import Dict, List
from playwright.sync_api import Locator, Page, sync_playwright

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

try:
    from .config_loader import AppConfig
    from .client_data_loader import ClientData
    from .login import LoginFailedError, LoginResult, perform_login
except ImportError:
    from config_loader import AppConfig
    from client_data_loader import ClientData
    from login import LoginFailedError, LoginResult, perform_login


class SiteLentoError(RuntimeError):
    pass


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def normalizar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def digitos_monetarios(valor: str) -> str:
    digitos = "".join(ch for ch in valor if ch.isdigit())
    if not digitos or int(digitos) == 0:
        return "0"
    return digitos


def somente_digitos(valor: str) -> str:
    return "".join(ch for ch in valor if ch.isdigit())


def extrair_numero_proposta(texto: str) -> str:
    match = re.search(r"#\s*(\d+)", texto)
    return match.group(1) if match else ""


def extrair_prazo_parcela(texto: str) -> str:
    match = re.search(r"(\d+\s*x\s*(?:de\s*)?R\$\s*[\d\.\,]+)", texto, flags=re.IGNORECASE)
    if match:
        return normalizar_texto(match.group(1))

    match = re.search(r"(\d+)\s*parcelas\s*(R\$\s*[\d\.\,]+)", texto, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)}x de {normalizar_texto(match.group(2))}"
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
        log_step("Iniciando execucao do simulador Banco PAN")
        with sync_playwright() as p:
            log_step("Abrindo navegador")
            browser = p.chromium.launch(headless=self.config.headless)
            log_step("Abrindo nova pagina")
            page = browser.new_page()
            log_step("Configurando timeout padrao")
            page.set_default_timeout(self.config.timeout_ms)
            log_step(f"Acessando URL base: {self.config.base_url}")
            page.goto(self.config.base_url)
            page.wait_for_timeout(3000)
            try:
                log_step("Executando login")
                login_result = perform_login(page, self.config)
                log_step("Mapeando CPF da proposta")
                resultados = self.simulador_pf(
                    page,
                    cpf=self.client_data.cpf,
                    timeout_ms=self.config.timeout_ms,
                    login_result=login_result,
                )
                log_step("Execucao Banco PAN finalizada")
                return resultados
            except LoginFailedError as exc:
                log_step("Falha de login detectada; finalizando automacao")
                return [
                    {
                        "status": "login_invalido",
                        "mensagem": exc.message,
                    }
                ]

    def simulador_pf(
        self,
        page,
        cpf: str,
        timeout_ms: int,
        login_result: LoginResult | None = None,
    ) -> List[Dict[str, str]]:
        resultados: List[Dict[str, str]] = []
        if login_result and login_result.senha_expirando_mensagem:
            resultados.append(
                {
                    "status": "senha_expirando",
                    "mensagem": login_result.senha_expirando_mensagem,
                }
            )

        log_step("Aguardando campo CPF")
        campo_cpf = page.locator("#combo__input")
        try:
            campo_cpf.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise SiteLentoError("Site lento: campo CPF do Banco PAN nao carregou.") from exc

        log_step("Selecionando categoria Carro")
        radio_carro = page.locator('input[name="mahoe"][value="financiamento"]')
        if radio_carro.is_visible():
            radio_carro.check()
            page.wait_for_timeout(500)

        log_step("Preenchendo CPF")
        self._digitar_e_tab(page, campo_cpf, cpf)
        page.wait_for_timeout(2500)

        log_step("Preenchendo telefone")
        campo_telefone = page.locator('input[formcontrolname="cellNumber"], input[placeholder="Digite o celular..."]').first
        campo_telefone.wait_for(state="visible", timeout=timeout_ms)
        self._preencher_telefone_e_aguardar_placa(page, campo_telefone, timeout_ms)

        log_step("Preenchendo placa")
        campo_placa = page.locator('input[placeholder="Digite a placa..."]:not([disabled])').first
        campo_placa.wait_for(state="visible", timeout=timeout_ms)
        self._digitar_e_tab(page, campo_placa, self.client_data.placa_veiculo.upper())
        page.wait_for_timeout(2500)

        log_step("Aguardando campos de valores do veiculo")
        campo_valor_venda = page.locator('input[label="Valor de venda"]').first
        campo_valor_entrada = page.locator('input[label="Valor de entrada"]').first
        campo_valor_venda.wait_for(state="visible", timeout=timeout_ms)
        campo_valor_entrada.wait_for(state="visible", timeout=timeout_ms)

        log_step("Preenchendo valor do financiamento")
        self._digitar_e_tab(
            page,
            campo_valor_venda,
            digitos_monetarios(self.client_data.valor_financiamento),
        )

        log_step("Preenchendo valor de entrada")
        self._digitar_e_tab(
            page,
            campo_valor_entrada,
            digitos_monetarios(self.client_data.valor_entrada),
        )

        ids_antes = self._ids_propostas(page)

        log_step("Clicando em Simular")
        botao_simular = page.locator("button", has_text="Simular").first
        botao_simular.wait_for(state="visible", timeout=timeout_ms)
        botao_simular.click()

        log_step("Aguardando simulacao do Banco PAN")
        novo_card = self._aguardar_nova_proposta(page, ids_antes, timeout_ms)
        texto_card = normalizar_texto(novo_card.inner_text())
        numero_proposta = extrair_numero_proposta(texto_card)

        log_step(f"Abrindo proposta gerada #{numero_proposta}")
        botao_visualizar = novo_card.locator("button", has_text="Visualizar proposta").first
        botao_visualizar.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        botao_visualizar.click()
        page.wait_for_timeout(2000)
        page.wait_for_url(re.compile(r".*/detalhes-proposta/.*"), timeout=timeout_ms)
        page.wait_for_timeout(4000)

        ofertas = self._coletar_parcelas_aprovadas(page, numero_proposta)
        if not ofertas:
            resultados.append(
                {
                    "status": "nao_aprovado_credito",
                    "mensagem": "Nenhuma parcela aprovada foi encontrada no Banco PAN.",
                    "proposta": numero_proposta,
                }
            )
            return resultados

        resultados.extend(ofertas)
        return resultados

    def _digitar_e_tab(self, page: Page, campo: Locator, valor: str, espera_apos_tab_ms: int = 900) -> None:
        campo.click()
        page.wait_for_timeout(400)
        campo.fill("")
        page.wait_for_timeout(300)
        campo.type(valor, delay=90)
        page.wait_for_timeout(700)
        page.keyboard.press("Tab")
        page.wait_for_timeout(espera_apos_tab_ms)

    def _preencher_telefone_e_aguardar_placa(self, page: Page, campo_telefone: Locator, timeout_ms: int) -> None:
        valores_tentativa = [
            somente_digitos(self.client_data.celular),
            self.client_data.celular,
        ]
        for valor in valores_tentativa:
            self._digitar_e_tab(page, campo_telefone, valor, espera_apos_tab_ms=3000)
            campo_placa_habilitado = page.locator('input[placeholder="Digite a placa..."]:not([disabled])').first
            try:
                campo_placa_habilitado.wait_for(state="visible", timeout=8000)
                return
            except PlaywrightTimeoutError:
                log_step("Campo placa ainda desabilitado; tentando telefone novamente")

        raise SiteLentoError("Campo de placa nao habilitou apos preenchimento do telefone no Banco PAN.")

    def _ids_propostas(self, page: Page) -> set[str]:
        ids: set[str] = set()
        cards = page.locator("app-vehicle-offer")
        for index in range(cards.count()):
            texto = normalizar_texto(cards.nth(index).inner_text())
            numero = extrair_numero_proposta(texto)
            if numero:
                ids.add(numero)
        return ids

    def _aguardar_nova_proposta(self, page: Page, ids_antes: set[str], timeout_ms: int) -> Locator:
        tempo_aguardado = 0
        intervalo = 3000
        max_timeout = max(timeout_ms, 120000)
        while tempo_aguardado < max_timeout:
            cards = page.locator("app-vehicle-offer")
            total_cards = cards.count()
            for index in range(total_cards):
                card = cards.nth(index)
                texto = normalizar_texto(card.inner_text())
                numero = extrair_numero_proposta(texto)
                if numero and numero not in ids_antes:
                    return card
            page.wait_for_timeout(intervalo)
            tempo_aguardado += intervalo

        cards = page.locator("app-vehicle-offer")
        if cards.count() > 0:
            primeiro_card = cards.first
            texto = normalizar_texto(primeiro_card.inner_text())
            numero = extrair_numero_proposta(texto)
            if numero and numero not in ids_antes:
                return primeiro_card
        raise SiteLentoError("Banco PAN nao retornou uma nova proposta apos a simulacao.")

    def _coletar_parcelas_aprovadas(self, page: Page, numero_proposta: str) -> List[Dict[str, str]]:
        log_step("Coletando parcelas aprovadas")
        opcoes = page.locator("app-custom-checkbox.installments-container__radio").filter(
            has_text="Aprovado"
        )
        total = opcoes.count()
        resultados: List[Dict[str, str]] = []
        for index in range(total):
            opcao = opcoes.nth(index)
            texto_opcao = normalizar_texto(opcao.inner_text())
            if "Indispon" in texto_opcao:
                continue

            log_step(f"Selecionando parcela aprovada {index + 1} de {total}")
            opcao.scroll_into_view_if_needed()
            page.wait_for_timeout(700)
            opcao.click()
            page.wait_for_timeout(2000)

            resumo = normalizar_texto(page.locator("app-proposal-resume").inner_text())
            parcela_texto = extrair_prazo_parcela(resumo) or extrair_prazo_parcela(texto_opcao)
            entrada_texto = page.locator("#input-entry-value").input_value().strip()
            financiado_texto = page.locator("#input-funded-value").input_value().strip()
            valor_venda_texto = page.locator("#input-saleValue-value").input_value().strip()
            detalhes_parcela = separar_parcela(parcela_texto)

            resultados.append(
                {
                    "quantidade_parcelas": detalhes_parcela["quantidade_parcelas"],
                    "valor_parcela": detalhes_parcela["valor_parcela"],
                    "parcela": parcela_texto,
                    "taxa": "",
                    "entrada": entrada_texto,
                    "financiado": financiado_texto,
                    "valor_venda": valor_venda_texto,
                    "proposta": numero_proposta,
                    "status": "aprovado",
                }
            )

        return resultados
