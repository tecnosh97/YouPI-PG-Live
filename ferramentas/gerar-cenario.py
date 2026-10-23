# -*- coding: utf-8 -*-
"""Gera o Cenario.model.json: uma PISTA DE DANCA CLARA.

POR QUE UM GERADOR E NAO O JSON NA MAO

O cenario tem umas 400 pecas, e a maioria e' repeticao com um parametro
mudando (os tiles da pista, os degraus, as caneluras das colunas, os refletores
da grade). Escrito na mao, o arquivo tem milhares de linhas em que ninguem acha
nada -- e mudar "a cor da pista" vira procurar e substituir vinte blocos
identicos, com a chance certa de esquecer um. Aqui a cor da pista e' uma linha
na paleta.

O ARQUIVO GERADO E' QUE E' O PRODUTO: o Rojo le' ele, e este script existe pra
poder REGERAR quando for mexer no mapa. Ele fica em ferramentas/ pra viajar
junto com o kit.

    python ferramentas/gerar-cenario.py

═══════════════════════════════════════════════════════════════════
O QUE MUDOU: DE ARENA DE PREMIACAO ESCURA PRA PISTA DE DANCA CLARA
═══════════════════════════════════════════════════════════════════

O mapa anterior era uma arena de premiacao noturna: piso quase preto, paredes
grafite, dourado em tudo. Ele tinha um problema que nao se resolvia com
ajuste fino -- ERA ESCURO. E escuro e' o pior defeito possivel pra ESTA live,
porque a unica coisa que ela vende e' a SKIN de quem comentou. Skin escura em
cenario escuro, num video comprimido de celular, vira uma mancha.

O jogo tambem nao e' uma premiacao: e' gente DANCANDO. O cenario certo pra
isso e' uma pista -- piso quadriculado, caixa de som, globo espelhado, grade de
luz por cima.

Entao aqui esta' a pista, e ela e' CLARA. Tres coisas sustentam isso, e vale
saber qual e' qual antes de mexer:

  1. O PISO E' CLARO E QUADRICULADO. Sao 160 tiles de 10 studs, em duas cores
     quase iguais, com uma fresta escura entre eles. O quadriculado nao e'
     enfeite: ele da' ESCALA -- com ele da' pra ver o tamanho de cada boneco em
     relacao ao chao, e um avatar que cresceu com presente parece maior de
     verdade, em vez de so' parecer mais perto.

  2. AS PAREDES SAO CLARAS E FOSCAS. Um lugar fechado e claro so' funciona se
     as paredes forem foscas: parede clara e BRILHANTE vira um espelho de
     clarao, e e' dai' que vem o "estourou". Aqui o brilho especular esta' onde
     ele pertence -- no piso polido e nos metais.

  3. A LUZ CONTINUA BRANCA E DIRECIONAL. Doze focos brancos, cinco na frente e
     quatro no fundo, e nenhum foco COLORIDO apontado pra galera. Luz colorida
     repinta a roupa de todo mundo: quem chegou de vermelho aparece roxo, e a
     skin que a pessoa veio ver deixa de ser a dela. A cor da festa fica nos
     OBJETOS -- o rosa e o ciano das faixas, o painel do fundo, o globo -- que
     aparecem no quadro sem pintar ninguem.

═══════════════════════════════════════════════════════════════════
CLARO SEM ESTOURAR -- ONDE MORA CADA AJUSTE
═══════════════════════════════════════════════════════════════════

A ARMADILHA E' QUE A PISTA E' UM LUGAR FECHADO. Ela tem `Forro` em y=121,
paredes laterais em x=+-118 e a parede do fundo. Com GlobalShadows ligado, o
sol e a lua NAO ENTRAM: dentro desta caixa, quem manda no nivel de luz e'
`Lighting.Ambient` -- e nao o `Brightness`, nem o `ClockTime`, nem o
`OutdoorAmbient`, que e' onde a gente tenta mexer primeiro e nao acontece nada.

Por isso o ajuste do claro fica repartido em tres lugares:

  Ambient (roblox/default.project.json)   O PISO DE LUZ da pista inteira. Ele
      multiplica a cor propria de cada peca, entao subir ele clareia MUITO os
      avatares (cor clara) e o set claro junto.

  os focos, aqui neste arquivo   a DIRECAO. Sem eles a imagem fica chapada:
      luz que vem de todos os lados ao mesmo tempo tira o volume de tudo. Cada
      avatar precisa de um lado claro e um lado escuro pra se separar do
      vizinho num video comprimido.

  Bloom, Exposicao e Glare (default.project.json)   O FREIO DO CLARAO. E' aqui
      que "claro" vira "estourado" se alguem exagerar. Com o set claro, o
      Threshold do bloom SUBIU (2.2) e a ExposureCompensation ZEROU: qualquer
      coisa acima do threshold vira borrao branco, e um set claro tem area
      demais perto do limite pra brincar com isso.

REGRA PRATICA PRA NAO ESTOURAR: nenhuma cor deste arquivo passa de 232, e
nenhuma superficie GRANDE e' Neon. Neon desenha a propria cor no brilho maximo,
sem cair com a distancia -- uma parede Neon clara e' um clarao garantido. O
Neon aqui esta' em quatro lugares finos: a beirada da pista, os dois frisos do
fundo e as lentes dos refletores.

═══════════════════════════════════════════════════════════════════
E NAO EXISTE UMA LETRA NO MAPA
═══════════════════════════════════════════════════════════════════

A parede antiga escrevia "COMENTE SEU NICK DO ROBLOX" em letra de dois metros.
Texto pedindo interacao dentro do quadro e' o que as plataformas leem como isca
de engajamento -- a live perde alcance e chega a ser derrubada no meio.

Aqui isso e' uma REGRA, e nao um estado: este arquivo nao tem funcao de
escrever texto. Se um dia precisar de chamada, ela vai no OVERLAY DO OBS, fora
do jogo, onde da' pra desligar sem regerar o mapa nem reabrir o Studio.

═══════════════════════════════════════════════════════════════════
AS DUAS MEDIDAS QUE NAO PODEM MUDAR
═══════════════════════════════════════════════════════════════════

  y = 0        o topo dos TILES da pista. E' onde a formacao planta os pes (ver
               Formacao.posicao). Subir um stud deixa cem bonecos flutuando.

  `Telao`      a peca em z=-74, y 18..32. A camera PROCURA ELA PELO NOME em
               tempo de execucao e enquadra a live inteira por ela. O
               `conferir_telao`, no fim deste arquivo, reprova a geracao se ela
               sair do lugar.
"""

import io
import json
import os
import re

# A pasta do kit e' a MAE desta (ferramentas/). Caminho relativo ao
# arquivo, e nao ao diretorio de onde voce chamou: assim o gerador
# funciona do Explorer, do prompt e de dentro de um editor.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "roblox/src/Workspace/Cenario.model.json")
CONFIG = os.path.join(RAIZ, "roblox/src/ReplicatedStorage/Config.luau")


# ═══════════════════════ A PALETA ═══════════════════════
#
# Um lugar so'. Trocar o clima da pista inteira e' mexer aqui.
#
# NENHUMA COR PASSA DE 232, e isso e' o freio do clarao. Com o Ambient alto que
# uma pista clara exige, uma cor em 250 chega no branco puro depois do tonemap
# -- e area branca sem desenho e' exatamente o "estourou". 232 deixa a pele e a
# roupa dos avatares, que sao iluminadas por foco DIRETO, continuarem sendo a
# coisa mais clara do quadro. Que e' o lugar delas.

def rgb(r, g, b):
    return [round(r / 255, 4), round(g / 255, 4), round(b / 255, 4)]


# ── o chao ──
SALAO          = rgb(191, 196, 207)   # o piso do salao em volta do palco
SALAO_CLARO    = rgb(223, 227, 234)   # o topo dos degraus laterais
PALCO          = rgb(170, 176, 190)   # a pedra polida que emoldura a pista
PISTA_A        = rgb(228, 224, 216)   # o tile claro
PISTA_B        = rgb(203, 198, 189)   # o tile um degrau abaixo
PISTA_JUNTA    = rgb(96, 100, 112)    # o rejunte, visto pelas frestas

#[[ O TILE QUE ACENDE, e por que ele e' ESCURO.
#
#   Ele e' Neon, e Neon desenha a cor no brilho maximo sem cair com a
#   distancia. Um lilas claro em Neon acende como BRANCO; este lilas escuro
#   acende como lilas. Mesma regra dos frisos e das lentes la' embaixo, e e' a
#   regra que mais evita clarao neste arquivo. ]]
PISTA_ACESA    = rgb(134, 96, 140)

# ── o set ──
CLARO          = rgb(228, 229, 234)   # a parede clara e FOSCA
CLARO_MEDIO    = rgb(198, 201, 210)   # o segundo plano dela
ESTRUTURA      = rgb(122, 128, 144)   # trelica, moldura, torre: o cinza medio
ESTRUTURA_ESC  = rgb(84, 89, 102)
MADEIRA        = rgb(196, 164, 124)   # o acabamento quente do rodape e da viga

#[[ AS DUAS CORES DA FESTA. Elas moram nos OBJETOS, e nunca na luz.
#
#   Um refletor rosa apontado pra formacao repinta a roupa de cem pessoas -- e
#   a skin que a live existe pra mostrar deixa de ser a da pessoa. Nas pecas,
#   a mesma cor entrega o clima de pista sem tocar em ninguem.
#
#   Cada uma tem uma versao METAL (recebe sombra, escurece onde nao ha' luz,
#   ganha especular) e uma NEON (mais escura, pelo motivo do PISTA_ACESA). ]]
ROSA           = rgb(224, 122, 168)
ROSA_NEON      = rgb(146, 66, 104)
CIANO          = rgb(126, 196, 224)
CIANO_NEON     = rgb(58, 118, 150)

# ── a luz ──
LUZ_QUENTE     = rgb(255, 246, 232)
LUZ_FRIA       = rgb(226, 238, 255)

#[[ A COR DA LENTE NAO E' A COR DA LUZ, E CONFUNDIR AS DUAS ESTOURA A TELA.
#
#   A LUZ pode ser quase branca: ela ilumina, e a claridade dela cai com a
#   distancia. A LENTE e' uma peca Neon -- e Neon desenha a propria cor no
#   brilho maximo, sem cair com nada. Doze lentes de 10x7 studs em 255 sao doze
#   retangulos de branco puro no alto do quadro, e no plano aberto do fim do
#   ciclo, quando a grade inteira entra em cena, elas viram um clarao. ]]
LENTE_QUENTE   = rgb(214, 200, 176)
LENTE_FRIA     = rgb(172, 190, 212)

#[[ O painel aceso do fundo, de baixo (mais claro) pra cima (mais fundo).
#
#   Degrade de VALOR, e ele DESCE: a parte de baixo do painel e' a que fica
#   logo acima das cabecas, e e' ela que separa a silhueta de quem esta' na
#   frente. Ao contrario, o ponto mais escuro cairia justamente onde ele mais
#   atrapalha.
#
#   E ELE E' MAIS ESCURO QUE A PAREDE EM VOLTA, de proposito. Parece invertido
#   -- e' o painel "aceso" -- e nao e': ele e' uma SurfaceGui, e SurfaceGui
#   ignora luz e desenha a cor crua. Num set claro, uma faixa de 148 studs
#   desenhando cor crua clara e' a UNICA coisa do mapa que nao obedece ao
#   Lighting: ela estoura antes de todo o resto. Um degrade lilas medio acende
#   sem competir com a pele de ninguem.
#
#   Isso importa porque silhueta e' o fracasso deste produto: a live inteira
#   existe pra mostrar a SKIN de quem comentou, e skin contra fundo mais claro
#   que ela vira recorte preto. ]]
PAINEL_BAIXO   = rgb(186, 168, 200)
PAINEL_ALTO    = rgb(104, 88, 128)


# ═══════════════════════ Auxiliares ═══════════════════════

def peca(nome, tamanho, pos, cor, material="SmoothPlastic", sombra=False,
         **extra):
    """Uma BasePart ancorada, sem colisao e sem consulta.

    Tudo no cenario e' assim: os avatares nao colidem com nada (eles sao
    plantados na grade), e peca com CanQuery ligado entra em raycast a' toa.
    Cada peca do cenario que participa da fisica e' um custo por quadro pra
    nada -- e com centenas de pecas isso aparece no FPS da gravacao.

    `sombra` E' O UNICO PARAMETRO QUE VOCE PRECISA PENSAR AO ADICIONAR PECA.

    A regra: LIGA nas pecas grandes e estruturais (parede, coluna, degrau,
    portico) e DEIXA DESLIGADO nas tirinhas de acabamento -- fio, friso,
    nervura, canelura -- e nos 160 tiles da pista. Sao eles que sao centenas, e
    a sombra de um tile rente ao chao nao aparece em video nenhum. E' ai' que a
    economia realmente esta'.
    """
    props = {
        "Size": [float(x) for x in tamanho],
        "CFrame": [float(pos[0]), float(pos[1]), float(pos[2]),
                   1.0, 0, 0.0, 0, 1, 0, -0.0, 0, 1.0],
        "Anchored": True,
        "Locked": True,
        "CanCollide": False,
        "CanTouch": False,
        "CanQuery": False,
        "CastShadow": bool(sombra),
        "Material": material,
        "Color": cor,
        "TopSurface": "Smooth",
        "BottomSurface": "Smooth",
    }
    props.update(extra)
    return {"name": nome, "className": "Part", "properties": props}


def pasta(nome, filhos):
    return {"name": nome, "className": "Folder", "children": filhos}


def udim2(sx, sy, ox=0, oy=0):
    return {"UDim2": [[sx, ox], [sy, oy]]}


def mistura(a, b, t):
    """A cor no meio do caminho entre duas. E' o que faz os degrades."""
    return [a[c] + (b[c] - a[c]) * t for c in range(3)]


#[[ NAO EXISTE FUNCAO DE ESCREVER TEXTO NESTE ARQUIVO, E ISSO E' DE PROPOSITO.
#
#   A versao anterior tinha uma `texto()` de sete linhas, e foi por ela que a
#   parede acabou com "COMENTE SEU NICK DO ROBLOX" em letra de dois metros. Nao
#   foi decisao de ninguem: a ferramenta estava ali, e escrever no telao era o
#   caminho mais curto pra "explicar o jogo".
#
#   O problema e' que o quadro da live nao e' lugar de pedir interacao. Texto
#   assim e' lido como isca de engajamento pela plataforma, e o preco vem em
#   alcance -- as vezes com a live derrubada no meio.
#
#   Tirar a FUNCAO, e nao so' o texto, e' o que impede a proxima pessoa (ou o
#   proximo eu) de refazer o mesmo caminho sem perceber. Onde a chamada mora
#   agora: no overlay do OBS, e na sua voz. ]]


# ═══════════════════════ Luz de verdade ═══════════════════════
#
# Neon NAO ilumina: ele desenha a propria cor no brilho maximo e para por ai'.
# Quem ilumina sao estes objetos, e eles exigem o Lighting em tecnologia Future
# (ver roblox/default.project.json).
#
# O NUMERO DE LUZES E' UM ORCAMENTO, E NAO UM GOSTO: cada uma custa por quadro,
# e esta live e' GRAVADA enquanto roda. Doze no total -- uma no painel do
# fundo, cinco na frente, quatro no fundo, duas nas laterais. Todas com Shadows
# desligado: sombra dinamica por luz e' o item mais caro do Future, e a sombra
# que da' volume aqui e' a do sol.


def foco(cor, brilho=1.0, alcance=70, angulo=120, face="Bottom"):
    """Um SpotLight pendurado numa peca. Aponta pra baixo por padrao."""
    return {
        "name": "Foco",
        "className": "SpotLight",
        "properties": {
            "Color": cor,
            "Brightness": float(brilho),
            "Range": float(alcance),
            "Angle": float(angulo),
            "Face": face,
            "Shadows": False,
        },
    }


def luz_de_face(cor, brilho=1.0, alcance=90, angulo=100, face="Back"):
    """Uma SurfaceLight: a face inteira da peca vira fonte de luz.

    E' o que faz o painel do fundo ILUMINAR a galera em vez de so' parecer
    aceso. Um SpotLight no mesmo lugar produziria um circulo de luz no chao; a
    SurfaceLight espalha pela largura da parede, que e' como um painel de LED
    de verdade se comporta.
    """
    return {
        "name": "LuzDaFace",
        "className": "SurfaceLight",
        "properties": {
            "Color": cor,
            "Brightness": float(brilho),
            "Range": float(alcance),
            "Angle": float(angulo),
            "Face": face,
            "Shadows": False,
        },
    }


# ═══════════════════════ 1. A PISTA ═══════════════════════
#
# Tres alturas, e a diferenca entre elas e' o que faz um PALCO existir:
#
#   y = -14.0   o salao. Piso claro e polido, quase sempre fora do quadro.
#   y =  -1.0   o palco. A pedra que emoldura a pista.
#   y =   0.0   os TILES. E' aqui que a formacao pisa.
#
# ═══════════════════════════════════════════════════════════════════
# POR QUE A PISTA E' FEITA DE 160 TILES, E NAO DE UM BLOCO SO'
# ═══════════════════════════════════════════════════════════════════
#
# Porque um bloco so' nao tem ESCALA. Uma placa clara de 100 x 160 studs pode
# ter dez metros ou cem, e o olho nao tem como saber -- e' a mesma razao pela
# qual as almofadas existem na parede de cima. Com o quadriculado, cada tile e'
# uma regua: da' pra ver que um avatar ocupa meio tile e que o de quem mandou
# galaxia ocupa tres. O crescimento por presente, que e' o que a live vende,
# fica VISIVEL em vez de depender da comparacao com o vizinho.
#
# E ele resolve de graca o problema de coplanaridade que um piso desenhado com
# faixas por cima teria: tiles vizinhos se tocam mas NAO se sobrepoem, e faces
# que nao se cruzam nunca brigam (ver `conferir_coplanares`). A "fresta" entre
# eles nao e' desenho nenhum -- e' o rejunte escuro aparecendo por baixo.

NIVEL_SALAO = -14.0
TOPO_PALCO = -1.0

PISTA_LARGURA = 100.0
PISTA_FUNDO = 160.0
PISTA_Z = 25.0          # o centro dela em Z
TILE = 10.0             # o passo da grade
JUNTA = 0.5             # a fresta entre um tile e o vizinho


def pista_de_tiles():
    """Os 160 tiles, mais o rejunte que aparece nas frestas.

    O REJUNTE FICA 0.6 ABAIXO do topo dos tiles, e nao rente. Rente, a face de
    cima dele dividiria o plano y=0 com a face de cima de todos os 160 -- que
    e' a definicao do chao piscando, e em toda a area da pista de uma vez. Com
    o degrau, cada plano fica sozinho na altura dele, e a fresta ganha
    profundidade de verdade.
    """
    itens = []
    meio = TILE / 2

    #[[ O rejunte. Escuro e FOSCO: ele so' precisa aparecer como linha. Em
    #   material polido ele devolveria o teto e a fresta viraria um risco
    #   claro, que e' o contrario do que ela existe pra ser. ]]
    itens.append(peca("Rejunte", (PISTA_LARGURA, 6, PISTA_FUNDO),
                      (0, -3.6, PISTA_Z), PISTA_JUNTA, "Slate",
                      CanCollide=True))

    colunas = int(PISTA_LARGURA / TILE)
    fileiras = int(PISTA_FUNDO / TILE)
    x0 = -PISTA_LARGURA / 2
    z0 = PISTA_Z - PISTA_FUNDO / 2

    for i in range(colunas):
        for j in range(fileiras):
            x = x0 + meio + i * TILE
            z = z0 + meio + j * TILE

            #[[ O XADREZ, em duas cores QUASE IGUAIS.
            #
            #   Xadrez de verdade (claro contra escuro) roubaria o quadro: a
            #   pista ocupa o terco de baixo da tela o tempo todo, e um padrao
            #   forte ali disputa com a formacao. Duas cores separadas por um
            #   degrau de valor bastam pra o olho ler a grade e nao bastam pra
            #   ele PARAR nela. ]]
            cor = PISTA_A if (i + j) % 2 == 0 else PISTA_B
            material = "Marble"
            extra = {"Reflectance": 0.08}

            #[[ Os tiles ACESOS. Sao oito, em duas fileiras ao longo das
            #   laterais, e nao um tabuleiro inteiro piscando.
            #
            #   Oito e' o numero que faz a pista LER como pista sem virar
            #   fonte de luz: 48 tiles acesos (a borda inteira) sao 4.300 studs
            #   quadrados de Neon no terco de baixo do quadro -- o clarao que
            #   este mapa foi refeito pra nao ter. ]]
            if j % 4 == 1 and i in (0, colunas - 1):
                cor = PISTA_ACESA
                material = "Neon"
                extra = {}

            itens.append(peca(f"Tile{i}_{j}", (TILE - JUNTA, 6, TILE - JUNTA),
                              (x, -3, z), cor, material, CanCollide=True,
                              **extra))
    return itens


def chao():
    #[[ ═══════════════ A REGRA DO CHAO PISCANDO ═══════════════
    #
    #   NENHUMA superficie horizontal pode dividir a mesma altura com outra que
    #   esteja embaixo dela. Duas faces coplanares fazem a placa de video
    #   alternar entre as duas a cada quadro, e o chao PISCA -- forte, e mais
    #   ainda quando a camera se move, que e' o tempo inteiro numa live.
    #
    #   A solucao nunca e' um empurraozinho: e' um DEGRAU DE VERDADE. Meio stud
    #   e' pouco pra vista de longe e MUITO pro buffer de profundidade -- que e'
    #   o que importa. O `conferir_coplanares`, no fim deste arquivo, reprova a
    #   geracao se alguem reintroduzir o problema. ]]
    itens = [
        #[[ O SALAO. Piso claro e polido: num set claro ele devolve o teto e as
        #   luzes da grade, e vira granito de saguao em vez de mancha.
        #
        #   Reflectance 0.2 e nao 0.55 como no mapa escuro: reflexo forte num
        #   piso CLARO devolve o ceu inteiro e o chao vira um espelho de clarao.
        #   Reflexo e' um efeito que so' funciona sobre cor escura.
        #
        #   Ele vai muito alem da arena pra a camera do plano aberto nunca pegar
        #   a borda do mundo -- ela recua ate' 120 studs. ]]
        peca("PisoDoSalao", (1600, 12, 1600), (0, NIVEL_SALAO - 6, 100),
             SALAO, "SmoothPlastic", CanCollide=True, Reflectance=0.2),
    ]

    #[[ O PALCO: a pedra que emoldura a pista.
    #
    #   Ele desce ate' o chao do salao em vez de flutuar: a face lateral dele E'
    #   o degrau do palco, e e' ela que da' a leitura de "elevado". ]]
    altura_palco = TOPO_PALCO - NIVEL_SALAO
    itens.append(peca("Palco", (170, altura_palco, 210),
                      (0, NIVEL_SALAO + altura_palco / 2, 30),
                      PALCO, "SmoothPlastic", sombra=True,
                      CanCollide=True, Reflectance=0.15))

    #[[ A PISTA. O TOPO DOS TILES E' O y=0 DO KIT INTEIRO.
    #
    #   E' onde a formacao planta os pes (ver Formacao.posicao e
    #   Avatares.plantar). Esta e' a unica medida do mapa que nao pode mudar --
    #   subir a pista um stud deixa cem bonecos flutuando.
    #
    #   O tamanho vem da FORMACAO, e nao do olho: dez colunas a 6 studs dao 60
    #   de largura, dez fileiras a 8 dao 80 de profundidade, e o colosso nasce
    #   28 studs atras da primeira. 100 x 160 cobre tudo isso com folga pros
    #   presentes grandes, que ocupam mais de um slot. ]]
    itens += pista_de_tiles()

    #[[ O FIO ACESO na beirada da pista -- um dos Neons do mapa.
    #
    #   Ele desenha o contorno do piso de danca, e e' o que impede que a pista
    #   clara e o palco encostem virando duas manchas coladas. Fino de
    #   proposito: faixa grossa vira uma segunda fonte de luz e passa a competir
    #   com o painel do fundo.
    #
    #   AS QUATRO FICAM DO LADO DE FORA DA PISTA, E ISSO NAO E' ESTILO.
    #   Encostada por dentro, a face de fora da faixa dividiria o plano x=-50
    #   com a face dos tiles ao longo de 160 studs -- uma faixa de LUZ piscando
    #   a live inteira. Por fora, a face de dentro da faixa toca a de fora do
    #   tile: faces OPOSTAS no mesmo plano nao brigam, porque uma delas esta'
    #   sempre de costas pra camera. ]]
    for nome, tam, pos, cor in (
            ("FioPistaFrente", (101.6, 1.6, 0.8), (0, -1.2, 105.4), ROSA_NEON),
            ("FioPistaFundo", (101.6, 1.6, 0.8), (0, -1.2, -55.4), CIANO_NEON),
            ("FioPistaEsq", (0.8, 1.6, 160), (-50.4, -1.2, 25), ROSA_NEON),
            ("FioPistaDir", (0.8, 1.6, 160), (50.4, -1.2, 25), CIANO_NEON)):
        itens.append(peca(nome, tam, pos, cor, "Neon"))

    #[[ A BORDA DO PALCO, em metal e NAO em neon.
    #
    #   Ela fecha o palco contra o salao no plano aberto. Em neon viravam 210
    #   studs de risco aceso dos dois lados do quadro, a coisa mais brilhante do
    #   mapa competindo com a formacao. Em metal ela reflete a luz da grade e
    #   escurece onde nao ha' luz, que e' o comportamento de uma moldura. ]]
    for nome, tam, pos in (
            ("BordaPalcoFrente", (171.6, 1.2, 0.8), (0, -1.8, 135.4)),
            ("BordaPalcoEsq", (0.8, 1.2, 210), (-85.4, -1.8, 30)),
            ("BordaPalcoDir", (0.8, 1.2, 210), (85.4, -1.8, 30))):
        itens.append(peca(nome, tam, pos, MADEIRA, "Metal", Reflectance=0.25))
    return pasta("Pista", itens)


# ═══════════════════════ 2. OS DEGRAUS LATERAIS ═══════════════════════
#
# Os degraus que sobem dos dois lados do palco. Nao sao decoracao: sao o que
# transforma "uma pista no meio do nada" em "uma pista DENTRO de um lugar".
#
# Eles sobem do escuro pro claro (de baixo pra cima), e isso e' de proposito: a
# parte de baixo aparece nas bordas do quadro o tempo todo, e uma borda um
# degrau mais escura EMPURRA o olho pro meio, que e' onde a formacao esta'.
#
# O nariz colorido de cada degrau e' o que impede que cinco blocos claros virem
# um bloco claro so'. Em METAL: em neon eram cinco riscos acesos de 200 studs
# de cada lado, e eles sozinhos dominavam o quadro inteiro.

def degraus():
    itens = []
    DEGRAUS = 5
    for lado, sinal, cor_nariz in (("Esq", -1, ROSA), ("Dir", 1, CIANO)):
        for i in range(DEGRAUS):
            largura = 16.0
            #[[ 92 e' o comeco: o palco termina em 85, entao sobra um corredor
            #   de 7 studs entre os dois. O corredor tem funcao -- ele e' a
            #   sombra que separa o palco dos degraus. Encostados, os dois
            #   viram uma peca so' e o palco perde a borda. ]]
            dentro = 92.0 + i * largura
            topo = NIVEL_SALAO + (i + 1) * 5.0
            altura = topo - (NIVEL_SALAO - 12)
            itens.append(peca(
                f"Degrau{lado}{i}", (largura, altura, 200),
                (sinal * (dentro + largura / 2), topo - altura / 2, 20),
                mistura(CLARO_MEDIO, SALAO_CLARO, i / (DEGRAUS - 1)), "Concrete",
                sombra=True))

            #[[ O nariz. Fica EM CIMA do degrau (0.6 acima do topo dele), e nao
            #   embutido: embutido, o topo dos dois disputaria a mesma altura ao
            #   longo de 200 studs. 0.6 e' mais que a folga minima e menos do
            #   que o olho percebe como ressalto. ]]
            itens.append(peca(
                f"NarizDegrau{lado}{i}", (1.4, 0.6, 200),
                (sinal * (dentro + 0.7), topo + 0.3, 20), cor_nariz, "Metal",
                Reflectance=0.2))
    return pasta("Degraus", itens)


# ═══════════════════════ 3. A PAREDE DE LED ═══════════════════════
#
# ═══════════════════════════════════════════════════════════════════
# A PAREDE E' TRES PECAS, E A DO MEIO E' O CONTRATO COM A CAMERA
# ═══════════════════════════════════════════════════════════════════
#
#   PainelInferior y  4..18  (148 x 14)  ATRAS DA GALERA. Parede clara fosca.
#   Telao          y 18..32  (148 x 14)  O PAINEL ACESO. So' esta peca se chama
#                                        "Telao", e e' ela que o
#                                        Camera.client.luau mede e promete
#                                        caber no quadro.
#   PainelSuperior y 32..56  (148 x 24)  O alto, almofadado. Enfeite de plano
#                                        aberto.
#
# A PASTA SE CHAMA `ParedeDeLED`, E O NOME E' CODIGO
#
# O `medirTelao` do Camera.client.luau procura `Cenario > ParedeDeLED > Telao`
# em tempo de execucao pra medir o telao de verdade em vez de confiar nos
# numeros do Config. No mapa anterior esta pasta se chamava `Fundo`, a busca
# nunca achava nada e a camera vivia da reserva -- funcionava por acidente, e
# ia parar de funcionar no dia em que alguem arrastasse a parede no Studio.
#
# POR QUE A FAIXA ACESA MORA NO MEIO
#
# Porque a camera filma NA ALTURA DO PEITO (Config.CAMERA.ALTURA = 1). Com a
# lente a 4 studs do chao e as cabecas da galera a 6, TODA CABECA FICA ACIMA DA
# LINHA DO HORIZONTE -- e tapa o que estiver atras dela e mais baixo. A conta,
# na distancia de trabalho: a cabeca de quem a camera segue sobe uns 7 graus
# acima do centro; a 90 studs de parede, 7 graus sao 11 studs de altura. Tudo
# abaixo de y=15 esta', na pratica, atras de alguem.
#
# O ALTO TAMBEM NAO SERVE: a lente baixa alcanca ate' uns 29 studs de parede
# antes da borda de cima do quadro. Sobra a janela do MEIO -- y 18..32 -- e e'
# por isso que ela e' uma peca separada, com nome proprio.
#
# MEXEU NA ALTURA OU NA POSICAO DO `Telao`? A camera recua junto. O
# `conferir_telao`, no fim deste arquivo, reprova a geracao; e o
# roblox/testes/enquadramento.spec.luau trava os mesmos numeros.
BASE_TELAO = 18.0
ALTURA_TELAO = 14.0
TOPO_TELAO = BASE_TELAO + ALTURA_TELAO      # 32
BASE_PAREDE = 4.0
TOPO_PAREDE = 56.0
Z_PAREDE = -74.0
MEIA_LARGURA_TELAO = 74.0

# Ate' onde a pista fecha por cima e pelos lados. E' o que impede o plano aberto
# do fim de ciclo de mostrar CEU atras de um salao fechado -- ver `casca`.
TOPO_ARENA = 118.0

#[[ ONDE A PISTA FECHA NA FRENTE -- E POR QUE ESTE NUMERO E' 300 E NAO 180.
#
#   A casca tinha teto, fundo e laterais, e NAO tinha frente. Enquanto a lente
#   ficava dentro da caixa isso nao aparecia; o problema comecava quando ela
#   SAIA, porque ai' o quadro deixa de ser "a pista por dentro" e passa a ser
#   "a pista vista de fora", com o vazio do lado de fora em volta dela. O que
#   chegava era: chega um momento e fica de noite.
#
#   O numero, entao, nao e' estetico -- e' o alcance da camera:
#
#     plano aberto      z = profundidade da formacao + CameraRecuo
#     profundidade      72 studs com a formacao de fabrica (10 fileiras x 8)
#     CameraRecuo       85 de fabrica, e o PAINEL deixa subir ate' 200
#
#   72 + 200 = 272, e a casca acabava em 180. Era so' arrastar o recuo no
#   painel pra a lente sair pela frente. Em 300 ela nao sai mais, com 28 studs
#   de sobra. ]]
FRENTE_ARENA = 300.0


def _superficie(nome_peca, filhos, pixels=20):
    """A SurfaceGui de uma peca da parede.

    Ela NAO carrega texto, e nao existe caminho neste arquivo que a faca
    carregar (ver o bloco sobre a funcao `texto`, que foi removida). O que ela
    desenha e' luz: faixas de cor, mais baratas que uma peca por faixa e
    exatamente no plano da parede, sem chance de brigar com ela.
    """
    return {
        "name": nome_peca,
        "className": "SurfaceGui",
        "properties": {
            # A peca esta' em z=-74 sem rotacao, e no Roblox a face "Front"
            # aponta pra -Z. A camera fica do lado +Z: e' a "Back" que ela ve'.
            "Face": "Back",
            # Sem influencia de luz: um painel que escurece quando a luz da
            # pista muda deixa de ser a fonte de contraste que ele existe pra
            # ser.
            "LightInfluence": 0,
            "PixelsPerStud": pixels,
            "SizingMode": "PixelsPerStud",
            "ZIndexBehavior": "Sibling",
        },
        "children": filhos,
    }


def _faixa(nome, y, altura, cor):
    return {
        "name": nome,
        "className": "Frame",
        "properties": {
            "Size": udim2(1, altura),
            "Position": udim2(0, y),
            "BackgroundColor3": cor,
            "BorderSizePixel": 0,
        },
    }


def tela_do_painel():
    #[[ O DEGRADE, EM FAIXAS.
    #
    #   O Roblox tem UIGradient, mas ele nao viaja bem por um .model.json (o
    #   formato de ColorSequence em JSON e' um convite a erro silencioso). Doze
    #   faixas encostadas, vistas dos 90 studs em que esta parede sempre e'
    #   vista, leem como degrade continuo.
    #
    #   As faixas se sobrepoem 1% de proposito: aqui elas sao GUI, e nao pecas,
    #   entao nao existe briga de plano -- e sem a sobra o antialiasing da
    #   escala desenha um fio de fundo entre uma e outra.
    #
    #   TUDO DENTRO DE UM FRAME CHAMADO `Fundo`, e o nome tambem e' codigo: o
    #   `lacoTelao` do Principal.server.luau procura `Tela > Fundo` pra acender
    #   o cartao de chamada de um mapa antigo e apagar a tabela de precos que
    #   ele carregava. Sem o Fundo, aquele laco procura por 30 segundos e
    #   desiste calado. ]]
    faixas = []
    N = 12
    for i in range(N):
        t = i / (N - 1)
        faixas.append(_faixa(f"Faixa{i}", i / N, 1 / N + 0.01,
                             mistura(PAINEL_ALTO, PAINEL_BAIXO, t)))

    #[[ Os dois fios, um em cada ponta. Sem eles o painel aceso encosta direto
    #   na parede clara e a borda some -- e o que da' a esta parede a cara de
    #   "tarja acesa" e' ela ter comeco e fim visiveis. ]]
    faixas.append(_faixa("FioDoTopo", 0.0, 0.03, CIANO))
    faixas.append(_faixa("FioDaBase", 0.97, 0.03, ROSA))

    fundo = {
        "name": "Fundo",
        "className": "Frame",
        "properties": {
            "Size": udim2(1, 1),
            "Position": udim2(0, 0),
            "BackgroundColor3": PAINEL_ALTO,
            "BorderSizePixel": 0,
        },
        "children": faixas,
    }
    return _superficie("Tela", [fundo])


def parede_de_led():
    itens = []

    #[[ A FAIXA ATRAS DAS CABECAS. Parede clara e FOSCA, e o valor dela e' o
    #   ajuste mais delicado do mapa.
    #
    #   Clara demais e os avatares viram silhueta contra ela -- e o jogo existe
    #   pra mostrar a SKIN, entao silhueta e' o fracasso do produto. Escura
    #   demais e o cabelo escuro de metade dos avatares some no fundo.
    #
    #   Num set claro a saida e' o MATERIAL, e nao a cor: em Concrete ela
    #   espalha a luz em vez de devolver, entao fica clara sem virar brilho. Em
    #   material liso e polido, esta parede sozinha seria o clarao do quadro. ]]
    baixo = BASE_TELAO - BASE_PAREDE
    itens.append(peca("PainelInferior", (148, baixo, 4),
                      (0, BASE_PAREDE + baixo / 2, Z_PAREDE),
                      CLARO_MEDIO, "Concrete", sombra=True))

    #[[ O `Telao`. O NOME FICOU, e o nome importa mais que a aparencia: e' por
    #   ele que o Camera.client.luau acha esta peca em tempo de execucao (ver
    #   `medirTelao`) e promete que ela cabe no quadro.
    #
    #   Ele e' um painel de LED sem uma letra, e ACENDE de verdade: a
    #   SurfaceLight joga luz pra frente e desenha a nuca e os ombros de quem
    #   esta' na formacao. E' a luz de contra da pista, e e' o que mais separa a
    #   galera do fundo num video comprimido.
    #
    #   Trocar o nome desta peca quebra o enquadramento da live inteira, e o
    #   `conferir_telao` no fim do arquivo existe pra isso nao passar batido. ]]
    meio = BASE_TELAO + ALTURA_TELAO / 2
    telao = peca("Telao", (MEIA_LARGURA_TELAO * 2, ALTURA_TELAO, 4),
                 (0, meio, Z_PAREDE), PAINEL_BAIXO, "SmoothPlastic")
    telao["children"] = [tela_do_painel(),
                         luz_de_face(LUZ_QUENTE, brilho=0.9, alcance=85,
                                     angulo=120, face="Back")]
    itens.append(telao)

    #[[ O ALTO DA PAREDE, ALMOFADADO.
    #
    #   Era uma placa de 148 x 24 studs, e uma placa desse tamanho nao tem
    #   escala nenhuma: podia ter 20 studs ou 200. Agora e' um caixilho com sete
    #   almofadas rebaixadas, que e' o que uma parede de salao tem -- e o que da'
    #   ao olho uma unidade de medida pra estimar o tamanho do lugar.
    #
    #   A camera de perto nao alcanca esta faixa: ela so' aparece no plano geral
    #   do fim de ciclo, e por 3 segundos. Por isso o desenho e' de longe --
    #   pouca peca, grande, com sombra propria. ]]
    alto = TOPO_PAREDE - TOPO_TELAO
    itens.append(peca("PainelSuperior", (148, alto, 4),
                      (0, TOPO_TELAO + alto / 2, Z_PAREDE), CLARO,
                      "Concrete", sombra=True))
    for i in range(7):
        x = -63 + i * 21
        # A almofada avanca 0.6 na frente da placa (nao 0.2): a folga minima do
        # verificador e' 0.25, e trabalhar rente a ela e' pedir pra o proximo
        # ajuste quebrar.
        itens.append(peca(f"AlmofadaAlta{i}", (17, alto - 7, 4.6),
                          (x, TOPO_TELAO + alto / 2, Z_PAREDE),
                          CLARO_MEDIO, "Concrete"))
        # Os dois fios da almofada -- em cima e embaixo. Com um so' (o de
        # baixo), a almofada terminava sem remate e o alto da parede voltava a
        # ser uma placa. Sao as unicas linhas horizontais deste terco do
        # quadro, e e' por elas que ele deixa de ser um vazio.
        for lado, dy in (("Base", -1), ("Topo", 1)):
            itens.append(peca(
                f"FioAlmofada{lado}{i}", (17.8, 0.7, 4.9),
                (x, TOPO_TELAO + alto / 2 + dy * ((alto - 7) / 2 + 0.35),
                 Z_PAREDE), MADEIRA, "Metal", Reflectance=0.25))

    #[[ A CORNIJA, e por que ela existe.
    #
    #   No video em pe' o terco de CIMA do quadro e' parede -- e ele estava
    #   entregando cor lisa, o que e' o mesmo que entregar nada. A cornija e'
    #   uma faixa quente correndo no alto: uma peca so', que pega a luz da
    #   grade e desenha uma linha horizontal onde antes so' havia vazio.
    #
    #   Ela fica ACIMA das almofadas e ABAIXO da moldura do topo, sem encostar
    #   em nenhuma das duas -- e' remate, e remate que encosta vira emenda.
    #
    #   6.4 de profundidade: ela AVANCA 1.2 stud na frente da moldura, e nao
    #   fica rente. Rente, as duas faces dividiam o plano e o alto da parede
    #   passava a piscar; avancada, ela vira o que uma cornija e' de fato --
    #   uma saliencia que pega luz por cima e faz sombra por baixo. ]]
    itens.append(peca("Cornija", (152, 1.6, 6.4), (0, 54.8, Z_PAREDE),
                      MADEIRA, "Metal", Reflectance=0.3))

    #[[ Os fios que separam as tres pecas -- os outros DOIS neons do mapa.
    #
    #   Sem eles as tres encostam e a parede volta a ser um bloco so' -- e ai' a
    #   janela acesa do meio, que e' a que faz o trabalho, nao se distingue de
    #   nada. Com os fios, o olho le' uma FAIXA ACESA entre duas apagadas, que
    #   e' exatamente o que ela e'. ]]
    for i, (y, cor) in enumerate(((BASE_TELAO, ROSA_NEON),
                                  (TOPO_TELAO, CIANO_NEON))):
        itens.append(peca(f"FrisoDivisor{i}", (150, 0.7, 4.6),
                          (0, y, Z_PAREDE), cor, "Neon"))

    #[[ A moldura da parede: fina, so' pra o fundo ter uma borda.
    #
    #   As laterais TERMINAM ANTES do topo e da base (52 de altura em vez de
    #   58), e nao por estilo: com todas as quatro chegando na mesma altura, o
    #   topo da lateral e o topo da barra de cima disputam o plano y=59 no canto
    #   -- e o canto da moldura pisca. Encaixadas por dentro, cada face de cima
    #   fica sozinha na altura dela. ]]
    itens += [
        # 5.6 de profundidade, e nao 5: com 5 a moldura sobrava 0.2 stud sobre o
        # friso divisor, e 0.2 e' menos que a folga que o verificador exige.
        peca("MolduraTopo", (156, 3, 5.6), (0, 57.5, Z_PAREDE), MADEIRA,
             "Metal", Reflectance=0.2),
        peca("MolduraBase", (156, 3, 5.6), (0, 2.5, Z_PAREDE), ESTRUTURA,
             "Concrete"),
        peca("MolduraEsq", (3, 52, 5.6), (-75.5, 30, Z_PAREDE), MADEIRA,
             "Metal", Reflectance=0.2),
        peca("MolduraDir", (3, 52, 5.6), (75.5, 30, Z_PAREDE), MADEIRA,
             "Metal", Reflectance=0.2),
    ]

    #[[ AS ALAS LATERAIS. Elas fecham o quadro dos dois lados e impedem que a
    #   camera pegue o vazio alem da pista quando a formacao anda pra frente.
    #   Sao ripas verticais com um friso entre cada duas -- a mesma linguagem do
    #   resto, e a mais barata pra entregar "parede de salao". ]]
    for lado, sinal, acento in (("Esq", -1, ROSA), ("Dir", 1, CIANO)):
        itens.append(peca(f"Ala{lado}", (46, 58, 4),
                          (sinal * 101, 30, Z_PAREDE), CLARO_MEDIO, "Concrete",
                          sombra=True))
        for i in range(5):
            # 4.6: sobra 0.3 sobre a ala (era 0.2, menos que a folga minima).
            itens.append(peca(f"RipaAla{lado}{i}", (0.8, 54, 4.6),
                              (sinal * (81 + i * 10.5), 30, Z_PAREDE),
                              ESTRUTURA, "Metal"))
        # O friso vertical de acento, encostado no telao.
        itens.append(peca(f"AcentoLateral{lado}", (1.2, 52, 4.6),
                          (sinal * 77.8, 30, Z_PAREDE), acento, "Metal",
                          Reflectance=0.25))
    return pasta("ParedeDeLED", itens)


# ═══════════════════════ 4. A CASCA ═══════════════════════
#
# O que impede o plano aberto de mostrar CEU.
#
# A parede do fundo tem 56 studs. Na camera de perto isso basta e sobra -- com a
# lente a 4 studs do chao e 40 graus de abertura, o quadro alcanca uns 27 studs
# de parede, entao nem o topo dela aparece.
#
# So' que no fim de cada ciclo a camera RECUA ate' 120 studs pra mostrar a
# multidao inteira, e dali ela ve' quase 90 studs de altura la' no fundo. Tudo
# acima de 56 era ceu azul aberto -- atras de um salao fechado. Era o defeito
# mais caro do mapa em uma imagem so': o momento mais bonito da live, o unico
# plano em que a formacao inteira aparece, terminava com meio quadro de ceu de
# jogo de tiro.
#
# A casca resolve por fechamento: parede alta atras, duas laterais, um forro e a
# frente. Nenhuma delas aparece na camera de perto -- todas moram acima ou fora
# do que a lente de trabalho alcanca -- e todas aparecem no plano aberto, que e'
# o unico lugar onde elas precisam existir.

def casca():
    itens = []

    #[[ A continuacao da parede do fundo, ate' o forro.
    #
    #   Ela recua 2 studs (z -76 e nao -74): a face da frente dela dividiria o
    #   plano z=-72 com a face das alas laterais ao longo dos 3 studs em que as
    #   duas se cruzam em altura. Recuada, ela le' como o que e' -- a parte de
    #   cima da parede, um plano atras do acabamento. ]]
    alto = TOPO_ARENA - TOPO_PAREDE
    itens.append(peca("ParedeAlta", (240, alto, 6),
                      (0, TOPO_PAREDE + alto / 2, Z_PAREDE - 2),
                      CLARO_MEDIO, "Concrete", sombra=True))

    #[[ As laterais. Em +-118 elas ficam FORA do que a lente enxerga de perto
    #   (a 14 studs do alvo, 40 graus abrem uns 20 studs de largura) e DENTRO do
    #   que o plano aberto enxerga -- que e' exatamente o efeito procurado:
    #   invisiveis o tempo todo, presentes no momento em que a pista precisa ter
    #   paredes. ]]
    for lado, sinal in (("Esq", -1), ("Dir", 1)):
        #[[ 136 de altura, e nao 132: com 132 o topo dela ficava exatamente em
        #   y=118, a mesma altura do topo da parede do fundo, e os dois planos
        #   brigavam na quina. Passando 4 studs alem, ela entra no forro -- que
        #   e' como uma parede encontra um teto de verdade.
        #
        #   Ela vai de z=-140 ate' a FRENTE_ARENA: a lateral e' o que fecha o
        #   corredor pelos lados ao longo de todo o alcance da lente. ]]
        itens.append(peca(f"ParedeLateral{lado}", (6, 136, 440),
                          (sinal * 118, NIVEL_SALAO + 68, 80),
                          CLARO_MEDIO, "Concrete", sombra=True))
        # As pilastras da parede lateral: sem elas sao 440 studs de placa lisa.
        for i in range(11):
            itens.append(peca(f"PilastraLateral{lado}{i}", (2.4, 126, 8),
                              (sinal * 114.5, NIVEL_SALAO + 66, -110 + i * 40),
                              CLARO, "Concrete"))

    #[[ O FORRO. Claro e alto, ele fecha o volume por cima.
    #
    #   Fica ACIMA da grade de luz (que vive em y 74..84) pra a trelica
    #   continuar lendo como trelica pendurada, e nao como desenho colado no
    #   teto.
    #
    #   Ele avanca 6 studs ALEM da parede da frente, e isso e' obrigatorio, nao
    #   acabamento: terminando os dois no mesmo z, o forro e a parede dividiriam
    #   a face da frente numa area de 248 x 4 studs -- z-fighting garantido, e o
    #   `conferir_coplanares` reprova a geracao. ]]
    itens.append(peca("Forro", (250, 6, 457), (0, TOPO_ARENA + 3, 83.5),
                      CLARO_MEDIO, "Concrete", sombra=True))

    #[[ A PAREDE DA FRENTE -- a peca que faz disto um LUGAR FECHADO.
    #
    #   Nenhum plano da live olha pra ca' (a lente aponta sempre pro -Z, pro
    #   palco), entao esta peca nunca entra no quadro -- e mesmo assim ela e' o
    #   conserto do "chega um momento e fica de noite": com o recuo alto a lente
    #   saia pela frente da pista, e dali o quadro passava a mostrar a pista por
    #   FORA, com o vazio em volta. Fechada a frente, nao existe mais lado de
    #   fora pra ela alcancar.
    #
    #   248 de largura, e nao 250: em 250 ela dividiria as faces laterais com o
    #   forro (os dois em x=+-125) ao longo dos 4 studs em que se cruzam em
    #   altura. ]]
    itens.append(peca("ParedeFrente", (248, 136, 6),
                      (0, NIVEL_SALAO + 68, FRENTE_ARENA + 3),
                      CLARO_MEDIO, "Concrete", sombra=True))
    return pasta("Casca", itens)


# ═══════════════════════ 5. O PORTICO ═══════════════════════
#
# O portico que emoldura a pista -- a peca que mais diz "palco" no mapa inteiro,
# e uma das mais baratas.
#
# ELE E' DIMENSIONADO PRA NAO ENCOSTAR NO QUADRO UTIL, e isso e' o contrario de
# um detalhe. As colunas ficam em x = +-84, FORA dos +-74 do telao; a viga fica
# acima dos 32 do telao. Ou seja: a camera de perto -- que e' onde a live vive
# -- nunca ve' o portico tapar nada. Ele existe pro plano aberto do fim de
# ciclo, e e' la' que ele entrega o "uau".
#
# Uma coluna a 70 studs, ou uma viga a 30, apareceria cortando a faixa acesa em
# todos os enquadramentos de perto -- e o `enquadramento.spec.luau` nao pegaria
# isso, porque ele confere geometria de camera, e nao o que esta' na frente.

def portico():
    itens = []
    for lado, sinal, acento in (("Esq", -1, ROSA), ("Dir", 1, CIANO)):
        itens.append(peca(f"ColunaPortico{lado}", (10, 66, 10),
                          (sinal * 84, 33, -66), CLARO, "Concrete", sombra=True))
        #[[ AS CANELURAS. Sao o que separa "coluna" de "bloco em pe'".
        #
        #   Quatro sulcos verticais na face virada pra camera. Custam quatro
        #   pecas por coluna e resolvem sozinhas o problema de uma superficie de
        #   10 x 66 studs nao ter nada em que o olho se apoie. ]]
        for i in range(4):
            itens.append(peca(f"CaneluraPortico{lado}{i}", (0.7, 60, 10.6),
                              (sinal * 84 + (i - 1.5) * 2.2, 33, -66),
                              ESTRUTURA, "Metal"))
        # O fio de acento na aresta de dentro, virado pra pista.
        itens.append(peca(f"FioPortico{lado}", (1.2, 62, 10.6),
                          (sinal * 78.4, 33, -66), acento, "Metal",
                          Reflectance=0.25))
        #[[ O capitel ENVOLVE o topo da coluna (64..68 contra a coluna que
        #   termina em 66) em vez de sentar em cima dele. Sentado, o topo dos
        #   dois ficaria na mesma altura e o canto do portico piscaria -- e o
        #   canto do portico e' o que o plano aberto mais enquadra. ]]
        itens.append(peca(f"CapitelPortico{lado}", (14, 4, 14),
                          (sinal * 84, 66, -66), MADEIRA, "Metal", sombra=True,
                          Reflectance=0.2))

    # A viga apoia EXATAMENTE no topo do capitel (68): faces opostas se
    # tocando, que e' construcao normal e nunca briga.
    itens.append(peca("VigaPortico", (190, 8, 10), (0, 72, -66),
                      CLARO, "Concrete", sombra=True))
    #[[ O fio atravessa a FACE da viga, e nao a barriga dela. Por baixo, o topo
    #   do fio dividiria altura com o topo do capitel; e ninguem ve' a barriga
    #   de uma viga a 70 studs de altura, entao era acabamento gasto.
    #
    #   189 e nao 190: com a mesma largura da viga, as duas pontas dividiriam o
    #   plano x=+-95 ao longo dos 10 studs de profundidade. ]]
    itens.append(peca("FioVigaPortico", (189, 1.2, 10.6), (0, 72, -66),
                      MADEIRA, "Metal", Reflectance=0.3))
    return pasta("Portico", itens)


# ═══════════════════════ 6. A GRADE DE LUZ ═══════════════════════
#
# Trelica de palco com SOFTBOX BRANCO, e nao refletor colorido varrendo a pista.
#
# E' a decisao mais contra-intuitiva do mapa, e a mais importante: uma pista de
# verdade tem luz colorida, e aqui isso seria um erro de produto. O jogo inteiro
# existe pra mostrar a SKIN das pessoas, e luz colorida repinta a roupa de todo
# mundo -- quem chegou de vermelho aparece roxo, e a skin que a pessoa veio ver
# deixa de ser a dela.
#
# Softbox branco faz o oposto: entrega a cor real de cada avatar. A cor da festa
# fica nos OBJETOS (o rosa e o ciano das faixas, o painel do fundo, o globo
# espelhado), que aparecem no quadro sem pintar ninguem.
#
# Sao doze fontes: cinco quentes na frente, quatro frias no fundo, duas de
# preenchimento nas laterais e uma no painel do fundo. E' a receita de luz de
# tres pontos, repetida ao longo da pista.

def grade_de_luz():
    itens = []

    # As quatro torres e as vigas.
    for nome, x, z in (("EsqFundo", -96, -50), ("EsqFrente", -96, 82),
                       ("DirFundo", 96, -50), ("DirFrente", 96, 82)):
        itens.append({
            "name": f"Torre{nome}",
            "className": "TrussPart",
            "properties": {
                "Size": [2.0, 88.0, 2.0],
                "CFrame": [float(x), 30.0, float(z),
                           1.0, 0, 0.0, 0, 1, 0, -0.0, 0, 1.0],
                "Anchored": True, "Locked": True, "CanCollide": False,
                "CanTouch": False, "CanQuery": False, "CastShadow": False,
                "Color": ESTRUTURA,
            },
        })
    #[[ As vigas LATERAIS correm 1 stud abaixo das transversais.
    #
    #   Numa grade de trelica de verdade e' assim mesmo (uma direcao apoia na
    #   outra), e aqui isso resolve de quebra o canto piscando: com as quatro na
    #   mesma altura, os topos se cruzam no mesmo plano nos quatro cantos. ]]
    itens += [
        peca("VigaFundo", (192, 3, 3), (0, 82.5, -50), ESTRUTURA, "Metal"),
        peca("VigaFrente", (192, 3, 3), (0, 82.5, 82), ESTRUTURA, "Metal"),
        peca("VigaEsq", (3, 3, 132), (-96, 81.5, 16), ESTRUTURA, "Metal"),
        peca("VigaDir", (3, 3, 132), (96, 81.5, 16), ESTRUTURA, "Metal"),
    ]

    #[[ OS SOFTBOX.
    #
    #   Caixa cinza + face branca grande e fosca. O "grande e fosco" e' o que
    #   define um softbox: fonte larga faz sombra suave, e sombra suave e' o que
    #   deixa um rosto legivel na compressao do TikTok.
    #
    #   A face Neon e' o OBJETO aceso no quadro; quem ilumina de verdade e' o
    #   SpotLight pendurado nela. Sao coisas separadas de proposito -- so' os
    #   cinco do meio ganham foco, porque doze luzes e' o orcamento por quadro
    #   desta live. ]]
    for i in range(7):
        x = -78 + i * 26
        itens.append(peca(f"SoftboxFrente{i}", (11, 3, 8), (x, 78, 82),
                          ESTRUTURA))
        lente = peca(f"LuzFrente{i}", (10, 0.6, 7), (x, 76.3, 82),
                     LENTE_QUENTE, "Neon")
        if 1 <= i <= 5:
            lente["children"] = [foco(LUZ_QUENTE, brilho=1.7, alcance=180,
                                      angulo=110)]
        itens.append(lente)
    for i in range(5):
        x = -70 + i * 35
        itens.append(peca(f"SoftboxFundo{i}", (11, 3, 8), (x, 78, -50),
                          ESTRUTURA))
        lente = peca(f"LuzFundo{i}", (10, 0.6, 7), (x, 76.3, -50),
                     LENTE_FRIA, "Neon")
        if 0 <= i <= 3:
            lente["children"] = [foco(LUZ_FRIA, brilho=1.25, alcance=165,
                                      angulo=100)]
        itens.append(lente)

    #[[ OS REFLETORES DAS VIGAS LATERAIS.
    #
    #   Sao OBJETO de quadro, e nao iluminacao: uma grade so' de softbox branco
    #   le' como estudio, e o que este mapa precisa dizer e' PISTA. Ficam nas
    #   laterais, fora da coluna central que o 9:16 aproveita, entao entregam o
    #   clima sem disputar espaco com ninguem.
    #
    #   Os DOIS do meio de cada lado ganham um foco de preenchimento, apontado
    #   pra baixo: e' o que tira a sombra dura do lado do rosto de quem esta'
    #   nas pontas da formacao. ]]
    for lado, sinal, cor in (("Esq", -1, ROSA_NEON), ("Dir", 1, CIANO_NEON)):
        for i in range(6):
            z = -34 + i * 24
            itens.append(peca(f"Refletor{lado}{i}", (5, 5, 5),
                              (sinal * 96, 77, z), ESTRUTURA))
            lente = peca(f"LenteRefletor{lado}{i}", (4, 0.8, 4),
                         (sinal * 96, 74.2, z), cor, "Neon")
            if i == 3:
                lente["children"] = [foco(LUZ_QUENTE, brilho=0.9, alcance=150,
                                          angulo=120)]
            itens.append(lente)

    #[[ O GLOBO ESPELHADO. Uma peca, e ela sozinha diz "pista de danca".
    #
    #   Fica no eixo do palco, alto o bastante pra so' aparecer no plano aberto
    #   e nos closes de quem esta' na frente -- e nunca entre a lente e um
    #   avatar. E' Metal com Reflectance alta em vez de Neon: um globo Neon nao
    #   e' um globo, e' uma bola branca. Espelhado, ele devolve o rosa e o
    #   ciano das laterais e o painel do fundo -- ou seja, ele mostra a festa em
    #   vez de acender junto.
    #
    #   A haste existe pra ele nao parecer flutuando. Ela nasce NO forro da
    #   viga e termina antes do topo do globo, encostando sem sobrepor. ]]
    itens.append(peca("HasteDoGlobo", (0.8, 10, 0.8), (0, 76, 16),
                      ESTRUTURA, "Metal"))
    itens.append({
        "name": "GloboEspelhado",
        "className": "Part",
        "properties": {
            "Shape": "Ball",
            "Size": [9.0, 9.0, 9.0],
            "CFrame": [0.0, 66.5, 16.0, 1.0, 0, 0.0, 0, 1, 0, -0.0, 0, 1.0],
            "Anchored": True, "Locked": True, "CanCollide": False,
            "CanTouch": False, "CanQuery": False, "CastShadow": True,
            "Material": "Metal",
            "Color": CLARO,
            "Reflectance": 0.75,
        },
    })
    return pasta("Luzes", itens)


# ═══════════════════════ 7. O SOM ═══════════════════════
#
# O que enche as laterais e o fundo do quadro sem competir com a formacao.
#
# Duas coisas so', e as duas trabalham: as COLUNAS dao altura e ritmo ao
# corredor entre o palco e os degraus, e as CAIXAS DE SOM dizem, sem uma
# palavra, que tipo de lugar e' este. Elas substituem os trofeus da arena de
# premiacao -- mesma funcao no quadro, outro assunto.
#
# As caixas ficam ATRAS da formacao (z = -52), e isso e' calculado: qualquer
# objeto alto entre a galera e a camera entraria na frente de alguem no close --
# que e' justamente o plano que a pessoa que acabou de comentar recebe.

def som_e_colunas():
    itens = []
    for lado, sinal, acento in (("Esq", -1, ROSA), ("Dir", 1, CIANO)):
        #[[ As colunas do corredor. Ficam nos 7 studs entre o palco (termina em
        #   85) e os degraus (comecam em 92).
        #
        #   x = +-89, e nao +-85: a coluna precisa comecar DEPOIS da borda do
        #   palco (que vai ate' 85.8). Encostada nela, a face de dentro dividia
        #   o plano com a face do palco ao longo de 60 studs de altura. ]]
        for i, z in enumerate((-40, 0, 40, 80)):
            itens.append(peca(f"Coluna{lado}{i}", (5, 60, 7),
                              (sinal * 89, NIVEL_SALAO + 30, z),
                              CLARO, "Concrete", sombra=True))
            #[[ O fio de acento na face virada pro palco. Ele SOBRESSAI 0.4 da
            #   coluna: rente, as duas faces ficariam no mesmo plano.
            #
            #   E comeca em y=2, acima do fio da beirada da pista: os dois
            #   seriam acesos, e dois acesos que se cruzam no mesmo plano e' o
            #   defeito mais visivel que este mapa pode ter. ]]
            itens.append(peca(f"FioColuna{lado}{i}", (1.2, 42, 5),
                              (sinal * 86.5, 23, z), acento, "Metal",
                              Reflectance=0.25))
            #[[ O remate ENVOLVE o topo da coluna em vez de sentar nele --
            #   mesma razao do capitel do portico. ]]
            itens.append(peca(f"RemateColuna{lado}{i}", (9, 4, 11),
                              (sinal * 89, NIVEL_SALAO + 60, z),
                              MADEIRA, "Metal", Reflectance=0.2))

        #[[ A CAIXA DE SOM. Tres modulos empilhados, do maior pro menor.
        #
        #   O topo dela fica em y=18: exatamente a base da faixa acesa do fundo.
        #   Assim as duas EMOLDURAM o painel em vez de cortarem ele -- e no
        #   plano aberto a leitura e' de um palco visto de frente, que e' o que
        #   este mapa inteiro persegue.
        #
        #   Empilhada com as faces se TOCANDO (um modulo comeca onde o outro
        #   termina). Faces opostas encostadas nao brigam; sobrepostas, sim.
        #
        #   Os cones sao pecas separadas e mais escuras, e sao eles que fazem a
        #   caixa parecer uma caixa em vez de tres blocos: sem eles, isto aqui
        #   e' um pedestal. ]]
        base_x = sinal * 64
        itens.append(peca(f"CaixaBase{lado}", (12, 8, 12), (base_x, 2, -52),
                          ESTRUTURA_ESC, "Metal", sombra=True))
        for i, (dy, altura, largura) in enumerate(((10.5, 5.0, 11.0),
                                                   (15.0, 4.0, 9.5),
                                                   (18.2, 2.4, 8.0))):
            itens.append(peca(f"CaixaSom{lado}{i}",
                              (largura, altura, largura * 0.9),
                              (base_x, dy, -52), ESTRUTURA, "Metal",
                              sombra=True, Reflectance=0.1))
            # O cone, na face virada pra camera. 0.4 na frente da caixa: rente,
            # as duas faces dividiriam o mesmo plano.
            itens.append(peca(f"ConeSom{lado}{i}",
                              (largura * 0.6, altura * 0.55, 0.6),
                              (base_x, dy, -52 + largura * 0.45 + 0.3),
                              ESTRUTURA_ESC, "Fabric"))
        # O friso de acento que separa a base dos modulos.
        itens.append(peca(f"FrisoCaixa{lado}", (13, 0.8, 13),
                          (base_x, 6.4, -52), acento, "Metal",
                          Reflectance=0.25))
    return pasta("Som", itens)


# ═══════════════════════ Montagem ═══════════════════════

# ═══════════════════ A CONFERENCIA DO CHAO PISCANDO ═══════════════════
#
# Duas superficies na MESMA altura, uma sobre a area da outra, fazem a placa de
# video alternar entre elas a cada quadro. O chao PISCA -- e pisca mais quanto
# mais a camera se mexe, que numa live e' o tempo inteiro.
#
# O defeito e' facil de reintroduzir (basta encostar uma peca nova no palco) e
# IMPOSSIVEL de ver no JSON: os numeros parecem certos, e o sintoma so' aparece
# com o jogo rodando. Por isso a geracao FALHA aqui em vez de avisar -- um mapa
# que pisca nao deve chegar ao arquivo.
FOLGA_MINIMA = 0.25


def _caixa(peca_json):
    p = peca_json["properties"]
    x, y, z = p["CFrame"][0], p["CFrame"][1], p["CFrame"][2]
    sx, sy, sz = p["Size"]
    return {
        "nome": peca_json["name"],
        "x0": x - sx / 2, "x1": x + sx / 2,
        "y0": y - sy / 2, "y1": y + sy / 2,
        "z0": z - sz / 2, "z1": z + sz / 2,
    }


#[[ AS FACES QUE A CAMERA CHEGA A VER, e os dois eixos em que duas delas
#   precisam se cruzar pra brigarem de verdade.
#
#   `y0` (a face de BAIXO) esta' fora de proposito: a camera desta live vive
#   acima do palco olhando pra baixo, entao a barriga de uma peca nunca chega ao
#   quadro. Incluir y0 so' encheria o relatorio de briga que ninguem ve' -- e um
#   verificador que reprova o que esta' certo e' um verificador que a proxima
#   pessoa desliga. ]]
FACES_VISIVEIS = (
    ("x0", "y", "z"), ("x1", "y", "z"),
    ("y1", "x", "z"),
    ("z0", "x", "y"), ("z1", "x", "y"),
)


def conferir_coplanares(mapa):
    #[[ ANTES ESTA FUNCAO SO' OLHAVA O TOPO DAS PECAS.
    #
    #   Ela nasceu pra resolver "o chao pisca", que e' briga de face
    #   HORIZONTAL, e por isso comparava so' `cima` contra `cima`. O problema e'
    #   que z-fighting nao tem nada de especial com a horizontal: duas faces
    #   VERTICAIS no mesmo plano brigam igual, e essas passavam inteiras.
    #
    #   Agora sao as cinco faces que aparecem no quadro. So' conta como briga
    #   quando as duas faces olham pro MESMO lado (`x0` contra `x0`, e nao
    #   contra `x1`): faces opostas encostadas sao construcao normal -- uma peca
    #   em cima da outra, uma faixa encostada por fora -- e a de tras nunca e'
    #   desenhada.
    #
    #   Os 160 tiles da pista passam por aqui SEM briga nenhuma, e vale saber
    #   por que: eles dividem a altura y=0 entre si, mas nao se sobrepoem em x
    #   nem em z -- e faces que nao se cruzam nunca disputam pixel. ]]
    todas = [_caixa(p) for grupo in mapa["children"] for p in grupo["children"]
             if "CFrame" in p["properties"] and "Size" in p["properties"]]

    brigas = []
    for i, a in enumerate(todas):
        for b in todas[i + 1:]:
            for face, u, v in FACES_VISIVEIS:
                # Sem cruzamento nos outros dois eixos as faces nem se olham.
                # `<=` e nao `<`: peca ENCOSTADA na outra tem cruzamento zero, e
                # isso e' o contrario de briga -- e' a montagem certa.
                if a[u + "1"] <= b[u + "0"] or b[u + "1"] <= a[u + "0"]:
                    continue
                if a[v + "1"] <= b[v + "0"] or b[v + "1"] <= a[v + "0"]:
                    continue
                d = abs(a[face] - b[face])
                if d >= FOLGA_MINIMA:
                    continue
                cruz_u = min(a[u + "1"], b[u + "1"]) - max(a[u + "0"], b[u + "0"])
                cruz_v = min(a[v + "1"], b[v + "1"]) - max(a[v + "0"], b[v + "0"])
                brigas.append(
                    f"{a['nome']} e {b['nome']}: a face {face} dos dois em "
                    f"{a[face]:.2f} (diferenca {d:.3f}), brigando numa area de "
                    f"{cruz_u:.1f} x {cruz_v:.1f} studs")
    return brigas


# ═══════════════ A CONFERENCIA DO CONTRATO COM A CAMERA ═══════════════
#
# O Camera.client.luau procura, em tempo de execucao, uma peca chamada `Telao`
# dentro do Cenario, e usa as medidas DELA pra decidir o enquadramento de toda a
# live. O Config.luau guarda os mesmos numeros como reserva, e o
# roblox/testes/enquadramento.spec.luau trava eles num teste.
#
# Ou seja: sao TRES lugares que precisam concordar, e dois deles nao levantam
# erro nenhum quando discordam. O sintoma de uma discordancia e' a camera
# recuando demais (ou de menos) pra caber uma parede que nao esta' mais ali --
# um enquadramento errado a live inteira, sem uma linha no Output.
#
# Ja' aconteceu: o Config passou meses dizendo Y 4..21 com o mapa em Y 18..32.
# Onze studs de erro numa reserva que ninguem exercita e' invisivel ate' o dia
# em que ela e' a unica coisa que resta.
#
# Por isso a geracao FALHA aqui. Mexeu no telao? Mexa nos tres, ou nao mexa.

def conferir_telao(mapa):
    achadas = [p for grupo in mapa["children"] for p in grupo["children"]
               if p["name"] == "Telao"]
    if len(achadas) != 1:
        return [f"o mapa tem {len(achadas)} pecas chamadas 'Telao', e precisa "
                f"ter exatamente 1 -- a camera procura ela pelo nome"]

    p = achadas[0]["properties"]
    z, meia_largura = p["CFrame"][2], p["Size"][0] / 2
    base = p["CFrame"][1] - p["Size"][1] / 2
    topo = p["CFrame"][1] + p["Size"][1] / 2

    try:
        with io.open(CONFIG, encoding="utf-8") as f:
            bloco = f.read().split("TELAO = {", 1)[1].split("}", 1)[0]
    except (OSError, IndexError):
        return ["nao achei o bloco TELAO no Config.luau -- sem ele nao da' pra "
                "conferir se a camera e o mapa concordam"]

    esperado = {"Z": z, "TOPO": topo, "BASE": base,
                "MEIA_LARGURA": meia_largura}
    problemas = []
    for chave, valor in esperado.items():
        achado = re.search(rf"\b{chave}\s*=\s*(-?[\d.]+)", bloco)
        if not achado:
            problemas.append(f"o Config.luau nao declara TELAO.{chave}")
            continue
        if abs(float(achado.group(1)) - valor) > 0.001:
            problemas.append(
                f"TELAO.{chave}: o mapa diz {valor:g} e o Config.luau diz "
                f"{achado.group(1)} -- a camera vai enquadrar o lugar errado")
    return problemas


#[[ ═══════════ A CONFERENCIA DO CHAO DA FORMACAO ═══════════
#
#   A formacao planta os pes em y=0 (ver Formacao.posicao e Avatares.plantar), e
#   isso so' funciona se existir chao EM y=0 debaixo dela. Com a pista virando
#   um tabuleiro de 160 tiles, ficou facil demais mexer no tamanho do tile, na
#   junta ou no centro e deixar um pedaco da grade sem piso -- e o sintoma
#   disso e' uma fileira inteira de bonecos flutuando, que ninguem liga a uma
#   mudanca no gerador do cenario.
#
#   A area que precisa ter piso sai da propria formacao:
#
#     x   as colunas vao de -(N-1)/2 a +(N-1)/2 vezes ESPACO_X -- com os 10 por
#         fileira de fabrica, +-27 studs. Mais meio corpo de um avatar de
#         escala 6 nas pontas: +-44.
#     z   o colosso nasce em -ESPACO_Z * 3.5 = -28, e dez fileiras a 8 studs
#         chegam a +72. Com folga: de -30 a +86.
#
#   Confere so' isso, e nao a pista inteira -- sobrar piso e' inofensivo. ]]
def conferir_chao_da_formacao(mapa):
    precisa_x, precisa_z0, precisa_z1 = 44.0, -30.0, 86.0

    topos = [_caixa(p) for grupo in mapa["children"] for p in grupo["children"]
             if p["name"].startswith("Tile")
             and abs(p["properties"]["CFrame"][1] + p["properties"]["Size"][1] / 2) < 0.001]
    if not topos:
        return ["nenhum tile da pista tem o topo em y=0 -- a formacao inteira "
                "vai nascer flutuando"]

    x0 = min(t["x0"] for t in topos)
    x1 = max(t["x1"] for t in topos)
    z0 = min(t["z0"] for t in topos)
    z1 = max(t["z1"] for t in topos)

    problemas = []
    if x0 > -precisa_x or x1 < precisa_x:
        problemas.append(
            f"a pista vai de x={x0:g} a x={x1:g} e a formacao precisa de "
            f"+-{precisa_x:g} -- as pontas das fileiras ficam sem chao")
    if z0 > precisa_z0 or z1 < precisa_z1:
        problemas.append(
            f"a pista vai de z={z0:g} a z={z1:g} e a formacao precisa de "
            f"{precisa_z0:g} a {precisa_z1:g} -- fileira sem chao")
    return problemas


def contar_luzes(mapa):
    """Quantas fontes de luz o mapa acende. E' orcamento, e aparece no relato.

    Cada luz custa por quadro, e esta live e' gravada enquanto roda. Ter o
    numero impresso a cada geracao e' o que impede ele de subir de doze pra
    trinta sem ninguem notar -- que e' como um mapa bonito vira um mapa que
    engasga na gravacao.
    """
    acesas = ("PointLight", "SpotLight", "SurfaceLight")
    total = 0
    for grupo in mapa["children"]:
        for p in grupo["children"]:
            for filho in p.get("children") or []:
                if filho.get("className") in acesas:
                    total += 1
    return total


def main():
    mapa = {
        "className": "Folder",
        "children": [
            chao(),
            degraus(),
            parede_de_led(),
            casca(),
            portico(),
            grade_de_luz(),
            som_e_colunas(),
        ],
    }

    reprovas = (conferir_coplanares(mapa)
                + conferir_telao(mapa)
                + conferir_chao_da_formacao(mapa))
    if reprovas:
        print("O MAPA NAO PASSOU NA CONFERENCIA (nao gravei o arquivo):")
        for r in reprovas:
            print("  " + r)
        raise SystemExit(1)

    with io.open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(mapa, f, ensure_ascii=False, indent=2)
        f.write("\n")

    total = sum(len(p["children"]) for p in mapa["children"])
    sombras = sum(1 for g in mapa["children"] for p in g["children"]
                  if p["properties"].get("CastShadow"))
    print(f"cenario gerado: {len(mapa['children'])} grupos, {total} pecas")
    for p in mapa["children"]:
        print(f"  {p['name']:<14} {len(p['children'])} pecas")
    print(f"{contar_luzes(mapa)} fontes de luz, {sombras} pecas fazendo sombra")
    print("nenhuma face coplanar nas 5 faces visiveis -- nada vai piscar")
    print("o Telao esta' onde a camera e o Config.luau esperam")
    print("a pista cobre toda a area onde a formacao planta os pes")
    print("nenhum texto no mapa -- a chamada vive no overlay do OBS")


main()
