from dataclasses import dataclass
from typing import Dict, List, Optional
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


def is_driver_connection_error(exc: Exception) -> bool:
    message = str(exc)
    return (
        "Connection closed while reading from the driver" in message
        or "Target closed" in message
        or "Browser closed" in message
        or "has been closed" in message
    )


@dataclass
class Simulator:
    config: AppConfig
    client_data: ClientData

    def run(self) -> List[Dict[str, str]]:
        log_step("Iniciando execução do simulador")
        max_driver_retries = 2
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_driver_retries + 1):
            with sync_playwright() as p:
                log_step("Abrindo navegador")
                browser = p.chromium.launch(headless=self.config.headless)
                log_step("Abrindo nova página")
                page = browser.new_page()
                log_step("Configurando timeout padrão")
                page.set_default_timeout(self.config.timeout_ms)
                try:
                    log_step(f"Acessando URL base: {self.config.base_url}")
                    page.goto(self.config.base_url)
                    page.wait_for_timeout(4500)
                    log_step("Executando login")
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
                except Exception as exc:
                    last_exc = exc
                    if is_driver_connection_error(exc) and attempt < max_driver_retries:
                        log_step(
                            "Conexao com o driver fechada. Reiniciando o navegador "
                            f"(tentativa {attempt}/{max_driver_retries})."
                        )
                        continue
                    raise
        if last_exc is not None:
            raise last_exc
        return []

    def simulador_pf(self, page, cpf: str, timeout_ms: int) -> List[Dict[str, str]]:
        mensagem_sem_aprovacao = "Não temos condições aprováveis para este cliente."

        def retorno_sem_aprovacao() -> List[Dict[str, str]]:
            log_step("Cliente sem credito aprovado; finalizando automacao")
            return [
                {
                    "status": "nao_aprovado_credito",
                    "mensagem": mensagem_sem_aprovacao,
                }
            ]

        botao_novo_simulador = page.get_by_role("button", name="Novo Simulador PF")
        try:
            log_step("Aguardando botão 'Novo Simulador PF'")
            botao_novo_simulador.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            log_step("Botão não apareceu, recarregando página")
            page.reload()
            try:
                log_step("Aguardando botão 'Novo Simulador PF' (após reload)")
                botao_novo_simulador.wait_for(state="visible", timeout=timeout_ms)
            except PlaywrightTimeoutError as exc:
                raise SiteLentoError("Site lento: botão 'Novo Simulador PF' não carregou.") from exc

        log_step("Clicando em 'Novo Simulador PF'")
        botao_novo_simulador.click()
        page.wait_for_timeout(3000)
        campo_cpf = page.get_by_role("textbox", name="CPF")
        log_step("Aguardando campo CPF")
        campo_cpf.wait_for(state="visible", timeout=timeout_ms)
        log_step("Preenchendo CPF")
        campo_cpf.click()
        page.wait_for_timeout(500)
        campo_cpf.fill(cpf)
        page.wait_for_timeout(1500)
        aviso_sem_aprovacao = page.get_by_text(mensagem_sem_aprovacao, exact=True)
        if aviso_sem_aprovacao.is_visible():
            return retorno_sem_aprovacao()
        log_step("Confirmando CPF")
        page.get_by_role("button", name="Continuar").click()
        page.wait_for_timeout(3500)
        if aviso_sem_aprovacao.is_visible():
            return retorno_sem_aprovacao()

        log_step("Selecionando aba Placa")
        aba_placa = page.get_by_role("tab", name="Placa")
        if not aba_placa.is_visible():
            if aviso_sem_aprovacao.is_visible():
                return retorno_sem_aprovacao()
            raise SiteLentoError("Fluxo não avançou para a etapa da placa após a consulta do CPF.")
        aba_placa.click()
        page.wait_for_timeout(1000)
        log_step("Preenchendo placa do veiculo")
        page.get_by_role("textbox", name="Placa").click()
        page.wait_for_timeout(500)
        page.get_by_role("textbox", name="Placa").fill(self.client_data.placa_veiculo)
        page.wait_for_timeout(1000)
        log_step("Buscando veiculo")
        page.get_by_role("button", name="Buscar veículo").click()
        page.wait_for_timeout(2500)
        # Seleciona o primeiro rádio disponível após a busca.
        log_step("Selecionando primeiro veiculo encontrado")
        page.get_by_role("radio").first.check()
        page.wait_for_timeout(1000)
        log_step("Preenchendo valor do veiculo")
        page.get_by_role("textbox", name="valor do veículo").click()
        page.wait_for_timeout(500)
        page.get_by_role("textbox", name="valor do veículo").fill(self.client_data.valor_financiamento)
        page.wait_for_timeout(1500)
        log_step("Simulando financiamento")
        page.get_by_role("button", name="Simular financiamento").click()
        page.wait_for_timeout(12000)

        # Configurar taxa (retorno)
        log_step("Abrindo configuracao de retorno")
        page.locator("//*[@id=\"financing-conditions\"]/div/form/div/div[3]/div/app-simulator-installments/div[1]/div[2]/div/div/div[1]/ul/li[2]/app-return-settings/div/button").click()
        page.wait_for_timeout(4000)
        log_step("Abrindo seletor de retorno")
        seletor_retorno = page.locator("#ids-select-11")
        seletor_retorno.wait_for(state="visible", timeout=timeout_ms)
        seletor_retorno.click()
        page.wait_for_timeout(1000)
        try:
            log_step(f"Selecionando retorno: {self.client_data.retorno_estrelas}")
            opcao_retorno = page.get_by_role(
                "option",
                name=self.client_data.retorno_estrelas,
                exact=True,
            )
            opcao_retorno.wait_for(state="visible", timeout=timeout_ms)
            opcao_retorno.click()
        except Exception as exc:
            opcoes_disponiveis = [
                texto.strip()
                for texto in page.locator("[role='option']").all_inner_texts()
                if texto.strip()
            ]
            print(
                f"[WARN] Falha ao selecionar retorno {self.client_data.retorno_estrelas}: {exc}. "
                f"Opcoes encontradas: {opcoes_disponiveis}"
            )
            return []
        page.wait_for_timeout(1000)
        log_step("Aplicando retorno selecionado")
        page.get_by_role("button", name="Alterar retorno").click()
        page.wait_for_timeout(8000)

        # Coletar valores das opções de parcelamento
        log_step("Coletando opcoes de parcelamento")
        resumo_parcela = page.locator("//*[@id=\"summary-simulation-card\"]/div[2]/div/div[2]/p")
        resumo_taxa = page.locator("//*[@id=\"summary-simulation-card\"]/div[2]/ol/li[1]/span/span[2]/span[1]")
        resumo_entrada = page.locator("//*[@id=\"summary-simulation-card\"]/div[2]/ol/li[2]/span/span[2]/span")
        valor_financiado = page.locator("//*[@id=\"financing-conditions\"]/div/form/div/div[2]/div[3]/div/div[2]/div/div[2]/div/div[2]/p")

        radios = page.locator("[data-cy=\"select-installment\"]")
        total_radios = radios.count()
        resultados: List[Dict[str, str]] = []
        for idx in range(total_radios):
            log_step(f"Selecionando parcela {idx + 1} de {total_radios}")
            radios.nth(idx).check()
            page.wait_for_timeout(10000)
            resumo_parcela.wait_for(state="visible", timeout=timeout_ms)
            page.wait_for_timeout(3000)
            parcela_texto = resumo_parcela.inner_text().strip()
            page.wait_for_timeout(500)
            taxa_texto = resumo_taxa.inner_text().strip()
            page.wait_for_timeout(500)
            entrada_texto = resumo_entrada.inner_text().strip()
            page.wait_for_timeout(500)
            financiado_texto = valor_financiado.inner_text().strip()
            page.wait_for_timeout(500)
            linha = (
                f"[PARCELA] {parcela_texto} | Taxa: {taxa_texto} | "
                f"Entrada: {entrada_texto} | Financiado: {financiado_texto}"
            )
            resultados.append(
                {
                    "parcela": parcela_texto,
                    "taxa": taxa_texto,
                    "entrada": entrada_texto,
                    "financiado": financiado_texto,
                }
            )
            print(linha)
        if resultados:
            log_step("Exibindo resultados em alerta")
            page.evaluate(
                "data => alert(data)",
                "\n".join(
                    (
                        f"[PARCELA] {item['parcela']} | Taxa: {item['taxa']} | "
                        f"Entrada: {item['entrada']} | Financiado: {item['financiado']}"
                    )
                    for item in resultados
                ),
            )
        page.wait_for_timeout(10000)
        return resultados
