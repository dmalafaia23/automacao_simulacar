from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Thread
from typing import Callable, Dict, List, Tuple

from .banks import run_c6bank, run_itau
from .external_api import (
    create_processing,
    insert_processing_offers,
    normalize_offers,
    update_processing,
    update_processing_bank,
)
from .schemas import SimulationCreateResponse, SimulationRequest


BankRunner = Callable[[SimulationRequest], List[Dict[str, str]]]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BankPlan:
    internal_name: str
    display_name: str
    runner: BankRunner


class SimulationOrchestrator:
    def create_job(self, payload: SimulationRequest) -> SimulationCreateResponse:
        plans = self._bank_plans(payload)
        if not plans:
            raise ValueError("No enabled banks were provided for processing.")

        created = create_processing(
            dados_requisicao=payload.model_dump(mode="json"),
            bancos=[plan.display_name for plan in plans],
        )
        created_data = created["data"]
        worker = Thread(target=self._run_job, args=(created_data, payload, plans), daemon=True)
        worker.start()
        return SimulationCreateResponse(
            id=created_data["id"],
            status=created_data["status"],
            quantidade_bancos=created_data["quantidade_bancos"],
            bancos=created_data.get("bancos", []),
        )

    def _bank_plans(self, payload: SimulationRequest) -> List[BankPlan]:
        plans: List[BankPlan] = []
        if payload.itau and payload.itau.enabled:
            plans.append(BankPlan("itau", "Itaú", run_itau))
        if payload.c6bank and payload.c6bank.enabled:
            plans.append(BankPlan("c6bank", "C6 Bank", run_c6bank))
        return plans

    def _run_job(self, created_data: Dict[str, object], payload: SimulationRequest, plans: List[BankPlan]) -> None:
        processamento_id = str(created_data["id"])
        bancos_registrados = created_data.get("bancos", [])
        if not isinstance(bancos_registrados, list) or not plans:
            update_processing(
                processamento_id,
                status="erro",
                quantidade_bancos_concluidos=0,
                quantidade_bancos_com_erro=len(plans),
                finalizado_em=utcnow_iso(),
            )
            return

        bancos_por_nome = {
            str(item["nome_banco"]): item
            for item in bancos_registrados
            if isinstance(item, dict) and "nome_banco" in item
        }
        update_processing(processamento_id, status="processando")

        concluidos = 0
        com_erro = 0
        with ThreadPoolExecutor(max_workers=len(plans)) as executor:
            future_map: Dict[object, Tuple[BankPlan, Dict[str, object]]] = {}
            for plan in plans:
                banco_registrado = bancos_por_nome.get(plan.display_name)
                if banco_registrado is None:
                    com_erro += 1
                    continue

                input_data = self._bank_input_data(payload, plan.internal_name)
                update_processing_bank(
                    str(banco_registrado["id"]),
                    status="processando",
                    dados_entrada=input_data,
                    iniciado_em=utcnow_iso(),
                )
                future = executor.submit(plan.runner, payload)
                future_map[future] = (plan, banco_registrado)

            for future in as_completed(future_map):
                plan, banco_registrado = future_map[future]
                banco_id = str(banco_registrado["id"])
                try:
                    result = future.result()
                    update_processing_bank(
                        banco_id,
                        status="concluido",
                        dados_retorno=result,
                        finalizado_em=utcnow_iso(),
                    )
                    ofertas = normalize_offers(plan.display_name, result)
                    if ofertas:
                        insert_processing_offers(banco_id, ofertas)
                    concluidos += 1
                except Exception as exc:
                    com_erro += 1
                    update_processing_bank(
                        banco_id,
                        status="erro",
                        mensagem_erro=str(exc),
                        finalizado_em=utcnow_iso(),
                    )

        if concluidos > 0 and com_erro > 0:
            final_status = "concluido_com_erros"
        elif concluidos > 0:
            final_status = "concluido"
        else:
            final_status = "erro"

        update_processing(
            processamento_id,
            status=final_status,
            quantidade_bancos_concluidos=concluidos,
            quantidade_bancos_com_erro=com_erro,
            finalizado_em=utcnow_iso(),
        )

    def _bank_input_data(self, payload: SimulationRequest, internal_name: str) -> Dict[str, object]:
        if internal_name == "itau" and payload.itau:
            return payload.itau.model_dump(mode="json")
        if internal_name == "c6bank" and payload.c6bank:
            return payload.c6bank.model_dump(mode="json")
        return {}
