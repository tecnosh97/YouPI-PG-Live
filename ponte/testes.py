"""Testes das regras da live. Rodam sozinhos, sem rede e sem Roblox.

    python ponte\\testes.py

(ou, mais facil, pelo TESTES-INTERNOS.bat, que roda esta suite junto com a do
enquadramento da camera.)

POR QUE ESTES TESTES EXISTEM

As regras de presente sao a parte do kit em que um erro nao levanta excecao
nenhuma: ele so' faz a rosa ficar do tamanho da galaxia. Ninguem percebe
olhando o codigo, e quem percebe e' o espectador que pagou 1000 moedas e viu o
mesmo efeito de quem pagou 1.

Cada teste aqui e' uma afirmacao sobre o PRODUTO, e nao sobre a implementacao:
"presente mais caro tem que crescer mais", "presente que nunca foi cadastrado
tem que funcionar mesmo assim", "curtida nao pode furar a fila".
"""

import json
import os
import sys
import unittest
import urllib.error

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "servidor"))

import conta     # noqa: E402
import nicks     # noqa: E402
import painel    # noqa: E402
import regras    # noqa: E402
import servidor  # noqa: E402

#[[ A ponte entra com "--simular" NO ARGV, e isso nao e' firula.
#
#   O ponte.py, no import, exige a biblioteca TikTokLive -- e se ela nao estiver
#   instalada, ele a INSTALA. Rodar a suite de testes numa maquina limpa
#   dispararia um download de varios minutos, e o que a pessoa veria e' o
#   TESTES-INTERNOS.bat "travado". Com a bandeira, o import pula essa exigencia:
#   nada aqui fala com o TikTok.
#
#   Tirado logo em seguida porque o unittest tambem le' o argv, e um
#   "--simular" sobrando ali vira "argumento desconhecido" na hora de rodar. ]]
sys.argv.append("--simular")
try:
    import ponte  # noqa: E402
finally:
    sys.argv.remove("--simular")


class ConfigDeMentira(painel.ConfigDoPainel):
    """A ConfigDoPainel sem rede: recebe o dicionario pronto."""

    def __init__(self, dados):
        super().__init__("", "")
        self._cfg = dados
        self._versao = 1


# ══════════════════════════════════════════════════════════════════
#  A ESCADA DOS PRESENTES
# ══════════════════════════════════════════════════════════════════

class TesteEscadaDosPresentes(unittest.TestCase):
    """Presente mais caro tem que fazer mais coisa. Sempre."""

    def test_faixas_de_preco_sobem_junto_com_o_valor(self):
        anterior = None
        for moedas in (1, 10, 30, 200, 1000):
            e = regras.efeito_do_presente("presente que ninguem cadastrou", moedas)
            if anterior is not None:
                self.assertGreaterEqual(
                    e["crescimento"], anterior["crescimento"],
                    f"o presente de {moedas} moedas cresce MENOS que o anterior")
                self.assertGreaterEqual(
                    e["prio"], anterior["prio"],
                    f"o presente de {moedas} moedas tem prioridade MENOR")
            anterior = e

    def test_presente_desconhecido_nunca_fica_sem_efeito(self):
        """A rede de seguranca por preco. E' o que faz o kit funcionar com um
        presente que o TikTok lancou ontem, sem cadastro nenhum."""
        e = regras.efeito_do_presente("Presente Inventado Ontem", 500)
        self.assertGreater(e["escala"], 1.0)
        self.assertGreater(e["crescimento"], 0)
        self.assertGreater(e["prio"], 0)

    def test_os_quatro_presentes_do_kit_tem_efeitos_distintos(self):
        vistos = {}
        for nome in ("rose", "doughnut", "sunglasses", "galaxy"):
            e = regras.efeito_do_presente(nome, 1)
            vistos[nome] = (e["escala"], e["crescimento"], e["danca"])
        self.assertEqual(len(set(vistos.values())), 4,
                         f"dois presentes com o MESMO efeito: {vistos}")

    def test_combo_nao_muda_a_faixa_do_presente(self):
        """Dez rosas de 1 moeda continuam sendo rosas.

        Tratar o total do combo como valor unitario transformaria dez rosinhas
        num presente de outra faixa -- e o espectador que gastou 10 moedas
        receberia o efeito de quem gastou 10 de uma vez so'.
        """
        uma = regras.efeito_do_presente("rose", 1)
        dez = regras.efeito_do_presente("rose", 1, total_combo=10)
        self.assertEqual(uma["escala"], dez["escala"])
        self.assertEqual(uma["crescimento"], dez["crescimento"])
        # So' a prioridade sobe: combo maior fura mais a fila.
        self.assertGreater(dez["prio"], uma["prio"])

    def test_nenhum_efeito_passa_dos_tetos(self):
        """Um painel editado na mao nao pode gerar um avatar que quebra a live."""
        louco = {"escala": 999, "crescimento": 999, "segura": 999, "cena": 999,
                 "chuva": 999, "furacao": 999, "prio": 999, "brilho": 99,
                 "colosso": 999, "danca_geral": 9999}
        e = regras.limitar(louco)
        self.assertLessEqual(e["escala"], regras.ESCALA_MAX)
        self.assertLessEqual(e["crescimento"], regras.CRESCIMENTO_MAX)
        self.assertLessEqual(e["segura"], regras.SEGURA_MAX)
        self.assertLessEqual(e["chuva"], regras.CHUVA_MAX)
        self.assertLessEqual(e["furacao"], regras.FURACAO_MAX)
        self.assertLessEqual(e["brilho"], regras.BRILHO_MAX)

    def test_efeito_torto_vira_efeito_completo(self):
        """O resto da ponte espera TODOS os campos. Um efeito vindo do painel
        com metade das chaves quebraria em outro lugar, longe daqui."""
        e = regras.limitar({"escala": 2})
        for campo in ("prio", "escala", "crescimento", "vida", "segura", "cena",
                      "furacao", "chuva", "cor", "brilho", "danca",
                      "danca_geral", "colosso"):
            self.assertIn(campo, e)

    def test_danca_desconhecida_vira_a_padrao(self):
        """O Roblox NAO reclama de uma animacao que nao existe: ela carrega, o
        Play() funciona, e o boneco fica parado em pe'. Barrar aqui e' o unico
        ponto do caminho em que da' pra perceber o erro."""
        self.assertEqual(regras.limitar({"danca": "nao_existe"})["danca"], "")
        self.assertEqual(regras.limitar({"danca": "galaxia"})["danca"], "galaxia")


# ══════════════════════════════════════════════════════════════════
#  O PAINEL MANDA NO JOGO
# ══════════════════════════════════════════════════════════════════

class TestePainelMandaNoJogo(unittest.TestCase):
    """O pedido central do produto: o que esta' no painel e' o que acontece."""

    def setUp(self):
        self.cfg = ConfigDeMentira({
            "presentes": {
                "rose": {"escala": 1.5, "crescimento": 0.25, "prio": 2,
                         "id": "5655", "grupo": "rosa"},
                "rosa": {"escala": 1.5, "crescimento": 0.25, "prio": 2,
                         "id": "5655", "grupo": "rosa"},
                "galaxy": {"escala": 3.2, "crescimento": 1.6, "prio": 6,
                           "id": "6064", "grupo": "galaxia"},
            },
            "faixas": [
                {"min": 1000, "efeito": {"escala": 3.0, "crescimento": 1.5, "prio": 6}},
                {"min": 1, "efeito": {"escala": 1.0, "crescimento": 0.1, "prio": 2}},
            ],
            "acoes": {},
            "geral": {"tamanho_max": 8.0, "crescimento_suave": 0.9},
        })

    def test_valor_do_painel_vence_a_tabela_de_fabrica(self):
        e = self.cfg.efeito_do_presente("rose", 1)
        self.assertEqual(e["escala"], 1.5)
        self.assertEqual(e["crescimento"], 0.25)

    def test_casa_por_id_quando_o_nome_chega_de_outra_regiao(self):
        """O nome do presente muda de pais pra pais; o ID nao.

        E' o caso concreto de uma live com audiencia de fora: o presente chega
        como "Rosa" pra uns e "Rose" pra outros, e um terceiro nome numa
        terceira regiao. Pelo ID, todos recebem o mesmo efeito.
        """
        e = self.cfg.efeito_do_presente("UmNomeQueNinguemCadastrou", 1,
                                        presente_id="5655")
        self.assertEqual(e["escala"], 1.5)
        self.assertEqual(e["crescimento"], 0.25)

    def test_id_vence_o_apelido(self):
        """Se os dois casarem em fichas diferentes, o ID manda -- ele e' o
        identificador confiavel."""
        e = self.cfg.efeito_do_presente("rose", 1, presente_id="6064")
        self.assertEqual(e["escala"], 3.2, "o ID deveria ter vencido o nome")

    def test_id_em_formatos_diferentes_casa_igual(self):
        """O mesmo ID chega como inteiro, como float e como texto no caminho."""
        for forma in ("5655", 5655, 5655.0):
            e = self.cfg.efeito_do_presente("qualquer", 1, presente_id=forma)
            self.assertEqual(e["escala"], 1.5, f"nao casou com o ID {forma!r}")

    def test_sem_cadastro_cai_na_faixa_do_painel(self):
        e = self.cfg.efeito_do_presente("Presente Novo", 2000)
        self.assertEqual(e["escala"], 3.0)
        self.assertEqual(e["crescimento"], 1.5)

    def test_painel_fora_do_ar_cai_na_tabela_de_fabrica(self):
        """Nunca e' o painel que decide se a live FUNCIONA; so' o quanto ela
        e' sua."""
        vazio = ConfigDeMentira(None)
        e = vazio.efeito_do_presente("galaxy", 1000)
        self.assertEqual(e["escala"], regras.LENDARIO["escala"])
        self.assertEqual(e["crescimento"], regras.LENDARIO["crescimento"])

    def test_ajustes_de_crescimento_chegam_como_decimal(self):
        """O `geral()` inteiro transformaria 0.9s de animacao em ZERO -- o
        crescimento suave viraria um salto seco e o ajuste do painel pareceria
        nao funcionar."""
        self.assertEqual(self.cfg.geral_decimal("crescimento_suave", 0.6), 0.9)
        self.assertEqual(self.cfg.geral_decimal("tamanho_max", 6.0), 8.0)

    def test_acao_desligada_no_painel_nao_spawna(self):
        cfg = ConfigDeMentira({
            "acoes": {"curtida": {"ativo": False}, "comentario": {"ativo": True}},
        })
        efeito, _ = cfg.efeito_curtida()
        self.assertIsNone(efeito, "curtida desligada nao pode spawnar")
        self.assertIsNotNone(cfg.efeito_do_comentario())

    def test_na_duvida_a_curtida_fica_DESLIGADA(self):
        """Sem painel, a curtida NAO spawna.

        E' a correcao de um defeito que aparecia ao vivo: no primeiro soluco de
        rede a curtida voltava a spawnar sozinha, e como curtida nao aparece no
        chat, quem estava transmitindo via bonecos nascendo do nada.
        """
        efeito, _ = ConfigDeMentira(None).efeito_curtida()
        self.assertIsNone(efeito)

    def test_na_duvida_o_comentario_fica_LIGADO(self):
        """Comentario com nick e' A promessa do kit: falhar fechado nele
        deixaria a live muda, que e' o defeito oposto e igualmente ruim."""
        self.assertIsNotNone(ConfigDeMentira(None).efeito_do_comentario())


# ══════════════════════════════════════════════════════════════════
#  O LIMITADOR DE TAXA
# ══════════════════════════════════════════════════════════════════

class TesteLimitadorDeTaxa(unittest.TestCase):
    """So' presente fura a fila. Foi um bug de verdade: curtida tem prio 1, e a
    regra antiga (`prio > 0`) deixava ela passar como se fosse paga."""

    def novoTradutor(self):
        import ponte
        return ponte.Tradutor("", "", simular_envio=True)

    def evento(self, tipo, prio):
        return {"tipo": tipo, "prio": prio, "nickname": "x", "roblox_id": 1,
                "escala": 1, "segura": 0}

    def test_presente_passa_sempre(self):
        t = self.novoTradutor()
        presentes = [self.evento("presente", 5) for _ in range(20)]
        escolhidos = t.escolher(presentes)
        self.assertEqual(len(escolhidos), 20,
                         "presente foi pago: nao pode ser barrado por orcamento")

    def test_curtida_NAO_fura_a_fila(self):
        t = self.novoTradutor()
        curtidas = [self.evento("curtida", 1) for _ in range(50)]
        escolhidos = t.escolher(curtidas)
        self.assertLess(len(escolhidos), 10,
                        "curtida passou pelo teto de taxa -- era o bug antigo")

    def test_seguiu_e_compartilhou_tambem_nao_furam(self):
        t = self.novoTradutor()
        eventos = [self.evento("seguiu", 2) for _ in range(50)]
        self.assertLess(len(t.escolher(eventos)), 10)

    def test_o_que_sobra_vai_pro_mais_valioso(self):
        """Com o orcamento apertado, um "seguiu" (raro) nao pode perder a vaga
        pra dois comentarios que chegaram depois dele."""
        t = self.novoTradutor()
        t.credito = 1.0
        eventos = [self.evento("seguiu", 2),
                   self.evento("comentario", 0),
                   self.evento("comentario", 0)]
        escolhidos = t.escolher(eventos, dt=0)
        self.assertEqual(len(escolhidos), 1)
        self.assertEqual(escolhidos[0]["tipo"], "seguiu")


# ══════════════════════════════════════════════════════════════════
#  A LEITURA DO NICK NO CHAT
# ══════════════════════════════════════════════════════════════════

class TesteLeituraDeNick(unittest.TestCase):

    def test_comentario_de_uma_palavra_e_o_caso_comum(self):
        self.assertEqual(nicks.achar_nick("builderman"), "builderman")
        self.assertEqual(nicks.achar_nick("  Player_123  "), "Player_123")

    def test_frase_com_aviso(self):
        self.assertEqual(nicks.achar_nick("meu nick e Fulano123"), "Fulano123")
        self.assertEqual(nicks.achar_nick("nick: Beltrano"), "Beltrano")

    def test_conversa_de_chat_nao_vira_avatar(self):
        """Mostrar o avatar de um ESTRANHO porque alguem escreveu uma palavra
        comum e' o erro mais caro deste modulo: "que", "esse", "onde" e "vez"
        sao todas contas reais no Roblox."""
        for texto in ("kkkkk", "oi", "que", "esse", "onde", "vez", "bora",
                      "top", "muito bom", "eu quero"):
            self.assertIsNone(nicks.achar_nick(texto),
                              f"{texto!r} nao deveria virar nick")

    def test_emoji_nas_bordas_nao_estraga_o_nick(self):
        self.assertEqual(nicks.achar_nick("Player123!!!"), "Player123")

    def test_formato_invalido_e_recusado(self):
        for texto in ("ab", "_comeca_com_underscore", "termina_", "a" * 30):
            self.assertIsNone(nicks.achar_nick(texto), f"{texto!r} passou")


# ══════════════════════════════════════════════════════════════════
#  OS AJUSTES NO DISCO
# ══════════════════════════════════════════════════════════════════

class TesteAjustes(unittest.TestCase):

    def test_presentes_e_SUBSTITUIDO_e_nao_mesclado(self):
        """E' o que faz DESLIGAR um presente funcionar. Com a mesclagem normal,
        "sumiu" nao quer dizer nada -- o valor antigo continuaria pra sempre."""
        base = {"presentes": {"rose": {"escala": 1}, "galaxy": {"escala": 3}}}
        novo = {"presentes": {"rose": {"escala": 2}}}
        fora = servidor._mesclar(base, novo)
        self.assertEqual(list(fora["presentes"]), ["rose"])
        self.assertEqual(fora["presentes"]["rose"]["escala"], 2)

    def test_outras_secoes_sao_mescladas_chave_a_chave(self):
        """O painel manda so' o pedaco que ele conhece, e um update raso
        apagaria o resto."""
        base = {"geral": {"por_fila": 10, "total_avatares": 100}}
        fora = servidor._mesclar(base, {"geral": {"por_fila": 5}})
        self.assertEqual(fora["geral"]["por_fila"], 5)
        self.assertEqual(fora["geral"]["total_avatares"], 100)

    def test_arquivo_antigo_ganha_os_campos_novos(self):
        """Quem ATUALIZOU o kit nao pode ficar com presentes que nao crescem."""
        antigo = {"presentes": {
            "rose": {"prio": 2, "escala": 1.0, "segura": 1.0, "cor": "FF9EC4"},
        }}
        migrado = servidor._migrar(servidor._mesclar(servidor.AJUSTES_PADRAO, antigo))
        rose = migrado["presentes"]["rose"]
        self.assertIn("crescimento", rose)
        self.assertGreater(rose["crescimento"], 0)
        self.assertEqual(rose["grupo"], "rosa")
        self.assertEqual(rose["rotulo"], "Rosa")

    def test_valor_acima_do_teto_e_cortado_na_LEITURA(self):
        """O caso real: o oculos ficou gravado com escala 10, o painel mostrava
        10, e o jogo desenhava 4 -- porque o teto do motor e' 4. O painel virava
        um mentiroso."""
        salvo = {"presentes": {"sunglasses": {"escala": 10, "prio": 5}}}
        migrado = servidor._migrar(servidor._mesclar(servidor.AJUSTES_PADRAO, salvo))
        self.assertEqual(migrado["presentes"]["sunglasses"]["escala"],
                         regras.ESCALA_MAX)

    def test_identidade_do_presente_sobrevive_a_normalizacao(self):
        """O `limitar` so' conhece campos de efeito. Se ele passasse por cima
        do nome e do ID, salvar o painel apagaria o cadastro."""
        e = servidor._normalizar_efeito({
            "escala": 2, "grupo": "rosa", "rotulo": "Rosa", "id": "5655",
            "moedas": 1, "apelidos": ["rose", "rosa"], "emoji": "R"})
        self.assertEqual(e["grupo"], "rosa")
        self.assertEqual(e["id"], "5655")
        self.assertEqual(e["apelidos"], ["rose", "rosa"])

    def test_arquivo_corrompido_nao_impede_a_live_de_subir(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            f.write("{ isto nao e' json valido")
            caminho = f.name
        try:
            a = servidor.Ajustes(caminho)
            self.assertIn("presentes", a.ler())
        finally:
            os.unlink(caminho)


# ══════════════════════════════════════════════════════════════════
#  O CONTRATO COM O ROBLOX
# ══════════════════════════════════════════════════════════════════

class TesteContratoComORoblox(unittest.TestCase):

    def test_o_spawn_leva_tudo_que_o_jogo_le(self):
        """Se um campo sumir daqui, o jogo cai no valor padrao dele -- sem erro
        nenhum, e com o presente fazendo outra coisa."""
        spawn = regras.montar_spawn(
            "id1", "Fulano", 156, regras.limitar(regras.GRANDE), 30,
            nick_roblox="builderman", presente="Doughnut", tipo="presente",
            presente_id="1234")
        for campo in ("tiktok_id", "nickname", "nick_roblox", "roblox_id",
                      "prio", "escala", "crescimento", "vida", "segura", "cena",
                      "furacao", "cor", "brilho", "danca", "danca_geral",
                      "colosso", "presente", "presente_id", "moedas", "tipo",
                      "curtidas", "combo"):
            self.assertIn(campo, spawn, f"o campo {campo} sumiu do spawn")

    def test_o_spawn_e_serializavel_em_json(self):
        """Ele viaja por HTTP ate' o Roblox. Um valor que nao serializa derruba
        o envio do LOTE inteiro, e nao so' daquele evento."""
        spawn = regras.montar_spawn("id1", "Fulano", 1, regras.limitar(regras.BARATO))
        json.dumps(spawn)

    def test_o_teto_de_escala_e_o_mesmo_nos_dois_lados(self):
        """TRES lugares cortam o tamanho de nascimento, e discordar sai caro.

        O `ESCALA_MAX` daqui vale 6. O `Servidor.luau` corta o evento na entrada
        e o `Avatares.escalaDe` corta de novo antes do ScaleTo. Enquanto os dois
        do Luau cortavam em 4, a galaxia -- gravada em 6 no painel e no arquivo
        -- nascia do tamanho do oculos, e nao havia erro em lugar nenhum: o
        painel mostrava 6, o jogo desenhava 4, e a queixa que chega e' "mexo no
        painel e o jogo faz outra coisa".
        """
        alvos = (
            ("ServerScriptService/Servidor.luau",
             r"escala\s*=\s*math\.clamp\(tonumber\(ev\.escala\)\s*or\s*1,\s*[\d.]+,\s*([\d.]+)\)"),
            ("ServerScriptService/Avatares.luau",
             r"return math\.clamp\(tonumber\(spawn\.escala\)\s*or\s*1,\s*[\d.]+,\s*([\d.]+)\)"),
        )
        import re
        for arquivo, padrao in alvos:
            caminho = os.path.join(RAIZ, "roblox", "src", *arquivo.split("/"))
            with open(caminho, encoding="utf-8") as f:
                achado = re.search(padrao, f.read())
            self.assertIsNotNone(achado, f"nao achei o teto de escala em {arquivo}")
            self.assertEqual(
                float(achado.group(1)), float(regras.ESCALA_MAX),
                f"{arquivo} corta a escala em {achado.group(1)} e o Python em "
                f"{regras.ESCALA_MAX} -- o painel vai mentir sobre o tamanho")

    def test_as_dancas_do_python_existem_no_config_do_roblox(self):
        """CONTRATO ENTRE OS DOIS LADOS. Uma danca que passe aqui e nao exista
        no Config.luau vira um boneco PARADO EM PE' no meio da formacao -- e o
        Roblox nao reclama de AnimationId inexistente."""
        config = os.path.join(RAIZ, "roblox", "src", "ReplicatedStorage",
                              "Config.luau")
        with open(config, encoding="utf-8") as f:
            texto = f.read()
        bloco = texto.split("DANCAS = {", 1)[1].split("}", 1)[0]
        for danca in regras.DANCAS_VALIDAS:
            self.assertIn(danca + " =", bloco,
                          f"a danca {danca!r} nao existe em Config.luau (DANCAS)")


# ══════════════════════════════════════════════════════════════════
#  O @ DO TIKTOK
# ══════════════════════════════════════════════════════════════════
#
# O defeito que estes testes trancam nao era "o kit nao conecta". Era pior: o
# kit conectava, falhava, e a mensagem mandava a pessoa conferir a UNICA coisa
# que estava certa -- o @ dela. Cada teste aqui e' uma afirmacao sobre a
# MENSAGEM, e nao sobre a conexao.

class TesteOArrobaDaLive(unittest.TestCase):
    """O que a pessoa cola no campo Conta vira um @ utilizavel."""

    def test_arroba_com_maiuscula_e_espaco_vira_o_arroba_do_tiktok(self):
        self.assertEqual(conta.interpretar("  @Monster  "),
                         ("monster", None))

    def test_o_link_do_perfil_colado_inteiro_funciona(self):
        """O caminho mais curto entre o TikTok e este campo e' o botao
        Compartilhar -> Copiar link. Recusar isso e' recusar o que a pessoa
        naturalmente faz."""
        for link in ("https://www.tiktok.com/@Monster",
                     "https://www.tiktok.com/@Monster/live",
                     "https://www.tiktok.com/@Monster/live?lang=pt-BR",
                     "tiktok.com/@Monster",
                     "www.tiktok.com/@Monster/"):
            self.assertEqual(conta.interpretar(link)[0], "monster", link)

    def test_caractere_invisivel_colado_junto_nao_derruba_o_arroba(self):
        """ESTE E' O BUG ORIGINAL. Copiar do app traz espaco de largura zero
        junto; ele nao aparece no campo, nao aparece no print que chega ao
        suporte, e o `.strip()` do Python nao tira. O TikTok respondia
        'usuario nao encontrado' pra um @ visivelmente certo."""
        self.assertEqual(conta.interpretar("​Monster﻿"),
                         ("monster", None))

    def test_ponto_e_underscore_sao_arrobas_legitimos(self):
        """Barrar um @ valido e' pior que deixar passar um invalido: o invalido
        o TikTok recusa em 30 segundos, o valido nunca chega a ser tentado."""
        for bom in ("maria.silva", "ze_01", "a.b_c.d"):
            self.assertEqual(conta.interpretar(bom), (bom, None), bom)

    def test_arroba_impossivel_e_recusado_com_frase_que_diz_o_que_fazer(self):
        for ruim in ("joao da silva", "maria+silva", "a" * 30):
            achado, recado = conta.interpretar(ruim)
            self.assertEqual(achado, "", ruim)
            self.assertTrue(recado, f"{ruim!r} foi recusado sem explicacao")

    def test_link_curto_nao_vira_um_arroba_inventado(self):
        """`vm.tiktok.com/ZMabc` nao carrega o @ dentro dele. Chutar 'zmabc'
        produziria um @ errado com cara de certo -- e a mensagem seguinte
        acusaria a pessoa de ter digitado errado."""
        achado, recado = conta.interpretar("https://vm.tiktok.com/ZMabc123/")
        self.assertEqual(achado, "")
        self.assertIn("link curto", recado)


class TesteQuemDizQueOArrobaNaoExiste(unittest.TestCase):
    """So' um 404 de verdade autoriza a frase 'confira o @'."""

    def _conferir(self, resposta):
        def abrir(req, timeout=None, context=None):
            if isinstance(resposta, Exception):
                raise resposta
            return resposta
        return conta.conferir("Monster", abrir=abrir)

    def test_404_do_tiktok_e_a_unica_prova_de_que_nao_existe(self):
        erro = urllib.error.HTTPError("u", 404, "nao existe", {}, None)
        self.assertEqual(self._conferir(erro), conta.NAO_EXISTE)

    def test_403_e_500_nao_sao_prova_de_nada(self):
        """O TikTok recusa consulta o tempo todo -- captcha, limite de uso,
        bloqueio de IP. Tratar isso como 'nao existe' e' exatamente o bug que
        mandava a pessoa conferir o @ certo."""
        for codigo in (403, 429, 500, 503):
            erro = urllib.error.HTTPError("u", codigo, "nao", {}, None)
            self.assertEqual(self._conferir(erro), conta.SEM_RESPOSTA,
                             f"o codigo {codigo} virou veredito")

    def test_internet_caindo_nao_vira_conta_inexistente(self):
        self.assertEqual(self._conferir(urllib.error.URLError("sem rede")),
                         conta.SEM_RESPOSTA)

    def test_o_perfil_respondendo_prova_que_o_arroba_existe(self):
        class Resposta:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        self.assertEqual(self._conferir(Resposta()), conta.EXISTE)


# ══════════════════════════════════════════════════════════════════
#  DE QUEM E' A SKIN QUE VAI APARECER
# ══════════════════════════════════════════════════════════════════
#
# ESTE E' O ERRO MAIS CARO QUE O KIT PODE COMETER, e ele nao levanta excecao
# nenhuma: a pessoa comenta o nick, manda um presente, e na tela nasce um boneco
# grande e brilhando com o NOME dela em cima e a SKIN DE OUTRA PESSOA.
#
# Do lado de quem pagou, isso nao parece um bug -- parece que o jogo trocou
# ela de lugar. E nao ha' nada que ela possa fazer pra corrigir.
#
# A causa e' concreta: o TikTok manda o @ em uns eventos e o id numerico em
# outros, entao a ponte tem um indice de reserva pelo NOME DE EXIBICAO. So' que
# nome de exibicao nao e' unico -- duas "ana" numa live grande e' rotina.
#
# Cada teste aqui e' uma afirmacao sobre QUEM aparece na tela.

class TesteDeQuemEASkin(unittest.TestCase):

    def novo(self):
        return ponte.Tradutor("", "", simular_envio=True)

    def test_o_id_e_o_caminho_normal(self):
        t = self.novo()
        t._lembrar("@ana", {"roblox_id": 111, "nickname": "Ana", "nick": "AnaRbx"})
        achado, origem = t._quem_e_e_como("@ana")
        self.assertEqual(achado["roblox_id"], 111)
        self.assertEqual(origem, "id")

    def test_o_nome_salva_o_presente_de_quem_chegou_com_outro_id(self):
        """O motivo de o indice por nome existir: comentario e presente da MESMA
        pessoa chegam com chaves diferentes."""
        t = self.novo()
        t._lembrar("@ana", {"roblox_id": 111, "nickname": "Ana Live", "nick": "AnaRbx"})
        achado, origem = t._quem_e_e_como("6789012345", "Ana Live")
        self.assertEqual(achado["roblox_id"], 111)
        self.assertEqual(origem, "nome")

    def test_duas_pessoas_com_o_mesmo_nome_nao_herdam_a_skin_uma_da_outra(self):
        """O CONSERTO. Assim que o nome fica ambiguo ele para de valer de chave
        -- pras duas. Melhor um presente esperando a pessoa comentar o nick do
        que a skin de um estranho na tela com o nome dela em cima."""
        t = self.novo()
        t._lembrar("@ana1", {"roblox_id": 111, "nickname": "Ana", "nick": "AnaUm"})
        t._lembrar("@ana2", {"roblox_id": 222, "nickname": "Ana", "nick": "AnaDois"})

        self.assertIsNone(t._quem_e("id-desconhecido", "Ana"),
                          "o nome repetido continuou valendo de chave")
        # E cada uma continua sendo encontrada pelo PROPRIO id.
        self.assertEqual(t._quem_e("@ana1")["roblox_id"], 111)
        self.assertEqual(t._quem_e("@ana2")["roblox_id"], 222)

    def test_nome_curto_nunca_vira_chave(self):
        """"k", um emoji sozinho, dois caracteres: repetem numa live grande com
        certeza quase absoluta. Cada repeticao seria uma chance de trocar a skin
        de alguem."""
        t = self.novo()
        t._lembrar("@x", {"roblox_id": 111, "nickname": "k", "nick": "K"})
        self.assertIsNone(t._quem_e("outro-id", "k"))

    def test_o_nome_e_comparado_sem_ligar_pra_caixa_e_espaco(self):
        """Nome de espectador vem com maiuscula, acento e espaco duplo. Se a
        comparacao fosse literal, a MESMA pessoa nao se encontraria."""
        t = self.novo()
        t._lembrar("@ana", {"roblox_id": 111, "nickname": "Ana  Maria",
                            "nick": "AnaRbx"})
        self.assertEqual(t._quem_e("outro-id", "ana maria")["roblox_id"], 111)

    def test_comentar_de_novo_atualiza_a_skin_da_mesma_pessoa(self):
        """Trocar de nick no meio da live tem que funcionar -- e nao pode ser
        confundido com duas pessoas de mesmo nome."""
        t = self.novo()
        t._lembrar("@ana", {"roblox_id": 111, "nickname": "Ana", "nick": "AnaUm"})
        t._lembrar("@ana", {"roblox_id": 999, "nickname": "Ana", "nick": "AnaNova"})
        self.assertEqual(t._quem_e("@ana")["roblox_id"], 999)
        self.assertEqual(t._quem_e("outro-id", "Ana")["roblox_id"], 999,
                         "o nome deixou de valer por causa da propria dona")


if __name__ == "__main__":
    unittest.main(verbosity=2)
