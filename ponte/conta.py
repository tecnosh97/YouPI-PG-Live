# -*- coding: utf-8 -*-
"""O @ do TikTok: limpar o que a pessoa colou, e conferir se ele existe.

POR QUE ISTO E' UM ARQUIVO SO'
------------------------------
O @ entrava no kit por tres portas -- o campo do painel, a rota /controle do
servidor e o `--usuario` da linha de comando -- e cada uma limpava do seu
jeito, com um `.strip().lstrip("@")` escrito na mao. Tres limpezas parecidas
mas nao iguais e' o comeco classico do bug de "digitei certo e ele diz que nao
existe": basta uma das portas deixar passar um caractere invisivel.

Aqui a regra e' UMA. As tres portas chamam `interpretar`.

═══════════════════════════════════════════════════════════════════
O BUG QUE ESTE ARQUIVO EXISTE PRA MATAR
═══════════════════════════════════════════════════════════════════

O painel dizia **"usuario nao encontrado -- confira o @"** com o @ certo no
campo. Quem recebe essa frase faz a unica coisa que ela pede: confere o @, de
novo e de novo, e ele esta' certo o tempo todo.

A frase vinha do `UserNotFoundError` da biblioteca TikTokLive, e o problema e'
que esse erro NAO quer dizer "essa conta nao existe". Ele quer dizer tres
coisas diferentes de uma vez:

  1. o @ realmente nao existe;
  2. o @ existe, mas a conta nunca fez LIVE (o TikTok so' libera LIVE a partir
     de certo tamanho de conta) -- e ai' nao ha' nada pra conferir no @;
  3. o TikTok RECUSOU a consulta -- captcha, limite de uso, bloqueio de IP.

O caso 3 e' o mais comum de todos numa live de verdade, porque ele acontece
justamente quando a ponte reconecta varias vezes seguidas. A propria
biblioteca diz isso, em comentario, dentro do `client.py`:

    # Do not raise on UserNotFoundError as this can be a captcha issue

E entao a resposta que aparecia no painel acusava a unica coisa que estava
certa. Este arquivo separa os tres casos ANTES de a frase ser escrita: pergunta
ao TikTok, pela pagina publica do perfil, se aquele @ existe. So' um **404 de
verdade** autoriza dizer "confira o @".

E' a mesma correcao que ja' foi feita do lado do Roblox (ver `resolver_nick` no
servidor/servidor.py, com os motivos "nao_existe" e "sem_rede"): nunca
transformar "nao consegui perguntar" em "nao existe".
"""

import urllib.error
import urllib.request

try:
    from rede import contexto_ssl
except ImportError:                       # rodando de outra pasta
    def contexto_ssl():
        return None


#[[ Caracteres que a pessoa cola SEM VER.
#
#   Copiar o @ de dentro do app do TikTok, do WhatsApp ou de uma mensagem
#   formatada traz junto marca de direcao de texto e espaco de largura zero.
#   Eles nao aparecem no campo, nao aparecem no print que a pessoa manda pro
#   suporte, e o `.strip()` do Python NAO os remove: sao caracteres, nao
#   espaco em branco.
#
#   O sintoma e' exatamente o que este arquivo veio matar -- "o @ esta'
#   visivelmente certo e ele diz que nao existe". ]]
_INVISIVEIS = dict.fromkeys((
    0x200B,   # espaco de largura zero
    0x200C,   # nao-juntador
    0x200D,   # juntador
    0x200E,   # marca de esquerda-pra-direita
    0x200F,   # marca de direita-pra-esquerda
    0x2060,   # juntador de palavra
    0xFEFF,   # BOM, que vem colado em texto copiado de arquivo
    0x00AD,   # hifen condicional
))

#[[ O que o TikTok aceita num @: letra, numero, ponto e underscore, ate' 24.
#
#   A peneira e' de FORMATO, e nunca de existencia -- a mesma regra do
#   ponte/nicks.py. Quem diz se a conta existe e' o TikTok; aqui so' se barra o
#   que ele NAO CONSEGUE aceitar de jeito nenhum, pra a pessoa descobrir o erro
#   no clique em vez de depois de 30 segundos esperando uma conexao. ]]
_PERMITIDOS = set("abcdefghijklmnopqrstuvwxyz0123456789._")
MAX = 24

# Os dominios de link CURTO do TikTok (os que o botao "compartilhar" gera).
# Eles nao carregam o @ em lugar nenhum: o @ so' aparece depois de o link ser
# aberto. Adivinhar dali produziria um @ errado com cara de certo.
_CURTOS = ("vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com/v")


def _sem_invisiveis(valor):
    return str(valor or "").translate(_INVISIVEIS)


def _do_link(texto):
    """`https://www.tiktok.com/@fulano/live?lang=pt` -> `@fulano`, ou "".

    Devolve "" quando o link nao tem @ nenhum (link curto), e quem chama
    transforma isso no recado certo.
    """
    resto = texto.split("://", 1)[-1]
    dominio, _, caminho = resto.partition("/")
    if not caminho:
        return ""
    # O @ e' o que interessa; o resto do caminho (/live, /video/123) e' ruido.
    for pedaco in caminho.split("/"):
        if pedaco.startswith("@"):
            return pedaco
    # Sem @ no caminho: ou e' link curto, ou e' um link de video. Nos dois
    # casos nao da' pra saber o @ sem abrir o link.
    del dominio
    return ""


def interpretar(valor):
    """Texto qualquer -> (conta, recado).

    `conta` e' o @ limpo, em minusculas e sem arroba -- o formato que o TikTok
    usa. `recado` e' None quando deu tudo certo, ou uma frase pronta pro painel
    quando nao deu.

    Quando ha' recado, a conta volta VAZIA de proposito: gravar um @ que
    sabidamente nao serve so' faria a ponte gastar 30 segundos descobrindo
    sozinha o que ja' se sabia aqui.
    """
    texto = _sem_invisiveis(valor).strip()
    if not texto:
        return "", "Digite o seu @ do TikTok."

    baixo = texto.lower()
    if any(d in baixo for d in _CURTOS):
        return "", ("Esse é um link curto do TikTok, e ele não carrega o @ "
                    "dentro dele. Abra o link no navegador e copie o @ que "
                    "aparece no perfil (aquele que começa com arroba).")

    # So' trata como link o que TEM barra ou esquema: um @ pode conter ponto
    # ("maria.silva"), entao procurar por "tiktok.com" no texto solto barraria
    # um @ legitimo chamado justamente assim.
    if "/" in texto or baixo.startswith("http"):
        texto = _do_link(texto)
        if not texto:
            return "", ("Não achei o @ dentro desse link. Copie só o @ do "
                        "perfil (por exemplo: Monster).")

    conta = texto.strip().lstrip("@").strip().lower()
    if not conta:
        return "", "Digite o seu @ do TikTok."

    if len(conta) > MAX:
        return "", (f"Um @ do TikTok tem no máximo {MAX} caracteres, e esse "
                    f"tem {len(conta)}. Copiou a frase inteira em vez de só "
                    f"o @?")

    ruins = sorted({c for c in conta if c not in _PERMITIDOS})
    if ruins:
        # O espaco merece frase propria: e' o unico "caractere errado" que a
        # pessoa nao consegue ver escrito entre aspas.
        if " " in ruins:
            return "", ("O @ do TikTok não tem espaço. Digite só o @, sem o "
                        "resto da frase (por exemplo: Monster).")
        mostra = " ".join(f'"{c}"' for c in ruins)
        return "", (f"Um @ do TikTok só tem letras, números, ponto e "
                    f"underscore. Este tem {mostra} — confira se você não "
                    f"copiou junto algum caractere do texto em volta.")

    return conta, None


def limpar(valor):
    """So' a conta, sem o recado. Pros lugares que nao tem onde mostrar aviso."""
    return interpretar(valor)[0]


# ═══════════════════════ Esse @ existe mesmo? ═══════════════════════

# O perfil publico. E' a MESMA pagina que abre no navegador, e a resposta dela
# nao passa pelo servico de assinatura do TikTok -- ou seja, ela continua
# respondendo quando a conexao da live nao consegue subir, que e' exatamente o
# momento em que esta pergunta precisa ser feita.
URL_PERFIL = "https://www.tiktok.com/@{}"

# Sem User-Agent de navegador o TikTok devolve 403 pra tudo. O sintoma disso
# seria a propria mentira que este arquivo veio consertar: "essa conta nao
# existe" pra toda conta. Com o UA, um 404 volta a significar 404.
CABECALHOS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

EXISTE = "existe"
NAO_EXISTE = "nao_existe"
SEM_RESPOSTA = "sem_resposta"


def conferir(conta, tempo_limite=8, abrir=None):
    """O @ existe no TikTok? Nunca levanta.

    Devolve uma das tres constantes acima.

    NA DUVIDA, DIZ QUE EXISTE -- e essa assimetria e' o ponto inteiro da
    funcao. Os dois erros possiveis nao custam a mesma coisa:

      - dizer "nao existe" pra um @ que existe manda a pessoa conferir a unica
        coisa que estava certa, e foi isso que aconteceu por meses;
      - dizer "existe" pra um @ que nao existe custa a ponte tentar de novo em
        30 segundos, e a mensagem no painel continua dizendo que esta'
        tentando.

    Por isso so' um **404 explicito** vira NAO_EXISTE. Qualquer outra coisa --
    403, 500, captcha, internet caindo -- e' SEM_RESPOSTA.

    `abrir` existe pros testes: e' o `urlopen`, injetavel.
    """
    conta = limpar(conta)
    if not conta:
        return SEM_RESPOSTA

    req = urllib.request.Request(URL_PERFIL.format(conta), headers=CABECALHOS)
    abrir = abrir or urllib.request.urlopen
    try:
        with abrir(req, timeout=tempo_limite, context=contexto_ssl()) as r:
            #[[ 200 NAO E' PROVA DE QUE EXISTE, e nao precisa ser.
            #
            #   Quando o TikTok resolve barrar, ele devolve 200 com uma pagina
            #   de captcha em vez de um erro. Tratar isso como "existe" e' a
            #   escolha certa aqui: o resultado e' a ponte continuar tentando
            #   em vez de acusar o @, que e' o comportamento seguro. ]]
            del r
            return EXISTE
    except urllib.error.HTTPError as e:
        return NAO_EXISTE if e.code == 404 else SEM_RESPOSTA
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return SEM_RESPOSTA
