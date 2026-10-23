"""Ponte Twitch IRC -> servidor local -> Roblox.

O IRC da Twitch entrega chat, Bits e notificacoes de inscricao sem exigir uma
URL publica. Os eventos sao normalizados para o mesmo Tradutor usado pelo
TikTok, portanto o jogo e o servidor nao precisam conhecer a plataforma.
"""

import argparse
import asyncio
import os
import pathlib
import ssl
import sys

# O modo Twitch reutiliza o modulo ponte.py, que fica na mesma pasta deste
# arquivo e nao e' um pacote Python separado.
sys.argv.append("--twitch")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ponte import Tradutor, laco_janela, laco_painel, laco_resumo, laco_testes
sys.argv.remove("--twitch")


IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697


def tags_do_irc(linha):
    tags = {}
    if not linha.startswith("@"):
        return tags
    bloco, _, _resto = linha.partition(" ")
    for item in bloco[1:].split(";"):
        chave, separador, valor = item.partition("=")
        if separador:
            tags[chave] = valor.replace("\\s", " ").replace("\\:", ";")
    return tags


def usuario_da_linha(linha, tags):
    sem_tags = linha.split(" ", 1)[1] if linha.startswith("@") else linha
    prefixo = sem_tags.split(" ", 1)[0].lstrip(":")
    login = prefixo.split("!", 1)[0] or tags.get("login", "")
    return {"id": login, "nickname": tags.get("display-name") or login}


def mensagem_da_linha(linha):
    _cabecalho, separador, texto = linha.rpartition(" :")
    return texto if separador else ""


def evento_da_linha(linha):
    """Converte uma linha IRC em um evento aceito pelo Tradutor."""
    tags = tags_do_irc(linha)
    if " PRIVMSG #" in linha:
        user = usuario_da_linha(linha, tags)
        bits = int(tags.get("bits", "0") or 0)
        if bits:
            return {"tipo": "presente", "user": user, "presente": "bits",
                    "presente_id": "twitch-bits", "moedas": bits,
                    "vezes": 1, "moedas_total": bits}
        return {"tipo": "comentario", "user": user,
                "texto": mensagem_da_linha(linha)}

    if " USERNOTICE #" in linha:
        user = usuario_da_linha(linha, tags)
        tipo = tags.get("msg-id", "")
        if tipo in {"sub", "resub", "subgift", "anonsubgift", "giftpaidupgrade"}:
            tier = tags.get("msg-param-sub-plan", "1000")
            try:
                valor = max(1, int(tier)) // 100
            except ValueError:
                valor = 10
            return {"tipo": "presente", "user": user,
                    "presente": "subscricao", "presente_id": "twitch-sub",
                    "moedas": valor, "vezes": 1, "moedas_total": valor}
    return None


async def conectar_twitch(canal, usuario, token, tradutor):
    contexto = ssl.create_default_context()
    reader, writer = await asyncio.open_connection(
        IRC_HOST, IRC_PORT, ssl=contexto)

    def enviar(comando):
        writer.write((comando + "\r\n").encode("utf-8"))

    enviar("CAP REQ :twitch.tv/tags twitch.tv/commands")
    enviar(f"PASS oauth:{token.removeprefix('oauth:')}")
    enviar(f"NICK {usuario}")
    enviar(f"JOIN #{canal}")
    await writer.drain()
    tradutor.relatar_conexao("conectada", canal)
    tradutor.contar(f"conectado na Twitch: #{canal}", nivel="ok")
    print(f"[twitch] conectado em https://twitch.tv/{canal}", flush=True)

    try:
        while True:
            bruto = await reader.readline()
            if not bruto:
                raise ConnectionError("servidor Twitch fechou a conexao")
            linha = bruto.decode("utf-8", errors="replace").rstrip("\r\n")
            if linha.startswith("PING"):
                enviar("PONG :tmi.twitch.tv")
                await writer.drain()
                continue
            evento = evento_da_linha(linha)
            if evento:
                tradutor.ao_evento(evento)
    finally:
        tradutor.relatar_conexao("desconectada", canal)
        writer.close()
        await writer.wait_closed()


async def principal():
    parser = argparse.ArgumentParser(description="Ponte Twitch -> Roblox")
    parser.add_argument("--canal", default=os.environ.get("TWITCH_CANAL", ""))
    parser.add_argument("--usuario", default=os.environ.get("TWITCH_USUARIO", ""))
    parser.add_argument("--token", default=os.environ.get("TWITCH_TOKEN", ""))
    parser.add_argument("--servidor", default=os.environ.get(
        "SERVIDOR_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--chave", default=os.environ.get(
        "CHAVE_ESCRITA", "escrita-local"))
    parser.add_argument("--donos", default=os.environ.get("DONOS", ""))
    parser.add_argument("--so-console", action="store_true")
    args = parser.parse_args()

    if not args.canal or not args.usuario or not args.token:
        parser.error("defina TWITCH_CANAL, TWITCH_USUARIO e TWITCH_TOKEN")

    tradutor = Tradutor(args.servidor, args.chave,
                        donos=[x for x in args.donos.split(",") if x.strip()],
                        simular_envio=args.so_console)
    tradutor.cfg.iniciar()
    tarefas = [laco_janela(tradutor), laco_resumo(tradutor),
               laco_testes(tradutor), laco_painel(tradutor)]

    async def manter_conexao():
        while True:
            try:
                await conectar_twitch(args.canal.lstrip("#").lower(),
                                      args.usuario.lower(), args.token, tradutor)
            except (OSError, asyncio.IncompleteReadError, ConnectionError) as erro:
                print(f"[twitch] conexao perdida: {erro}; tentando em 10s", flush=True)
                await asyncio.sleep(10)

    tarefas.append(manter_conexao())
    await asyncio.gather(*tarefas)


if __name__ == "__main__":
    try:
        asyncio.run(principal())
    except KeyboardInterrupt:
        print("\n[twitch] encerrada.")