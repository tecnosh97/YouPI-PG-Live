"""Comentario do chat -> UserId do Roblox.

Duas metades bem separadas:

    achar_nick(texto)   puro, sem rede: este comentario parece um nick?
    Buscador            lote + cache contra a API do Roblox

POR QUE A PENEIRA EXISTE
------------------------
O chat de uma live e' 95% "kkkk", "bora" e emoji. Sem peneira, CADA comentario
viraria uma consulta HTTP na API do Roblox, e a conta seria fechada por abuso
antes da live acabar.

Mas a peneira e' de FORMATO, nunca de existencia. Quem decide se um nick existe
e' a API do Roblox, e so' ela pode decidir isso. Por isso a peneira e' frouxa de
proposito: deixar passar um "vamos" custa uma linha num lote de 100 nomes;
barrar um nick de verdade custa um espectador que nao aparece na live.

O ERRO QUE NAO PODE ACONTECER
-----------------------------
Errar pra MENOS (ninguem aparece) e' chato mas recuperavel: a pessoa comenta de
novo. Errar pra MAIS -- mostrar o avatar de um ESTRANHO porque alguem escreveu
uma palavra comum -- e' pior, e acontece de verdade: "que", "esse", "onde",
"vez" e "demais" sao todas contas reais no Roblox. Por isso a lista de palavras
barradas cobre a classe gramatical inteira (pronome, artigo, preposicao,
adverbio curto), e nao so' giria de chat.

REGRA DE NOME DO ROBLOX
-----------------------
3 a 20 caracteres, letras/numeros/underscore, no maximo UM underscore, e nunca
comecando nem terminando com underscore.
"""

import json
import re
import time
import urllib.error
import urllib.request

#[[ O contexto TLS (ver rede.py, ao lado).
#
#   ESTA E' A CHAMADA QUE SUSTENTA A LIVE INTEIRA: e' aqui que o nick que a
#   pessoa comentou vira um UserId, e sem UserId nao nasce avatar nenhum. Numa
#   maquina com a lista de certificados curta -- o padrao do Windows -- toda
#   consulta falhava, e o `buscar` (que engole falha de proposito, pra nao
#   derrubar a ponte no meio da transmissao) devolvia um dicionario vazio.
#
#   O sintoma era o pior possivel: a live subia, o chat andava, o painel dizia
#   que estava tudo conectado, e simplesmente ninguem aparecia na tela. ]]
try:
    from rede import contexto_ssl
except ImportError:                       # rodando de outra pasta
    def contexto_ssl():
        return None

URL_LOTE = "https://users.roblox.com/v1/usernames/users"

# ─────────────────── O cabecalho que faz a API responder ───────────────────
#
# O Roblox passou a filtrar por assinatura de cliente no Cloudflare. Sem um
# User-Agent de navegador, TODA consulta volta 403 ("browser_signature_banned")
# -- o urllib se identifica como "Python-urllib/3.x" e isso basta pra barrar.
#
# O sintoma disso na live e' o pior possivel porque e' SILENCIOSO: o codigo
# engole erro de rede de proposito (perder um avatar e' aceitavel, derrubar a
# ponte nao), so' que ai' TODA consulta falha. Nenhum comentario vira avatar,
# nunca, e a tela vazia com o chat andando e' indistinguivel de "ninguem
# comentou o nick ainda".
#
# So' o User-Agent ja' passa hoje. Origin e Referer vao junto porque e' o que um
# navegador de verdade manda nesta rota, e o conjunto envelhece melhor.
CABECALHOS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Origin": "https://www.roblox.com",
    "Referer": "https://www.roblox.com/",
}

# 3 a 20 caracteres, sem underscore nas pontas.
_FORMATO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{1,18}[A-Za-z0-9]$")

# Palavras que a pessoa usa ANTES de dizer o nick ("meu nick e Fulano"). Quando
# uma delas aparece, o nick vem logo depois -- e isso mata a ambiguidade de uma
# frase com varias palavras de formato valido.
#
# ─────────────── FORTES E FRACOS, E POR QUE A DIVISAO EXISTE ───────────────
#
# Um aviso FORTE e' uma declaracao explicita: quem escreve "nick: vamos" esta'
# mesmo dizendo que o nick dela e' "vamos", entao o forte VENCE a lista de
# palavras barradas -- senao quem se chama "Bom" ou "Legal" nunca apareceria.
#
# Um aviso FRACO e' so' uma pista de posicao. "eu", "meu" e "sou" comecam
# metade das frases de um chat, e deixa-los vencer a lista de barradas
# produzia um erro concreto e frequente: "eu quero" devolvia "quero" -- que e'
# uma conta real no Roblox -- e o kit spawnava o avatar de um estranho porque
# alguem disse que queria jogar.
#
# Os dois guiam a busca do mesmo jeito; so' o forte ignora a lista de barradas.
_AVISOS_FORTES = frozenset((
    "nick", "nome", "user", "usuario", "usuário", "conta", "chamo",
))

_AVISOS_FRACOS = frozenset((
    "roblox", "meu", "minha", "eu", "sou",
))

_AVISOS = _AVISOS_FORTES | _AVISOS_FRACOS

# Quantas palavras olhar depois do aviso antes de desistir. Existe porque "meu
# nick e Fulano" tem um "e" no caminho: parar na primeira palavra que nao serve
# devolveria a palavra errada.
_ALCANCE = 3

# Palavras de chat brasileiro que passam no formato mas nunca sao um nick.
# Ver o cabecalho do modulo: a lista e' larga de proposito.
_BARRADAS = frozenset("""
oi ola ols alo eae eai opa salve fala falae bora vamos vamo top boa boaa
mano cara mana brother irmao sim nao tmj vlw flw obg blz beleza valeu
kkk kkkk kkkkk kkkkkk kkkkkkk rsrs rs haha hahaha hehe huehue
jogo jogar joga jogou quero queria manda mandei mande entra entrei entao
aqui agora depois antes hoje ontem amanha gente live linda lindo lindao
primeiro segundo terceiro primeira segunda terceira ultimo ultima
eu tu ele ela nois nos voce voces eles elas isso essa esse essas esses
aquilo aquele aquela isto este esta estas estes demais muito pouco mto
poko cada toda todo todos todas umas uns algum alguma alguns algumas
nada tudo qualquer que quem qual quais onde quando como porque porq pq
vez vezes veses la ca ali mesmo entao mas so ai bem pra pro para com sem
sobre sempre nunca talvez ainda ja tambem so' oque cade
love like follow hello hey yes yeah yep nope lol lmao omg wow nice good
bad cool please thanks thank you hi bye plis pls
""".split()) | frozenset("""
bom otimo otima ruim melhor pior legal massa show brabo irado dahora
sinistro chique bonito bonita feio feia grande pequeno pequena novo nova
mds nossa caramba eita vish aff uau ata sla sei acho achei
suave tranquilo certo errado exato exata real verdade mentira serio
parca chefe amigo amiga galera pessoal turma povo
oi2 alguem ninguem alguma coisa coisas jeito forma vezes hora horas
dia dias mes ano anos minuto minutos segundo segundos
faz fazer fez feito ver vendo viu olha olhe veja
ta to tao eh ne neh né vai vou vem venha volta tenta tente
""".split())
#[[ A SEGUNDA LISTA VEIO DE UM TESTE QUE FALHOU, E O CASO E' EXEMPLAR.
#
#   "muito bom" no chat devolvia "bom" -- porque "muito" estava barrado e
#   "bom" nao. E `bom` e' uma conta REAL no Roblox: o kit spawnava o avatar de
#   um desconhecido porque alguem elogiou a live.
#
#   E' exatamente a classe de erro que o cabecalho deste modulo diz ser a pior:
#   errar pra MENOS custa um espectador que comenta de novo; errar pra MAIS
#   poe a skin de um estranho na tela, e a pessoa que comentou nunca entende
#   por que apareceu outro boneco.
#
#   A lista e' larga de proposito, e o custo de ser larga e' baixo: quem se
#   chama "Bom" ou "Legal" pode escrever "meu nick e Bom", que o passo 1 do
#   `achar_nick` atende -- o aviso vence a lista de barradas. ]]

# \W e' Unicode-aware no Python 3: trata letra acentuada como LETRA e so' corta
# pontuacao, emoji e simbolo de verdade.
#
# Uma classe ASCII aqui ([^A-Za-z0-9_]) teria um bug serio: "e" com acento
# tambem nao e' ASCII, e e' a ULTIMA letra de "voce" -- cortaria a palavra pra
# "voc" em vez de rejeita-la inteira. Como nome de Roblox so' aceita ASCII,
# "voce" precisa continuar "voce" pra falhar a validacao de formato, em vez de
# virar "voc" por acidente e casar com a conta de um estranho.
_BORDAS = re.compile(r"^\W+|\W+$", re.UNICODE)


def _limpar(palavra):
    """Tira pontuacao e emoji das BORDAS, preservando o miolo do nick."""
    return _BORDAS.sub("", palavra)


def _serve(palavra):
    return bool(_FORMATO.match(palavra)) and palavra.count("_") <= 1


def achar_nick(texto):
    """O provavel nick do Roblox neste comentario, ou None.

    Puro: nenhuma rede. Nao afirma que o nick EXISTE -- so' que vale a pena
    perguntar pro Roblox.
    """
    if not texto:
        return None
    palavras = [p for p in (_limpar(t) for t in str(texto).split()) if p]
    if not palavras:
        return None

    # 1) "meu nick e Fulano" -- o aviso diz que o nick vem logo a seguir.
    #
    #    So' o aviso FORTE ignora a lista de palavras barradas. Ver o comentario
    #    em _AVISOS_FORTES: "eu quero" nao pode devolver "quero".
    for i, palavra in enumerate(palavras[:-1]):
        baixa = palavra.lower()
        if baixa not in _AVISOS:
            continue
        forte = baixa in _AVISOS_FORTES
        olhadas = 0
        passou_do_bloco = False
        for seguinte in palavras[i + 1:]:
            # Os avisos costumam vir colados ("meu nick"). Enquanto estamos
            # dentro desse bloco, pula -- e um aviso FORTE encontrado no
            # caminho promove a busca: em "meu nick e Fulano", o "meu" e' fraco
            # mas o "nick" logo depois e' forte, e quem manda e' o mais forte
            # dos dois.
            if not passou_do_bloco and seguinte.lower() in _AVISOS:
                if seguinte.lower() in _AVISOS_FORTES:
                    #[[ Depois de uma declaracao EXPLICITA ("nick", "nome",
                    #   "conta"), o que vem a seguir e' o nick -- mesmo que
                    #   essa proxima palavra tambem esteja na lista de avisos.
                    #
                    #   Sem esta linha, "meu nick Roblox" nao devolvia nada:
                    #   as tres palavras sao avisos, o bloco engolia as tres, e
                    #   quem se chama Roblox (ou User, ou Conta) nunca aparecia
                    #   na live escrevendo a frase mais natural possivel. ]]
                    forte = True
                    passou_do_bloco = True
                continue
            passou_do_bloco = True
            if _serve(seguinte) and (forte or seguinte.lower() not in _BARRADAS):
                return seguinte
            olhadas += 1
            if olhadas >= _ALCANCE:
                break
        break

    # 2) Comentario de UMA palavra so' -- o caso esmagadoramente comum. A
    #    pessoa le' "comente seu nick" e comenta so' o nick.
    if len(palavras) == 1:
        unica = palavras[0]
        if _serve(unica) and unica.lower() not in _BARRADAS:
            return unica
        return None

    # 3) Frase solta: a primeira palavra com cara de nick que nao seja palavra
    #    de chat nem aviso.
    #
    #    Os avisos ficam de fora AQUI (e nao no passo 1) de proposito: "meu",
    #    "nick" e "eu" tem formato de nick valido, e sem esta exclusao uma frase
    #    como "meu nick e Roblox" que nao casasse no passo 1 devolveria "meu".
    for palavra in palavras:
        baixa = palavra.lower()
        if _serve(palavra) and baixa not in _BARRADAS and baixa not in _AVISOS:
            return palavra
    return None


class Buscador:
    """Nicks -> UserIds, em lote e com cache.

    O cache guarda ACERTOS e ERROS. Guardar os erros e' o que segura a conta:
    numa live o mesmo "kkkk" chega centenas de vezes, e sem cache negativo cada
    um viraria uma consulta.

    Erro expira mais rapido que acerto porque um nick pode ser criado a
    qualquer momento; um UserId, uma vez resolvido, e' pra sempre.
    """

    # Limite pratico da API por requisicao.
    LOTE = 100

    def __init__(self, validade_acerto=86400, validade_erro=600, timeout=10,
                 url=URL_LOTE):
        self._cache = {}   # nick minusculo -> (user_id ou None, expira_em)
        self.validade_acerto = validade_acerto
        self.validade_erro = validade_erro
        self.timeout = timeout
        self.url = url
        # Contadores de diagnostico: aparecem no resumo da janela da ponte e
        # sao a unica forma de perceber que o cache parou de funcionar.
        self.consultas = 0
        self.no_cache = 0

    def _do_cache(self, nick, agora):
        item = self._cache.get(nick.lower())
        if item is None:
            return False, None
        valor, expira = item
        if agora >= expira:
            del self._cache[nick.lower()]
            return False, None
        return True, valor

    def _gravar(self, nick, valor, agora):
        validade = self.validade_acerto if valor else self.validade_erro
        self._cache[nick.lower()] = (valor, agora + validade)

    def _consultar(self, nicks):
        """O POST cru. Separado pra ser trocado nos testes, sem rede."""
        corpo = json.dumps({"usernames": nicks, "excludeBannedUsers": True}).encode()
        req = urllib.request.Request(self.url, data=corpo, headers=CABECALHOS,
                                     method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout,
                                    context=contexto_ssl()) as r:
            return json.loads(r.read().decode("utf-8"))

    def buscar(self, nicks, agora=None):
        """{nick_original: user_id} so' pros que EXISTEM.

        Nick inexistente simplesmente nao aparece no dicionario. Falha de rede
        devolve o que deu, sem levantar: numa live, perder um avatar e'
        aceitavel; derrubar a ponte no meio da transmissao nao e'.
        """
        agora = time.time() if agora is None else agora
        achados = {}
        faltando = []
        vistos = set()

        for nick in nicks:
            if not nick or nick.lower() in vistos:
                continue
            vistos.add(nick.lower())
            tem, valor = self._do_cache(nick, agora)
            if tem:
                self.no_cache += 1
                if valor:
                    achados[nick] = valor
            else:
                faltando.append(nick)

        for i in range(0, len(faltando), self.LOTE):
            pedaco = faltando[i:i + self.LOTE]
            try:
                resposta = self._consultar(pedaco)
                self.consultas += 1
            except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                    ValueError, TimeoutError):
                # De proposito NAO cacheia: a rede volta, e o proximo
                # comentario com esse nick tenta de novo. Cachear um erro de
                # rede como "nick nao existe" apagaria a pessoa por 10 minutos.
                continue

            veio = {}
            for item in (resposta or {}).get("data") or []:
                pedido = item.get("requestedUsername") or item.get("name")
                uid = item.get("id")
                if pedido and uid:
                    veio[str(pedido).lower()] = int(uid)

            for nick in pedaco:
                uid = veio.get(nick.lower())
                self._gravar(nick, uid, agora)
                if uid:
                    achados[nick] = uid

        return achados
