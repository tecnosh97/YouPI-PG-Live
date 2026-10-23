"""O MANIFESTO DE LICENÇAS — o arquivo que o app busca no GitHub.

O QUE É ISTO
------------
Um arquivo JSON, num repositório do GitHub, que diz quem pode usar o
YouPI-PG e até quando. O app busca esse arquivo na hora de subir, confere a
assinatura, e tira dele duas coisas: se a chave é válida, e o CONTEÚDO
PROTEGIDO (os IDs das animações de terceiro e as paletas das cenas).

Por que o conteúdo viaja dentro do manifesto, e não dentro do app: é o que
faz o app **degradar** em vez de quebrar. Sem chave válida, o app não
decifra o conteúdo, e a live continua funcionando com o dancing padrão e a
paleta de fábrica. Ninguém vê um erro — só falta a graça. É o
"desmontar silenciosamente" que dá pra fazer sem gritar na tela.

O FORMATO
---------
    {
      "versao": 1,
      "gerado": "2026-11-01T00:00:00",
      "chaves": {
        "<sha256 do codigo>": {
          "ate": "2026-12-01",
          "mes": "2026-11",
          "conteudo": "<blob cifrado em base64>",
          "notas": "o que o vendedor quiser lembrar"
        }
      },
      "assinatura": "<base64>"
    }

O QUE A ASSINATURA PROTEGE
--------------------------
A assinatura impede que alguém ALTERE o manifesto. Isso vale para duas
coisas, e as duas são reais:

  1. O COMPRADOR não pode se auto-autorizar. Ele tem o manifesto na mão
     (ele baixa do mesmo GitHub), e poderia acrescentar a chave dele com o
     hash que ele quiser. Sem assinatura, o app aceitaria. Com assinatura,
     o app recusa o manifesto alterado — e o app confere a assinatura com
     uma chave PÚBLICA que está no próprio código.

  2. O CANAL não pode ser sequestrado. O app busca o manifesto num
     endereço; se esse endereço fosse trocado por um servidor de alguém,
     todo mundo receberia o manifesto de outra pessoa — com um "update"
     adulterado, ou com uma licença inventada. A assinatura impede isso
     para o cliente honesto, que é o caso que importa.

A honestidade sobre o limite: um comprador que EDITE O CÓDIGO troca a
chave pública por uma sua e assina o manifesto dele. Isso continua
possível — é software local, e software local o cliente tem. O que a
assinatura garante é que o.esforço seja grande, e que a saída fácil
(apontar o app para um manifesto próprio) não funcione.

A CIFRAGEM DO CONTEÚDO
----------------------
O conteúdo é cifrado com AES-GCM, e a chave sai de:

    senha = codigo | codigo_de_ativacao | mes
    sal   = os primeiros bytes do sha256 do codigo

O CÓDIGO DE ATIVAÇÃO É O QUE IMPEDE O COMPARTILHAMENTO. O código sozinho
não decifra nada: é preciso o par. E o mês no meio da senha é o que faz a
rotação: o manifesto de dezembro é cifrado com a chave de dezembro, então
o blob de novembro não abre o app de dezembro.

O bloco que NÃO é cifrado é o que permite a degradação silenciosa: sem a
chave de decifragem, o app simplesmente não tem o conteúdo — e segue
funcionando com o que tem no próprio código.

DEPENDÊNCIA
------------
`cryptography` (pip install cryptography). Ela traz Ed25519 e AES-GCM, que
a biblioteca padrão do Python não tem.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import time

VERSAO = 1

# O ALFABETO da chave. Sem as letras que se confundem (I/1, O/0) e sem
# acento: o comprador vai dictar essa chave no telefone, provavelmente.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_RODADAS = 200_000


# ═══════════════════════════════════════════════════════════════════
#  OS CÓDIGOS
# ═══════════════════════════════════════════════════════════════════

def gerar_codigo(grupos=6, tamanho=5):
    """Um código legível: 6 grupos de 5, separados por hífen.

    O hífen não é decoração: sem ele, o código lido no telefone vira
    "ABC DE FGHJKL MN" e a mão erra. Com ele, o erro aparece no grupo,
    não no meio.
    """
    return "-".join("".join(secrets.choice(_ALFABETO) for _ in range(tamanho))
                    for _ in range(grupos))


def normalizar(valor):
    """'abc-def' -> 'ABCDEF'. A chave não tem caixa, e nem o hífen conta.

    O comprador digita o código do e-mail e às vezes cola com espaço no
    fim, ou com o hífen trocado por espaço. Recusar por causa disso é
    custar uma venda por um detalhe que ele não tem culpa.
    """
    return re.sub(r"[^A-Z0-9]", "", str(valor or "").upper())


def hash_codigo(valor):
    """O SHA-256 do código normalizado. É o índice da chave no manifesto."""
    return hashlib.sha256(normalizar(valor).encode("ascii")).hexdigest()


def mes_atual():
    """O mês no formato 'AAAA-MM'."""
    return time.strftime("%Y-%m")


def proximo_mes(mes=None):
    """O mês que vem, no formato 'AAAA-MM'."""
    mes = mes or mes_atual()
    ano, m = (int(x) for x in mes.split("-"))
    m += 1
    if m > 12:
        m = 1
        ano += 1
    return f"{ano:04d}-{m:02d}"


# ═══════════════════════════════════════════════════════════════════
#  A CIFRAGEM DO CONTEÚDO
# ═══════════════════════════════════════════════════════════════════

def derivar_chave(codigo, ativacao, mes, sal_extra=None):
    """A chave de AES que abre o conteúdo.

    A senha é o TRINCA: o código, o código de ativação e o mês. Tirar
    qualquer um dos três quebra a decifragem — e é isso que faz o
    compartilhamento de chave não funcionar e a rotação mensal ser real.
    """
    senha = f"{normalizar(codigo)}|{normalizar(ativacao)}|{mes}"
    sal = sal_extra or bytes.fromhex(hash_codigo(codigo))[:16]
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, _RODADAS)


def cifrar(conteudo, chave):
    """Cifra um dicionário e devolve base64 (nonce + texto)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    bruto = json.dumps(conteudo, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return base64.b64encode(nonce + AESGCM(chave).encrypt(nonce, bruto, None)).decode("ascii")


def decifrar(blob, chave):
    """Decifra. Devolve None se a chave estiver errada (ou o conteúdo adulterado).

    Devolve None em vez de levantar exceção porque é o caso NORMAL: o
    comprador digitou o código de ativação errado, ou a chave venceu. A
    app trata isso como "sem conteúdo", e segue funcionando.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        bruto = base64.b64decode(blob)
        if len(bruto) < 13:
            return None
        nonce, corpo = bruto[:12], bruto[12:]
        return json.loads(AESGCM(chave).decrypt(nonce, corpo, None).decode("utf-8"))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
#  A ASSINATURA
# ═══════════════════════════════════════════════════════════════════

def canonico(dados):
    """A forma exata que é assinada.

    Sorted keys, sem espaço, UTF-8. Se a forma mudasse entre quem
    assina e quem confere, a assinatura não bateria — e isso tem que ser
    uma coisa só, escrita uma vez.
    """
    return json.dumps(dados, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sem_assinatura(manifesto):
    return {k: v for k, v in manifesto.items() if k != "assinatura"}


def assinar(manifesto, chave_privada_pem):
    """Assina o manifesto (Ed25519). Devolve o base64 da assinatura."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    chave = load_pem_private_key(chave_privada_pem.encode("utf-8"), password=None)
    assinatura = chave.sign(canonico(_sem_assinatura(manifesto)))
    return base64.b64encode(assinatura).decode("ascii")


def verificar(manifesto, chave_publica_pem):
    """Confere a assinatura do manifesto. True ou False, e só.

    Devolve False (e não levanta) de propósito: um manifesto adulterado
    é um caso esperado, e a app precisa saber que "não vale" sem quebrar.
    """
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        assinatura = base64.b64decode(manifesto.get("assinatura") or "")
        chave = load_pem_public_key(chave_publica_pem.encode("utf-8"))
        chave.verify(assinatura, canonico(_sem_assinatura(manifesto)))
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
#  O MANIFESTO
# ═══════════════════════════════════════════════════════════════════

def montar(entradas, gerado=None):
    """Monta o manifesto a partir das entradas (sem assinar).

    `entradas` é a lista de fichas: {"codigo", "ativacao", "ate", "mes",
    "conteudo", "notas"}. A entrada antiga (a que venceu) é removida: o
    manifesto tem só as chaves que valem AGORA.
    """
    chaves = {}
    for e in entradas:
        if not e.get("codigo"):
            continue
        entrada = {
            "ate": str(e.get("ate") or ""),
            "mes": str(e.get("mes") or mes_atual()),
            "conteudo": str(e.get("conteudo") or ""),
        }
        if e.get("notas"):
            entrada["notas"] = str(e["notas"])[:120]
        chaves[hash_codigo(e["codigo"])] = entrada
    return {
        "versao": VERSAO,
        "gerado": gerado or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chaves": chaves,
    }


def conferir(manifesto, chave_publica_pem):
    """Confere a assinatura e devolve (ok, motivo)."""
    if not isinstance(manifesto, dict):
        return False, "o manifesto nao e' um objeto"
    if manifesto.get("versao") != VERSAO:
        return False, f"versao de manifesto desconhecida: {manifesto.get('versao')}"
    if not manifesto.get("assinatura"):
        return False, "o manifesto nao tem assinatura"
    if not verificar(manifesto, chave_publica_pem):
        return False, "a assinatura do manifesto nao confere"
    return True, "ok"


def entrada_de(manifesto, codigo):
    """A ficha do código, ou None."""
    if not isinstance(manifesto, dict):
        return None
    return (manifesto.get("chaves") or {}).get(hash_codigo(codigo))


def vencida(entrada, agora=None):
    """A entrada venceu?"""
    if not entrada:
        return True
    ate = str(entrada.get("ate") or "")
    if not ate:
        return False
    agora = agora or time.time()
    try:
        return time.mktime(time.strptime(ate[:10], "%Y-%m-%d")) < agora
    except (ValueError, TypeError):
        return False


def conteudo_de(entrada, codigo, ativacao):
    """O conteúdo protegido, ou None se o par não abrir.

    None aqui é o caso NORMAL e é o que produz a degradação silenciosa:
    sem conteúdo, o app continua funcionando com o que tem dentro dele.
    """
    if not entrada:
        return None
    mes = str(entrada.get("mes") or "")
    chave = derivar_chave(codigo, ativacao, mes)
    return decifrar(entrada.get("conteudo") or "", chave)
