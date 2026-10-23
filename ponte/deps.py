"""Instala o que falta e explica o que deu errado, em portugues.

POR QUE ISTO EXISTE
-------------------
Sem isto, a primeira coisa que um comprador ve' ao abrir o kit e' um traceback
do Python -- "ModuleNotFoundError: No module named 'TikTokLive'" -- e a conclusao
dele e' que o produto veio quebrado. Ele nao abre ticket: ele pede reembolso.

Entao a regra da casa: nenhuma tela do kit mostra traceback cru. Toda falha vira
uma caixa que diz o que aconteceu, o que fazer, e so' no fim o texto tecnico
para quem for dar suporte.
"""

import subprocess
import sys

# Onde o comprador pede ajuda. Ponha aqui o link do SEU Discord ou WhatsApp
# antes da primeira venda: este texto aparece em TODA mensagem de erro do kit.
SUPORTE = "Suporte Monster -- chame no canal que veio com a sua compra."

LARGURA = 66


def caixa(titulo, linhas):
    """Uma mensagem emoldurada, legivel de relance numa janela preta."""
    print()
    print("  " + "=" * LARGURA)
    print("   " + titulo)
    print("  " + "=" * LARGURA)
    print()
    for linha in linhas:
        print("   " + linha)
    print()


def erro_fatal(titulo, linhas, detalhe=""):
    """Explica, espera o ENTER e sai. O ENTER importa: sem ele a janela fecha
    sozinha e o comprador nao chega a ler nada."""
    caixa(titulo, linhas)
    if detalhe:
        print("  " + "-" * LARGURA)
        print("   Detalhe tecnico (mande junto ao pedir ajuda):")
        print()
        for linha in str(detalhe).splitlines():
            print("   " + linha)
        print()
    try:
        input("   Aperte ENTER para fechar esta janela. ")
    except (EOFError, KeyboardInterrupt):
        pass
    raise SystemExit(1)


def python_em_uso():
    v = sys.version_info
    return f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})"


# A versao minima do Python que o kit aceita.
#
# 3.10 nao e' um numero escolhido a dedo: e' o que a TikTokLive 6.6.6 declara em
# "Requires-Python". Num Python mais velho o pip simplesmente recusa e responde
# "could not find a version that satisfies the requirement TikTokLive" -- uma
# frase que nao tem a palavra "versao do Python" em lugar nenhum e que manda o
# comprador procurar problema de internet a tarde inteira.
#
# (A ponte tambem usa asyncio.to_thread, que so' existe do 3.9 pra frente. Num
# 3.8 o kit instalava, subia, e so' quebrava na PRIMEIRA live -- com um
# AttributeError no meio da transmissao.)
MINIMO = (3, 10)


def garantir_python(minimo=MINIMO):
    """Barra Python velho AQUI, na porta de entrada.

    Os .bat ja' conferem isto antes de chamar o Python, mas quem roda o
    `ponte.py` na mao -- e quem da' suporte faz isso o tempo todo -- passa por
    fora deles. Sem esta conferencia, o mesmo problema volta disfarcado de outro.
    """
    if sys.version_info >= minimo:
        return
    pedido = ".".join(str(n) for n in minimo)
    v = sys.version_info
    erro_fatal(
        "ESTE PYTHON E' ANTIGO DEMAIS PRO KIT",
        [f"O kit precisa do Python {pedido} ou mais novo.",
         f"Este aqui e' o {v.major}.{v.minor}.",
         "",
         "Rode o 1-INSTALACAO.bat: ele baixa e instala uma versao nova do",
         "lado, sem mexer na que ja' esta' ai'.",
         "",
         SUPORTE],
        detalhe=python_em_uso())


def garantir(*pacotes):
    """garantir(("websockets", "websockets>=12.0"), ...)

    Cada par e' (nome pra importar, nome pra instalar) -- os dois nem sempre
    batem, e usar um no lugar do outro faz o pip instalar um pacote que nao
    existe.
    """
    faltando = []
    for importar, instalar in pacotes:
        try:
            __import__(importar)
        except ImportError:
            faltando.append((importar, instalar))

    if not faltando:
        return

    nomes = ", ".join(i for i, _ in faltando)
    caixa("FALTA INSTALAR UMA COISA -- eu resolvo agora",
          [f"Preciso de: {nomes}",
           "",
           "Estou baixando. Isso leva de alguns segundos a poucos minutos,",
           "dependendo da sua internet. Nao feche esta janela."])

    alvos = [instalar for _, instalar in faltando]
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
             "--quiet", *alvos])
    except (subprocess.CalledProcessError, OSError) as e:
        erro_fatal(
            "NAO CONSEGUI INSTALAR AS BIBLIOTECAS",
            ["Tentei baixar sozinho e nao deu. Quase sempre e' uma destas:",
             "",
             "  1) Sem internet, ou a internet caiu no meio.",
             "  2) Antivirus ou firewall bloqueando o Python.",
             "  3) Python instalado sem o pip.",
             "",
             "Para tentar na mao, abra o Prompt de Comando e rode:",
             "",
             f'  "{sys.executable}" -m pip install ' + " ".join(alvos),
             "",
             SUPORTE],
            detalhe=f"{type(e).__name__}: {e}")

    # Confere de novo: o pip pode sair com codigo 0 e mesmo assim o import
    # continuar falhando (versao errada, instalacao pela metade, ou o pip de
    # OUTRO Python). Sem esta conferencia o erro apareceria depois, longe daqui,
    # como se fosse outro problema.
    ainda_falta = []
    for importar, _ in faltando:
        try:
            __import__(importar)
        except ImportError:
            ainda_falta.append(importar)

    if ainda_falta:
        erro_fatal(
            "INSTALEI, MAS AINDA NAO ESTA FUNCIONANDO",
            ["A instalacao disse que deu certo, mas o Python continua sem",
             f"enxergar: {', '.join(ainda_falta)}",
             "",
             "Isso costuma ser mais de um Python instalado na maquina: o pip",
             "instalou num, e o kit esta' rodando no outro.",
             "",
             "Feche TODAS as janelas pretas e rode o 2-COMECAR-LIVE.bat de novo --",
             "so' isso ja' resolve na maioria dos casos.",
             "",
             SUPORTE],
            detalhe=python_em_uso())

    caixa("PRONTO -- bibliotecas instaladas", ["Seguindo com a live."])
