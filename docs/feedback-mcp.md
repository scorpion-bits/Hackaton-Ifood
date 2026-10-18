# Feedback sobre o MCP do iFood (entregável 06)

Anotar **na hora** cada dor real: data/hora, o que tentamos, o que aconteceu, impacto, sugestão.

| Quando | Situação | O que aconteceu | Impacto | Sugestão |
|---|---|---|---|---|
| 17/10 manhã | `POST /marketplace` sem token | 401 diz "Your client should automatically re-register and obtain new tokens", mas o `id.ifood.com.br` não publica `registration_endpoint` (sem registro dinâmico de cliente) | Clientes MCP que seguem a mensagem tentam DCR e falham; confunde quem está começando | Ajustar a mensagem ("use o client_id/secret do MCP Portal") ou oferecer DCR |
| 17/10 manhã | Documentação (llms-full.txt, seção de endpoints e quickstart) | Cita `auth.ifood.com`, `dev-auth.ifood.com`, `api-mcp.ifood.com/v3/*`, `mcp.ifood.dev` e `npm install @ifood/mcp-sdk` — nenhum resolve / o pacote não existe no npm. O real é `id.ifood.com.br` + `consumer-mcp.ifood.com.br/marketplace` | Quem segue a doc perde tempo com URLs mortas | Atualizar os exemplos com os endpoints reais |
| 17/10 manhã | Doc recomenda "Pending Action" (QR/device code) para agentes | `/device` e o grant `device_code` não aparecem em `id.ifood.com.br/.well-known/openid-configuration` | Não dá para saber se o fluxo recomendado para agentes existe | Publicar o grant nos metadados ou marcar como "em breve" |
| 17/10 manhã | Doc da Web Login | Diz `code_challenge_method: pkce` e scopes "comma-separated"; os metadados reais pedem `S256` e o padrão OAuth separa scopes por espaço | Implementação literal da doc falha | Corrigir para `S256` e espaço |
| 17/10 manhã | Cadastro do agente | O vídeo dizia "uma Redirect URL por agente", mas o formulário já aceita várias (ok). Escopos continuam **imutáveis** depois de ativo | Errar o escopo obriga a recriar o agente e a passar de novo pela homologação | Permitir editar escopos com nova revisão; atualizar o vídeo |
| 17/10 noite | Doc de contas de teste | O link "criação de conta" aponta para `mcp-developer.ifood-sandbox.com.br/pt-BR/sign-up`, domínio que não respondeu no nosso teste; o portal real é `mcp-developer.ifood.com.br` (botão "Faça login") | Equipe aprovada não achava onde entrar no portal | Corrigir o link e pôr um botão "Meus agentes" visível na doc |
| 17/10 ~22h | `list_tools` no MCP real (conta de teste) | O servidor expõe **23 tools**; a doc lista 24 — `listItemTaxonomy` não existe | Quem planeja pela doc conta com uma tool que não há | Atualizar a lista da doc ou publicar a tool |
| 17/10 ~22h | `searchOffers` e `getRecommendations` com `latitude`/`longitude` soltos (como os exemplos da doc) | Erro: "`userLocation` is required and must be a JSON object with numeric `latitude` and `longitude`" — 0 resultados | Nenhuma busca funcionou no 1º teste; o agente não encontra lojas | Citar `userLocation` (objeto) na doc e nos exemplos; a mensagem de erro é boa e deveria ser o padrão das outras tools |
| 17/10 ~22h | `listAddresses` no MCP real | Formato diferente do exemplo da doc (nosso leitor não achou a lista e a sala dizia "nenhum endereço salvo") | Integração quebra em silêncio | Publicar o `outputSchema` das tools (o `list_tools` já tem o campo) e manter a doc igual ao real |

