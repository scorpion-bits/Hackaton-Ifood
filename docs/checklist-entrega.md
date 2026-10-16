# Checklist de entrega

## Antes do congelamento (16h00 do dia 18, ajustar ao prazo real)
- [ ] `./iniciar.sh --testes` (ou `iniciar.ps1 -Testes`) passa
- [ ] App sobe do zero no **computador da apresentação** (Windows, sem Docker) com `iniciar.bat`
- [ ] Testado com a **internet do evento** e com o provedor de IA escolhido
- [ ] Modo `LLM_PROVIDER=mock` funciona como plano B (sem internet)
- [ ] "Recarregar demo" deixa tudo limpo em 1 clique
- [ ] Nenhum botão quebrado na tela da demo
- [ ] Todo dado simulado com selo **DEMONSTRAÇÃO**; todo número do pitch com fonte
- [ ] `.env` fora do git (`git status` não mostra `.env`); nenhuma chave em código ou slide

## Pitch
- [ ] Slides finais em `pitch/index.html`
- [ ] `cd pitch && npm run pdf` → `pitch/pitch.pdf` **commitado**
- [ ] Vídeo do plano B gravado (tela + voz) e acessível offline no PC da apresentação
- [ ] Ensaio cronometrado ≤ tempo oficial
- [ ] Momento "uau" da demo ensaiado 3×

## Repositório
- [ ] README com passo a passo para a banca rodar
- [ ] `docs/decisions.md` e `CLAUDE.md` atualizados
- [ ] Último commit enviado (`git push`) antes do prazo
- [ ] 👥 Se a banca precisar de chave: **perguntar antes** de entregar qualquer segredo

## No palco
- [ ] Notebook na tomada, notificações desligadas, zoom do navegador ajustado
- [ ] App aberto em `http://localhost:8000` com demo recarregada
- [ ] Vídeo do plano B aberto em outra aba
