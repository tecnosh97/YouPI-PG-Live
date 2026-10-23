"""O que cada presente do TikTok faz dentro do jogo.

Funcoes puras: entra nome e moedas, sai um dicionario de efeito. Sem rede, sem
live, sem Roblox -- da' pra testar tudo aqui sem abrir nada.

AS ALAVANCAS DE UM EFEITO
-------------------------
  prio        quem tem numero maior fura a fila de spawn e entra na frente
  escala      multiplicador de tamanho com que o avatar NASCE
  crescimento quanto de tamanho este presente SOMA num avatar que ja' esta'
              na tela (ver adiante -- e' a alavanca principal do produto)
  vida        segundos na tela antes de sumir
  segura      segundos em que NINGUEM mais nasce depois deste avatar
  cena        segundos de CINEMATICA (a camera corta e gira em volta dele)
  chuva       segundos cuspindo mais avatares da mesma pessoa
  furacao     segundos varrendo a formacao e derrubando todo mundo
  cor         cor do nome e do brilho, em hexadecimal
  brilho      forca da aura, de 0 a 5
  danca       o PASSO que este avatar dança (ver DANCAS_VALIDAS)

ESCALA E CRESCIMENTO SAO COISAS DIFERENTES, E CONFUNDI-LAS QUEBRA O PRODUTO
--------------------------------------------------------------------------
`escala` e' o tamanho de NASCIMENTO: vale quando a pessoa ainda nao tem boneco
nenhum na tela e o presente precisa criar um.

`crescimento` e' o que o telao promete -- "envie presentes e seu personagem
cresce". Ele SOMA no avatar que a pessoa ja' tem, presente after presente, ate'
o teto de `geral.tamanho_max`. E' cumulativo de proposito: e' o unico jeito de
o segundo presente da mesma pessoa valer alguma coisa visivel.

Um presente pode ter os dois: a rosa de quem ainda nao apareceu cria um boneco
de tamanho 1.0, e a rosa de quem ja' esta' na tela soma +0.15 no boneco dela.

POR QUE `segura` E `cena` SAO SEPARADOS
---------------------------------------
`segura` todo mundo tem, ate' quem so' comentou. Como a camera acompanha quem
acabou de chegar, segurar o proximo spawn por meio segundo e' o que faz a
camera passar de um em um em vez de piscar entre eles.

`cena` so' presente caro tem. Ela CORTA a camera pro avatar e faz um movimento
em volta. Vem sempre com um `segura` igual ou maior -- senao alguem nasceria no
meio do momento que a pessoa pagou pra ter.

A ARMADILHA DOS NOMES
---------------------
A API do TikTok devolve o nome do presente em INGLES, e ele MUDA de regiao pra
regiao e ao longo do tempo. Por isso a regra por nome e' so' um atalho.

Sao TRES caminhos de casamento, nesta ordem, e a ordem importa:

  1. ID do presente   numero estavel do TikTok. Imune a idioma e a regiao.
                      E' o caminho preferido, e o painel mostra o ID de cada
                      presente que chega justamente pra voce cadastrar sem
                      adivinhar nada.
  2. APELIDO          o nome em minusculas ("rose", "rosa", "galaxy"...).
                      Serve enquanto voce nao souber o ID.
  3. FAIXA DE PRECO   a rede de seguranca. Funciona com QUALQUER presente,
                      inclusive um que o TikTok lancou ontem e que voce nunca
                      cadastrou.

Nenhum presente fica sem efeito: se os tres primeiros falharem, o preco decide.
"""

# ─────────────────────── As dancas ───────────────────────
#
# CONTRATO COM O ROBLOX. Cada nome aqui precisa existir como chave em
# `DANCAS`, no roblox/src/ReplicatedStorage/Config.luau -- e' la' que mora o ID
# da animacao de cada uma.
#
# A lista existe pra um nome errado (digitado no painel, ou vindo de um
# ajustes.json editado na mao) virar "danca padrao" em vez de virar um boneco
# PARADO EM PE' no meio da formacao. O Roblox nao reclama de um AnimationId que
# nao existe: ele carrega, o Play() funciona, e o avatar simplesmente nao se
# mexe. Barrar aqui e' o unico ponto do caminho em que da' pra perceber o erro.
#
# As quatro ultimas sao gratuitas da propria Roblox (ver o bloco DANCAS no
# Config.luau). Elas existem pra o painel ter de que escolher sem depender da
# permissao de asset de terceiro: qualquer presente pode usar qualquer uma
# delas, e por isso o nome e' de PASSO e nao de presente.
DANCAS_VALIDAS = ("rosquinha", "oculos", "galaxia", "festa",
                  "disco", "solto", "passinho", "swing")


# ─────────────────────── Os efeitos de fabrica ───────────────────────
#
# Um lugar so' pra mexer no equilibrio da live. O painel escreve por cima
# destes valores; aqui e' o que vale quando o painel nunca foi aberto.
#
# A `danca` acompanha a FAIXA, e nao o nome do presente, e isso e' de proposito:
# assim um presente de 1000 moedas que o TikTok lancou ontem -- ou que chega com
# outro nome na sua regiao -- ja' entra dancando a danca da galaxia, sem voce
# cadastrar nada. E' a mesma logica que faz a faixa de preco sustentar o resto
# do kit.

#[[ A ESCADA DO `crescimento`
#
#   Os numeros nao sao redondos por acaso: eles formam uma escada em que cada
#   degrau e' visivelmente maior que o de baixo NA TELA, e nao so' na planilha.
#
#     rosa       +0.15  precisa de ~7 rosas pra dobrar de tamanho
#     medio      +0.30
#     rosquinha  +0.60  duas rosquinhas ja' destacam a pessoa da formacao
#     oculos     +1.00  uma so' e' o dobro do tamanho normal
#     galaxia    +1.60  uma so' leva quase ao teto
#
#   O teto (geral.tamanho_max, padrao 6.0) e' o que impede o crescimento
#   infinito: a partir dele o presente continua contando no placar e no brilho,
#   mas o boneco para de crescer. Sem teto, uma pessoa determinada transforma o
#   proprio avatar num predio que tapa a live inteira -- e' o defeito classico
#   deste genero de jogo. ]]

COMENTARIO = {"prio": 0, "escala": 1.0, "crescimento": 0, "vida": 45,
              "segura": 0.4, "cena": 0, "chuva": 0, "cor": "FFFFFF",
              "brilho": 0, "danca": ""}

BARATO = {"prio": 2, "escala": 2.0, "crescimento": 0.15, "vida": 90,
          "segura": 1.0, "cena": 0, "chuva": 0, "cor": "FF9EC4", "brilho": 1,
          "danca": ""}

MEDIO = {"prio": 3, "escala": 2.5, "crescimento": 0.3, "vida": 150,
         "segura": 4.0, "cena": 4.0, "chuva": 0, "cor": "FF2D6F", "brilho": 2,
         "danca": ""}

# A ROSQUINHA e as outras da faixa dela: primeiro degrau com danca propria.
GRANDE = {"prio": 4, "escala": 3.0, "crescimento": 0.6, "vida": 240,
          "segura": 5.5, "cena": 5.5, "chuva": 0, "cor": "FFA321", "brilho": 3,
          "danca": "rosquinha"}

# O OCULOS. O furacao e' o momento mais caro que nao envolve chuva: o avatar sai
# varrendo a formacao inteira e no fim a grade recomeca do zero. `segura` e' bem
# maior que `cena` de proposito -- a cena mostra ele chegando, e o resto do tempo
# e' a varredura acontecendo sem ninguem novo atrapalhando o quadro.
ENORME = {"prio": 5, "escala": 4.0, "crescimento": 1.0, "vida": 300,
          "segura": 14.0, "cena": 4.0, "furacao": 12.0, "chuva": 0,
          "cor": "27E1FF", "brilho": 4, "danca": "oculos"}

# A GALAXIA, o topo. A cinematica mais longa e uma chuva de 30s. So' o PRIMEIRO
# avatar da chuva ganha cena: 20 cinematicas de 9s enfileiradas travariam a live
# por tres minutos, e a graca da chuva e' o volume, nao a repeticao do close.
#
# Os avatares da chuva HERDAM a danca (a ponte so' zera cena e chuva neles), e
# e' isso que faz os 20 bonecos da galaxia chegarem dancando o mesmo passo --
# uma coreografia inteira aparecendo no meio da formacao normal.
LENDARIO = {"prio": 6, "escala": 6.0, "crescimento": 1.6, "vida": 300,
            "segura": 9.0, "cena": 9.0, "chuva": 30, "cor": "B14BFF",
            "brilho": 5, "danca": "galaxia"}


# ─────────────────────── Tetos de sanidade ───────────────────────
#
# Um combo de 10.000 rosas nao pode gerar um avatar gigante e eterno que trava
# a live. Valem tambem pro que vem do painel: confiar num lado so' e' como nao
# ter trava nenhuma.

ESCALA_MAX = 6.0
VIDA_MAX = 600
SEGURA_MAX = 25
CENA_MAX = 25
FURACAO_MAX = 20
CHUVA_MAX = 60
PRIO_MAX = 20
BRILHO_MAX = 5
COMBO_MAX = 100

#[[ Quanto UM presente pode somar de tamanho de uma vez.
#
#   Nao e' o teto do avatar -- esse e' o `geral.tamanho_max`, e ele mora no
#   painel porque depende do enquadramento que voce escolheu. Este aqui limita
#   o SALTO: um presente que somasse 20 de uma vez faria o boneco pular de
#   tamanho num quadro so', atravessar os vizinhos e sair do quadro antes de a
#   camera ter chance de recuar. 3.0 ja' e' um salto enorme na tela. ]]
CRESCIMENTO_MAX = 3.0

#[[ Os limites do TAMANHO ACUMULADO. Ficam aqui, e nao so' no Roblox, porque a
#   ponte precisa deles pra prever o tamanho e mostra-lo no painel -- e dois
#   lados com tetos diferentes e' exatamente o tipo de divergencia que faz o
#   painel mostrar um numero e o jogo desenhar outro. ]]
TAMANHO_MAX_PADRAO = 6.0
TAMANHO_MAX_TETO = 12.0
TAMANHO_MIN = 0.5


# ─────────────────────── As regras ───────────────────────
#
# (nomes que casam, moedas minimas, moedas maximas, efeito)
#
# `None` no lugar dos nomes = qualquer nome. Sao as linhas de faixa de preco, e
# sao elas que fazem o kit funcionar com presente que voce nunca cadastrou.
#
# A ordem importa: a primeira linha que casar vence. Nome antes de faixa, e
# faixa da mais cara pra mais barata.

REGRAS = (
    # nomes                                    min    max   efeito
    (("galaxy", "galaxia", "galáxia"),            0,  None, LENDARIO),
    (("sunglasses", "oculos", "óculos"),          0,  None, ENORME),
    (("doughnut", "donut", "rosquinha"),          0,  None, GRANDE),
    # A ROSA -- uma linha so'. "rose" e "rosa" nao sao duas rosas: sao o MESMO
    # presente com o nome que a API do TikTok manda em cada regiao. Se um dia
    # aparecer uma rosa mais cara, ela nao precisa de linha propria -- cai na
    # faixa de preco logo abaixo e sobe de nivel sozinha.
    (("rose", "rosa"),                            0,  None, BARATO),
    # Rede de seguranca por preco, pro que nao casou por nome:
    (None,                                     1000,  None, LENDARIO),
    (None,                                      200,  None, ENORME),
    (None,                                       30,  None, GRANDE),
    (None,                                       10,  None, MEDIO),
    (None,                                        1,  None, BARATO),
)


def _entre(valor, padrao, minimo, maximo):
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return padrao
    if n != n:  # NaN nao e' igual a si mesmo
        return padrao
    return max(minimo, min(maximo, n))


def limitar(efeito, prio_extra=0):
    """Aplica os tetos e devolve um efeito COMPLETO.

    Completo importa: o resto da ponte espera todos os campos presentes, e um
    efeito vindo do painel com metade das chaves quebraria em outro lugar,
    longe daqui, num campo que ninguem lembra que existe.
    """
    e = efeito if isinstance(efeito, dict) else {}
    return {
        "prio": int(_entre(e.get("prio"), 0, 0, PRIO_MAX) + int(prio_extra or 0)),
        "escala": round(_entre(e.get("escala"), 1.0, 0.5, ESCALA_MAX), 2),
        # Quanto este presente SOMA no avatar que a pessoa ja' tem na tela.
        # 0 = o presente nao faz crescer (so' cria boneco novo, brilha e conta
        # no placar). Ver o cabecalho do modulo pra diferenca entre os dois.
        "crescimento": round(_entre(e.get("crescimento"), 0, 0, CRESCIMENTO_MAX), 3),
        "vida": int(_entre(e.get("vida"), 45, 5, VIDA_MAX)),
        "segura": round(_entre(e.get("segura"), 0.4, 0, SEGURA_MAX), 2),
        "cena": round(_entre(e.get("cena"), 0, 0, CENA_MAX), 2),
        "furacao": round(_entre(e.get("furacao"), 0, 0, FURACAO_MAX), 2),
        "chuva": int(_entre(e.get("chuva"), 0, 0, CHUVA_MAX)),
        "cor": _cor(e.get("cor")),
        "brilho": int(_entre(e.get("brilho"), 0, 0, BRILHO_MAX)),
        # O passo que SO' este avatar dança. "" = a danca padrao, a mesma de
        # quem comentou.
        "danca": _danca(e.get("danca")),
        # Segundos em que a formacao INTEIRA troca pra danca especial e depois
        # volta sozinha. Teto de 120s: e' um momento da live, nao o novo normal.
        "danca_geral": round(_entre(e.get("danca_geral"), 0, 0, 120), 2),
        # Escala do COLOSSO: um gigante que nasce ATRAS da formacao, fora da
        # grade, pra ser visto por cima de todo mundo. 0 = avatar normal.
        # Teto de 40 porque acima disso ele fura o ceu e sai do quadro.
        "colosso": round(_entre(e.get("colosso"), 0, 0, 40), 2),
    }


def _cor(valor):
    """Aceita 'FF2D6F', '#FF2D6F' ou lixo. Lixo vira branco.

    Nome sem cor e' muito melhor que avatar sem nome -- e um hexadecimal torto
    vindo do painel nao pode derrubar o spawn.
    """
    limpo = str(valor or "").strip().lstrip("#").upper()
    if len(limpo) == 6 and all(c in "0123456789ABCDEF" for c in limpo):
        return limpo
    return "FFFFFF"


def _danca(valor):
    """Nome de danca conhecido, ou "" (a danca padrao).

    Nome desconhecido vira "" em vez de descer pro Roblox como esta'. Isso
    importa porque o Roblox NAO reclama de uma animacao que nao existe -- ela
    "carrega", o Play() funciona, e o boneco fica parado em pe' no meio da
    formacao dancando. Um erro de digitacao no painel viraria um avatar
    quebrado sem uma linha de aviso em lugar nenhum; aqui ele vira,
    silenciosamente, um avatar normal.
    """
    nome = str(valor or "").strip().lower()
    return nome if nome in DANCAS_VALIDAS else ""


def bonus_de_combo(total_moedas):
    """Combo maior fura mais a fila.

    Cresce por ORDEM DE GRANDEZA, e nao linear, pra uma rosa combada nao passar
    na frente de um presente caro so' por repeticao: 10 rosas de 1 moeda somam
    10 e ganham +1, enquanto a rosquinha sozinha ja' nasce dois degraus acima.
    """
    try:
        m = int(total_moedas)
    except (TypeError, ValueError):
        return 0
    if m < 10:
        return 0
    if m < 100:
        return 1
    if m < 1000:
        return 2
    if m < 10000:
        return 3
    return 4


def efeito_do_presente(nome, moedas, total_combo=None, presente_id=None):
    """Nome + moedas -> efeito. Tabela de FABRICA (sem painel).

    `moedas` e' o valor UNITARIO, e e' ele que escolhe a faixa. `total_combo` e'
    o valor do combo inteiro e so' mexe na PRIORIDADE.

    A diferenca importa: um combo de 10 rosas de 1 moeda vale 10 moedas no
    total, mas cada rosa continua sendo uma rosa de 1 -- tratar o total como
    valor unitario transformaria dez rosinhas num presente de outra faixa.

    `presente_id` e' aceito e IGNORADO aqui de proposito: a tabela de fabrica
    nao tem ID de presente nenhum (eles mudam, e chutar um numero errado seria
    pior que nao ter). Quem casa por ID e' o catalogo do painel, em painel.py.
    O parametro existe pra assinatura ser a MESMA dos dois lados -- sem isso, o
    dia em que a ponte cair na tabela de reserva ela quebraria com TypeError,
    e quebraria justamente quando o painel esta' fora do ar.
    """
    try:
        m = max(0, int(moedas))
    except (TypeError, ValueError):
        m = 0
    n = str(nome or "").strip().lower()
    extra = bonus_de_combo(m if total_combo is None else total_combo)

    for nomes, minimo, maximo, efeito in REGRAS:
        if nomes is not None and n not in nomes:
            continue
        if m < minimo:
            continue
        if maximo is not None and m > maximo:
            continue
        return limitar(efeito, extra)

    # Presente sem moedas, ou nome vazio, ou lixo: vira comentario em vez de
    # explodir. Nenhum evento torto pode derrubar a live.
    return limitar(COMENTARIO, extra)


def efeito_do_comentario():
    """Quem so' comentou o nick, sem presente nenhum."""
    return limitar(COMENTARIO)


def montar_spawn(tiktok_id, nickname, roblox_id, efeito, moedas=0,
                 nick_roblox="", presente="", tipo="comentario",
                 curtidas=0, combo=0, presente_id=""):
    """O evento exato que o jogo Roblox consome.

    UM EVENTO, DUAS COISAS POSSIVEIS DO OUTRO LADO

    Quem decide se este evento vira um boneco NOVO ou faz CRESCER o boneco que
    a pessoa ja' tem e' o Roblox, e nao a ponte -- porque so' o Roblox sabe
    quem esta' na tela neste instante. A ponte manda os dois numeros (`escala`
    pra nascer, `crescimento` pra somar) e o jogo aplica o que couber.

    Fazer essa escolha AQUI seria impossivel de acertar: a formacao e' apagada
    a cada ciclo, entao "esta pessoa ja' tem avatar" e' uma informacao que muda
    a cada poucos minutos e que a ponte so' saberia com atraso -- e o erro
    apareceria como um presente pago que nao fez nada.
    """
    e = efeito if isinstance(efeito, dict) else {}
    return {
        # Quem e' no TikTok (vira a linha de cima do rotulo).
        "tiktok_id": str(tiktok_id or ""),
        "nickname": str(nickname or "")[:40],
        # O nick do ROBLOX que a pessoa comentou (a segunda linha do rotulo).
        "nick_roblox": str(nick_roblox or "")[:40],
        "roblox_id": int(roblox_id),

        "prio": e.get("prio", 0),
        "escala": e.get("escala", 1.0),
        # Quanto somar no avatar que esta pessoa JA' tem na tela. O jogo usa
        # este numero quando acha o boneco dela, e cai no `escala` quando nao
        # acha (ela ainda nao apareceu, ou o ciclo limpou a formacao).
        "crescimento": e.get("crescimento", 0),
        "vida": e.get("vida", 45),
        "segura": e.get("segura", 0.4),
        "cena": e.get("cena", 0),
        "furacao": e.get("furacao", 0),
        "cor": e.get("cor", "FFFFFF"),
        "brilho": e.get("brilho", 0),
        # O passo deste avatar. Vai pro Roblox como atributo do boneco, e e' o
        # que faz a rosquinha dançar diferente do oculos, que dança diferente
        # da galaxia.
        "danca": e.get("danca", ""),
        "danca_geral": e.get("danca_geral", 0),
        "colosso": e.get("colosso", 0),

        # O NOME do presente que trouxe esta pessoa ("" = veio de comentario ou
        # curtida). Quem usa e' a VOZ: da' pra gravar uma fala so' pra rosquinha
        # e outra so' pra galaxia, em vez de um "chegou alguem" generico.
        "presente": str(presente or "")[:60],
        # O ID NUMERICO do presente no TikTok. Vai junto pro painel poder
        # mostrar "chegou o presente 5655 (Rose)" e voce cadastrar o gatilho
        # pelo ID, que nao muda de regiao pra regiao como o nome muda.
        "presente_id": str(presente_id or "")[:20],
        "moedas": max(0, int(moedas or 0)),

        # O QUE a pessoa fez: comentario | curtida | seguiu | compartilhou |
        # presente. Sem este campo, curtida e comentario chegam identicos
        # (moedas 0, presente "") e os placares separados nao teriam como
        # existir.
        "tipo": str(tipo or "comentario")[:20],

        # Quantas curtidas CRUAS este evento representa. Nao e' sempre 1: a
        # curtida e' o evento mais frequente da live e a ponte junta N antes de
        # spawnar. Mandar 1 faria o placar de curtidas medir SPAWNS, e quem
        # segurou o coracao apareceria com um numero N vezes menor.
        "curtidas": max(0, int(curtidas or 0)),

        # A posicao dentro de um COMBO (x100 rosas = 100 eventos). 0 = o
        # primeiro, ou um presente avulso.
        "combo": max(0, int(combo or 0)),
    }
