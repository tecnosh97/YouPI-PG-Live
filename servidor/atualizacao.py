"""A ATUALIZAÇÃO — o app se atualiza sozinho, pelo GitHub.

O QUE É ISTO
------------
O app consulta o GitHub do dono e, se houver uma versão nova, baixa e
aplica. A pessoa que comprou não precisa baixar nada: o kit se conserta
sozinho.

Isso resolve o problema de sempre de um produto vendido como ZIP: cliente
com versão velha, erro que só se corrige no arquivo novo, e o "instala de
novo" que ninguém quer fazer no meio da live.

COMO A VERSÃO É COMPARADA
-------------------------
Por um ARQUIVO `VERSAO` na raiz do repositório, com o número da versão
("1.0.3"). O app lê esse arquivo no GitHub e compara com o `VERSAO` local.

Por que um arquivo, e não a tag de uma release? Porque a publicação é um
`git push` para o ramo, e o cliente baixa o ramo inteiro — é o que faz o
programa se atualizar sem ninguém clicar em nada. Releases seriam uma
etapa a mais, e o cliente teria de instalar o GitHub CLI para isso.

O QUE A ATUALIZAÇÃO NÃO TOCA
----------------------------
A pasta `config`. É onde mora a licença do cliente, o @ do TikTok e as
preferências dele. Atualizar o programa não pode apagar a configuração de
quem está usando — e o `config` do repositório é o do VENDEDOR (com a
chave vazia), então copiar por cima apagaria a chave do cliente.

Também não apaga nada. Um arquivo que sumiu numa versão nova continua
existindo na máquina do cliente até a próxima instalação limpa. Isso é
preferível a apagar o `rojo.exe` (que não vai no repositório) e quebrar o
jogo inteiro.
"""

import io
import json
import os
import shutil
import ssl
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# Onde o app busca as versões novas.
#
# O PROGRAMA fica num repositório próprio, e o MANIFESTO de licenças em
# outro. São coisas diferentes com destinos diferentes: o primeiro é o que o
# cliente baixa, o segundo é o que o cliente consulta para saber se a chave
# vale.
REPO_PADRAO = os.environ.get("YOUPI_REPO_APP") or "tecnosh97/YouPI-PG-Live"
RAMO_PADRAO = os.environ.get("YOUPI_RAMO_APP") or "main"

# A pasta que a atualização NÃO toca.
PRESERVAR = ("config",)

VERSAO_PADRAO = "1.0.0"


def versao_local():
    """A versão que está neste computador agora."""
    try:
        with io.open(os.path.join(RAIZ, "VERSAO"), "r", encoding="utf-8-sig") as f:
            v = f.read().strip()
            if v:
                return v
    except (OSError, ValueError):
        pass
    return VERSAO_PADRAO


def _versao_para_numeros(texto):
    """'1.2.3' -> (1, 2, 3). O que não é número vira 0."""
    limpo = str(texto or "").strip().lstrip("vV")
    partes = []
    for p in limpo.split("."):
        digitos = "".join(c for c in p if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes[:3])


def mais_nova(versao_atual, versao_nova):
    """A versão nova é mais nova que a atual?"""
    return _versao_para_numeros(versao_nova) > _versao_para_numeros(versao_atual)


def _pedir(url, token=None, timeout=15):
    cabecalhos = {"User-Agent": "YouPI-PG/1.0"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def url_da_versao(repo=REPO_PADRAO, ramo=RAMO_PADRAO):
    """O endereço do arquivo VERSAO no repositório."""
    return (f"https://raw.githubusercontent.com/{repo}/{ramo}/VERSAO")


def url_do_pacote(repo=REPO_PADRAO, ramo=RAMO_PADRAO):
    """O endereço do pacote com o programa inteiro."""
    return f"https://github.com/{repo}/archive/refs/heads/{ramo}.zip"


def verificar(repo=REPO_PADRAO, ramo=RAMO_PADRAO, token=None):
    """A versão mais nova no repositório.

    Devolve (versao, url_do_pacote) ou (None, motivo).
    """
    try:
        bruto = _pedir(url_da_versao(repo, ramo), token)
    except urllib.error.HTTPError as e:
        return None, f"o GitHub respondeu {e.code}"
    except Exception as e:
        return None, f"nao consegui falar com o GitHub: {e}"

    try:
        versao = bruto.decode("utf-8", "replace").strip()
    except Exception:
        return None, "a versao do repositorio veio ilegivel"

    if not versao:
        return None, "o repositorio nao tem o arquivo VERSAO"

    if not mais_nova(versao_local(), versao):
        return None, f"ja' esta' na ultima versao ({versao_local()})"

    return versao, url_do_pacote(repo, ramo)


def baixar(url, destino_zip, token=None):
    """Baixa o pacote."""
    req = urllib.request.Request(url, headers={"User-Agent": "YouPI-PG/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        with open(destino_zip, "wb") as f:
            shutil.copyfileobj(r, f)
    return destino_zip


def aplicar(arquivo_zip, destino=RAIZ, preservar=PRESERVAR):
    """Aplica o pacote por cima da pasta do app.

    Devolve (ok, quantos_itens).

    DUAS REGRAS, e as duas importam mais do que parecem:

      1. O `config` NUNCA e' sobrescrito. E' onde mora a licença de quem
         esta' usando, e o `config` do repositorio e' o do vendedor (com a
         chave vazia) — copiar por cima apagaria a chave do cliente.

      2. NADA E' APAGADO. Um arquivo que saiu numa versao nova continua
         na maquina ate a proxima instalacao limpa. Apagar seria perigoso:
         o `rojo.exe` nao vai no repositorio (21 MB), e sem ele o jogo
         deixa de remontar.
    """
    pasta = tempfile.mkdtemp(prefix="atualizacao-")
    try:
        with zipfile.ZipFile(arquivo_zip) as z:
            z.extractall(pasta)

        # o zip vem com uma pasta na raiz (YouPI-PG-Live-main/...)
        raiz = pasta
        entradas = [e for e in os.listdir(pasta) if not e.startswith("__MACOSX")]
        if len(entradas) == 1 and os.path.isdir(os.path.join(pasta, entradas[0])):
            raiz = os.path.join(pasta, entradas[0])

        copiados = 0
        pulados = 0
        for item in os.listdir(raiz):
            if item in preservar:
                pulados += 1
                continue
            origem = os.path.join(raiz, item)
            destino_item = os.path.join(destino, item)
            try:
                if os.path.isdir(origem):
                    shutil.copytree(origem, destino_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(origem, destino_item)
                copiados += 1
            except OSError:
                pass
        return True, copiados
    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def atualizar(destino=RAIZ, repo=REPO_PADRAO, ramo=RAMO_PADRAO, token=None,
              forcar=False):
    """O caminho inteiro: consulta, compara, baixa e aplica.

    Devolve (atualizou, mensagem).
    """
    if forcar:
        versao = "forcada"
        url = url_do_pacote(repo, ramo)
    else:
        versao, url = verificar(repo, ramo, token)
        if not url:
            return False, url or "nao achei versao nova"

    temporario = os.path.join(tempfile.gettempdir(), "youpi-pg-update.zip")
    try:
        baixar(url, temporario)
        ok, resultado = aplicar(temporario, destino)
    except Exception as e:
        return False, f"nao consegui aplicar a atualizacao: {e}"
    finally:
        try:
            os.remove(temporario)
        except OSError:
            pass

    if not ok:
        return False, f"nao consegui aplicar a atualizacao: {resultado}"
    return True, f"atualizado para {versao} ({resultado} itens)"
