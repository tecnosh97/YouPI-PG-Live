"""Ponte YouTube Live Chat -> servidor local -> Roblox.

Le comentarios e Super Chat da live pelo YouTube Data API v3. A API publica
o chat por polling, entao nao precisa abrir uma porta no roteador.
"""

import argparse
import asyncio
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.error
import urllib.request

sys.argv.append("--twitch")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ponte import Tradutor, laco_janela, laco_painel, laco_resumo, laco_testes
sys.argv.remove("--twitch")


API = "https://www.googleapis.com/youtube/v3"


def _ler_json(url):
    with urllib.request.urlopen(url, timeout=30) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def video_id(valor):
    """Aceita ID puro ou links do YouTube em formatos comuns, inclusive live."""
    valor = (valor or "").strip()
    if not valor:
        return ""

    if "youtube.com" in valor or "youtu.be" in valor:
        partes = urllib.parse.urlparse(valor)
        hostname = (partes.hostname or "").lower()
        caminho = partes.path.strip("/")

        if hostname == "youtu.be":
            return caminho.split("/")[-1]

        if "youtube" in hostname:
            qs = urllib.parse.parse_qs(partes.query)
            if qs.get("v"):
                return qs["v"][0]

            for prefixo in ("live/", "shorts/", "embed/"):
                if caminho.startswith(prefixo):
                    return caminho[len(prefixo):].split("/", 1)[0]

            if caminho and "/" not in caminho:
                return caminho

        return ""

    return valor


def eventos_da_resposta(dados):
    """Converte itens do YouTube no formato comum da ponte."""
    eventos = []
    for item in dados.get("items", []):
        trecho = item.get("snippet", {})
        autor = item.get("authorDetails", {})
        user = {
            "id": autor.get("channelId", ""),
            "nickname": autor.get("displayName", ""),
        }
        tipo = trecho.get("type")
        if tipo == "textMessageEvent":
            eventos.append({"tipo": "comentario", "user": user,
                            "texto": trecho.get("textMessageDetails", {}).get(
                                "messageText", "")})
        elif tipo == "superChatEvent":
            detalhes = trecho.get("superChatDetails", {})
            micros = int(detalhes.get("amountMicros", 0) or 0)
            eventos.append({
                "tipo": "presente", "user": user,
                "presente": "Super Chat",
                "presente_id": "youtube-super-chat",
                "moedas": max(1, micros // 1000000), "vezes": 1,
                "moedas_total": max(1, micros // 1000000),
                "texto": detalhes.get("userComment", ""),
            })
    return eventos


def obter_chat_id(video, chave):
    parametros = urllib.parse.urlencode({
        "part": "liveStreamingDetails", "id": video, "key": chave,
    })
    dados = _ler_json(f"{API}/videos?{parametros}")
    itens = dados.get("items", [])
    if not itens:
        raise RuntimeError("video nao encontrado ou sem transmissao ao vivo")
    chat_id = itens[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
    if not chat_id:
        raise RuntimeError("a live ainda nao esta ao vivo ou o chat esta desligado")
    return chat_id


async def ler_youtube(video, chave, tradutor):
    chat_id = await asyncio.to_thread(obter_chat_id, video, chave)
    pagina = ""
    intervalo = 5.0
    tradutor.relatar_conexao("conectada", f"YouTube: {video}")
    tradutor.contar(f"conectado no YouTube: video {video}", nivel="ok")
    print(f"[youtube] conectado em https://youtube.com/watch?v={video}", flush=True)

    while True:
        parametros = {
            "part": "snippet,authorDetails", "liveChatId": chat_id,
            "maxResults": 200, "key": chave,
        }
        if pagina:
            parametros["pageToken"] = pagina
        dados = await asyncio.to_thread(
            _ler_json, f"{API}/liveChat/messages?{urllib.parse.urlencode(parametros)}")
        for evento in eventos_da_resposta(dados):
            tradutor.ao_evento(evento)
        pagina = dados.get("nextPageToken", pagina)
        intervalo = max(1.0, datos_intervalo(dados, intervalo))
        await asyncio.sleep(intervalo)


def datos_intervalo(dados, anterior):
    """Usa o intervalo recomendado pela API, sem aceitar valores absurdos."""
    recomendado = dados.get("pollingIntervalMillis")
    if recomendado is None:
        return anterior
    return min(30.0, max(1.0, float(recomendado) / 1000))


async def principal():
    parser = argparse.ArgumentParser(description="Ponte YouTube Live -> Roblox")
    parser.add_argument("--video-id", default=os.environ.get("YOUTUBE_VIDEO_ID", ""))
    parser.add_argument("--api-key", default=os.environ.get("YOUTUBE_API_KEY", ""))
    parser.add_argument("--servidor", default=os.environ.get(
        "SERVIDOR_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--chave", default=os.environ.get(
        "CHAVE_ESCRITA", "escrita-local"))
    parser.add_argument("--donos", default=os.environ.get("DONOS", ""))
    parser.add_argument("--so-console", action="store_true")
    args = parser.parse_args()

    video = video_id(args.video_id)
    if not video or not args.api_key:
        parser.error("defina YOUTUBE_VIDEO_ID e YOUTUBE_API_KEY")

    tradutor = Tradutor(args.servidor, args.chave,
                        donos=[x for x in args.donos.split(",") if x.strip()],
                        simular_envio=args.so_console)
    tradutor.cfg.iniciar()
    tarefas = [laco_janela(tradutor), laco_resumo(tradutor),
               laco_testes(tradutor), laco_painel(tradutor)]

    async def manter_conexao():
        while True:
            try:
                await ler_youtube(video, args.api_key, tradutor)
            except (OSError, RuntimeError, ValueError, urllib.error.URLError) as erro:
                print(f"[youtube] conexao perdida: {erro}; tentando em 10s",
                      flush=True)
                await asyncio.sleep(10)

    tarefas.append(manter_conexao())
    await asyncio.gather(*tarefas)


if __name__ == "__main__":
    try:
        asyncio.run(principal())
    except KeyboardInterrupt:
        print("\n[youtube] encerrada.")