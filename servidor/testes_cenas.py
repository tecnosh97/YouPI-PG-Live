"""Testes do kit de CENAS. Rodam sozinhos, sem rede e sem Roblox.

    python servidor\\testes_cenas.py

POR QUE ESTES TESTES EXISTEM

A paleta de cada cena mora no servidor (servidor/cenas.py) e a regra que diz
qual peça do set é qual papel mora no jogo (roblox/src/ReplicatedStorage/
Cenas.luau). São dois lugares, e o set é um lugar só: se um deles errar, a
parede fica da cor errada e ninguém sabe por que -- não dá erro, não entra em
log, e a única pista é que "a live ficou estranha".

Estes testes fecham essa corrente em três partes:

  1. COBERTURA -- toda peça do mapa tem que cair em alguma regra. Uma peça
     sem regra fica com a cor do mapa, e o sintoma é uma parede da cor
     errada.

  2. COR -- a cor de fábrica de cada papel tem que ser a cor que a peça tem
     no mapa. É o que garante que a cena "Padrão" devolve o set EXATO como
     ele foi desenhado, e que trocar de cena não está inventando cor.

  3. PALETA -- cada cena tem todos os papéis, e nenhuma cor de superfície
     passa de 232 (acima disso a peça estoura em branco sob a luz do set).

O mapa lido aqui é o mesmo que o Rojo monta: roblox/src/Workspace/
Cenario.model.json.
"""

import json
import os
import re
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

import cenas  # noqa: E402

LUAS = os.path.join(RAIZ, "roblox", "src", "ReplicatedStorage", "Cenas.luau")
MAPA = os.path.join(RAIZ, "roblox", "src", "Workspace", "Cenario.model.json")

# A linha de regra no Luau tem este formato, e só este:
#     {"^PisoDoSalao$", "SALAO"},
LINHA_REGRA = re.compile(r'^\s*\{"(\^[^"]+)",\s*"([A-Z_]+)"\},?\s*$')


def _lua_para_regex(padrao):
    r"""Traduz um padrão de Luau para um de Python.

    Luau e Python têm a mesma sintaxe de padrão, com uma diferença: o `\%` do
    Luau é a classe de caractere, e no Python é `\\`. Só as classes que este
    arquivo usa são traduzidas.
    """
    trocas = {
        "%d": r"\d",
        "%a": r"[A-Za-z]",
        "%w": r"\w",
        "%s": r"\s",
        "%l": r"[a-z]",
        "%u": r"[A-Z]",
        "%%": "%",
    }
    saida = []
    i = 0
    while i < len(padrao):
        dois = padrao[i:i + 2]
        if dois in trocas:
            saida.append(trocas[dois])
            i += 2
            continue
        saida.append(padrao[i])
        i += 1
    return "".join(saida)


def ler_regras():
    """As regras do Luau: (regras de peça, regras de quadro).

    O arquivo do jogo é a FONTE das regras. Ler daqui, e não de uma copia
    em Python, é o que impede as duas pontas de saírem de sincronia: se
    alguém corrigir um nome no Luau, este teste passa a cobrar a correção
    nova, e não a velha.
    """
    with open(LUAS, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    pecas, quadros = [], []
    onde = None
    for linha in linhas:
        if "REGRAS_QUADRO" in linha and "local" in linha:
            onde = quadros
            continue
        if "REGRAS" in linha and "local" in linha:
            onde = pecas
            continue
        if onde is None:
            continue
        achado = LINHA_REGRA.match(linha)
        if achado:
            onde.append((achado.group(1), achado.group(2)))

    return pecas, quadros


def ler_mapa():
    """Todas as instâncias do mapa: (classe, nome, material, cor)."""
    with open(MAPA, "r", encoding="utf-8") as f:
        mapa = json.load(f)

    saida = []

    def anda(node):
        for filho in node.get("children", []):
            props = filho.get("properties", {})
            cor = props.get("Color")
            fundo = props.get("BackgroundColor3")
            mat = props.get("Material")
            saida.append({
                "classe": filho.get("className", ""),
                "nome": filho.get("name", ""),
                "material": mat,
                "cor": cor if cor is not None else fundo,
                "eh_quadro": "BackgroundColor3" in props,
            })
            anda(filho)

    anda(mapa)
    return saida


def cor255(cor):
    """A cor do mapa (0 a 1) virada no inteiro que a paleta usa (0 a 255)."""
    if not cor:
        return None
    return tuple(int(round(c * 255)) for c in cor)


# As DUAS regras que não dá para ler do nome sozinho. Elas existem aqui
# porque o mapa é a fonte da verdade do COMO o gerador desenhou o set:
#
#   - a pista tem três papéis, e o nome do tile não diz qual (o xadrez
#     alterna a paridade da soma dos dois números, e a fileira que acende é
#     a que tem material Neon);
#   - o acento do set existe em duas versões, e o MATERIAL diz qual: a de
#     metal é a cor clara, e a que acende é a escura.
#
# As duas estão conferidas uma a uma no teste de Luau
# (roblox/testes/cenas.spec.luau), que roda FORA do Roblox.
def resolver_slot(nome, material, regras):
    for padrao, slot in regras:
        if re.match(_lua_para_regex(padrao), nome):
            if slot == "PISTA":
                if material == "Neon":
                    return "PISTA_ACESA"
                i, j = re.match(r"^Tile(\d+)_(\d+)$", nome).groups()
                return "PISTA_A" if (int(i) + int(j)) % 2 == 0 else "PISTA_B"
            if slot == "NEON_A" and material == "Neon":
                return "NEON_A_VIVO"
            if slot == "NEON_B" and material == "Neon":
                return "NEON_B_VIVO"
            return slot
    return None


class TesteCenas(unittest.TestCase):
    def setUp(self):
        self.regras, self.quadros = ler_regras()
        self.mapa = ler_mapa()
        self.padrao = cenas.TEMAS["padrao"]["cores"]

    # ─────────────── 1. COBERTURA ───────────────

    def test_toda_pegaca_do_mapa_tem_uma_regra(self):
        """Uma peça sem regra fica com a cor do mapa, e ninguém sabe por quê."""
        sem = []
        for item in self.mapa:
            if item["classe"] in ("Folder", "SurfaceGui"):
                continue
            if item["classe"] in ("SpotLight", "SurfaceLight"):
                # As LUZES não são resolvidas pelo nome: os onze focos se
                # chamam todos "Foco", e o que os diferencia é o pai (uma luz
                # de frente é quente, uma de fundo é fria). A regra delas é
                # conferida no teste de Luau.
                continue
            if item["eh_quadro"]:
                achado = resolver_slot(item["nome"], None, self.quadros)
            else:
                achado = resolver_slot(item["nome"], item["material"], self.regras)
            if achado is None:
                sem.append(f'{item["classe"]} {item["nome"]}')
        self.assertEqual(sem, [], "peças do mapa sem regra de cor: "
                                 + ", ".join(sem[:20]))

    def test_as_regras_do_luau_foram_lidas(self):
        """A leitura das regras não pode vir vazia: seria um teste que passa."""
        self.assertGreater(len(self.regras), 70, "as regras do Luau não foram lidas")
        self.assertEqual(len(self.quadros), 4, "as regras dos quadros não foram lidas")

    # ─────────────── 2. COR ───────────────

    def test_a_cena_padrao_reproduz_o_mapa_exato(self):
        """A cena "Padrão" tem que devolver o set como ele foi desenhado.

        Se a cor de fábrica de um papel não for a cor que a peça tem no
        mapa, então trocar de cena está inventando cor — e a cena "Padrão"
        deixa de ser o botão de voltar.
        """
        erros = []
        for item in self.mapa:
            if item["classe"] in ("Folder", "SurfaceGui"):
                continue
            if item["eh_quadro"]:
                slot = resolver_slot(item["nome"], None, self.quadros)
                t = self._parametro(item["nome"])
            else:
                slot = resolver_slot(item["nome"], item["material"], self.regras)
                t = self._parametro(item["nome"])
            if slot is None:
                continue

            cor_esperada = self.padrao.get(slot)
            if cor_esperada is None:
                if slot == "DEGRAU":
                    a = self.padrao["DEGRAU_A"]
                    b = self.padrao["DEGRAU_B"]
                elif slot == "FAIXA":
                    a = self.padrao["PAINEL_ALTO"]
                    b = self.padrao["TELA"]
                else:
                    erros.append(f'{item["nome"]}: papel "{slot}" sem cor')
                    continue
                cor_esperada = [a[i] + (b[i] - a[i]) * (t or 0) for i in range(3)]

            cor_do_mapa = cor255(item["cor"])
            if cor_do_mapa is None:
                continue
            for canal in range(3):
                if abs(cor_esperada[canal] - cor_do_mapa[canal]) > 1:
                    erros.append(
                        f'{item["nome"]}: papel "{slot}" pintaria de '
                        f'{tuple(int(round(c)) for c in cor_esperada)} e a peça '
                        f'é {cor_do_mapa}')
                    break

        self.assertEqual(erros, [], "a cena de fábrica não reproduz o mapa: "
                         + " | ".join(erros[:10]))

    @staticmethod
    def _parametro(nome):
        m = re.match(r"^Degrau\w+(\d+)$", nome)
        if m:
            return int(m.group(1)) / 4
        m = re.match(r"^Faixa(\d+)$", nome)
        if m:
            return int(m.group(1)) / 11
        return None

    # ─────────────── 3. PALETA ───────────────

    def test_toda_cena_tem_todos_os_papeis(self):
        for chave, tema in cenas.TEMAS.items():
            faltando = [s for s in cenas.SLOTS if s not in tema["cores"]]
            self.assertEqual(faltando, [], f'a cena "{chave}" está sem: '
                             + ", ".join(faltando))

    def test_nenhuma_cor_de_superficie_passa_de_234(self):
        """Acima de 234, a peça estoura em branco sob a luz do set.

        A pista ocupa o terço de baixo do quadro o tempo todo: um tile
        estourado ali é um borrão branco no meio da multidão.

        O teto é 234 porque é o MAIOR valor que o próprio set de fábrica
        usa -- a parede clara é #E4E5EA, e o azul dela é 234. Uma cena que
        passa disso está mais clara do que o set que o kit desenhou, e
        estoura.
        """
        for chave, tema in cenas.TEMAS.items():
            for slot, cor in tema["cores"].items():
                if slot in ("LUZ_QUENTE", "LUZ_FRIA"):
                    continue  # cor de luz pode ser quase branca
                if slot in ("NEON_A", "NEON_B", "LENTE_QUENTE", "LENTE_FRIA"):
                    teto = 240  # acento e lente são peças pequenas
                else:
                    teto = 234
                for canal, valor in enumerate(cor):
                    self.assertLessEqual(
                        valor, teto,
                        f'a cena "{chave}" põe {slot} em {valor} no canal {canal} '
                        f'-- acima de {teto} a peça estoura')

    def test_o_tile_que_acende_nao_estoura_em_branco(self):
        """O tile aceso é Neon, e Neon desenha a cor no brilho máximo.

        Uma cor CLARA em Neon acende como BRANCO, e um branco piscando na
        pista é um clarão, não um destaque. O que protege é o canal mais
        alto da cor: abaixo de 210, o tile acende como a cor que ele é.
        """
        for chave, tema in cenas.TEMAS.items():
            cor = tema["cores"]["PISTA_ACESA"]
            self.assertLessEqual(
                max(cor), 210,
                f'na cena "{chave}" o tile que acende tem o canal mais alto em '
                f'{max(cor)} -- em Neon isso acende como branco')

    def test_o_acento_que_acende_e_mais_escuro_que_o_de_metal(self):
        """Em Neon, cor clara acende como BRANCO.

        O acento que acende tem que ser o mais escuro da paleta, senão o
        set vira um clarão em vez de um acento.
        """
        for chave, tema in cenas.TEMAS.items():
            for metal, vivo in (("NEON_A", "NEON_A_VIVO"),
                                ("NEON_B", "NEON_B_VIVO")):
                a = tema["cores"][metal]
                b = tema["cores"][vivo]
                soma_a = sum(a)
                soma_b = sum(b)
                self.assertLess(
                    soma_b, soma_a,
                    f'na cena "{chave}" o acento que acende ({vivo}) é mais '
                    f'claro que o de metal ({metal}) -- em Neon isso vira branco')

    def test_a_cena_padrao_e_a_paleta_do_gerador(self):
        """A cena de fábrica é o set como o gerador o desenhou.

        Estes valores são os do ferramentas/gerar-cenario.py. Se alguém mexer
        numa paleta, o lugar de mexer é o gerador -- e os dois têm que
        concordar.
        """
        esperado = {
            "SALAO": (191, 196, 207),
            "PALCO": (170, 176, 190),
            "REJUNTE": (96, 100, 112),
            "PISTA_A": (228, 224, 216),
            "PISTA_B": (203, 198, 189),
            "PISTA_ACESA": (134, 96, 140),
            "PAREDE": (228, 229, 234),
            "PAREDE_ESC": (198, 201, 210),
            "ESTRUTURA": (122, 128, 144),
            "ESTRUTURA_ESC": (84, 89, 102),
            "MADEIRA": (196, 164, 124),
            "NEON_A": (224, 122, 168),
            "NEON_B": (126, 196, 224),
            "NEON_A_VIVO": (146, 66, 104),
            "NEON_B_VIVO": (58, 118, 150),
            "LENTE_QUENTE": (214, 200, 176),
            "LENTE_FRIA": (172, 190, 212),
            "TELA": (186, 168, 200),
            "PAINEL_ALTO": (104, 88, 128),
            "LUZ_QUENTE": (255, 246, 232),
            "LUZ_FRIA": (226, 238, 255),
        }
        for slot, cor in esperado.items():
            self.assertEqual(tuple(self.padrao[slot]), cor,
                             f'a cor de fábrica de {slot} mudou')

    def test_o_nome_da_cena_e_aceito_qualquer_que_seja_a_caixa(self):
        self.assertEqual(cenas.nome_canonico("NEON"), "neon")
        self.assertEqual(cenas.nome_canonico("Neon"), "neon")
        self.assertEqual(cenas.nome_canonico("Pôr do sol"), "sunset")
        self.assertIsNone(cenas.nome_canonico("cena que nao existe"))

    def test_o_pacote_traz_a_cena_escolhida_e_a_tabela_inteira(self):
        pacote = cenas.pacote("neon")
        self.assertEqual(pacote["tema_atual"], "neon")
        self.assertEqual(list(pacote["temas"].keys()), list(cenas.ORDEM))
        for chave, tema in pacote["temas"].items():
            self.assertEqual(len(tema["cores"]), len(cenas.SLOTS))
            self.assertIn("atmo", tema["luz"])
            self.assertIn("tint", tema["luz"])

    def test_cena_desconhecida_cai_na_de_fabrica(self):
        """Cena errada não pode derrubar o painel: ela volta para a de fábrica."""
        self.assertEqual(cenas.nome_canonico("inexistente"), None)
        self.assertEqual(cenas.paleta("inexistente")["nome"], "Padrão")


if __name__ == "__main__":
    unittest.main(verbosity=2)
