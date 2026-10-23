"""
A VOZ DA LIVE -- narra quem a camera esta' mostrando, FORA do navegador.

POR QUE ESTE PROGRAMA EXISTE, E FORA DO NAVEGADOR

O Chrome e' o elo podre da corrente. Ele estrangula timers de aba em segundo
plano, trava audio ate' alguem clicar na pagina, e mata o contexto de
decodificacao quando quer. Cada um desses virava o mesmo sintoma no meio da
live: "parou de falar, so' volta se eu recarregar". Aqui e' um processo comum
do Windows -- ninguem minimiza, ninguem estrangula, nada disso existe.

COMO ELE SE LIGA NO RESTO

O contrato ja' estava pronto dos dois lados antes deste arquivo existir:

    Roblox  --POST /camera-->  servidor.py  --GET /camera-->  voz.py

O `Principal.server.luau` avisa em quem a camera parou (a chamada dentro do
`task.spawn`, pra uma fala perdida nunca segurar o jogo), o `servidor.py`
guarda isso em `Estado.foco`, e este programa pergunta. Nao inventei rota
nenhuma: so' plugue no que ja' existia.

O QUE ELE FALA

    quem mandou presente   ->  "Fulano mandou Rosa!"
    quem so' comentou      ->  "Olha o Fulano ai'!"

As frases tem variacao de proposito. Uma live de duas horas com UMA frase so'
vira ruido: o espectador para de ouvir no quinto avatar, e a narracao deixa de
cumprir a unica funcao que tem, que e' fazer a pessoa se reconhecer na tela.

NAO PRECISA INSTALAR NADA

Usa a voz que ja' vem no Windows (SAPI, a mesma do Narrador), chamada pelo
PowerShell. Sem pip, sem ffmpeg, sem biblioteca de audio -- porque tudo que
precisa ser instalado e' mais uma coisa que pode faltar na maquina de quem
comprou, no dia da live.

RODAR (o 2-COMECAR-LIVE.bat ja' abre esta janela):

    set SERVIDOR_URL=http://127.0.0.1:8000
    python voz.py
"""

import json
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Acentos no console do Windows: sem isto vira lixo mesmo com o chcp 65001 --
# inclusive nas mensagens de erro, que sao justo as que precisam ser lidas.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SERVIDOR = (os.environ.get("SERVIDOR_URL") or "http://127.0.0.1:8000").rstrip("/")

# De quanto em quanto tempo perguntar em quem a camera parou.
#
# 0.4s nao e' chute: a camera segura cada pessoa por alguns segundos, e uma
# consulta mais lenta que isso faz a fala sair DEPOIS de a camera ja' ter
# trocado -- o espectador ouve o nome de quem saiu da tela, que e' pior do que
# nao falar nada.
INTERVALO_S = 0.4

# O mesmo nick nao e' falado de novo dentro desta janela.
#
# A camera volta pra mesma pessoa com frequencia (ela e' escolhida por quem
# mandou presente, e quem manda um manda varios). Sem esta trava, a live vira
# o mesmo nome repetido em looping.
NAO_REPETIR_S = 25.0

FRASES_PRESENTE = [
    "{nick} mandou {presente}!",
    "Valeu {nick}, mandou {presente}!",
    "Olha o {presente} do {nick}!",
    "{nick} chegou com {presente}!",
]

FRASES_SEM_PRESENTE = [
    "Olha o {nick} ai'!",
    "Chegou o {nick}!",
    "{nick} ta' na area!",
    "E' o {nick}!",
]


def _pedir_foco():
    """Em quem a camera parou agora, ou None se o servidor nao respondeu.

    Devolver None em vez de estourar e' de proposito: o servidor pode estar
    subindo, reiniciando, ou ter morrido no meio da live. Nada disso e' motivo
    pra derrubar a narracao -- ela tenta de novo no proximo giro do laco.
    """
    try:
        req = urllib.request.Request(SERVIDOR + "/camera",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def _limpar(texto):
    """Tira o que quebraria a chamada do PowerShell.

    A frase entra numa string do PowerShell entre aspas simples, entao a aspa
    simples e' o unico caractere que precisa virar outra coisa -- um nick com
    apostrofo (`d'Angelo`) fecharia a string no meio e o comando morreria com
    erro de sintaxe, sem falar nada e sem dizer por que.

    Quebra de linha tambem sai: ela terminaria o comando ali mesmo.
    """
    return (str(texto or "")
            .replace("'", "")
            .replace("\r", " ")
            .replace("\n", " ")
            .strip())


def falar(frase):
    """Fala pela voz do Windows. Bloqueia ate' terminar, de proposito.

    Se nao bloqueasse, duas pessoas seguidas na camera virariam duas falas
    SOBREPOSTAS -- e duas vozes juntas nao sao duas informacoes, sao zero.
    O laco principal so' volta a perguntar depois que esta acabou.
    """
    frase = _limpar(frase)
    if not frase:
        return

    print("  " + frase, flush=True)

    # -NoProfile porque o perfil do PowerShell do usuario pode demorar
    # segundos pra carregar (ou falhar), e isso atrasaria CADA fala.
    comando = (
        "$ErrorActionPreference='Stop';"
        "$v=New-Object -ComObject SAPI.SpVoice;"
        "$v.Speak('" + frase + "') | Out-Null"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", comando],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=30,
            # Sem isto o Windows pisca uma janela preta A CADA FALA. Numa live
            # com o OBS capturando a tela inteira, isso aparece na transmissao.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.SubprocessError, OSError) as e:
        print("  [!] nao consegui falar: " + str(e), flush=True)


def _testar_a_voz():
    """Fala uma vez no boot, e diz na tela se nao conseguiu.

    Sem isto, uma maquina sem voz instalada ficava a live inteira em silencio
    com a janela aberta e verde, sem um unico sinal de que algo estava errado.
    Falhar aqui, no primeiro segundo, custa uma linha; falhar as 21h no meio da
    transmissao custa a live.
    """
    print("Testando a voz do Windows...", flush=True)
    falar("Voz da live ligada.")


def principal():
    print("=" * 60, flush=True)
    print(" A VOZ DA LIVE", flush=True)
    print("=" * 60, flush=True)
    print("Servidor: " + SERVIDOR, flush=True)
    print("", flush=True)

    _testar_a_voz()

    print("", flush=True)
    print("Narrando. Pode deixar esta janela de lado -- mas NAO feche:", flush=True)
    print("fechar aqui e' o que emudece a live.", flush=True)
    print("", flush=True)

    ultimo_nick = ""
    ultimo_em = 0.0
    falados = {}
    avisou_que_caiu = False

    while True:
        foco = _pedir_foco()

        if foco is None:
            # Avisa UMA vez, e nao a cada 0.4s: um servidor fora do ar por dois
            # minutos encheria a janela com trezentas linhas iguais, e a
            # mensagem que interessa (a primeira) sumiria pra cima.
            if not avisou_que_caiu:
                print("  [!] servidor nao respondeu -- seguindo tentando.",
                      flush=True)
                avisou_que_caiu = True
            time.sleep(1.0)
            continue

        if avisou_que_caiu:
            print("  servidor respondeu de novo.", flush=True)
            avisou_que_caiu = False

        nick = (foco.get("nick") or "").strip()
        presente = (foco.get("presente") or "").strip()
        em = float(foco.get("em") or 0.0)

        # `em` e' o carimbo de QUANDO a camera parou nessa pessoa. Comparar por
        # ele, e nao so' pelo nick, e' o que faz a camera voltar pra mesma
        # pessoa depois de um tempo ser narrada de novo -- sem ele, quem
        # aparecesse duas vezes na live so' era falado na primeira.
        mudou = bool(nick) and (nick != ultimo_nick or em != ultimo_em)

        if mudou:
            agora = time.time()
            if agora - falados.get(nick, 0.0) >= NAO_REPETIR_S:
                falados[nick] = agora
                if presente:
                    frase = random.choice(FRASES_PRESENTE).format(
                        nick=nick, presente=presente)
                else:
                    frase = random.choice(FRASES_SEM_PRESENTE).format(nick=nick)
                falar(frase)

            ultimo_nick = nick
            ultimo_em = em

            # A tabela cresce a cada nick novo e nunca encolhia. Numa live
            # grande sao milhares de nomes -- pequeno em memoria, mas e' o tipo
            # de vazamento que so' aparece na quinta hora de transmissao.
            if len(falados) > 500:
                corte = time.time() - NAO_REPETIR_S
                falados = {k: v for k, v in falados.items() if v >= corte}

        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    try:
        principal()
    except KeyboardInterrupt:
        print("", flush=True)
        print("Voz encerrada.", flush=True)
