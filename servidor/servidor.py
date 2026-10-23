"""Servidor local da live — o meio de campo entre o TikTok e o Roblox.

POR QUE ELE EXISTE
------------------
O Roblox nao fala WebSocket, e o HttpService so faz requisicao de SAIDA. O
jogo nao tem como ser AVISADO de que alguem comentou: ele precisa PERGUNTAR.
Este servidor e' quem guarda a resposta dessa pergunta.

    ponte.py  --POST /eventos-->  [ fila ]  <--GET /eventos--  Roblox Studio

A fila e' um anel com cursor: cada resposta diz ate' onde o jogo ja' leu, e a
pergunta seguinte continua dali. Um servidor de jogo que sobe no meio da live
se ancora no fim da fila em vez de receber o historico inteiro de uma vez --
senao a primeira coisa que ele faria era spawnar uma multidao de fantasmas.

Alem da fila, ele serve o PAINEL (onde voce mexe na live sem reiniciar nada) e
os OVERLAYS do OBS.

Python puro, so' biblioteca padrao. Nao precisa de Deno, nao precisa compilar
nada, e nao existe .exe sem assinatura para o antivirus comer.

Roda sozinho:
    python servidor/servidor.py
"""

import json
import mimetypes
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
WEB = os.path.join(AQUI, "web")
CONFIG_DIR = os.path.join(RAIZ, "config")
ARQ_AJUSTES = os.path.join(CONFIG_DIR, "ajustes.json")
# O arquivo da licença. A variável de ambiente existe para o teste de
# ponta a ponta poder apontar para um arquivo temporário -- sem ela, o
# teste mexeria no config de verdade de quem está rodando.
ARQ_LICENCA = os.environ.get("ARQ_LICENCA") or os.path.join(CONFIG_DIR,
                                                            "licenca.json")

#[[ OS TETOS DE EFEITO VEM DO ponte/regras.py, E NAO DE UMA COPIA AQUI.
#
#   POR QUE ISSO IMPORTA: o `limitar()` do regras.py corta cada valor antes de
#   ele virar um spawn. Se o servidor guardasse um teto DIFERENTE (ou nenhum),
#   acontecia o que ja' aconteceu neste kit: o oculos ficou gravado com escala
#   10, o painel mostrava 10, e o jogo desenhava 4 -- porque o teto real era 4.
#   O painel virava um mentiroso, e a queixa que chega e' "mexo no painel e o
#   jogo faz outra coisa".
#
#   Importar de la' e' o unico jeito de os dois nunca discordarem. Se por
#   algum motivo o import falhar (alguem rodou o servidor de outra pasta), o
#   servidor continua funcionando SEM normalizar -- perder o ajuste fino e'
#   melhor do que a live nao subir. ]]
sys.path.insert(0, os.path.join(RAIZ, "ponte"))
try:
    import regras as _regras
except ImportError:
    _regras = None

#[[ AS CENAS -- a paleta dos temas do cenário (ver servidor/cenas.py).
#
#   Vive num arquivo só, ao lado deste, e é a FONTE ÚNICA da paleta: o painel
#   lê daqui pra desenhar a prévia, e o jogo recebe a mesma tabela pelo
#   `/ajustes`. Duas cópias da paleta (uma em JS, outra em Luau) divergem na
#   primeira edição, e aí o painel mostra uma cor e o jogo põe outra.
#
#   Se o import falhar, a live continua funcionando e a troca de cena some --
#   perder o tema é melhor do que a live não subir. ]]
try:
    import cenas as _cenas
except ImportError:
    _cenas = None

#[[ A ATUALIZAÇÃO (ver servidor/atualizacao.py).
#
#   O app se atualiza sozinho, pelo GitHub. É o que resolve o problema de
#   um produto vendido como ZIP: cliente com versão velha, e um
#   "instala de novo" que ninguém quer fazer no meio da live.
#
#   Se o import falhar, o app continua funcionando sem se atualizar --
#   perder a atualização é melhor do que a live não subir. ]]
try:
    import atualizacao as _atualizacao
except ImportError:
    _atualizacao = None

#[[ O CLIENTE DA LICENÇA (ver servidor/licenca.py).
#
#   O servidor local busca o MANIFESTO (no GitHub) para saber se a licença
#   desta máquina vale, e para receber o CONTEÚDO PROTEGIDO.
#
#   Se o import falhar, este pacote não tem o sistema de licença: o
#   servidor sobe, e o app funciona sem o conteúdo extra. Perder a licença
#   degrada o produto; nunca o derruba. ]]
try:
    import licenca as _licenca
except ImportError:
    _licencia = None

#[[ O CONTEXTO TLS das consultas ao Roblox (ver ponte/rede.py).
#
#   No Windows a lista de certificados do Python costuma chegar pela metade, e
#   o sintoma disso NAO parece um problema de rede: parece "o nick nao existe".
#   Se o import falhar, o servidor segue com o padrao do Python -- resolver
#   nick pode parar de funcionar, mas a live nao deixa de subir por isso. ]]
try:
    import rede as _rede
except ImportError:
    _rede = None

#[[ A REGRA DO @ DO TIKTOK, uma so' pro kit inteiro (ver ponte/conta.py).
#
#   O painel manda pra ca' texto COLADO por uma pessoa: o link do perfil
#   inteiro, o @ com um caractere invisivel grudado, a frase com o @ no meio.
#   Antes esta rota limpava com um `.strip().lstrip("@")` proprio, diferente do
#   que a ponte fazia -- e duas limpezas quase iguais e' como nasce o "digitei
#   certo e ele diz que nao existe".
#
#   Se o import falhar, a rota volta pra limpeza simples: e' pior, mas nao
#   impede ninguem de conectar. ]]
try:
    import conta as _conta
except ImportError:
    _conta = None

PORTA = int(os.environ.get("PORTA", "8000"))

# Duas chaves, e nao uma. A de LEITURA vai dentro do jogo Roblox, que qualquer
# pessoa com o arquivo do lugar consegue abrir; a de ESCRITA fica so' na ponte.
# Se a de leitura vazar, o pior que fazem e' ler a fila. Com a de escrita,
# injetariam avatares falsos na sua live.
CHAVE_ESCRITA = os.environ.get("CHAVE_ESCRITA", "escrita-local")
CHAVE_LEITURA = os.environ.get("CHAVE_LEITURA", "leitura-local")

# Quantos eventos a fila guarda. 2000 e' bem mais do que o jogo consome (ele
# le' a cada 1s), e serve de folga para um travamento momentaneo do Studio nao
# fazer ninguem sumir. Acima disso os mais velhos caem -- eles ja' nao teriam
# valor nenhum na tela.
FILA_MAX = 2000


# ══════════════════════════════════════════════════════════════════════
#  A FILA
# ══════════════════════════════════════════════════════════════════════

class Fila:
    """Eventos numerados, com corte por cursor.

    `seq` e' um contador que so' cresce, e NAO e' o indice da lista: a lista
    perde os mais velhos e os indices andariam, mas o cursor que o jogo guarda
    precisa continuar valendo. Guardar o numero junto de cada evento resolve
    isso sem o jogo precisar saber de nada.
    """

    def __init__(self, maximo=FILA_MAX):
        self._itens = []          # [(seq, evento), ...]
        self._seq = 0
        self._maximo = maximo
        self._trava = threading.Lock()

    def juntar(self, eventos):
        with self._trava:
            for ev in eventos:
                self._seq += 1
                self._itens.append((self._seq, ev))
            sobra = len(self._itens) - self._maximo
            if sobra > 0:
                del self._itens[:sobra]
            return self._seq

    def desde(self, cursor):
        """(seq_atual, eventos_novos).

        `cursor` negativo (ou ausente) = "so' me diga onde a fila esta'" — e'
        como um servidor que acabou de subir se ancora sem receber historico.
        """
        with self._trava:
            if cursor is None or cursor < 0:
                return self._seq, []
            return self._seq, [ev for n, ev in self._itens if n > cursor]

    def topo(self):
        with self._trava:
            return self._seq


# ══════════════════════════════════════════════════════════════════════
#  OS AJUSTES (o que o painel salva)
# ══════════════════════════════════════════════════════════════════════
#
# A ponte tem a tabela de fabrica dela em regras.py e funciona sozinha desde o
# primeiro minuto, antes de existir painel nenhum. Isto aqui e' o que o painel
# escreve por cima. Nunca e' o painel que decide se a live funciona -- so' o
# quanto ela e' sua.

def _catalogo(grupos):
    """{grupo: (apelidos, rotulo, emoji, moedas, efeito)} -> {apelido: efeito}.

    Escrever os apelidos na mao, um bloco identico por linha, era o formato
    antigo -- e ele tinha um defeito de manutencao caro: onze blocos pra quatro
    presentes, e mexer no tamanho da galaxia significava lembrar de mexer em
    tres lugares. Quando alguem esquecia um, o presente passava a se comportar
    de um jeito na sua regiao e de outro na regiao de quem estava assistindo,
    que e' um bug praticamente impossivel de reproduzir.

    O campo `imagem` sai vazio de fabrica e nao e' esquecimento: e' o endereco
    da FIGURA do presente, e quem sabe qual e' ela e' a propria live. A ponte
    captura a imagem de cada presente que chega (o TikTok manda a URL junto do
    evento) e o painel oferece ela pronta na hora de cadastrar. Chutar um
    endereco aqui daria uma ficha com figura quebrada, que e' pior que ficha
    com emoji.
    """
    fora = {}
    for grupo, (apelidos, rotulo, emoji, moedas, efeito) in grupos.items():
        for apelido in apelidos:
            fora[apelido] = dict(efeito, grupo=grupo, rotulo=rotulo,
                                 emoji=emoji, moedas=moedas, id="", imagem="",
                                 apelidos=list(apelidos))
    return fora


AJUSTES_PADRAO = {
    # Efeito por FAIXA DE PRECO, da mais cara pra mais barata. E' a rede de
    # seguranca que faz presente novo (ou de outra regiao) ja' nascer
    # funcionando, sem voce ter que cadastrar nada.
    #
    # A `danca` vem junto pelo mesmo motivo: um presente de 1000 moedas que o
    # TikTok lancou ontem ja' chega dancando a danca da galaxia, sem cadastro.
    #
    #[[ A ESCADA DE TAMANHO E' A MESMA DO ponte/regras.py, E ISSO E' OBRIGATORIO.
    #
    #   Aqui e' a tabela do PAINEL; la' e' a de fabrica, que vale quando o painel
    #   nao respondeu. Enquanto as duas discordavam, a mesma rosa nascia 2.0x com
    #   o painel no ar e 1.0x sem ele -- e "o presente as vezes aparece pequeno"
    #   e' o tipo de defeito que ninguem consegue reproduzir de proposito.
    #
    #   E TODO PRESENTE NASCE MAIOR QUE UM COMENTARIO (que e' 1.0x). Um presente
    #   pago que poe na tela um boneco do mesmo tamanho do de quem so' digitou
    #   nao entrega o que foi pago: de longe, no celular, os dois sao o mesmo
    #   boneco. A rosa nasce 2x, e dai' pra cima. ]]
    "faixas": [
        {"min": 1000, "efeito": {"prio": 6, "escala": 6.0, "crescimento": 1.6,
                                 "vida": 300, "segura": 9.0,
                                 "cena": 9.0, "chuva": 30, "cor": "B14BFF", "brilho": 5,
                                 "danca": "galaxia"}},
        {"min": 200, "efeito": {"prio": 5, "escala": 4.0, "crescimento": 1.0,
                                "vida": 300, "segura": 14.0,
                                "cena": 4.0, "furacao": 12.0, "cor": "27E1FF", "brilho": 4,
                                "danca": "oculos"}},
        {"min": 30, "efeito": {"prio": 4, "escala": 3.0, "crescimento": 0.6,
                               "vida": 240, "segura": 5.5,
                               "cena": 5.5, "cor": "FFA321", "brilho": 3,
                               "danca": "rosquinha"}},
        {"min": 10, "efeito": {"prio": 3, "escala": 2.5, "crescimento": 0.3,
                               "vida": 150, "segura": 4.0,
                               "cena": 4.0, "cor": "FF2D6F", "brilho": 2,
                               "danca": "passinho"}},
        {"min": 1, "efeito": {"prio": 2, "escala": 2.0, "crescimento": 0.15,
                              "vida": 90, "segura": 1.0,
                              "cena": 0, "cor": "FF9EC4", "brilho": 1, "danca": ""}},
    ],
    # O CATALOGO DE PRESENTES. Vence a faixa de preco.
    #
    # POR QUE ELE EXISTE, ALEM DAS FAIXAS
    #
    # A faixa de preco sozinha erra em casos que importam. O caso concreto: o
    # OCULOS custa 199 moedas e a faixa dos "enormes" comeca em 200 -- por uma
    # moeda ele caia na faixa de baixo e entrava do tamanho de uma rosquinha.
    # Um presente de 199 moedas parecendo um de 30 e' dinheiro do espectador
    # entregue errado, e o tipo de coisa que ninguem percebe olhando o painel.
    #
    # ─── O FORMATO, E POR QUE ELE E' ASSIM ───
    #
    # A chave e' um APELIDO em minusculas, e o MESMO presente aparece sob todos
    # os apelidos dele. Isso nao e' repeticao: a API do TikTok manda o nome em
    # ingles e ele MUDA de regiao pra regiao -- "rose" e "rosa" sao o mesmo
    # presente, e so' um dos dois chega, dependendo de quem esta' assistindo.
    # Guardar sob os dois e' o que faz o gatilho pegar nos dois casos.
    #
    # Dentro de cada efeito vao tambem os campos de IDENTIDADE, e sao eles que
    # tornam o catalogo EDITAVEL pelo painel em vez de fixo no codigo:
    #
    #   grupo     a que presente estas linhas pertencem. E' por ele que o painel
    #             junta "rose" e "rosa" numa ficha so' em vez de duas.
    #   rotulo    o nome que aparece no painel.
    #   emoji     enfeite da ficha.
    #   id        o ID NUMERICO do presente no TikTok. VENCE O APELIDO, porque
    #             ele nao muda de regiao nem quando traduzem o nome. Vem vazio
    #             de fabrica de proposito: um ID chutado errado nunca casa, e o
    #             painel mostra o ID de verdade de cada presente que chegar na
    #             sua live pra voce cadastrar sem adivinhar.
    #   moedas    quanto ele custa. So' informativo (o valor real vem do evento).
    #
    # O campo `danca` e' o passo que o avatar daquele presente vai dançar. Os
    # nomes validos estao em ponte/regras.py (DANCAS_VALIDAS), e cada um deles
    # tem o ID da animacao em roblox/src/ReplicatedStorage/Config.luau (DANCAS).
    # "" = a danca padrao, a mesma de quem so' comentou.
    #
    # O campo `crescimento` e' quanto o presente SOMA de tamanho no avatar que a
    # pessoa ja' tem na tela -- e' a promessa do telao ("mande presentes e seu
    # personagem cresce"). O `escala` e' outra coisa: o tamanho com que o boneco
    # NASCE, quando a pessoa ainda nao tem nenhum.
    "presentes": _catalogo({
        # Rosa -- barata, prioridade, sem cinematica, danca padrao. E' de
        # proposito: a rosa e' o presente comum da live, e se ela ja' tivesse
        # passo proprio o passo deixaria de significar "alguem pagou caro".
        "rosa": (["rose", "rosa"], "Rosa", "\U0001F339", 1,
                 {"prio": 2, "escala": 2.0, "crescimento": 0.15, "segura": 1.0,
                  "cena": 0, "chuva": 0, "furacao": 0, "colosso": 0,
                  "danca_geral": 0, "danca": "", "cor": "FF9EC4", "brilho": 1}),

        # Rosquinha -- grande, com cinematica e danca propria.
        "rosquinha": (["doughnut", "donut", "rosquinha"], "Rosquinha",
                      "\U0001F369", 30,
                      {"prio": 4, "escala": 3.0, "crescimento": 0.6, "segura": 5.5,
                       "cena": 5.5, "chuva": 0, "furacao": 0, "colosso": 0,
                       "danca_geral": 0, "danca": "rosquinha", "cor": "FFA321",
                       "brilho": 3}),

        # Oculos -- o que nasce maior de todos, varre a formacao, danca propria.
        "oculos": (["sunglasses", "oculos", "óculos"], "Óculos", "\U0001F576", 199,
                   {"prio": 5, "escala": 4.0, "crescimento": 1.0, "segura": 14.0,
                    "cena": 4.0, "chuva": 0, "furacao": 12.0, "colosso": 0,
                    "danca_geral": 0, "danca": "oculos", "cor": "27E1FF",
                    "brilho": 4}),

        # Galaxia -- a cinematica mais longa, 30s de chuva, danca propria e o
        # maior crescimento. Os avatares da chuva herdam a danca: sao 20 bonecos
        # entrando no MESMO passo no meio da formacao.
        "galaxia": (["galaxy", "galaxia", "galáxia"], "Galáxia", "\U0001F30C", 1000,
                    {"prio": 6, "escala": 6.0, "crescimento": 1.6, "segura": 9.0,
                     "cena": 9.0, "chuva": 30, "furacao": 0, "colosso": 0,
                     "danca_geral": 0, "danca": "galaxia", "cor": "B14BFF",
                     "brilho": 5}),
    }),
    # O que cada ACAO do espectador faz. `ativo` desligado = nao spawna.
    # O que, ALEM do presente, faz um avatar nascer.
    #
    # SO' O COMENTARIO VEM LIGADO, E ISSO E' A REGRA DO PRODUTO.
    #
    # As tres de baixo vinham ligadas de fabrica, e o resultado ao vivo era o
    # oposto do que o kit promete: bastava UMA pessoa ter comentado o nick dela
    # alguma vez pra que cada 200 curtidas dela, cada seguida e cada
    # compartilhamento virassem um boneco NOVO. Numa live de verdade a curtida e'
    # o evento mais frequente que existe -- gente segura o coracao e manda
    # dezenas por segundo -- entao a formacao enchia sozinha, com o chat parado.
    #
    # Quem estava transmitindo via bonecos aparecendo do nada, sem ninguem
    # digitar, e nao tinha como saber de onde vinham: curtida nao aparece no
    # chat. Pior: isso mata o motivo de comentar. Se o boneco aparece de
    # qualquer jeito, o pedido "comenta o seu nick que voce aparece na tela" --
    # que e' o que faz a live crescer -- deixa de ser verdade.
    #
    # Elas continuam no painel, prontas, com os numeros calibrados. Ligar e' um
    # clique, e ai' e' uma escolha de quem esta' transmitindo, e nao uma
    # surpresa no meio da primeira live.
    "acoes": {
        "comentario": {"ativo": True, "prio": 0, "escala": 1.0, "vida": 45,
                       "segura": 0.4, "cena": 0, "cor": "FFFFFF", "brilho": 0},
        "curtida": {"ativo": False, "a_cada": 200, "prio": 1, "escala": 1.0,
                    "vida": 60, "segura": 0.6, "cena": 0, "cor": "FF6B9D", "brilho": 1},
        "seguiu": {"ativo": False, "prio": 2, "escala": 1.3, "vida": 90,
                   "segura": 2.0, "cena": 0, "cor": "4ADE80", "brilho": 1},
        "compartilhou": {"ativo": False, "prio": 2, "escala": 1.2, "vida": 90,
                         "segura": 1.5, "cena": 0, "cor": "60A5FA", "brilho": 1},
    },
    "geral": {
        # Quantos avatares cabem antes de a formacao fechar o ciclo e recomecar.
        "total_avatares": 100,
        # Quantos por fileira. A camera fica do lado +Z, entao fileira nova
        # nasce mais perto de quem assiste.
        "por_fila": 10,
        # Teto de quantos avatares um combo unico pode render.
        "combo_max": 100,
        # Distancia da camera no plano geral.
        "camera_recuo": 34,

        # ─────────────── O CRESCIMENTO ───────────────
        #
        # Ate' onde um avatar pode crescer somando presente sobre presente.
        #
        # 6.0 nao e' um numero solto: e' o maior tamanho em que um boneco ainda
        # CABE no enquadramento junto com a formacao. Acima disso a camera
        # precisa recuar tanto pra ele caber que todo o resto da live vira um
        # tapete de pontinhos no chao -- ou seja, o presente mais caro passa a
        # ESTRAGAR o quadro em vez de destacar quem pagou.
        "tamanho_max": 6.0,
        # Quanto o crescimento demora, em segundos. Salto seco parece bug; um
        # crescimento longo demais termina depois de a camera ja' ter ido
        # embora e a pessoa nao ve' o que pagou. 0.6s e' o ponto em que da'
        # pra ver acontecendo.
        "crescimento_suave": 0.6,
        #[[ O QUE UM PRESENTE FAZ NA TELA. Tres opcoes:
        #
        #   "novo"    cada presente cria um boneco NOVO. Ninguem cresce.
        #             E' a leitura "a live esta' enchendo": a tela mostra
        #             QUANTA gente participou.
        #
        #   "crescer" o presente faz crescer o boneco que a pessoa ja' tem.
        #             So' cria um novo se ela ainda nao estiver na tela.
        #             E' a leitura "quem gastou aparece": premia quem pagou.
        #
        #   "ambos"   as duas coisas: nasce um boneco novo E o que ela ja'
        #             tinha cresce.
        #
        # O PADRAO E' "novo", e a razao e' de produto e nao de codigo: presente
        # tem que colocar ALGUMA COISA NOVA na tela. Um boneco que so' incha no
        # meio da formacao e' um efeito que quem esta' assistindo pelo celular
        # nao liga ao presente que acabou de passar no chat -- e quem pagou
        # fica sem saber se funcionou. Boneco novo aparecendo e' inequivoco.
        #
        # O crescimento continua aqui pra quem quiser: "crescer" premia quem
        # gastou (o boneco DELA fica maior a cada presente) e "ambos" faz as
        # duas coisas. E' um clique no painel.
        "presente_faz": "novo",

        # ─────────────── O ENQUADRAMENTO ───────────────
        #
        # `vertical` liga a composicao pensada pra 9:16 (TikTok Live, OBS em
        # pe'). Ela nao so' muda o FOV: ela recua a camera, porque num quadro
        # estreito o telao inteiro so' cabe de mais longe.
        "vertical": False,
        # Abertura da lente. Menor = mais "teleobjetiva", achata a formacao e
        # aproxima o telao; maior = mais cenario e mais distorcao nas bordas.
        "camera_fov": 62,
        #[[ Distancia da camera pra quem ela esta' seguindo, no plano de perto.
        #
        #   E' o numero que decide entre "close claustrofobico" e "palco".
        #
        #   PRECISA BATER com Config.CAMERA.DISTANCIA no Luau, e nao por
        #   simetria: e' este valor que os testes de enquadramento medem
        #   (roblox/testes/enquadramento.spec.luau). Com os dois diferentes, o
        #   teste aprova um quadro e a live mostra outro -- que e' o pior tipo
        #   de teste que existe. ]]
        "camera_distancia": 38,
        # Altura da camera no plano de perto.
        "camera_altura": 19,

        #[[ ─────────── O CLOSE DE CHEGADA ───────────
        #
        #   Quem chega ganha alguns segundos de close, com o boneco grande e o
        #   nick legivel, e depois a camera volta pro plano normal.
        #
        #   Estava fixo no Config.luau, e nao no painel, e isso escondia o
        #   controle mais util da camera inteira: o close e' o unico momento em
        #   que a pessoa que acabou de comentar SE VE'. Longo demais e a live
        #   vira uma sequencia de retratos sem multidao nenhuma; curto demais e
        #   quem comentou pisca na tela e some.
        "camera_zoom": True,
        "camera_zoom_s": 2.2,
        # De onde o close comeca a procurar distancia, por unidade de tamanho
        # do boneco. Menor = mais perto do rosto.
        "camera_zoom_distancia": 9,
        # O quanto a camera "corre atras" do alvo. Baixo = camera preguicosa e
        # cinematografica; alto = ela cola no alvo e o movimento fica seco.
        "camera_suavidade": 0.08,
        # Quantos segundos o plano aberto do fim de ciclo dura. Nesse tempo
        # NINGUEM novo nasce -- e' o preco de mostrar a formacao cheia.
        "camera_aberta_s": 3.0,
        #[[ A CINEMATICA (a camera girando em volta de quem mandou presente
        #   caro). Vem DESLIGADA, e a razao e' de produto: numa live movimentada
        #   ela passava mais tempo rodando em torno de uma pessoa do que
        #   mostrando a live, e cada giro escondia a multidao do fundo.
        #
        #   Continua aqui porque numa live CALMA ela e' o efeito mais bonito do
        #   kit -- e agora ligar e' um clique, em vez de editar um arquivo Luau.
        "camera_cena": False,

        #[[ ─────────── A LUZ DO CENARIO ───────────
        #
        #   O nivel de luz da pista, ao vivo. A pista e' um lugar FECHADO (tem
        #   forro), entao quem manda na claridade dentro dela e' o Ambient --
        #   nao o Brightness nem a hora do dia, que e' onde a gente tenta mexer
        #   primeiro e nao acontece nada.
        #
        #   Estes dois andam JUNTOS: o ambiente clareia e a exposicao segura o
        #   estouro. Subir so' o ambiente leva as superficies claras ao branco
        #   puro (a area perde desenho, que e' o "estourou"); baixar a exposicao
        #   junto devolve o desenho sem escurecer a cena.
        "luz_ambiente": 0.58,
        "luz_exposicao": 0.0,

        #[[ ─────────── AS DANCAS QUE NAO SAO DE PRESENTE ───────────
        #
        #   `danca_padrao` e' o passo de quem SO' COMENTOU -- ou seja, o passo
        #   que 90% da formacao dança 90% do tempo. Ele era fixo no Config.luau,
        #   e o painel so' deixava escolher a danca dos presentes: dava pra
        #   escolher o passo da minoria e nao o da maioria.
        #
        #   `danca_especial` e' pra onde a formacao INTEIRA troca quando um
        #   presente com `danca_geral` chega, e volta sozinha depois.
        #
        #   "" nos dois = usa o que esta' no Config.luau. Os nomes validos sao
        #   os de ponte/regras.py (DANCAS_VALIDAS), e cada um tem o ID da
        #   animacao em roblox/src/ReplicatedStorage/Config.luau (DANCAS).
        "danca_padrao": "",
        "danca_especial": "",

        #[[ A CENA DO CENARIO.
        #
        #   Qual das paletas do kit de cenas (servidor/cenas.py) esta no ar.
        #   O nome e' o que o jogo recebe -- a paleta em si vem no mesmo
        #   `/ajustes`, na secao "cenas", pra que os dois lados nunca discordem
        #   sobre a cor.
        #
        #   Trocar por aqui vale em ate' 5 segundos, sem reiniciar nada. ]]
        "tema": "padrao",

        #[[ A ATUALIZAÇÃO AUTOMÁTICA.
        #
        #   Ligada, o app busca no GitHub do dono se há uma versão nova, e
        #   se aplica sozinho antes de subir.
        #
        #   Convém DESLIGAR enquanto você está mexendo no código: senão o
        #   app troca a versão no meio do seu trabalho. ]]
        "atualizar": True,
    },
    "rotulo": {
        # O balao do nome em cima da cabeca.
        "fundo": "000000",
        "transparencia": 0.35,
        "cor_do_presente": True,
        "mostrar_nick_roblox": True,
    },
    # A CONTA DO TIKTOK, e se a ponte deve estar conectada nela.
    #
    # Fica gravado junto dos ajustes de proposito: assim o painel lembra a sua
    # conta entre uma live e outra, e reconectar depois de um reinicio e' um
    # clique em vez de digitar o @ de novo.
    #
    # `revisao` sobe a cada mudanca. E' por ela que a ponte percebe que voce
    # mexeu -- comparar a CONTA nao bastaria: desconectar e reconectar na mesma
    # conta nao muda o texto, e a ponte ficaria sem saber que precisa agir.
    "tiktok": {
        "conta": "",
        "ligado": False,
        "revisao": 0,
    },
}


# Secoes em que o painel manda a LISTA COMPLETA, e nao um pedaco.
#
# `presentes` e' o caso: quando voce DESLIGA o gatilho proprio de um presente,
# ele some do que o painel envia. Com a mesclagem normal, "sumiu" nao quer dizer
# nada -- o valor antigo continuaria la' pra sempre, e desligar um presente no
# painel simplesmente nao funcionaria. Aqui a secao inteira e' substituida, e
# ausencia passa a significar remocao.
SECOES_SUBSTITUIDAS = ("presentes",)


def _mesclar(base, novo):
    """Copia profunda de `base` com `novo` por cima.

    Chave a chave, e nao um update() raso: o painel manda so' o pedaco que ele
    conhece, e um update raso apagaria o resto. Ja' aconteceu com a secao
    `geral` quando o painel de placar salvou sem ela.
    """
    fora = dict(base)
    if not isinstance(novo, dict):
        return fora
    for k, v in novo.items():
        if k in SECOES_SUBSTITUIDAS:
            fora[k] = json.loads(json.dumps(v)) if isinstance(v, dict) else {}
        elif isinstance(v, dict) and isinstance(fora.get(k), dict):
            fora[k] = _mesclar(fora[k], v)
        else:
            fora[k] = v
    return fora


def _normalizar_efeito(efeito):
    """Corta um efeito pelos MESMOS limites que o jogo vai aplicar.

    O painel mostra o que esta' gravado. Se o gravado passar do teto, o painel
    mostra um numero que o jogo nunca vai usar -- e foi exatamente isso que
    aconteceu com o oculos gravado em escala 10 num motor que corta em 4.

    Normalizando na LEITURA, o arquivo, o painel e o jogo passam a dizer a
    mesma coisa, e "mexi no painel e o jogo faz outra coisa" deixa de ter como
    acontecer. Os campos de identidade (nome, id, apelidos) sao preservados: o
    `limitar` do regras.py so' conhece os campos de efeito.
    """
    if _regras is None or not isinstance(efeito, dict):
        return efeito
    limpo = _regras.limitar(efeito)
    for campo in ("grupo", "rotulo", "emoji", "imagem", "moedas", "id",
                  "apelidos", "ativo", "a_cada"):
        if campo in efeito:
            limpo[campo] = efeito[campo]
    return limpo


def _migrar(dados):
    """Completa o que uma versao ANTERIOR do kit gravou.

    O `ajustes.json` de quem ja' usou o kit foi escrito por um painel que nao
    conhecia `grupo`, `rotulo`, `id` nem `crescimento`. Como a secao
    `presentes` e' SUBSTITUIDA na mesclagem (e precisa ser -- e' o que faz
    desligar um presente funcionar), esses campos nao voltam sozinhos: o
    arquivo antigo vence, e o painel novo abriria com quatro fichas sem nome e
    com crescimento zero. Ou seja, quem ATUALIZOU o kit teria presentes que
    nao fazem o avatar crescer, e nada na tela dizendo por que.

    Aqui cada apelido gravado e' reencontrado no catalogo de fabrica e recebe
    de volta so' o que falta. O que voce ajustou continua exatamente como voce
    deixou.
    """
    presentes = dados.get("presentes")
    if not isinstance(presentes, dict):
        return dados

    fabrica = AJUSTES_PADRAO["presentes"]
    for apelido, efeito in list(presentes.items()):
        if not isinstance(efeito, dict):
            presentes.pop(apelido, None)
            continue
        modelo = fabrica.get(apelido, {})
        efeito.setdefault("grupo", modelo.get("grupo") or apelido)
        efeito.setdefault("rotulo", modelo.get("rotulo") or apelido.title())
        efeito.setdefault("emoji", modelo.get("emoji") or "\U0001F381")
        # A FIGURA do presente. Vazia = o painel mostra o emoji. Ela chega
        # sozinha quando o presente aparece na live (a ponte captura a URL do
        # evento e o painel oferece ela na hora de cadastrar), entao um
        # ajustes.json antigo nao perde nada por nao ter o campo.
        efeito.setdefault("imagem", modelo.get("imagem") or "")
        efeito.setdefault("moedas", modelo.get("moedas") or 0)
        efeito.setdefault("id", "")
        efeito.setdefault("apelidos", modelo.get("apelidos") or [apelido])
        # O crescimento e' o unico campo NOVO que muda comportamento. Sem
        # padrao de fabrica pra copiar (um presente que voce mesmo criou), ele
        # sai do proprio tamanho: quem nasce grande cresce mais.
        if "crescimento" not in efeito:
            if "crescimento" in modelo:
                efeito["crescimento"] = modelo["crescimento"]
            else:
                try:
                    escala = float(efeito.get("escala") or 1.0)
                except (TypeError, ValueError):
                    escala = 1.0
                efeito["crescimento"] = round(max(0.0, (escala - 0.5)) * 0.5, 2)

    # As faixas herdam o crescimento da faixa de fabrica DE MESMO PISO. Um
    # padrao unico pra todas (0.3, por exemplo) achataria a escada inteira:
    # a galaxia passaria a crescer igual a uma rosa, e o presente de 1000
    # moedas ficaria indistinguivel do de 1 -- que e' precisamente o defeito
    # que este kit existe pra nao ter.
    por_piso = {f["min"]: f["efeito"].get("crescimento", 0.3)
                for f in AJUSTES_PADRAO["faixas"]}
    for faixa in dados.get("faixas") or []:
        if not isinstance(faixa, dict) or not isinstance(faixa.get("efeito"), dict):
            continue
        try:
            piso = int(faixa.get("min") or 0)
        except (TypeError, ValueError):
            piso = 0
        faixa["efeito"].setdefault("crescimento", por_piso.get(piso, 0.3))

    # A NORMALIZACAO vem por ULTIMO, depois de todos os setdefault. Antes
    # deles, os campos que acabaram de ser preenchidos ficariam de fora do
    # corte -- e um `crescimento` herdado de uma faixa poderia passar do teto
    # sem ninguem cortar.
    for apelido, efeito in list(presentes.items()):
        presentes[apelido] = _normalizar_efeito(efeito)
    for faixa in dados.get("faixas") or []:
        if isinstance(faixa, dict) and isinstance(faixa.get("efeito"), dict):
            faixa["efeito"] = _normalizar_efeito(faixa["efeito"])
    for chave, acao in (dados.get("acoes") or {}).items():
        if isinstance(acao, dict):
            dados["acoes"][chave] = _normalizar_efeito(acao)
    return dados


class Ajustes:
    def __init__(self, caminho=ARQ_AJUSTES):
        self.caminho = caminho
        self._trava = threading.Lock()
        self._dados = self._carregar()

    def _carregar(self):
        try:
            with open(self.caminho, "r", encoding="utf-8-sig") as f:
                return _migrar(_mesclar(AJUSTES_PADRAO, json.load(f)))
        except (OSError, ValueError):
            # Arquivo ausente ou corrompido nao pode impedir a live de subir.
            return json.loads(json.dumps(AJUSTES_PADRAO))

    def ler(self):
        with self._trava:
            return json.loads(json.dumps(self._dados))

    def salvar(self, novo):
        with self._trava:
            self._dados = _mesclar(self._dados, novo)
            dados = json.loads(json.dumps(self._dados))
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        # Escrita em dois passos: se o PC desligar no meio, o ajustes.json
        # antigo continua inteiro em vez de virar meio arquivo ilegivel -- e
        # meio arquivo ilegivel e' exatamente o que faria a live nao subir na
        # proxima vez.
        temp = self.caminho + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(temp, self.caminho)
        return dados


# ══════════════════════════════════════════════════════════════════════
#  A LICENÇA DO PRODUTO NESTA MÁQUINA
# ══════════════════════════════════════════════════════════════════════

class Licenca:
    """Se a licença desta máquina vale, e o que ela autorizou.

    A licença é conferida no arranque e de tempos em tempos depois.

    ENQUANTO ELA NÃO VALE, O SERVIDOR CONTINUA NO AR. A pessoa precisa do
    painel para ver o que há de errado e corrigir — se o servidor morresse,
    a única mensagem seria "não funciona", e ela não saberia o que fazer.

    MAS AS ROTAS QUE ALIMENTAM O JOGO DEVOLVEM 403. Isso é o que importa:
    sem licença, o jogo não recebe evento nenhum, a ponte não entrega
    presente nenhum, e o produto simplesmente não funciona — com o motivo
    escrito.

    FALHAR FECHADO é a parte que dá sentido ao resto: um sistema que
    "funciona quando der" é um sistema que funciona para quem quiser.
    """

    def __init__(self, caminho=None):
        self.caminho = caminho or ARQ_LICENCA
        self.cliente = None
        self.ok = False
        self.motivo = "a licenca ainda nao foi conferida"
        self.codigo = "verificando"
        self.dados = {}
        self.protegido = {}
        self.ultima = 0.0
        self._trava = threading.Lock()
        self._parar = False
        if _licenca is not None:
            self.cliente = _licenca.ClienteLicenca.do_arquivo(self.caminho)

    def _estado(self, ok, motivo, codigo, dados=None):
        with self._trava:
            self.ok = bool(ok)
            self.motivo = str(motivo or "")
            self.codigo = str(codigo or "")
            self.dados = dict(dados or {})
            self.ultima = time.time()

    def _recarregar(self):
        """Relê o config da licença.

        A chave é corrigida no arquivo (ou no painel) e a conferida seguinte
        pega a correção, sem precisar reiniciar o servidor. Sem isto, uma
        chave digitada errado na primeira hora ficaria errada a noite toda.

        O token em mãos é mantido quando a chave é a mesma: o token é a
        prova de vida da sessão, e jogá-lo fora a cada conferida faria o
        servidor pedir uma nova sessão a cada minuto.
        """
        if _licenca is None:
            return
        antigo = self.cliente
        novo = _licenca.ClienteLicenca.do_arquivo(self.caminho)
        # No modelo do MANIFESTO nao ha token: o cliente busca o manifesto
        # e pronto (nao existe sessao, nao existe heartbeat). Por isso o
        # recarregar e' so recarregar.
        #
        # As duas tentativas anteriores de carregar o token adiante
        # levantaram AttributeError DENTRO da thread da licenca — que morria
        # sem aviso, e o painel ficava mostrando "verificando" para sempre.
        # O nome do campo tambem mudou: e' `codigo` agora (antes `chave`).
        self.cliente = novo

    def conferir(self):
        """Confere a licença com o MANIFESTO (no GitHub).

        E traz o CONTEÚDO PROTEGIDO: os IDs das animações de terceiro e as
        paletas das cenas. Na build de VENDA, esses valores não estão em
        lugar nenhum do arquivo — chegam só de licença.
        """
        if _licenca is None:
            self._estado(False, "este pacote nao tem o sistema de licencas",
                         "sem_modulo")
            return False

        self._recarregar()
        if self.cliente is None:
            self.cliente = _licenca.ClienteLicenca.do_arquivo(self.caminho)

        ok, motivo, conteudo = self.cliente.conferir()

        if conteudo:
            # As paletas das cenas entram no servidor: e' o que faz a aba
            # Cenas do painel ter o que mostrar, e o que o jogo pinta.
            if _cenas is not None:
                _cenas.aplicar_paletas(conteudo.get("cenas") or {})
            with self._trava:
                self.protegido = conteudo

        self._estado(ok, motivo, self.cliente.estado,
                     {"expira": self.cliente.expira,
                      "maquina": self.cliente.maquina})
        return ok

    def vivo(self):
        """A licença continua valendo? (e o conteúdo ainda é o mesmo?)

        O manifesto é buscado de tempos em tempos. Quando o vendedor
        renova a chave do cliente, o código NOVO só entra no manifesto
        depois do push — e é essa conferida que pega.
        """
        return self.conferir()

    def laco(self, intervalo=1800):
        """A conferida de tempos em tempos, enquanto o servidor vive.

        30 minutos é o meio-termo: rápido o bastante para uma chave
        renovada pelo vendedor valer em menos de meia hora, e lento o
        bastante para não ser uma requisição ao GitHub por cliente a cada
        instante.

        O CACHE do cliente é o que dá a tolerância: se o GitHub estiver
        fora do ar, o manifesto em cache segura a validade por algumas
        horas — perder a live por causa de uma queda do GitHub seria pior
        do que a licença.
        """
        while not self._parar:
            # A conferida NUNCA derruba a thread. Um erro aqui (a rede
            # caiu, o config foi editado por cima, o provedor mudou) ia
            # matar a thread em silencio, e a licença pararia de ser
            # conferida sem nenhum aviso em lugar nenhum.
            try:
                self.conferir()
            except Exception as e:
                print(f"  (a conferida da licenca falhou: {e})")
            for _ in range(intervalo):
                if self._parar:
                    return
                time.sleep(1)

    def gravar_chave(self, chave, ativacao=""):
        """Grava a chave no config e reconfere NA HORA.

        Reconferir na hora e' o que faz o painel poder dizer "pronto!"
        em vez de "vai valer em ate 5 segundos" — o cliente ve o
        resultado do que acabou de digitar.
        """
        dados = {}
        try:
            with open(self.caminho, "r", encoding="utf-8-sig") as f:
                dados = json.load(f)
        except (OSError, ValueError):
            dados = {}
        dados["chave"] = str(chave or "").strip()
        if ativacao:
            dados["ativacao"] = str(ativacao).strip()
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        with open(self.caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        self._recarregar()
        return dados


    def ler(self, com_pacote=False):
        with self._trava:
            d = {"ok": self.ok, "motivo": self.motivo, "codigo": self.codigo,
                 "licenca": dict(self.dados),
                 "conferida_ha": self.ultima}
            if com_pacote:
                d["protegido"] = dict(self.protegido)
            return d

    def parar(self):
        self._parar = True


LICENCA = Licenca()


# ══════════════════════════════════════════════════════════════════════
#  ESTADO VIVO (placar, foco da camera, diagnostico)
# ══════════════════════════════════════════════════════════════════════

class Diario:
    """O que aconteceu na live, em ordem, pro painel mostrar.

    POR QUE NAO BASTA O `print` DA JANELA PRETA

    A ponte ja' imprime tudo numa janela de console. So' que a janela preta
    e' o pior lugar possivel pra procurar um problema durante uma
    transmissao: ela rola sozinha, nao tem busca, some atras do OBS, e o que
    voce precisa ler (o comentario que NAO virou avatar) passou ha' quarenta
    linhas. Aqui o mesmo evento fica gravado e o painel mostra do lado dos
    controles, com a cor certa e sem rolar sozinho.

    Anel com cursor, igual a' Fila e pelo mesmo motivo: o painel pergunta "o
    que houve desde o numero N" e recebe so' o que ele ainda nao viu.
    """

    MAXIMO = 500

    def __init__(self):
        self._itens = []
        self._seq = 0
        self._trava = threading.Lock()

    def juntar(self, linhas):
        agora = time.time()
        with self._trava:
            for linha in linhas:
                if not isinstance(linha, dict):
                    continue
                self._seq += 1
                self._itens.append((self._seq, {
                    "n": self._seq,
                    "quando": float(linha.get("quando") or agora),
                    # info | ok | aviso | erro. Qualquer outra coisa vira info:
                    # um nivel desconhecido nao pode fazer a linha sumir do
                    # painel -- linha invisivel e' pior que linha sem cor.
                    "nivel": _nivel(linha.get("nivel")),
                    "origem": str(linha.get("origem") or "ponte")[:16],
                    "texto": str(linha.get("texto") or "")[:400],
                }))
            sobra = len(self._itens) - self.MAXIMO
            if sobra > 0:
                del self._itens[:sobra]
            return self._seq

    def desde(self, cursor):
        with self._trava:
            if cursor is None or cursor < 0:
                # Painel abrindo agora: entrega o fim do historico, e nao a
                # fila inteira. Quem acabou de abrir quer ver o que esta'
                # acontecendo, e as 500 linhas de dez minutos atras so' fariam
                # a tela nascer rolada no lugar errado.
                return self._seq, [ev for _, ev in self._itens[-40:]]
            return self._seq, [ev for n, ev in self._itens if n > cursor]


NIVEIS = ("info", "ok", "aviso", "erro")


def _nivel(valor):
    texto = str(valor or "info").strip().lower()
    return texto if texto in NIVEIS else "info"


class Jogadores:
    """Quem esta' participando da live, com o que se sabe de cada um.

    DOIS DONOS, CADA UM DA SUA METADE, E ISSO E' DE PROPOSITO

    A PONTE sabe o que veio do TikTok: o @, o nick do Roblox, quantos
    presentes, quantas moedas, quando foi a ultima interacao.

    O JOGO sabe o que so' existe dentro do Roblox: o TAMANHO atual do avatar
    e quantos bonecos aquela pessoa tem na tela.

    Se um dos dois escrevesse a linha inteira, ele apagaria os campos do outro
    a cada atualizacao -- e o painel piscaria entre duas metades da verdade.
    Cada lado escreve so' as chaves que ele conhece.
    """

    MAXIMO = 400

    def __init__(self):
        self._trava = threading.Lock()
        self._por_id = {}

    def _linha(self, chave):
        linha = self._por_id.get(chave)
        if linha is None:
            linha = {"tiktok_id": chave, "nickname": "", "nick_roblox": "",
                     "roblox_id": 0, "presentes": 0, "moedas": 0,
                     "avatares": 0, "tamanho": 0.0, "ultima": 0.0}
            self._por_id[chave] = linha
        return linha

    def _aparar(self):
        """Segura a tabela num tamanho fixo, tirando quem sumiu ha' mais tempo.

        Sem isto, uma live de seis horas com trinta mil espectadores deixaria
        trinta mil linhas na memoria -- e o painel, que pede a lista inteira a
        cada dois segundos, passaria a mandar megabytes por resposta.
        """
        if len(self._por_id) <= self.MAXIMO:
            return
        ordenados = sorted(self._por_id.values(), key=lambda l: l["ultima"])
        for linha in ordenados[:len(self._por_id) - self.MAXIMO]:
            self._por_id.pop(linha["tiktok_id"], None)

    def por_ponte(self, lista):
        agora = time.time()
        with self._trava:
            for item in lista or []:
                if not isinstance(item, dict):
                    continue
                chave = str(item.get("tiktok_id") or "")
                if not chave:
                    continue
                linha = self._linha(chave)
                for campo in ("nickname", "nick_roblox"):
                    if item.get(campo):
                        linha[campo] = str(item[campo])[:40]
                for campo in ("roblox_id", "presentes", "moedas"):
                    try:
                        linha[campo] = int(item.get(campo) or linha[campo])
                    except (TypeError, ValueError):
                        pass
                linha["ultima"] = agora
            self._aparar()

    def por_jogo(self, tamanhos):
        """{tiktok_id: {"tamanho": n, "avatares": n}} vindo do Roblox."""
        with self._trava:
            for chave, dados in (tamanhos or {}).items():
                if not isinstance(dados, dict):
                    continue
                linha = self._linha(str(chave))
                try:
                    linha["tamanho"] = round(float(dados.get("tamanho") or 0), 2)
                    linha["avatares"] = int(dados.get("avatares") or 0)
                except (TypeError, ValueError):
                    pass
            self._aparar()

    def esquecer_tamanhos(self):
        """O ciclo limpou a formacao: ninguem tem avatar na tela agora.

        Chamado pelo jogo ao apagar a grade. Sem isto o painel continuaria
        mostrando "tamanho 4.2" de gente cujo boneco nao existe mais, e o
        numero so' voltaria ao normal se aquela pessoa participasse de novo --
        ou seja, quanto MENOS ativa a pessoa, mais errado o painel ficava.
        """
        with self._trava:
            for linha in self._por_id.values():
                linha["tamanho"] = 0.0
                linha["avatares"] = 0

    def ler(self, quantos=60):
        with self._trava:
            lista = sorted(self._por_id.values(),
                           key=lambda l: l["ultima"], reverse=True)
            return json.loads(json.dumps(lista[:quantos]))


class Estado:
    """O que muda o tempo todo e nao vale a pena gravar em disco."""

    def __init__(self):
        self._trava = threading.Lock()
        self.placar = {"moedas": [], "curtidas": [], "presenca": []}
        # Em quem a camera parou agora. A voz le' isto pra narrar.
        self.foco = {"nick": "", "presente": "", "tipo": "", "em": 0.0}
        #[[ `ultimo_sinal_ponte` NAO E' O MESMO QUE `ultimo_push`, E A
        #   DIFERENCA E' O QUE MATA UM ALARME FALSO NO PAINEL.
        #
        #   `ultimo_push` so' anda quando a ponte tem EVENTO pra mandar. Numa
        #   live de chat parado ela fica minutos sem empurrar nada, viva e
        #   saudavel -- e o painel, medindo por ele, anunciaria que a janela
        #   preta da ponte fechou.
        #
        #   Este aqui anda a cada sinal de vida DELA, inclusive o `GET /testes`
        #   que ela faz de 1 em 1 segundo mesmo com o chat mudo. E' o batimento
        #   que o vigia de 12s do painel precisa pra so' disparar quando a
        #   ponte morreu de verdade. ]]
        self.contadores = {"recebidos": 0, "entregues": 0, "ultimo_push": 0.0,
                           "ultimo_pull": 0.0, "espectadores": 0,
                           "ultimo_sinal_ponte": 0.0}
        # O que a PONTE diz que esta' acontecendo com a conexao do TikTok.
        # `estado`: parada | conectando | conectada | offline | erro
        self.conexao = {"estado": "parada", "conta": "", "detalhe": "",
                        "em": 0.0}
        # Presentes que ja' chegaram nesta sessao, pelo ID do TikTok. E' a
        # lista que o painel usa pra te oferecer "cadastrar este presente" com
        # o ID certo, em vez de voce ter que descobri-lo em algum lugar.
        self.presentes_vistos = {}

    def por_conexao(self, dados):
        with self._trava:
            self.conexao = {
                "estado": str(dados.get("estado") or "parada")[:20],
                "conta": str(dados.get("conta") or "")[:40],
                "detalhe": str(dados.get("detalhe") or "")[:200],
                "em": time.time(),
            }

    def ler_conexao(self):
        with self._trava:
            return dict(self.conexao)

    def viu_presente(self, presente_id, nome, moedas, imagem=""):
        """Um presente apareceu na live. Guarda ID, nome, valor e FIGURA.

        A FIGURA E' A PARTE NOVA, E ELA RESOLVE UM PROBLEMA REAL DO PAINEL

        Uma ficha de presente identificada so' por texto ("Rose, id 5655") obriga
        quem esta' transmitindo a decorar nome e numero -- e no meio de uma live,
        com o chat andando, ninguem decora. A figura e' como o presente aparece
        pra quem esta' assistindo: bate o olho e reconhece.

        Ela vem do proprio evento do TikTok (a ponte captura a URL), entao e'
        sempre a imagem CERTA daquele presente naquela regiao -- e nao um
        desenho parecido escolhido por nos.
        """
        chave = str(presente_id or "").strip()
        if not chave or not chave.isdigit():
            return
        with self._trava:
            item = self.presentes_vistos.get(chave)
            if item is None:
                if len(self.presentes_vistos) >= 120:
                    return
                item = {"id": chave, "nome": "", "moedas": 0, "vezes": 0,
                        "imagem": ""}
                self.presentes_vistos[chave] = item
            item["nome"] = str(nome or item["nome"])[:60]
            # Endereco curto demais nao e' URL de coisa nenhuma, e endereco
            # gigante e' lixo que o painel teria que desenhar. O limite tambem
            # protege a resposta do /presentes-vistos, que o painel busca de 5
            # em 5 segundos.
            figura = str(imagem or "").strip()[:400]
            if figura.startswith("http"):
                item["imagem"] = figura
            item.setdefault("imagem", "")
            try:
                item["moedas"] = max(item["moedas"], int(moedas or 0))
            except (TypeError, ValueError):
                pass
            item["vezes"] += 1

    def ler_presentes_vistos(self):
        with self._trava:
            return sorted(self.presentes_vistos.values(),
                          key=lambda i: i["vezes"], reverse=True)[:40]

    def marcar(self, chave, quanto=1):
        with self._trava:
            self.contadores[chave] = self.contadores.get(chave, 0) + quanto

    def carimbar(self, chave, valor=None):
        with self._trava:
            self.contadores[chave] = time.time() if valor is None else valor

    def por_placar(self, dados):
        with self._trava:
            for k in ("moedas", "curtidas", "presenca"):
                lista = dados.get(k)
                if isinstance(lista, list):
                    self.placar[k] = lista[:10]

    def ler_placar(self):
        with self._trava:
            return json.loads(json.dumps(self.placar))

    def por_foco(self, dados):
        with self._trava:
            self.foco = {
                "nick": str(dados.get("nick") or "")[:60],
                "presente": str(dados.get("presente") or "")[:60],
                "tipo": str(dados.get("tipo") or "")[:20],
                "em": time.time(),
            }

    def ler_foco(self):
        with self._trava:
            return dict(self.foco)

    def ler_contadores(self):
        with self._trava:
            return dict(self.contadores)


# ══════════════════════════════════════════════════════════════════════
#  RESOLVER NICK DO ROBLOX (ajuda do painel)
# ══════════════════════════════════════════════════════════════════════
#
# O painel tem um campo "testar com o nick X". Resolver aqui, e nao no
# navegador, e' obrigatorio: a API do Roblox nao manda CORS, entao um fetch
# vindo da pagina seria bloqueado pelo navegador antes de sair.

CABECALHOS_ROBLOX = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    # Sem User-Agent de navegador a API responde 403 (o Cloudflare do Roblox
    # barra assinatura de cliente HTTP). O sintoma e' cruel: parece que o nick
    # nao existe, quando na verdade nenhuma consulta chegou a ser respondida.
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Origin": "https://www.roblox.com",
    "Referer": "https://www.roblox.com/",
}


def resolver_nick(nome):
    """Nick do Roblox -> resultado. Nunca levanta.

    DEVOLVE QUAL FOI O PROBLEMA, E NAO SO' "deu errado".

        {"ok": True,  "id": 123, "nome": "Fulano"}
        {"ok": False, "motivo": "nao_existe"}
        {"ok": False, "motivo": "sem_rede", "detalhe": "..."}

    Os dois "False" eram um `None` so', e essa era a raiz de uma queixa cara:
    o painel recebia 404 dos dois jeitos e escrevia `O nick "fulano" nao existe
    no Roblox` mesmo quando a pergunta nunca tinha chegado ao Roblox. A pessoa
    entao conferia o nick -- a unica coisa que estava certa -- em vez de olhar
    pra internet ou pros certificados desta maquina.

    O painel ja' sabia mostrar as duas frases; quem apagava a diferenca era
    esta funcao.
    """
    nome = str(nome or "").strip()
    if not nome:
        return {"ok": False, "motivo": "nao_existe"}
    corpo = json.dumps({"usernames": [nome], "excludeBannedUsers": True}).encode()
    req = urllib.request.Request("https://users.roblox.com/v1/usernames/users",
                                 data=corpo, headers=CABECALHOS_ROBLOX, method="POST")
    ctx = _rede.contexto_ssl() if _rede else None
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            dados = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            TimeoutError, ValueError) as e:
        return {"ok": False, "motivo": "sem_rede",
                "detalhe": f"{type(e).__name__}: {e}"}
    for item in (dados or {}).get("data") or []:
        if item.get("id"):
            return {"ok": True, "id": int(item["id"]),
                    "nome": item.get("name") or nome}
    # A API respondeu e nao trouxe ninguem: agora sim, o nick nao existe.
    return {"ok": False, "motivo": "nao_existe"}


# ══════════════════════════════════════════════════════════════════════
#  HTTP
# ══════════════════════════════════════════════════════════════════════

FILA = Fila()
AJUSTES = Ajustes()
ESTADO = Estado()
DIARIO = Diario()
JOGADORES = Jogadores()

# Eventos que o PAINEL injetou (botao "testar"). Ficam aqui ate' a ponte
# buscar. Nao vao direto na fila do jogo de proposito: o painel manda um
# presente CRU ("Galaxy, 1000 moedas") e quem sabe traduzir isso em efeito --
# e resolver o nick, e aplicar o combo -- e' a ponte, num lugar so'.
TESTES = []
TESTES_TRAVA = threading.Lock()


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "LiveInterativa/1.0"

    # ---------- utilidades ----------

    def log_message(self, formato, *args):
        # O log padrao imprime UMA LINHA POR REQUISICAO. Com o jogo perguntando
        # 1x/s e o painel 1x/2s, a janela vira uma cachoeira em que nenhum aviso
        # de verdade e' legivel. Os avisos que importam sao impressos na mao.
        pass

    def _responder(self, codigo, corpo=b"", tipo="application/json; charset=utf-8"):
        if isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        # O painel e os overlays sao servidos por este mesmo servidor, entao
        # CORS nao seria necessario. Mas quem poe o overlay no OBS as vezes o
        # abre de outro lugar, e um erro de CORS ali e' invisivel: a fonte fica
        # simplesmente preta, sem nenhuma mensagem.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-chave")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def _json(self, codigo, dados):
        self._responder(codigo, json.dumps(dados, ensure_ascii=False))

    def _corpo(self):
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if tamanho <= 0 or tamanho > 4_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, OSError):
            return {}

    def _autorizado(self, esperada):
        # Rodando em 127.0.0.1 nada disto e' alcancavel de fora da maquina. A
        # chave existe para o dia em que este servidor for pra nuvem: ai' e' a
        # unica coisa entre a sua live e quem quiser injetar avatar falso nela.
        return (self.headers.get("X-Chave") or "") == esperada

    def _arquivo(self, nome):
        caminho = os.path.join(WEB, nome)
        if not os.path.isfile(caminho):
            return self._responder(404, "nao encontrado", "text/plain; charset=utf-8")
        tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo == "application/javascript":
            tipo += "; charset=utf-8"
        with open(caminho, "rb") as f:
            self._responder(200, f.read(), tipo)

    # ---------- rotas ----------

    def do_OPTIONS(self):
        self._responder(204, b"", "text/plain")

    def do_GET(self):
        partes = urllib.parse.urlparse(self.path)
        rota = partes.path.rstrip("/") or "/"
        args = urllib.parse.parse_qs(partes.query)

        if rota == "/":
            self.send_response(302)
            self.send_header("Location", "/painel")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if rota == "/painel":
            return self._arquivo("painel.html")
        if rota == "/placar.html":
            return self._arquivo("placar.html")

        # O JOGO pergunta aqui, 1x por segundo.
        if rota == "/eventos":
            #[[ A LIVE NÃO PARA QUANDO A LICENÇA VENCE.
            #
            #   Este é o coração do modelo do manifesto: o que a licença
            #   protege é o CONTEÚDO (as danças de terceiro e as cenas), e
            #   não a fila de eventos.
            #
            #   Se a licença acabasse derrubando a fila, a pessoa perderia
            #   a live no meio da transmissão — e é a hora em que ela mais
            #   precisa de você. O que acontece é o oposto: a live segue
            #   normally, e o que falta é o extra. Sem aviso, sem drama.
            #
            #   Quem não pagou continua com o produto básico. Quem pagou
            #   tem tudo. E o painel diz a diferença, em uma linha. ]]
            if not self._autorizado(CHAVE_LEITURA):
                return self._json(401, {"erro": "chave de leitura invalida"})
            cru = (args.get("desde") or [None])[0]
            try:
                cursor = int(cru) if cru is not None else None
            except (TypeError, ValueError):
                cursor = None
            seq, lista = FILA.desde(cursor)
            ESTADO.carimbar("ultimo_pull")
            if lista:
                ESTADO.marcar("entregues", len(lista))
            return self._json(200, {"seq": seq, "lista": lista})

        if rota == "/ajustes":
            #[[ O PACOTE DAS CENAS VAI JUNTO DO AJUSTE.
            #
            #   O jogo pergunta aqui a cada 5 segundos, e o painel lê o mesmo
            #   endereço. Colocando a paleta no MESMO payload, os dois lados
            #   recebem a cena escolhida e a tabela de cores de uma vez -- e
            #   não existe janela em que um deles já trocou e o outro ainda
            #   mostra a cor antiga.
            #
            #   A paleta NÃO fica dentro do `ajustes.json`: ela é gerada, não
            #   gravada. ]]
            dados = AJUSTES.ler()
            if _cenas is not None:
                tema = (dados.get("geral") or {}).get("tema")
                dados["cenas"] = _cenas.pacote(tema)
            return self._json(200, dados)

        #[[ A LICENÇA, vista pelo jogo e pelo painel.
        #
        #   O painel chama sem `pacote=1` e recebe só o estado. O jogo chama
        #   COM `pacote=1` e recebe também o que a licença autoriza: os IDs
        #   das danças e as paletas das cenas.
        #
        #   Na build de venda, esses dois NÃO estão em lugar nenhum do ZIP:
        #   vêm daqui, e daqui vêm do manifesto (que está no GitHub, cifrado
        #   com a chave do cliente). ]]
        if rota == "/licenca":
            quer_pacote = "pacote=1" in (self.path or "")
            d = LICENCA.ler(com_pacote=quer_pacote)
            return self._json(200, d)

        #[[ GRAVAR A CHAVE, DEPOIS DO PAINEL.
        #
        #   O cliente digita o codigo e o codigo de ativacao no painel, e
        #   a licenca e' conferida NA HORA — o painel diz "pronto!" ou diz
        #   o que deu errado, sem esperar o proximo ciclo.
        #
        #   E' por isso que o `config\licenca.json` existe: um arquivo que
        #   o cliente preenche a mao, e que a ATUALIZACAO nunca sobrescreve
        #   (ela preserva a pasta `config` de propensao). ]]
        if rota == "/licenca/chave":
            corpo = self._corpo()
            chave = str(corpo.get("chave") or "").strip()
            ativacao = str(corpo.get("ativacao") or "").strip()
            if not chave:
                return self._json(400, {"ok": False,
                                        "erro": "a chave e' obrigatoria"})
            try:
                LICENCA.gravar_chave(chave, ativacao)
            except Exception as e:
                return self._json(500, {"ok": False, "erro": str(e)})
            valida = LICENCA.conferir()
            return self._json(200, {"ok": valida, "estado": LICENCA.ler()})

        if rota == "/placar":
            return self._json(200, ESTADO.ler_placar())

        #[[ A LISTA DE CENAS.
        #
        #   Existe separada do /ajustes por um motivo: o comando de chat
        #   `!temas` precisa da lista para responder, e ele nao tem o painel
        #   aberto. A paleta inteira nao vem aqui -- so' os nomes, que e' o que
        #   ocupa uma linha de tela. ]]
        if rota == "/cenas":
            if _cenas is None:
                return self._json(503, {
                    "erro": "este pacote nao tem o kit de cenas"})
            return self._json(200, {
                "temas": list(_cenas.ORDEM),
                "nomes": {c: (_cenas.TEMAS.get(c) or {
                    "nome": _cenas._NOME_EM_FALTA.get(c, c)})["nome"]
                    for c in _cenas.ORDEM},
                "atual": _cenas.nome_canonico(
                    (AJUSTES.ler().get("geral") or {}).get("tema")) or _cenas.PADRAO,
            })

        # A VOZ pergunta aqui pra saber em quem a camera parou.
        if rota == "/camera":
            return self._json(200, ESTADO.ler_foco())

        if rota == "/nick":
            nome = (args.get("nome") or [""])[0]
            achado = resolver_nick(nome)
            if achado.get("ok"):
                return self._json(200, achado)
            if achado.get("motivo") == "sem_rede":
                #[[ 503, E NAO 404. O painel trata os dois de forma diferente
                #   de proposito: 404 e' "o Roblox respondeu que nao existe" e
                #   503 e' "nao consegui perguntar". Devolver 404 aqui era o
                #   que fazia o painel acusar de inexistente um nick certo. ]]
                DIARIO.juntar([{
                    "nivel": "erro", "origem": "servidor",
                    "texto": ("nao consegui perguntar ao Roblox sobre o nick "
                              f"'{nome}'. {achado.get('detalhe', '')} "
                              f"(certificados: {_rede.origem_dos_certificados()}, "
                              f"{_rede.quantos_certificados()} raizes)"
                              if _rede else achado.get("detalhe", "")),
                }])
                return self._json(503, {"erro": "nao consegui falar com o Roblox",
                                        "motivo": "sem_rede",
                                        "detalhe": achado.get("detalhe", "")})
            return self._json(404, {"erro": "nick nao encontrado"})

        # A PONTE busca os testes que o painel injetou.
        if rota == "/testes":
            if not self._autorizado(CHAVE_ESCRITA):
                return self._json(401, {"erro": "chave de escrita invalida"})
            # O BATIMENTO DA PONTE. Ela bate aqui de 1 em 1 segundo mesmo com o
            # chat parado, entao e' o unico sinal que distingue "ponte viva e
            # quieta" de "janela preta fechada".
            ESTADO.carimbar("ultimo_sinal_ponte")
            with TESTES_TRAVA:
                pendentes, TESTES[:] = list(TESTES), []
            return self._json(200, {"lista": pendentes})

        if rota == "/estado":
            c = ESTADO.ler_contadores()
            agora = time.time()
            conexao = ESTADO.ler_conexao()
            return self._json(200, {
                "fila": FILA.topo(),
                "recebidos": c.get("recebidos", 0),
                "entregues": c.get("entregues", 0),
                "espectadores": c.get("espectadores", 0),
                # Segundos desde o ultimo sinal de cada lado. E' o diagnostico
                # que responde "de que lado esta' o problema?" sem abrir
                # nenhuma outra janela: ponte muda ou jogo mudo.
                "ponte_ha": round(agora - c["ultimo_push"], 1) if c.get("ultimo_push") else None,
                "jogo_ha": round(agora - c["ultimo_pull"], 1) if c.get("ultimo_pull") else None,
                "conexao": conexao,
                # O estado da licença entra no diagnóstico pelo mesmo motivo
                # do resto: a pergunta mais importante quando nada acontece
                # é "de que lado está o problema?", e "a licença caiu" é uma
                # das respostas possíveis.
                "licenca": {
                    "ok": LICENCA.ok,
                    "motivo": LICENCA.motivo,
                    "codigo": LICENCA.codigo,
                    "dados": LICENCA.ler().get("licenca", {}),
                },
                # Ha' quanto tempo a ponte deu o ultimo sinal de vida sobre a
                # conexao. Sem isto, uma ponte que MORREU aparece pro painel
                # exatamente como uma ponte conectada e quieta -- o ultimo
                # estado que ela publicou fica congelado na tela pra sempre.
                "conexao_ha": (round(agora - conexao["em"], 1)
                               if conexao.get("em") else None),
                #[[ Segundos desde QUALQUER sinal de vida da ponte.
                #
                #   O painel ja' pedia este campo e ele nunca existiu aqui: o
                #   `??` do JavaScript caia no `conexao_ha`, que so' anda
                #   quando a conexao MUDA de estado (ou de 30 em 30s). Com o
                #   vigia do painel em 12s, isso acendia "A PONTE PAROU DE
                #   RESPONDER" por 18 segundos de cada 30, com a ponte aberta e
                #   funcionando na frente da pessoa.
                #
                #   `None` enquanto a ponte nunca falou -- o painel trata
                #   ausencia como "sem vigia", e nao como "morreu". ]]
                "ponte_viva_ha": (round(agora - c["ultimo_sinal_ponte"], 1)
                                  if c.get("ultimo_sinal_ponte") else None),
            })

        if rota == "/controle":
            return self._json(200, (AJUSTES.ler().get("tiktok") or {}))

        if rota == "/jogadores":
            return self._json(200, {"lista": JOGADORES.ler()})

        if rota == "/presentes-vistos":
            return self._json(200, {"lista": ESTADO.ler_presentes_vistos()})

        if rota == "/logs":
            cru = (args.get("desde") or [None])[0]
            try:
                cursor = int(cru) if cru is not None else None
            except (TypeError, ValueError):
                cursor = None
            seq, linhas = DIARIO.desde(cursor)
            return self._json(200, {"seq": seq, "lista": linhas})

        return self._responder(404, "nao encontrado", "text/plain; charset=utf-8")

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        rota = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

        # A PONTE empurra os spawns aqui.
        if rota == "/eventos":
            if not self._autorizado(CHAVE_ESCRITA):
                return self._json(401, {"erro": "chave de escrita invalida"})
            corpo = self._corpo()
            eventos = corpo.get("eventos")
            if not isinstance(eventos, list):
                return self._json(400, {"erro": "esperava {'eventos': [...]}"})
            seq = FILA.juntar(eventos[:500])
            ESTADO.marcar("recebidos", len(eventos))
            ESTADO.carimbar("ultimo_push")
            ESTADO.carimbar("ultimo_sinal_ponte")
            return self._json(200, {"seq": seq})

        if rota == "/ajustes":
            return self._json(200, AJUSTES.salvar(self._corpo()))

        #[[ TROCAR A CENA DO CENARIO.
        #
        #   Uma rota propria, e nao um POST /ajustes generico, por dois motivos.
        #
        #   Primeiro: o POST /ajustes substitui a secao "presentes" INTEIRA, e
        #   nao mescla. Quem so' quer trocar a cor do set acabaria gravando
        #   presents vazios por cima dos que existiam -- apagando de passagem a
        #   configuracao de presentes, que e' a parte do kit que a live mais
        #   usa.
        #
        #   Segundo: o comando de chat `!cena` nao manda o pacote inteiro. Ele
        #   manda so' o nome da cena, e esta rota sabe o que fazer com um
        #   nome. Quem chama e' a ponte, que tem a chave de escrita.
        #
        #   A troca e' GRAVADA, igual a qualquer outro ajuste: quem escolheu
        #   uma cena quer ela de novo na proxima live, e nao toda vez que a
        #   live comeca. ]]
        #[[ GRAVAR A CHAVE, DEPOIS DO PAINEL -- o caminho do POST.
        #
        #   O painel manda POST em /licenca/chave; sem a rota na mesa do
        #   POST o botao do painel recebia 404 e o codigo do comprador
        #   NUNCA chegava a gravar. A regra fica com a copia do GET
        #   (mesmas ordens, mesmo caminho). ]]
        if rota == "/licenca/chave":
            corpo = self._corpo()
            chave = str(corpo.get("chave") or "").strip()
            ativacao = str(corpo.get("ativacao") or "").strip()
            if not chave:
                return self._json(400, {"ok": False,
                                        "erro": "a chave e' obrigatoria"})
            try:
                LICENCA.gravar_chave(chave, ativacao)
            except Exception as e:
                return self._json(500, {"ok": False, "erro": str(e)})
            valida = LICENCA.conferir()
            return self._json(200, {"ok": valida, "estado": LICENCA.ler()})

        if rota == "/cena":
            if _cenas is None:
                return self._json(503, {
                    "erro": "este pacote nao tem o kit de cenas"})
            corpo = self._corpo()
            pedido = corpo.get("tema")
            canonico = _cenas.nome_canonico(pedido)
            if canonico is None:
                return self._json(400, {
                    "erro": f"cena desconhecida: {pedido!r}",
                    "cenas": list(_cenas.ORDEM),
                })
            AJUSTES.salvar({"geral": {"tema": canonico}})
            DIARIO.juntar([{
                "nivel": "ok",
                "origem": "servidor",
                "texto": "cena trocada para '"
                         + (_cenas.TEMAS.get(canonico, {}).get("nome")
                            or _cenas._NOME_EM_FALTA.get(canonico, canonico)) + "'",
            }])
            return self._json(200, {"ok": True, "tema": canonico})

        # O JOGO publica os placares aqui (alimenta o overlay do OBS).
        if rota == "/placar":
            if not self._autorizado(CHAVE_LEITURA):
                return self._json(401, {"erro": "chave invalida"})
            ESTADO.por_placar(self._corpo())
            return self._json(200, {"ok": True})

        # O JOGO avisa em quem a camera parou (a voz usa isto).
        if rota == "/camera":
            if not self._autorizado(CHAVE_LEITURA):
                return self._json(401, {"erro": "chave invalida"})
            ESTADO.por_foco(self._corpo())
            return self._json(200, {"ok": True})

        # ─────────── A CONEXAO COM O TIKTOK ───────────
        #
        # O PAINEL pede (conta X, ligado/desligado) e a PONTE relata o que
        # conseguiu. Sao rotas separadas porque sao duas verdades diferentes:
        # "o que voce pediu" e "o que esta' acontecendo". Junta-las faria o
        # painel mostrar "conectado" no instante do clique, antes de o TikTok
        # ter dito qualquer coisa -- e uma conta errada apareceria como
        # conectada por varios segundos.
        if rota == "/controle":
            corpo = self._corpo()
            atual = AJUSTES.ler().get("tiktok") or {}
            conta = corpo.get("conta")
            conta = (str(atual.get("conta") or "") if conta is None
                     else str(conta))

            #[[ O @ E' CONFERIDO AQUI, ANTES DE VIRAR ORDEM PRA PONTE.
            #
            #   Um @ com espaco, com o link inteiro colado ou com um caractere
            #   invisivel junto so' dava sinal de vida 30 segundos depois, la'
            #   na ponte, e com a frase errada ("usuario nao encontrado").
            #   Descobrir no clique e dizer O QUE esta' errado poupa a live
            #   inteira.
            #
            #   So' barra quando o pedido e' pra CONECTAR: um "desconectar"
            #   com o campo vazio e' um pedido legitimo, e recusa-lo deixaria
            #   a pessoa presa numa conta ruim. ]]
            limpa, recado = (_conta.interpretar(conta) if _conta
                             else (conta.strip().lstrip("@").strip().lower(), None))
            if recado and bool(corpo.get("ligado")):
                return self._json(400, {"erro": recado, "motivo": "conta_invalida"})
            if recado:
                # DESCONECTAR com o campo baguncado nao pode apagar a conta
                # gravada: ela e' o que o painel repoe no campo na proxima vez,
                # e perde-la transforma um clique em Desconectar em "digite
                # tudo de novo".
                limpa = str(atual.get("conta") or "")

            novo = {
                "conta": limpa[:40],
                "ligado": bool(corpo.get("ligado")),
                # A revisao SOBE SEMPRE, mesmo sem nada ter mudado de valor.
                # E' o que faz "desconectar e conectar de novo na mesma conta"
                # ser uma ordem que a ponte enxerga -- comparando so' os
                # campos, esse clique nao mudaria nada e o botao pareceria
                # quebrado.
                "revisao": int(atual.get("revisao") or 0) + 1,
            }
            AJUSTES.salvar({"tiktok": novo})
            DIARIO.juntar([{
                "nivel": "info", "origem": "painel",
                "texto": ("pediu para CONECTAR em @" + novo["conta"]
                          if novo["ligado"] else "pediu para DESCONECTAR"),
            }])
            return self._json(200, novo)

        # A PONTE relata o estado real da conexao.
        if rota == "/conexao":
            if not self._autorizado(CHAVE_ESCRITA):
                return self._json(401, {"erro": "chave de escrita invalida"})
            ESTADO.por_conexao(self._corpo())
            ESTADO.carimbar("ultimo_sinal_ponte")
            return self._json(200, {"ok": True})

        # PONTE e JOGO escrevem no diario.
        if rota == "/logs":
            corpo = self._corpo()
            linhas = corpo.get("linhas")
            if not isinstance(linhas, list):
                return self._json(400, {"erro": "esperava {'linhas': [...]}"})
            return self._json(200, {"seq": DIARIO.juntar(linhas[:200])})

        if rota == "/jogadores":
            corpo = self._corpo()
            if isinstance(corpo.get("lista"), list):
                JOGADORES.por_ponte(corpo["lista"])
            if isinstance(corpo.get("tamanhos"), dict):
                JOGADORES.por_jogo(corpo["tamanhos"])
            if corpo.get("limpar_tamanhos"):
                JOGADORES.esquecer_tamanhos()
            return self._json(200, {"ok": True})

        # A PONTE avisa que viu um presente, com o ID de verdade dele.
        if rota == "/presentes-vistos":
            corpo = self._corpo()
            ESTADO.viu_presente(corpo.get("id"), corpo.get("nome"),
                                corpo.get("moedas"), corpo.get("imagem"))
            return self._json(200, {"ok": True})

        # O PAINEL simula um presente sem gastar moeda.
        if rota == "/testar":
            corpo = self._corpo()
            pedido = {
                "presente": str(corpo.get("presente") or "Teste")[:60],
                "moedas": max(0, int(corpo.get("moedas") or 0)),
                "vezes": max(1, min(int(corpo.get("vezes") or 1), 100)),
                "nick": str(corpo.get("nick") or "")[:40],
                "tipo": str(corpo.get("tipo") or "presente")[:20],
                #[[ A DANCA FORCADA do botao "ver como fica" da aba Dancas.
                #
                #   Vazio = o passo sai da regra do presente, como sempre. Com
                #   nome, a ponte troca so' a danca do efeito e o resto do
                #   caminho continua identico ao de um presente de verdade --
                #   que e' o unico jeito de o teste provar alguma coisa.
                #
                #   Nome invalido nao e' barrado aqui de proposito: quem
                #   decide o que e' uma danca valida e' o `_danca` do
                #   ponte/regras.py, num lugar so'. La' um nome desconhecido
                #   vira "danca padrao"; barrar aqui tambem seria a segunda
                #   copia da mesma regra. ]]
                "danca": str(corpo.get("danca") or "")[:20],
            }
            with TESTES_TRAVA:
                if len(TESTES) > 200:
                    return self._json(429, {"erro": "muitos testes na fila"})
                TESTES.append(pedido)
            return self._json(200, {"ok": True, "pedido": pedido})

        return self._responder(404, "nao encontrado", "text/plain; charset=utf-8")


def _porta_livre(porta):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", porta))
            return True
        except OSError:
            return False


# O mesmo piso de versao da ponte (ver ponte/deps.py, MINIMO).
#
# Este servidor sozinho rodaria num Python mais velho -- ele so' usa biblioteca
# padrao antiga. Recusar assim mesmo e' de proposito: a ponte NAO roda (a
# TikTokLive exige 3.10), e um servidor no ar sem ponte produz o pior
# diagnostico que existe neste kit -- todas as janelas abrem, o painel carrega,
# e simplesmente nao acontece nada. Melhor parar aqui, com o motivo escrito.
MINIMO = (3, 10)


def _atualizacao_ativa():
    """A atualização automática está ligada?

    Convém DESLIGAR enquanto você está mexendo no código: senão o app
    troca a versão no meio do seu trabalho.
    """
    try:
        geral = AJUSTES.ler().get("geral") or {}
        return geral.get("atualizar", True) is not False
    except Exception:
        return True


def principal():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    if sys.version_info < MINIMO:
        v = sys.version_info
        print()
        print("  ============================================================")
        print("   ESTE PYTHON E ANTIGO DEMAIS PRO KIT")
        print("  ============================================================")
        print()
        print("   O kit precisa do Python %s ou mais novo."
              % ".".join(str(n) for n in MINIMO))
        print("   Este aqui e o %d.%d (%s)" % (v.major, v.minor, sys.executable))
        print()
        print("   Rode o 1-INSTALACAO.bat: ele baixa e instala uma versao nova")
        print("   do lado, sem mexer na que ja esta ai.")
        print()
        input("   Aperte ENTER para fechar. ")
        raise SystemExit(1)

    #[[ A ATUALIZAÇÃO, antes de qualquer coisa.
    #
    #   O app se atualiza pelo GitHub. A conferida acontece AQUI, antes do
    #   servidor subir, porque aplicar um pacote por cima com o programa
    #   rodando é pedir para quebrar alguma coisa no meio.
    #
    #   E antes do servidor subir porque, se a atualização trocar o
    #   `servidor.py` justamente, é este processo que tem que estar
    #   velho -- o novo entra na próxima vez que abrir. ]]
    if _atualizacao is not None and _atualizacao_ativa():
        try:
            atualizou, mensagem = _atualizacao.atualizar()
            if atualizou:
                print()
                print("  ============================================================")
                print("   ATUALIZACAO APLICADA")
                print("  ============================================================")
                print()
                print(f"   {mensagem}")
                print()
                print("   Se a live nao subiu depois desta mensagem, feche")
                print("   as janelas pretas e rode o 2-COMECAR-LIVE-TIKTOK.bat")
                print("   de novo -- e' so' a primeira vez depois da atualizacao.")
                print()
        except Exception as e:
            print(f"  (a atualizacao nao deu certo: {e})")

    if not _porta_livre(PORTA):
        print()
        print("  ============================================================")
        print(f"   A PORTA {PORTA} JA ESTA OCUPADA")
        print("  ============================================================")
        print()
        print("   Quase sempre e' uma janela desta mesma live que ficou")
        print("   aberta de uma sessao anterior.")
        print()
        print("   Feche TODAS as janelas pretas e rode o 2-COMECAR-LIVE.bat de novo.")
        print("   Se nao achar as janelas, reiniciar o PC resolve.")
        print()
        input("   Aperte ENTER para fechar. ")
        raise SystemExit(1)

    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Manipulador)
    servidor.daemon_threads = True

    #[[ A LICENÇA, conferida ao vivo.
    #
    #   A conferida é feita numa thread à parte, e o servidor sobe na hora.
    #   A licença não pode SEGURAR a abertura do servidor: se o servidor de
    #   chaves do vendedor estiver fora do ar, a pessoa ainda precisa do
    #   painel para ver o que há de errado.
    #
    #   O que não abre é o JOGO: sem licença, /eventos devolve 403. ]]
    thread = threading.Thread(target=LICENCA.laco, daemon=True)
    thread.start()

    print()
    print("  ============================================================")
    print("   SERVIDOR DA LIVE NO AR")
    print("  ============================================================")
    print()
    print(f"   Painel de controle : http://localhost:{PORTA}/painel")
    print(f"   Overlay do OBS     : http://localhost:{PORTA}/placar.html")
    print()
    print("   Deixe esta janela ABERTA durante a live inteira.")
    print("   Se ela fechar, nada mais aparece no jogo.")
    print()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n   Servidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    # O servidor local cuida da licenca: ela e' conferida com o servidor de
    # chaves do vendedor assim que o servidor sobe (ver a classe Licenca).
    principal()
