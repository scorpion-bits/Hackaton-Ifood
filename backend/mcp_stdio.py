"""Sobe o servidor MCP sozinho.

    python mcp_stdio.py           # stdio (Claude Desktop, MCP Inspector)
    python mcp_stdio.py --http    # Streamable HTTP em http://127.0.0.1:8001/mcp
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import db  # noqa: E402
from app.mcp_server import criar_servidor  # noqa: E402

if __name__ == "__main__":
    db.inicializar()
    servidor = criar_servidor()
    if "--http" in sys.argv:
        servidor.run("streamable-http", host="127.0.0.1", port=8001)
    else:
        servidor.run()
