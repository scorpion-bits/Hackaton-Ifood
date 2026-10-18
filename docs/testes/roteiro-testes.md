# Roteiro de testes — Thales (o agente do Thales guia, passo a passo)

> Agente do Thales: guie um passo por vez, espere o Thales dizer o que viu, e registre todo problema em
> `docs/testes/bugs.md`. **Não edite código.** Antes, `git pull` do `ccr-4c429dbb-lp7btg`. Commits com
> `--author="Thales Miguel Hajes <email>"` + `Responsável: Thales`.

## 0. Preparação (PC do Thales: Windows, sem Docker, Python 3.14, Node 24)
1. `git pull` no branch de integração.
2. `iniciar.bat` (ou `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1`). Anotar qualquer erro de instalação.
3. `iniciar.bat --testes` (ou `-Testes`). Anotar quantos testes passam/falham.
4. Abrir `http://localhost:8000`. No celular na mesma rede: o endereço com `ip_local` de `/api/saude`.

## 1. Modo demonstração (sem internet de MCP) — o plano B da demo
Seguir `docs/roteiro-demo.md` em viewport de celular (DevTools 390×780) + 1 celular de verdade:
1. Home → criar sala → QR/link aparecem.
2. 3 convidados entram (abas anônimas/celular) e escrevem as frases do roteiro.
3. Rodar Match → disputa → deck → "É um Match!" → escolher.
4. Pagamento separado: Pix (QR aparece), cartão simulado, dinheiro → organizador marca "recebi".
5. Enviar pedidos → cartões de pedido com status → rastro das tools.
6. "Ajustar com o IBits" (quando sair): "troca o sorvete do Milan por açaí" → novo resultado.
7. "Recarregar demo" e repetir uma vez.

Checar em cada tela: selo DEMONSTRAÇÃO, nenhum número estranho (R$ 0,00, NaN, "undefined"), textos cortados,
botão que não responde, erro no console (F12).

## 2. Frases livres (pegar a IA de surpresa)
Testar 5 frases fora do roteiro (ex.: "coxinha", "nada com glúten até R$ 30", "qualquer coisa", texto vazio,
emoji). Anotar o que o IBits respondeu.

## 3. MCP real (só no PC com `.env`, com quem tiver as credenciais)
1. `IFOOD_MCP_MODO=real` no `.env` → reiniciar → login OAuth com conta de teste (OTP no portal).
2. Repetir o passo 1 até o carrinho: lojas reais aparecem? taxa de entrega aparece?
3. **Nunca pagar Pix.** Envio real só se o Milan confirmar `IFOOD_MCP_PERMITIR_ENVIO=true`.
4. Toda estranheza do MCP (erro, campo faltando, demora) → também em `docs/feedback-mcp.md` (entregável 6).

## 4. Ensaio
Cronometrar a demo de 2 min do `docs/roteiro-demo.md` 3 vezes; anotar onde travou.
