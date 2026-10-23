# -*- coding: utf-8 -*-
"""Renderiza o cenario como a CAMERA DA LIVE o ve', sem abrir o Studio.

Nao e' um render bonito -- e' um instrumento de CONFERENCIA. Ele responde as
perguntas que so' se responderia apertando Play:

  - o fundo aceso cabe no quadro?
  - os avatares aparecem destacados dele, e de que tamanho?
  - a formacao cabe, ou sobra/falta cenario nas laterais?
  - como fica em 9:16?

Usa a MESMA matematica de enquadramento do Camera.client.luau (portada em
enquadramento.py), entao o que aparece aqui e' o que a lente vai fazer.
"""
import io
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CENARIO = os.path.join(RAIZ, "roblox/src/Workspace/Cenario.model.json")

# ESTES NUMEROS SAO COPIA do Config.luau (bloco CAMERA e bloco TELAO) e do
# gerar-cenario.py. Mexeu la'? Mexa aqui, senao a previa passa a mostrar um
# enquadramento que a live nao faz -- que e' pior que nao ter previa.
#
# TELAO_TOPO e' 32 e nao 56 porque a peca "Telao" e' so' a JANELA DO MEIO da
# parede do fundo (y 18..32): e' a faixa ACESA, a unica que a camera promete
# caber no quadro -- e a unica que fica acima da linha das cabecas.
TELAO_Z, TELAO_TOPO = -74.0, 32.0
ALTURA_BASE, PARTIDA, MARGEM = 1.0, 13.0, 4.0
# O topo do quadro e' o do BALAO DO NOME, e nao o da cabeca -- e' o que garante
# que o nick cabe. Ver `topoDoBalao` no Camera.client.luau.
ROTULO_ALTURA = 2.2
TELAO_RECUO_MAX = 22.0
MIN_D, MAX_D = 8.0, 120.0

#[[ O TELAO NAO TEM MAIS TEXTO, E A PREVIA DEIXOU DE DESENHAR TEXTO JUNTO.
#
#   Ate' a versao anterior esta previa carimbava as tres linhas da chamada
#   ("COMENTE SEU NICK DO ROBLOX") por cima da peca do telao, pra responder a
#   pergunta "da' pra LER isso no 9:16?".
#
#   A pergunta deixou de existir: o mapa virou uma arena de premiacao SEM UMA
#   LETRA (ver ferramentas/gerar-cenario.py -- texto no quadro e' lido como
#   isca de engajamento pela plataforma). Uma previa que continuasse
#   desenhando as linhas mostraria um enquadramento que a live nao faz, e isso
#   e' pior do que nao ter previa: e' uma previa que mente.
#
#   O que ela responde AGORA e' o que continua importando -- quanto do fundo
#   aceso aparece atras da galera, e de que tamanho cada avatar fica. Essa
#   conta e' a mesma, e ela e' a razao de o `Telao` continuar existindo como
#   peca com nome proprio mesmo sem carregar recado nenhum. ]]

# A formacao, do Config.luau.
POR_FILA, ESPACO_X, ESPACO_Z = 10, 6, 8


# ─────────────────── O solver (igual ao do Luau) ───────────────────

def elevacao(yp, zp, ycam, zcam):
    return math.degrees(math.atan2(yp - ycam, max(zcam - zp, 0.01)))


def topo_do_balao(pes, topo, escala):
    """Onde termina o BALAO DO NOME -- o topo de verdade do quadro.

    Igual ao `topoDoBalao` do Camera.client.luau. Sem ele a previa mostraria
    um enquadramento mais folgado que o da live, e o defeito que ele veio
    prevenir (o nick cortado pela borda de cima) nao apareceria aqui.
    """
    return (pes + (topo - pes) * 0.78 + ROTULO_ALTURA * escala
            + 1.1 * math.sqrt(escala))


def resolver(alvo_z, pes, topo, fov, escala=1.0, partida=None,
             teto_telao=None, margem=None, altura_base=None):
    """`altura_base` poe a lente onde o chamador quiser -- o close a poe no
    MEIO do que precisa caber, que e' o que faz o eixo sair reto."""
    base = ALTURA_BASE if altura_base is None else altura_base
    ycam = pes + base + (topo - pes) * 0.5
    topo_quadro = topo_do_balao(pes, topo, escala)
    limite = fov - 2 * (MARGEM if margem is None else margem)
    partida = PARTIDA if partida is None else partida

    def abertura(d, com_telao):
        zc = alvo_z + d
        angs = [elevacao(pes, alvo_z, ycam, zc),
                elevacao(topo_quadro, alvo_z, ycam, zc)]
        if com_telao:
            angs.append(elevacao(TELAO_TOPO, TELAO_Z, ycam, zc))
        return min(angs), max(angs)

    def cabe(d, ct):
        lo, hi = abertura(d, ct)
        return hi - lo <= limite

    # O telao empurra a lente ate' aqui e para: passando disso, o solver
    # desiste dele e entrega o plano de perto (ver CAMERA.TELAO_RECUO_MAX).
    teto = min(TELAO_RECUO_MAX if teto_telao is None else teto_telao, MAX_D)

    com_telao = True
    if cabe(partida, True):
        d = partida
    elif teto > partida and cabe(teto, True):
        lo, hi = partida, teto
        for _ in range(18):
            m = (lo + hi) / 2
            if cabe(m, True):
                hi = m
            else:
                lo = m
        d = hi
    else:
        com_telao = False
        if cabe(partida, False):
            d = partida
        else:
            lo, hi = partida, MAX_D
            for _ in range(18):
                m = (lo + hi) / 2
                if cabe(m, False):
                    hi = m
                else:
                    lo = m
            d = hi

    d = max(MIN_D, min(MAX_D, d))
    lo, hi = abertura(d, com_telao)
    return d, (lo + hi) / 2, ycam


# ─────────────────── Projecao ───────────────────

class Camera:
    def __init__(self, pos, pitch_graus, fov, larg, alt):
        self.pos = pos
        self.pitch = math.radians(pitch_graus)
        self.fov = math.radians(fov)
        self.larg, self.alt = larg, alt
        self.f = (alt / 2) / math.tan(self.fov / 2)

    def ver(self, p):
        """Mundo -> espaco da camera. Devolve (x, y, profundidade)."""
        dx = p[0] - self.pos[0]
        dy = p[1] - self.pos[1]
        dz = p[2] - self.pos[2]
        # A camera olha pra -Z, inclinada pelo pitch em torno de X.
        c, s = math.cos(self.pitch), math.sin(self.pitch)
        ry = dy * c - (-dz) * s
        rz = dy * s + (-dz) * c
        return dx, ry, rz

    def projetar(self, v):
        """Ponto JA' no espaco da camera -> tela."""
        x, y, z = v
        return (self.larg / 2 + x * self.f / z,
                self.alt / 2 - y * self.f / z, z)

    def tela(self, p):
        v = self.ver(p)
        if v[2] <= PERTO:
            return None
        return self.projetar(v)


# O PLANO PROXIMO, e por que ele precisa existir.
#
# Sem recorte, qualquer face com UM canto atras da camera era descartada
# inteira -- e as pecas maiores do cenario (o piso, de 340 studs de fundura, e
# a plataforma) SEMPRE tem um canto atras, porque a camera fica em cima delas.
# O resultado era um render sem chao nenhum: o piso e a plataforma nao
# apareciam, e a previa acusava falta de cenario onde nao faltava nada.
#
# Com o recorte, a face que atravessa o plano e' cortada e a parte da frente e'
# desenhada -- que e' o que a placa de video faz de verdade.
PERTO = 0.5


def recortar(pontos):
    """Sutherland-Hodgman contra o plano proximo, no espaco da camera."""
    fora = []
    for i in range(len(pontos)):
        atual = pontos[i]
        proximo = pontos[(i + 1) % len(pontos)]
        dentro_a = atual[2] > PERTO
        dentro_p = proximo[2] > PERTO
        if dentro_a:
            fora.append(atual)
        if dentro_a != dentro_p:
            t = (PERTO - atual[2]) / (proximo[2] - atual[2])
            fora.append(tuple(atual[k] + (proximo[k] - atual[k]) * t
                              for k in range(3)))
    return fora


# Os cantos sao gerados como bit2=sinal de Y, bit1=X, bit0=Z (ver `cantos`).
# Esta tabela precisa casar com essa ordem; quando ela nao casa, as normais
# ficam trocadas, o descarte de faces de costas apaga as erradas e o render
# mostra buracos pretos e pecas sumidas.
FACES = [
    ((4, 5, 7, 6), (0, 1, 0)),    # topo
    ((0, 2, 3, 1), (0, -1, 0)),   # fundo
    ((0, 1, 5, 4), (-1, 0, 0)),   # esquerda
    ((2, 6, 7, 3), (1, 0, 0)),    # direita
    ((0, 4, 6, 2), (0, 0, -1)),   # tras
    ((1, 3, 7, 5), (0, 0, 1)),    # frente
]

LUZ = (-0.35, 0.88, 0.32)


def cantos(pos, tam):
    hx, hy, hz = tam[0] / 2, tam[1] / 2, tam[2] / 2
    return [(pos[0] + sx * hx, pos[1] + sy * hy, pos[2] + sz * hz)
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def poligonos(cam, pos, tam, cor):
    """As faces visiveis desta caixa, ja' em coordenadas de tela."""
    cs = cantos(pos, tam)
    # A ordem do `cantos` e' sx,sy,sz -- reindexa pro esquema das FACES.
    idx = [0, 1, 4, 5, 2, 3, 6, 7]
    cs = [cs[i] for i in idx]

    fora = []
    for ordem, normal in FACES:
        centro = [sum(cs[i][k] for i in ordem) / 4 for k in range(3)]
        pra_cam = [cam.pos[k] - centro[k] for k in range(3)]
        if sum(normal[k] * pra_cam[k] for k in range(3)) <= 0:
            continue                                   # face de costas
        vistos = recortar([cam.ver(cs[i]) for i in ordem])
        if len(vistos) < 3:
            continue                                   # inteira atras da lente
        pts = [cam.projetar(v) for v in vistos]

        lambert = max(0.0, sum(normal[k] * LUZ[k] for k in range(3)))
        brilho = 0.45 + 0.55 * lambert
        rgb = tuple(min(255, int(c * 255 * brilho)) for c in cor)
        prof = sum(p[2] for p in pts) / len(pts)
        fora.append((prof, [(p[0], p[1]) for p in pts], rgb))
    return fora


# ─────────────────── O cenario ───────────────────

def carregar_pecas():
    d = json.load(io.open(CENARIO, encoding="utf-8"))
    pecas = []

    def andar(no):
        p = no.get("properties") or {}
        if "Size" in p and "CFrame" in p:
            pecas.append((no.get("name", "?"),
                          [float(v) for v in p["Size"]],
                          [float(v) for v in p["CFrame"][:3]],
                          [float(v) for v in p.get("Color", [0.6, 0.6, 0.6])]))
        for c in no.get("children") or []:
            andar(c)

    andar(d)
    return pecas


def avatares(quantos, escalas=None):
    """Bonecos de mentira nas posicoes que a Formacao daria."""
    fora = []
    for i in range(quantos):
        escala = (escalas or {}).get(i, 1.0)
        fileira, col = divmod(i, POR_FILA)
        if fileira % 2 == 1:
            col = POR_FILA - 1 - col
        x = (col - (POR_FILA - 1) / 2) * ESPACO_X
        z = fileira * ESPACO_Z
        # Corpo + cabeca, so' pra a silhueta ler como gente.
        fora.append(([1.9 * escala, 4.2 * escala, 1.1 * escala],
                     [x, 2.1 * escala, z], [0.24, 0.45, 0.85]))
        fora.append(([1.5 * escala, 1.5 * escala, 1.5 * escala],
                     [x, 5.0 * escala, z], [0.98, 0.85, 0.62]))
    return fora


ZOOM_DISTANCIA = 9.0
ZOOM_MARGEM = 2.0


def render(nome, larg, alt, fov, quantos, escalas=None, alvo=None, close=False):
    escalas = escalas or {}
    alvo = alvo if alvo is not None else quantos - 1
    fileira = alvo // POR_FILA
    esc_alvo = escalas.get(alvo, 1.0)
    #[[ O CLOSE DE CHEGADA: corta na cintura, parte de muito mais perto e nao
    #   pede o telao. Ver `destinoZoom` no Camera.client.luau. ]]
    extra = {}
    if close:
        topo_q = topo_do_balao(0.0, 6.0 * esc_alvo, esc_alvo)
        extra = dict(partida=ZOOM_DISTANCIA * esc_alvo, teto_telao=0.0,
                     margem=ZOOM_MARGEM,
                     altura_base=topo_q / 2 - 6.0 * esc_alvo * 0.5)
    d, eixo, ycam = resolver(fileira * ESPACO_Z, 0.0, 6.0 * esc_alvo, fov,
                             esc_alvo, **extra)

    cam = Camera((0, ycam, fileira * ESPACO_Z + d), eixo, fov, larg, alt)

    tudo = []
    for _, tam, pos, cor in carregar_pecas():
        tudo += poligonos(cam, pos, tam, cor)
    for tam, pos, cor in avatares(quantos, escalas):
        tudo += poligonos(cam, pos, tam, cor)

    tudo.sort(key=lambda t: -t[0])           # pintor: do fundo pra frente

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg}" '
           f'height="{alt}" viewBox="0 0 {larg} {alt}">',
           f'<rect width="{larg}" height="{alt}" fill="#12141c"/>']
    for _, pts, (r, g, b) in tudo:
        pontos = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        svg.append(f'<polygon points="{pontos}" fill="rgb({r},{g},{b})"/>')

    svg.append("</svg>")
    destino = os.path.join(RAIZ, "previas")
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, nome)
    io.open(caminho, "w", encoding="utf-8").write("\n".join(svg))
    print(f"{nome}: camera em z={cam.pos[2]:.1f} y={ycam:.1f} "
          f"pitch={eixo:.1f} deg, distancia {d:.1f}")
    return caminho


if __name__ == "__main__":
    # FOV 40 nos dois formatos -- a lente fechada da camera nova. Ver o bloco
    # CAMERA do Config.luau pra o porque de nao ser mais 62/68.
    render("previa-16x9.svg", 1280, 720, 40, 34)
    render("previa-9x16.svg", 608, 1080, 40, 34)
    render("previa-cheia.svg", 1280, 720, 40, 100)
    render("previa-presente.svg", 1280, 720, 40, 34,
           escalas={33: 4.0}, alvo=33)
    #[[ A FILEIRA 0 e' o caso APERTADO da LARGURA: a camera esta' o mais longe
    #   possivel do fundo (a formacao inteira ainda esta' na frente dela), e e'
    #   ai' que a fatia visivel da parede e' a mais estreita -- 26% da largura
    #   dela, no 9:16. E' o quadro em que o fundo aceso menos ajuda a separar a
    #   galera, entao e' o que decide se o degrade de valor esta' certo.
    #
    #   O alvo e' o 5 e nao o 3 porque a previa poe a lente sempre em x=0,
    #   enquanto a camera de verdade acompanha o X de quem ela segue. O 5 nasce
    #   quase no meio da fileira, entao os dois coincidem e o quadro sai
    #   honesto -- com um alvo da ponta, ele apareceria vazio. ]]
    render("previa-fileira0.svg", 608, 1080, 40, 34, alvo=5)
    #[[ O CLOSE, que e' o que a galera ve' no instante em que comenta. E' aqui
    #   que se confere a unica coisa que importa de perto: da' pra ver a SKIN,
    #   e o boneco esta' destacado do fundo? ]]
    render("previa-close.svg", 608, 1080, 40, 34, alvo=25, close=True)
    render("previa-close-169.svg", 1280, 720, 40, 34, alvo=25, close=True)
