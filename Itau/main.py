import json
from pathlib import Path

from config_loader import load_config
from client_data_loader import load_client_data
from simulator import Simulator


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    print("[STEP] Carregando configuracao")
    config = load_config(base_dir / "config.json")
    print("[STEP] Carregando dados do cliente")
    client_data = load_client_data(base_dir / "client_data.json")
    print("[STEP] Iniciando simulacao")
    resultados = Simulator(config, client_data).run()
    banco_nome = "Itau"
    output_dir = base_dir / "resultados"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{banco_nome}_resultados.json"
    print(f"[STEP] Salvando resultados em {output_path}")
    output_payload = {"banco": banco_nome, "simulacoes": resultados}
    output_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
