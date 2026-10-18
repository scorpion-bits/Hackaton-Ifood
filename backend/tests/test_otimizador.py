"""Otimizador do Match: restrições duras, justiça, perfil, limite de lojas e perecível."""

import json

from app.match.modelos import Candidato, Combinacao, Pesos, para_dict
from app.match.otimizador import otimizar, pesos_por_perfil


def cand(pid, loja, item, preco, nota, eta=30, vertical="RESTAURANT", perecivel=False, viola=None):
    return Candidato(
        participante_id=pid, loja_id=loja, loja_nome=f"Loja {loja}", item_id=item, item_nome=item,
        preco=preco, eta_min=eta, vertical=vertical, perecivel=perecivel, nota=nota,
        motivo="teste", viola=viola or [],
    )


def item_de(comb: Combinacao, pid: str) -> str:
    return comb.escolhas[pid].item_id


def test_restricao_dura_elimina_candidato():
    candidatos = {
        "ana": [
            cand("ana", "A", "x-bacon", 30, 0.95, viola=["vegetariano"]),
            cand("ana", "A", "salada", 25, 0.6),
        ],
        "bia": [
            cand("bia", "A", "combo-caro", 80, 0.99),
            cand("bia", "A", "combo", 35, 0.7),
        ],
    }
    combos = otimizar(candidatos, Pesos(), orcamentos={"ana": None, "bia": 40})
    assert combos
    for comb in combos:
        assert item_de(comb, "ana") == "salada"
        assert item_de(comb, "bia") == "combo"


def test_pessoa_sem_opcao_valida_vira_aviso_sem_quebrar():
    candidatos = {
        "ana": [cand("ana", "A", "salada", 25, 0.8)],
        "caio": [cand("caio", "A", "x-bacon", 30, 0.9, viola=["sem_gluten"])],
    }
    combos = otimizar(candidatos, Pesos())
    assert len(combos) == 1
    assert "caio" not in combos[0].escolhas
    assert combos[0].componentes["pessoas_sem_opcao"] == 1
    assert "sem opção válida para caio" in combos[0].explicacao
    assert otimizar({"caio": candidatos["caio"]}, Pesos()) == []


def test_justica_nunca_escolhe_quem_fica_com_nota_baixa_sem_necessidade():
    # Mesma loja e mesmo preço: a melhor combinação dá a cada um a sua melhor opção.
    candidatos = {
        "ana": [cand("ana", "A", "a-otimo", 20, 1.0), cand("ana", "A", "a-ok", 20, 0.6)],
        "bia": [cand("bia", "A", "b-ruim", 20, 0.2), cand("bia", "A", "b-ok", 20, 0.5)],
    }
    sem_justica = otimizar(candidatos, Pesos(alfa_justica=0.0), top=1)[0]
    com_justica = otimizar(candidatos, Pesos(alfa_justica=0.5), top=1)[0]
    assert sem_justica.componentes["media_nota"] == 0.75
    assert com_justica.componentes["termo_justica"] == 0.25
    assert com_justica.componentes["min_nota"] >= 0.5
    assert item_de(com_justica, "bia") == "b-ok"


def test_justica_muda_o_vencedor():
    # A: Ana 1,0 + Bia 0,2 → média 0,60, mín 0,2. B: Ana 0,7 + Bia 0,45 → média 0,575, mín 0,45.
    candidatos = {
        "ana": [cand("ana", "A", "a-otimo", 20, 1.0), cand("ana", "B", "a-bom", 20, 0.7)],
        "bia": [cand("bia", "A", "b-ruim", 20, 0.2), cand("bia", "B", "b-ok", 20, 0.45)],
    }
    neutros = dict(beta_custo=0.0, gama_atraso=0.0, delta_lojas=0.0, epsilon_perecivel=0.0)
    sem = otimizar(candidatos, Pesos(alfa_justica=0.0, **neutros), max_lojas=1, top=1)[0]
    com = otimizar(candidatos, Pesos(alfa_justica=0.5, **neutros), max_lojas=1, top=1)[0]
    assert sem.lojas == ["A"] and sem.componentes["min_nota"] == 0.2
    assert com.lojas == ["B"] and com.componentes["min_nota"] == 0.45
    assert com.componentes["media_nota"] < sem.componentes["media_nota"]


def test_perfil_barato_muda_o_vencedor():
    candidatos = {
        "ana": [cand("ana", "A", "premium", 60, 0.95), cand("ana", "B", "simples", 25, 0.75)],
        "bia": [cand("bia", "A", "premium", 60, 0.95), cand("bia", "B", "simples", 25, 0.75)],
    }
    equilibrado = otimizar(candidatos, pesos_por_perfil(["equilibrado"]), max_lojas=1, top=1)[0]
    barato = otimizar(candidatos, pesos_por_perfil(["barato", "barato"]), max_lojas=1, top=1)[0]
    assert equilibrado.lojas == ["A"]
    assert barato.lojas == ["B"]
    assert barato.componentes["custo_total"] < equilibrado.componentes["custo_total"]


def test_pesos_por_perfil():
    assert pesos_por_perfil([]) == Pesos()
    assert pesos_por_perfil(["inexistente"]) == Pesos()
    barato = pesos_por_perfil(["barato"])
    rapido = pesos_por_perfil(["rapido"])
    qualidade = pesos_por_perfil(["qualidade"])
    assert barato.beta_custo > Pesos().beta_custo
    assert rapido.gama_atraso > Pesos().gama_atraso
    assert qualidade.beta_custo < Pesos().beta_custo and qualidade.alfa_justica > Pesos().alfa_justica
    misto = pesos_por_perfil(["barato", "barato", "rapido"])
    assert barato.beta_custo > misto.beta_custo > rapido.beta_custo


def test_max_lojas_respeitado():
    candidatos = {
        "ana": [cand("ana", "A", "a1", 20, 0.9), cand("ana", "D", "d1", 20, 0.5)],
        "bia": [cand("bia", "B", "b1", 20, 0.9), cand("bia", "D", "d2", 20, 0.5)],
        "caio": [cand("caio", "C", "c1", 20, 0.9), cand("caio", "D", "d3", 20, 0.5)],
    }
    for limite in (1, 2, 3):
        combos = otimizar(candidatos, Pesos(), max_lojas=limite, top=10)
        assert combos
        assert all(len(c.lojas) <= limite for c in combos)
        assert all(len(set(c.lojas)) == len(c.lojas) for c in combos)
    assert otimizar(candidatos, Pesos(), max_lojas=1, top=10)[0].lojas == ["D"]


def test_taxas_entram_no_custo_e_top_distintas_ordenadas():
    candidatos = {
        "ana": [cand("ana", "A", "a1", 20, 0.8), cand("ana", "B", "b1", 20, 0.8), cand("ana", "A", "a2", 22, 0.7)],
    }
    sem_taxa = otimizar(candidatos, Pesos(), top=3)
    assert all(not c.taxa_conhecida for c in sem_taxa)
    assert "sem taxa" in sem_taxa[0].explicacao

    com_taxa = otimizar(candidatos, Pesos(), taxas={"A": 9.0, "B": 2.0}, top=3)
    assert all(c.taxa_conhecida for c in com_taxa)
    assert com_taxa[0].lojas == ["B"]  # mesma nota, taxa menor
    assert com_taxa[0].componentes["custo_total"] == 22.0
    assert [c.score for c in com_taxa] == sorted((c.score for c in com_taxa), reverse=True)
    chaves = {tuple(sorted((p, e.item_id) for p, e in c.escolhas.items())) for c in com_taxa}
    assert len(chaves) == len(com_taxa)


def test_penal_perecivel_so_com_eta_muito_diferente():
    candidatos = {
        "ana": [cand("ana", "SUSHI", "temaki", 40, 0.9, eta=55)],
        "bia": [cand("bia", "SORVETE", "sorvete", 15, 0.9, eta=20, perecivel=True)],
    }
    comb = otimizar(candidatos, Pesos())[0]
    assert comb.componentes["penal_perecivel"] == 1.0
    assert comb.componentes["termo_perecivel"] < 0
    assert "perecível" in comb.explicacao

    candidatos["bia"][0].eta_min = 45
    assert otimizar(candidatos, Pesos())[0].componentes["penal_perecivel"] == 0.0

    candidatos["bia"][0].eta_min = 20
    candidatos["bia"][0].vertical = "GROCERIES"
    assert otimizar(candidatos, Pesos())[0].componentes["penal_perecivel"] == 0.0


def test_poda_com_muitas_pessoas_nao_explode():
    candidatos = {
        f"p{i}": [cand(f"p{i}", "A", f"i{i}-{j}", 10 + j, 1 - j * 0.05) for j in range(10)]
        for i in range(6)
    }
    combos = otimizar(candidatos, Pesos(), top=3)
    assert len(combos) == 3
    assert all(c.escolhas[f"p{i}"].item_id == f"i{i}-0" for c in combos[:1] for i in range(6))


def test_explicacao_e_para_dict_serializavel():
    candidatos = {"ana": [cand("ana", "A", "a1", 82.4, 0.75)]}
    comb = otimizar(candidatos, Pesos())[0]
    assert comb.explicacao.startswith("1 loja · todos bem atendidos · R$ 82,40 sem taxa")
    dados = para_dict(comb)
    json.dumps(dados)
    assert dados["escolhas"]["ana"]["preco"] == 82.4


# ---------- C4b: vários itens por pessoa (slots) ----------
def test_orcamento_vale_para_a_soma_dos_slots_da_pessoa():
    candidatos = {
        "zen": [cand("zen", "B", "smash-caro", 30, 0.9), cand("zen", "B", "smash", 22, 0.8)],
        "zen#2": [cand("zen#2", "B", "shake", 19, 0.9)],
    }
    pessoa_de = {"zen": "zen", "zen#2": "zen"}
    melhor = otimizar(candidatos, Pesos(), orcamentos={"zen": 42}, pessoa_de=pessoa_de, top=1)[0]
    assert set(melhor.escolhas) == {"zen", "zen#2"}
    assert item_de(melhor, "zen") == "smash"  # 30 + 19 passaria de 42; 22 + 19 cabe
    assert sum(c.preco for c in melhor.escolhas.values()) <= 42
    assert melhor.componentes["slots_fora"] == 0


def test_slot_extra_fica_de_fora_quando_nao_cabe_no_orcamento():
    candidatos = {
        "zen": [cand("zen", "B", "smash", 30, 0.9)],
        "zen#2": [cand("zen#2", "S", "sorvete", 19, 0.9)],
    }
    combos = otimizar(candidatos, Pesos(), orcamentos={"zen": 40}, pessoa_de={"zen#2": "zen"})
    assert combos
    melhor = combos[0]
    assert set(melhor.escolhas) == {"zen"}  # o principal fica; o extra sai
    assert melhor.componentes["slots_fora"] == 1
    assert "1 item ficou de fora" in melhor.explicacao
    assert all(sum(c.preco for c in c_.escolhas.values()) <= 40 for c_ in combos)


def test_media_e_minimo_sao_por_pessoa():
    candidatos = {
        "ana": [cand("ana", "A", "a1", 10, 1.0)],
        "ana#2": [cand("ana#2", "A", "a2", 10, 0.2)],
        "bia": [cand("bia", "A", "b1", 10, 0.6)],
    }
    comb = otimizar(candidatos, Pesos(), pessoa_de={"ana#2": "ana"}, top=1)[0]
    assert comb.componentes["media_nota"] == 0.6  # ana = (1,0 + 0,2)/2 = 0,6; bia = 0,6
    assert comb.componentes["min_nota"] == 0.6
    assert set(comb.escolhas) == {"ana", "ana#2", "bia"}


def test_limite_de_lojas_tira_o_extra_e_mantem_o_principal():
    # Milan: japonês (J) + sorvete (S); Zenon: hambúrguer (B) + sorvete (S). Com 2 lojas não cabe tudo.
    candidatos = {
        "milan": [cand("milan", "J", "temaki", 33, 0.9, eta=45)],
        "milan#2": [cand("milan#2", "S", "sorvete", 19, 0.9, eta=25, perecivel=True)],
        "zenon": [cand("zenon", "B", "smash", 30, 0.9, eta=35)],
        "zenon#2": [cand("zenon#2", "S", "sundae", 19, 0.9, eta=25, perecivel=True)],
    }
    pessoa_de = {"milan#2": "milan", "zenon#2": "zenon"}
    duas = otimizar(candidatos, Pesos(), max_lojas=2, pessoa_de=pessoa_de)
    assert duas and all(len(c.lojas) <= 2 for c in duas)
    assert set(duas[0].lojas) == {"J", "B"}
    assert set(duas[0].escolhas) == {"milan", "zenon"}
    tres = otimizar(candidatos, Pesos(), max_lojas=3, pessoa_de=pessoa_de, top=1)[0]
    assert set(tres.escolhas) == set(candidatos)


def test_pessoa_sem_opcao_no_conjunto_de_lojas_fica_de_fora_sem_zerar_o_resultado():
    candidatos = {
        "ana": [cand("ana", "A", "a1", 10, 0.9)],
        "bia": [cand("bia", "B", "b1", 10, 0.9)],
        "caio": [cand("caio", "C", "c1", 10, 0.9)],
    }
    combos = otimizar(candidatos, Pesos(), max_lojas=2, top=5)
    assert combos and all(len(c.lojas) <= 2 for c in combos)
    assert len(combos[0].escolhas) == 2
    assert combos[0].componentes["pessoas_sem_opcao"] == 1


def test_explicacao_em_linguagem_simples_sem_nota():
    """Sem jargão: nada de "nota ≥ 0,7"; diz se todos ficaram bem atendidos ou se alguém ficou longe do pedido."""
    from app.match import leilao
    from app.match.otimizador import BEM_ATENDIDO

    assert leilao.FELIZ == BEM_ATENDIDO  # "bem atendido" é o mesmo limiar do fechamento do leilão
    bem = otimizar({"ana": [cand("ana", "A", "a1", 20, 0.8)], "bia": [cand("bia", "A", "b1", 20, 0.6)]}, Pesos())[0]
    longe = otimizar({"ana": [cand("ana", "A", "a1", 20, 0.8)], "bia": [cand("bia", "A", "b1", 20, 0.3)]},
                     Pesos())[0]
    sem = otimizar({"ana": [cand("ana", "A", "a1", 20, 0.8)],
                    "caio": [cand("caio", "A", "x", 30, 0.9, viola=["sem_gluten"])]}, Pesos())[0]
    assert "todos bem atendidos" in bem.explicacao
    assert "alguém ficou longe do que pediu" in longe.explicacao
    assert "quem entrou está bem atendido" in sem.explicacao and "sem opção válida para caio" in sem.explicacao
    for comb in (bem, longe, sem):
        assert "nota" not in comb.explicacao and "≥" not in comb.explicacao


def test_slot_extra_entra_quando_ha_folga_no_limite_de_lojas():
    """Regressão (A5, etapa 05): o açaí/sorvete era cortado porque δ + custo + perecível > penalidade do slot,
    mesmo com folga no limite de 3 lojas. Atender o pedido vale mais que economizar uma loja."""
    candidatos = {
        "milan": [cand("milan", "japones", "guioza", 22.9, 0.73, eta=45)],
        "milan#2": [cand("milan#2", "acai", "acai300", 16.9, 0.73, eta=20, perecivel=True)],
        "zenon": [cand("zenon", "burger", "smash", 29.9, 0.9, eta=35)],
    }
    pesos = Pesos(alfa_justica=0.5, beta_custo=0.5, gama_atraso=0.2, delta_lojas=0.1667, epsilon_perecivel=0.3)
    combos = otimizar(candidatos, pesos, max_lojas=3, orcamentos={"milan": 45.0, "zenon": 50.0},
                      pessoa_de={"milan": "milan", "milan#2": "milan", "zenon": "zenon"})
    melhor = combos[0]
    assert set(melhor.escolhas) == {"milan", "milan#2", "zenon"}
    assert set(melhor.lojas) == {"japones", "acai", "burger"}
    assert melhor.componentes["slots_fora"] == 0
    # com o limite de 2 lojas o extra sai (aí sim por causa do limite)
    dois = otimizar(candidatos, pesos, max_lojas=2, orcamentos={"milan": 45.0, "zenon": 50.0},
                    pessoa_de={"milan": "milan", "milan#2": "milan", "zenon": "zenon"})
    assert "milan#2" not in dois[0].escolhas


# ---------- combos (Trilha A′, etapa 05: A′F3) ----------
def test_combo_cobre_os_itens_da_pessoa_e_nunca_vem_junto_com_os_avulsos():
    import dataclasses
    combo = dataclasses.replace(cand("ana", "B", "combo", 42.9, 0.9), cobre=["ana#2", "ana#3"])
    candidatos = {
        "ana": [cand("ana", "B", "smash", 29.9, 0.9), combo],
        "ana#2": [cand("ana#2", "B", "batata", 16.9, 0.9)],
        "ana#3": [cand("ana#3", "C", "suco", 12.9, 0.6)],
    }
    pessoa_de = {"ana": "ana", "ana#2": "ana", "ana#3": "ana"}
    combos = otimizar(candidatos, Pesos(), max_lojas=3, top=3, pessoa_de=pessoa_de)
    melhor = combos[0]
    assert [c.item_id for c in melhor.escolhas.values()] == ["combo"]
    assert melhor.cobertos == {"ana#2": "ana", "ana#3": "ana"}
    assert melhor.componentes["slots_fora"] == 0 and melhor.componentes["custo_total"] == 42.9
    for c in combos:  # nenhuma combinação leva o combo e um avulso do que ele já cobre
        ids = {x.item_id for x in c.escolhas.values()}
        assert not ("combo" in ids and ids & {"batata", "suco"})
