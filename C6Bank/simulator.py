from dataclasses import dataclass
from typing import Dict, List
from playwright.sync_api import sync_playwright

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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


@dataclass
class Simulator:
    config: AppConfig
    client_data: ClientData

    def run(self) -> List[Dict[str, str]]:
        log_step("Iniciando execução do simulador")
        with sync_playwright() as p:
            log_step("Abrindo navegador")
            browser = p.chromium.launch(headless=self.config.headless)
            log_step("Abrindo nova pagina")
            context = browser.new_context(
                geolocation={"latitude": -23.5505, "longitude": -46.6333}
            )
            context.grant_permissions(["geolocation"], origin=self.config.base_url)
            page = context.new_page()
            log_step("Configurando timeout padrao")
            page.set_default_timeout(self.config.timeout_ms)
            log_step(f"Acessando URL base: {self.config.base_url}")
            page.goto(self.config.base_url)
            page.wait_for_timeout(4500)
            log_step("Executando login")
            try:
                perform_login(page, self.config)
                log_step("Executando simulador PF")
                resultados = self.simulador_pf(
                    page,
                    cpf=self.client_data.cpf,
                    timeout_ms=self.config.timeout_ms,
                )
                # Não fechar o navegador por enquanto, conforme solicitado.
                log_step("Execução do simulador finalizada")
                return resultados
            except LoginFailedError as exc:
                log_step("Falha de login detectada; finalizando automacao")
                return [
                    {
                        "status": "login_invalido",
                        "mensagem": exc.message,
                    }
                ]

    def simulador_pf(self, page, cpf: str, timeout_ms: int) -> List[Dict[str, str]]:
        log_step("Aguardando botão 'Criar uma nova proposta'")
        botao_nova_proposta = page.get_by_role("button", name="Criar uma nova proposta")
        try:
            botao_nova_proposta.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise SiteLentoError("Site lento: botão 'Criar uma nova proposta' não carregou.") from exc

        log_step("Clicando em 'Criar uma nova proposta'")
        botao_nova_proposta.click()
        page.wait_for_timeout(6000)

        log_step("Acessando campo CPF")
        page.get_by_role("textbox", name="CPF").click()
        page.wait_for_timeout(1000)
        log_step("Preenchendo CPF")
        page.get_by_role("textbox", name="CPF").fill(cpf)
        page.wait_for_timeout(1000)

        log_step("Acessando campo Celular")
        page.get_by_role("textbox", name="Celular").click()
        page.wait_for_timeout(1000)
        log_step("Preenchendo Celular")
        page.get_by_role("textbox", name="Celular").fill(self.client_data.celular)
        page.wait_for_timeout(1000)

        log_step("Acessando campo Data de Nascimento")
        page.get_by_role("textbox", name="Data de Nascimento").click()
        page.wait_for_timeout(500)
        log_step("Preenchendo Data de Nascimento")
        page.get_by_role("textbox", name="Data de Nascimento").fill(self.client_data.data_nascimento)
        page.wait_for_timeout(500)

        checkbox_cnh = page.locator(".mat-checkbox-inner-container").first
        if self.client_data.possui_cnh:
            log_step("Checkbox de CNH deve permanecer marcado")
            page.wait_for_timeout(500)
        else:
            log_step("Desmarcando checkbox de CNH")
            checkbox_cnh.click()
            page.wait_for_timeout(500)

        log_step("Abrindo selecao de UF")
        page.locator("#mat-select-value-1").click()
        page.wait_for_timeout(500)
        log_step(f"Selecionando UF: {self.client_data.uf}")
        page.locator("#mat-option-25").get_by_text(self.client_data.uf).click()
        page.wait_for_timeout(500)

        log_step("Acessando campo Placa")
        page.get_by_role("textbox", name="Placa").click()
        page.wait_for_timeout(500)
        log_step("Preenchendo Placa")
        page.get_by_role("textbox", name="Placa").fill(self.client_data.placa_veiculo)
        page.wait_for_timeout(1500)

        log_step("Abrindo combobox Marca")
        page.get_by_role("combobox", name="Marca").click()
        page.wait_for_timeout(2500)

        log_step("Acessando campo Valor do Veículo")
        campo_valor_veiculo = page.get_by_role("textbox", name="Valor do Veículo")
        campo_valor_veiculo.click()
        page.wait_for_timeout(800)
        log_step("Preenchendo Valor do Veículo")
        campo_valor_veiculo.press("Control+A")
        page.wait_for_timeout(300)
        campo_valor_veiculo.type(self.client_data.valor_financiamento, delay=120)
        page.wait_for_timeout(800)
        page.keyboard.press("Tab")
        page.wait_for_timeout(800)

        log_step("Acessando campo Valor de entrada")
        campo_valor_entrada = page.get_by_role("textbox", name="Valor de entrada")
        campo_valor_entrada.click()
        page.wait_for_timeout(800)
        log_step("Preenchendo Valor de entrada")
        campo_valor_entrada.press("Control+A")
        page.wait_for_timeout(300)
        campo_valor_entrada.type(self.client_data.valor_entrada, delay=120)
        page.wait_for_timeout(800)
        page.keyboard.press("Tab")
        page.wait_for_timeout(800)

        log_step("Clicando em Simular")
        page.get_by_role("button", name="Simular").click()
        page.wait_for_timeout(30000)

        aviso_entrada = page.get_by_role("heading", name="Valor de entrada abaixo do mí")
        if aviso_entrada.is_visible():
            log_step("Fechando aviso de entrada baixa")
            page.get_by_role("button", name="ENTENDI").click()
            page.wait_for_timeout(1000)

        log_step("Abrindo configuracoes do lojista")
        page.get_by_text("Configurações do lojista").click()
        page.wait_for_timeout(2500)
        log_step("Configurando taxa do lojista")
        campo_porcentagem = page.get_by_role("textbox", name="Porcentagem")
        campo_porcentagem.click()
        page.wait_for_timeout(500)
        campo_porcentagem.press("Control+A")
        page.wait_for_timeout(300)
        campo_porcentagem.type(self.client_data.retorno_estrelas, delay=120)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Confirmar").click()
        page.wait_for_timeout(5000)

        log_step("Voltando para o topo da pagina")
        page.locator("body").press("Home")
        page.wait_for_timeout(1000)

        resultados: List[Dict[str, str]] = []
        parcelas = [60, 48, 36, 24, 12]
        for parcela in parcelas:
            nome_botao = f"{parcela}x de R$"
            log_step(f"Selecionando parcela {nome_botao}")
            try:
                botao_parcela = page.get_by_role("button", name=nome_botao)
                if not botao_parcela.is_visible():
                    log_step(f"Parcela {nome_botao} nao encontrada, pulando")
                    page.wait_for_timeout(500)
                    continue
                botao_parcela.click()
                page.wait_for_timeout(5000)
                parcela_texto = botao_parcela.inner_text().strip()

                entrada_campo = page.get_by_role("textbox", name="Entrada")
                entrada_campo.click()
                page.wait_for_timeout(500)
                entrada_texto = entrada_campo.input_value().strip()
                page.wait_for_timeout(3000)

                financiado_texto = page.get_by_text("FinanciamentoR$").inner_text().strip()
                page.wait_for_timeout(500)

                linha = (
                    f"[PARCELA] {parcela_texto} | "
                    f"Entrada: {entrada_texto} | Financiado: {financiado_texto}"
                )
                resultados.append(
                    {
                        "parcela": parcela_texto,
                        "taxa": "",
                        "entrada": entrada_texto,
                        "financiado": financiado_texto,
                    }
                )
                print(linha)
            except Exception as exc:
                print(f"[WARN] Falha ao selecionar parcela {nome_botao}: {exc}")
                page.wait_for_timeout(500)
                continue

        if resultados:
            log_step("Exibindo resultados em alerta")
            page.evaluate(
                "data => alert(data)",
                "\n".join(
                    (
                        f"[PARCELA] {item['parcela']} | "
                        f"Entrada: {item['entrada']} | Financiado: {item['financiado']}"
                    )
                    for item in resultados
                ),
            )
        page.wait_for_timeout(10000)
        return resultados
