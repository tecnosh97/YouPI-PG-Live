"""AS CENAS -- o kit de temas do cenário, trocados ao vivo.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O mapa do kit foi desenhado com UMA paleta só: o salão claro, o rosa e o
ciano. Trocar isso significava editar o gerador do cenário e remontar o
arquivo do jogo -- ou seja, reiniciar a live. O produto tem a cena de fechamento
a cada ciclo da formação, e é justamente no meio da live que a cor do set
importa mais.

Aqui a cor deixa de ser do MAPA e passa a ser um DADO. O gerador continua
desenhando o mesmo set; o que muda é a cor que cada peça recebe em tempo de
execução. Trocar de cena custa um clique no painel (ou um `!cena` no chat) e
vale em até 5 segundos, sem reiniciar nada.

A REGRA QUE FAZ ESSA TROCA FUNCIONAR
------------------------------------
Toda peça do set tem um PAPEL -- "isto é a parede", "isto é o acento quente",
"isto é o tile que acende" -- e não uma cor. A paleta de cada cena é uma
tabela de PAPEL -> cor. Por isso uma cena nova não precisa redesenhar o mapa:
ela só diz que "a parede" passa a ser verde, e todas as paredes ficam verdes
de uma vez, juntas.

Este arquivo é o ÚNICO lugar onde a paleta mora. O painel lê daqui para
desenhar a prévia, e o jogo recebe a mesma tabela pelo `/ajustes`. Não há
cópia da paleta em JavaScript nem em Luau: uma cor trocada aqui aparece nos
dois lados no mesmo instante, e um tema novo é um item novo nesta lista.

A REGRA DO 232
--------------
Nenhuma cor de SUPERFÍCIE passa de 232. Acima disso, sob a luz ambiente alta
do set, a peça estoura e vira um borrão branco -- e o pior lugar pra isso é a
pista, que ocupa o terço de baixo do quadro o tempo todo. As duas exceções
são as cores de LUZ (que são luz, não superfície) e as cores NEON, que seguem
a regra do gerador: em Neon, cor clara acende como BRANCO, então o neon
vivo é sempre o mais escuro da paleta.
"""

# Os papéis do set. A ordem é a de leitura no painel: do chão para o teto.
SLOTS = (
    "SALAO",           # o piso em volta do palco
    "PALCO",           # a pedra que emoldura a pista
    "REJUNTE",         # a fresta escura entre os tiles
    "PISTA_A",         # o tile claro do xadrez
    "PISTA_B",         # o tile escuro do xadrez
    "PISTA_ACESA",     # o tile que acende (Neon)
    "DEGRAU_A",        # o degrau mais baixo (começa o degrade)
    "DEGRAU_B",        # o degrau mais alto (termina o degrade)
    "PAREDE",          # a parede clara
    "PAREDE_ESC",      # a parede do fundo
    "ESTRUTURA",       # treliça, moldura, torre
    "ESTRUTURA_ESC",   # a caixa de som
    "MADEIRA",         # o acabamento quente (rodapé, viga, capitel)
    "NEON_A",          # o acento quente, na versão de metal
    "NEON_B",          # o acento frio, na versão de metal
    "NEON_A_VIVO",     # o acento quente, na versão que acende
    "NEON_B_VIVO",     # o acento frio, na versão que acende
    "LENTE_QUENTE",    # a lente da luz de frente
    "LENTE_FRIA",      # a lente da luz de fundo
    "TELA",            # o painel do fundo, na base
    "PAINEL_ALTO",     # o painel do fundo, no topo
    "LUZ_QUENTE",      # a cor da luz quente
    "LUZ_FRIA",        # a cor da luz fria
)

# A cena de fábrica é o set como ele foi desenhado. Ela precisa ser EXATA:
# quem não mexe em nada tem que ver o mesmo mapa de sempre.
_PADRAO = {
    "SALAO": (191, 196, 207),
    "PALCO": (170, 176, 190),
    "REJUNTE": (96, 100, 112),
    "PISTA_A": (228, 224, 216),
    "PISTA_B": (203, 198, 189),
    "PISTA_ACESA": (134, 96, 140),
    "DEGRAU_A": (198, 201, 210),
    "DEGRAU_B": (223, 227, 234),
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

_LUZ_PADRAO = {
    "atmo": (204, 207, 219),
    "decay": 0.72,
    "haze": 0.4,
    "tint": (255, 254, 252),
    "bloom": 0.12,
    "saturacao": 0.08,
    "contraste": 0.04,
}


def _cena(nome, cores, atmo, decay, haze, tint, bloom, saturacao, contraste):
    """Monta uma cena já no formato que o jogo consome."""
    faltando = [s for s in SLOTS if s not in cores]
    if faltando:
        raise ValueError(f"a cena '{nome}' está sem: {', '.join(faltando)}")
    return {
        "nome": nome,
        "cores": {s: tuple(cores[s]) for s in SLOTS},
        "luz": {
            "atmo": tuple(atmo),
            "decay": float(decay),
            "haze": float(haze),
            "tint": tuple(tint),
            "bloom": float(bloom),
            "saturacao": float(saturacao),
            "contraste": float(contraste),
        },
    }


def _cena_de(nome, cores, luz):
    """Repassa os parâmetros de luz na folha que _cena() pede."""
    return _cena(
        nome, cores,
        luz["atmo"], luz["decay"], luz["haze"], luz["tint"],
        luz["bloom"], luz["saturacao"], luz["contraste"],
    )


TEMAS = {
    # [[ ESTA É A BUILD DE VENDA. As paletas não estão aqui:
    #	elas chegam com a LICENÇA, pelo manifesto do GitHub. As
    #	estruturas (os papéis, as regras, a matemática) continuam,
    #	porque elas não são segredo -- o que é segredo é a cor. ]]
}

# A ordem em que as cenas aparecem no painel.
ORDEM = ("padrao", "neon", "matrix", "sunset", "gelo", "carvao")

PADRAO = "padrao"

# Nomes de exibição, usados pela blindagem quando a mesa da licença
# chega sem uma paleta qualquer.
_NOME_EM_FALTA = {
    "padrao": "Padrão", "neon": "Neon", "matrix": "Matrix",
    "sunset": "Sunset", "gelo": "Gelo", "carvao": "Carvão",
}


def _luz_do_pacote(luz):
    """A luz volta ao formato interno, vindo do pacote da licença."""
    return {
        "atmo": tuple(luz.get("atmo") or _LUZ_PADRAO["atmo"]),
        "decay": float(luz.get("decay", _LUZ_PADRAO["decay"])),
        "haze": float(luz.get("haze", _LUZ_PADRAO["haze"])),
        "tint": tuple(luz.get("tint") or _LUZ_PADRAO["tint"]),
        "bloom": float(luz.get("bloom", _LUZ_PADRAO["bloom"])),
        "saturacao": float(luz.get("saturacao", _LUZ_PADRAO["saturacao"])),
        "contraste": float(luz.get("contraste", _LUZ_PADRAO["contraste"])),
    }


def aplicar_paletas(paletas):
    """Troca as paletas deste arquivo pelas que vieram da LICENÇA.

    A build de VENDA chega aqui sem paleta nenhuma: as cores saem do
    servidor de chaves, e não do ZIP. É isso que impede o arquivo que o
    comprador recebe de carregar as paletas junto -- e, no modo publicado,
    impede que elas apareçam no lugar nenhum para ele.

    A build de FONTE (a do vendedor, que roda o servidor de chaves) tem as
    paletas no próprio arquivo, e esta função não é chamada.

    Devolve True se entrou paleta nova.
    """
    global TEMAS, ORDEM

    if not isinstance(paletas, dict) or not paletas:
        return False

    novas = {}
    for chave, tema in paletas.items():
        if not isinstance(tema, dict):
            continue
        cores = tema.get("cores") or {}
        if not all(s in cores for s in SLOTS):
            continue
        novas[chave] = {
            "nome": tema.get("nome", chave),
            "cores": {s: tuple(cores[s]) for s in SLOTS},
            "luz": _luz_do_pacote(tema.get("luz") or {}),
        }

    if not novas:
        return False

    TEMAS = novas
    ORDEM = tuple(k for k in ORDEM if k in TEMAS) or tuple(TEMAS.keys())
    return True


def existe(nome):
    """O nome da cena existe? (aceita tanto 'neon' quanto 'Neon')"""
    return _resolver(nome) is not None


def _resolver(nome):
    if not isinstance(nome, str):
        return None
    alvo = nome.strip().lower()
    if alvo in TEMAS:
        return alvo
    for chave, cena in TEMAS.items():
        if cena["nome"].strip().lower() == alvo:
            return chave
    return None


def nome_canonico(nome):
    """'Neon' -> 'neon'. Devolve None se a cena não existe."""
    return _resolver(nome)


def tem_cena(nome):
    """A cena existe?"""
    return _resolver(nome) is not None


def paleta(nome):
    """A paleta de uma cena, no formato que o jogo consome.

    Blindagem: se a mesa veio sem a paleta da licença (manifesto
    atrasado, arquivo novo), devolve a paleta de fábrica. O jogo vive
    e a cor erra no lugar certo -- jamais o servidor, que não morre.
    """
    chave = _resolver(nome) or PADRAO
    if chave not in TEMAS:
        return _cena_de(_NOME_EM_FALTA.get(chave, chave), _PADRAO, _LUZ_PADRAO)
    return TEMAS[chave]


def pacote(tema_atual):
    """O que o `/ajustes` devolve: a cena escolhida e a tabela com todas.

    O jogo e o painel leem o MESMO pacote. É por isso que a prévia do painel
    e a cor que aparece no jogo não têm como divergir: não são duas listas,
    é uma.
    """
    atual = _resolver(tema_atual) or PADRAO
    entradas = {}
    for chave in ORDEM:
        tema = TEMAS.get(chave)
        if tema is None:
            # a paleta da licença não chegou: a de fábrica apara a mesa.
            # O /ajustes responde de qualquer jeito -- é ele que o jogo
            # pergunta a cada 5 segundos, e sem resposta ele desiste.
            tema = _cena_de(_NOME_EM_FALTA.get(chave, chave), _PADRAO, _LUZ_PADRAO)
        entradas[chave] = {
            "nome": tema["nome"],
            "cores": {s: list(tema["cores"][s]) for s in SLOTS},
            "luz": {
                "atmo": list(tema["luz"]["atmo"]),
                "decay": float(tema["luz"]["decay"]),
                "haze": float(tema["luz"]["haze"]),
                "tint": list(tema["luz"]["tint"]),
                "bloom": float(tema["luz"]["bloom"]),
                "saturacao": float(tema["luz"]["saturacao"]),
                "contraste": float(tema["luz"]["contraste"]),
            },
        }
    # paletas que a licença trouxe fora da ORDEM também entram no pacote
    for chave, tema in TEMAS.items():
        if chave in entradas:
            continue
        entradas[chave] = {
            "nome": tema["nome"],
            "cores": {s: list(tema["cores"][s]) for s in SLOTS},
            "luz": {
                "atmo": list(tema["luz"]["atmo"]),
                "decay": float(tema["luz"]["decay"]),
                "haze": float(tema["luz"]["haze"]),
                "tint": list(tema["luz"]["tint"]),
                "bloom": float(tema["luz"]["bloom"]),
                "saturacao": float(tema["luz"]["saturacao"]),
                "contraste": float(tema["luz"]["contraste"]),
            },
        }
    return {"tema_atual": atual, "temas": entradas}
