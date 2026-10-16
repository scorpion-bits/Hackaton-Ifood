"""Teste rápido das credenciais reais: `python -m app.ifood.testar_real` (dentro de backend/).

Mostra se o token sai e o que cada endpoint de leitura devolve. Não altera nada no iFood.
"""

from .. import config
from .real import ENDPOINTS, ClienteReal


def main() -> None:
    cli = ClienteReal(config.carregar())
    print("Base:", cli.cfg.ifood_base_url)
    try:
        cli._autenticar()
        print("[ok] token obtido em", ENDPOINTS["token"])
    except Exception as e:  # noqa: BLE001 - diagnóstico para humanos
        print("[falhou] token:", e)
        return
    try:
        lojas = cli.listar_lojas()
        print(f"[ok] {len(lojas)} loja(s):", lojas[:3])
    except Exception as e:  # noqa: BLE001
        print("[falhou] lojas:", e)
        return
    if lojas:
        try:
            itens = cli.listar_itens(lojas[0]["id"])
            print(f"[ok] {len(itens)} item(ns) no cardápio da primeira loja:", itens[:3])
        except Exception as e:  # noqa: BLE001
            print("[falhou] cardápio:", e)


if __name__ == "__main__":
    main()
