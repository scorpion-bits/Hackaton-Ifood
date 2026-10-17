"""Cliente das APIs do iFood com dois modos e a mesma interface: "mock" (demonstração) e "real"."""

from .. import config
from .base import ClienteIFood, ErroIFood, NaoSuportado


def obter_cliente() -> ClienteIFood:
    cfg = config.carregar()
    if cfg.ifood_modo == "real":
        from .real import ClienteReal

        return ClienteReal(cfg)
    from .mock import ClienteMock

    return ClienteMock()


__all__ = ["ClienteIFood", "ErroIFood", "NaoSuportado", "obter_cliente"]
