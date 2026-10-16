# MCP — guia rápido da equipe

MCP (Model Context Protocol) é o padrão para expor **ferramentas** a agentes de IA. Um servidor MCP declara
ferramentas (nome, descrição, schema JSON dos argumentos); qualquer cliente MCP (nosso agente, Claude Desktop,
MCP Inspector, outros agentes) lista e chama essas ferramentas.

## Nosso servidor

- Código: `backend/app/mcp_server.py`. SDK oficial Python **`mcp` 2.x** (`from mcp.server.mcpserver import MCPServer`).
  > Atenção: tutoriais antigos usam `from mcp.server.fastmcp import FastMCP` (v1). Na 2.x, `FastMCP` virou
  > `MCPServer` e os campos dos tipos viraram snake_case (`input_schema`, `is_error`, `structured_content`).
  > Guia de migração: https://py.sdk.modelcontextprotocol.io/v2/migration/
- Ferramentas (prefixo = lado):

| Ferramenta | Lado | Tipo |
|---|---|---|
| `vendedor_listar_cardapio(loja_id)` | vendedor | leitura |
| `vendedor_propor_disponibilidade(loja_id, item_id, disponivel, motivo)` | vendedor | **proposta** |
| `vendedor_propor_promocao(loja_id, item_id, desconto_pct, motivo)` | vendedor | **proposta** (1–70%) |
| `comprador_listar_lojas()` | comprador | leitura |
| `comprador_buscar_itens(termo, preco_max?)` | comprador | leitura |
| `comprador_propor_pedido(loja_id, itens[], motivo, orcamento_max?)` | comprador | **proposta** (checa estoque e orçamento) |
| `consultar_acao(acao_id)` | ambos | leitura |

- **Proposta** = cria uma ação `pendente` na tabela `acoes`. Só a pessoa executa, pelo botão Confirmar
  (`POST /api/acoes/{id}/confirmar`). Nenhuma ferramenta MCP confirma ação. É de propósito: é parte do pitch.
- Erros de negócio levantam `ToolError` → o modelo recebe a mensagem (ex.: "passa do orçamento") e explica.

## Como adicionar uma ferramenta

```python
@mcp.tool(annotations=LEITURA)          # ou PROPOSTA se mexe com dinheiro/preço/pedido
@_erros_legiveis
def comprador_comparar_lojas(termo: str) -> dict:
    """Descrição curta: o modelo decide usar a ferramenta por ela."""
    ...
```
O schema dos argumentos sai das anotações de tipo. Ação sensível → chame `acoes.propor(...)` em vez de executar.
Novo tipo de ação → registre em `EXECUTORES` (`backend/app/acoes.py`).

## Três jeitos de usar o mesmo servidor

1. **Pelo nosso app** (padrão): o agente usa um cliente MCP **em processo** (`Client(criar_servidor())`), sem
   subprocesso. Funciona igual no Windows.
2. **stdio** (Claude Desktop / Inspector): `python mcp_stdio.py` dentro de `backend/`.
3. **HTTP** (outro agente na rede, ex.: agente comprador falando com agente vendedor):
   `python mcp_stdio.py --http` → `http://127.0.0.1:8001/mcp`.

## Testar com o MCP Inspector

```bash
cd backend
npx @modelcontextprotocol/inspector .venv/bin/python mcp_stdio.py        # Linux
npx @modelcontextprotocol/inspector .venv\Scripts\python.exe mcp_stdio.py # Windows
```
Abre uma página local: "Connect" → "Tools" → escolha a ferramenta → preencha → "Run".

## Testar no Claude Desktop

Em *Settings → Developer → Edit Config* (`claude_desktop_config.json`), com caminhos **absolutos**:

```json
{
  "mcpServers": {
    "comercio-ifood": {
      "command": "C:\\caminho\\Hackaton-Ifood\\backend\\.venv\\Scripts\\python.exe",
      "args": ["C:\\caminho\\Hackaton-Ifood\\backend\\mcp_stdio.py"]
    }
  }
}
```
Reinicie o Claude Desktop; as ferramentas aparecem no ícone de ferramentas do chat.

## Testes automatizados

`backend/tests/test_mcp_e_acoes.py` chama as ferramentas pelo protocolo MCP (cliente em processo).
Rodamos também um teste manual por stdio com handshake `legacy` (o que clientes antigos usam) — funcionou.
