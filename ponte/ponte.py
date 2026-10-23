"""A ponte: le' a sua live do TikTok e entrega spawns pro servidor local.

    TikTok Live  -->  ponte.py  --POST /eventos-->  servidor  <--GET--  Roblox

O que ela faz, em ordem:

  1. conecta na sua live e escuta comentario, presente, curtida, seguir e
     compartilhar;
  2. acha nick do Roblox no meio do chat e resolve pra UserId (em lote);
  3. aplica as regras de presente (do painel, com regras.py de reserva);
  4. empurra pro servidor no ritmo que o jogo consegue engolir.

MODOS

    python ponte/ponte.py --usuario seu_arroba     live de verdade
    python ponte/ponte.py --simular                eventos falsos, sem live

O modo simular existe pra voce configurar o painel do seu jeito ANTES da
primeira live de verdade. Configurar no ar, com gente assistindo, e' o caminho
mais rapido pra uma live ruim.
"""

import argparse
import asyncio
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request

import deps

# ANTES de qualquer outra coisa: Python velho demais nao passa daqui. Se passar,
# o erro reaparece la' na frente disfarcado de "nao consegui instalar a
# biblioteca" (o pip recusando a TikTokLive por causa da versao) ou, pior, de um
# AttributeError no meio da primeira live.
deps.garantir_python()

# ANTES dos imports pesados: se faltar biblioteca, resolve sozinho e explica.
#
# So' no modo LIVE. O modo simulacao nao fala com o TikTok, e exigir a biblioteca
# dele ali faria a primeira experiencia de quem comprou -- que e' justamente o
# 4-MODO-TESTE.bat -- comecar com um download de varios minutos, sem necessidade
# nenhuma. Olhar o argv na mao (em vez de esperar o argparse) porque este
# import precisa acontecer antes de qualquer coisa pesada.
if "--simular" not in sys.argv and "--twitch" not in sys.argv:
    deps.garantir(("TikTokLive", "TikTokLive>=6.6.6"))

#[[ O `certifi` E' EXIGIDO SEPARADO, E NAO DE CARONA NA TikTokLive.
#
#   Ele quase sempre ja' vem junto dela, e por isso passou tanto tempo sem
#   ninguem declarar: funcionava por acidente. No dia em que a TikTokLive troca
#   de cliente HTTP, o certifi some da maquina e o que quebra e' RESOLVER NICK
#   -- ou seja, a live sobe e ninguem aparece, sem nenhuma mensagem ligando uma
#   coisa a outra.
#
#   Vale tambem no MODO SIMULACAO: ele nao fala com o TikTok, mas fala com o
#   Roblox pra transformar nick em UserId, e e' exatamente o caminho que este
#   pacote conserta.
#
#   Ver ponte/rede.py pro motivo de a lista do Windows nao bastar. ]]
deps.garantir(("certifi", "certifi"))

import nicks          # noqa: E402
import painel         # noqa: E402
import regras         # noqa: E402

# O @ da live: limpar o que foi colado e conferir se ele existe DE VERDADE
# antes de acusar a digitacao de alguem. Ver o cabecalho de ponte/conta.py --
# ele explica por que "UserNotFoundError" nao pode virar "confira o @".
#
# Importado como `tiktok` porque este laco ja' tem variaveis chamadas `conta` e
# `arroba`, e um modulo com o mesmo nome de uma variavel local e' um modulo que
# some no meio da funcao onde ele mais e' preciso.
import conta as tiktok   # noqa: E402

# O console do Windows abre em cp1252, e apelido de TikTok e' cheio de emoji
# ("Maria (coracao)"). Sem isto, imprimir o nome de quem acabou de mandar
# presente levanta UnicodeEncodeError e derruba a ponte -- no meio da live.
# errors="replace" porque um emoji virar "?" no log e' sempre melhor do que
# perder o evento.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# =========================== Constantes de ritmo ===========================

# Janela de agrupamento dos comentarios antes de consultar o Roblox. Numa live
# movimentada chegam dezenas de comentarios por segundo e a API aceita 100 nomes
# por requisicao: 1s de espera troca ~50 requisicoes por 1. O espectador nao
# percebe 1 segundo; a API percebe muito.
JANELA_S = 1.0

# Presente de quem ainda nao disse o nick fica guardado por este tempo.
#
# Sem isto, quem manda presente e SO' DEPOIS comenta o nick -- que e' a ordem
# natural, ja' que o presente e' o impulso e o nick e' o passo seguinte --
# entraria como espectador comum e perderia exatamente o que pagou.
VALIDADE_ORFAO_S = 180

# De quanto em quanto tempo a CHUVA cospe mais um avatar. 1,5s em 30s da' 20
# avatares: um quinto da formacao inteira vindo de uma pessoa so', que e' o
# ponto de um presente desse valor.
CHUVA_INTERVALO_S = 1.5

# Quantos spawns a ponte empurra por segundo, no maximo.
#
# Casa com o ritmo do jogo: 0,4s de `segura` por comentario mais ~0,15s pra
# montar o avatar da' cerca de 1,8 por segundo. Empurrar mais que isso e'
# desperdicio -- o excedente so' engorda a fila do jogo com gente velha.
#
# Filtrar AQUI, e nao no jogo, e' melhor por um motivo: aqui ainda se sabe o que
# e' presente e o que e' comentario, entao da' pra jogar fora comentario antigo
# e nunca um presente.
#
# Se mudar o `segura` do COMENTARIO em regras.py, refaca a conta:
#     TETO_POR_SEGUNDO ~= 1 / (segura + 0.15)
TETO_POR_SEGUNDO = 1.8

# Teto do credito acumulado, em segundos de orcamento. Sem teto, um minuto de
# silencio viraria uma enxurrada quando a live voltasse a movimentar.
#
# Derivado do teto (e nao um numero solto) porque um credito ABAIXO do teto por
# segundo estrangula a taxa em silencio -- o tipo de bug que so' aparece meses
# depois, quando alguem sobe o teto e nada muda.
CREDITO_MAX = TETO_POR_SEGUNDO * 2

# Comandos de teste: digitar isto no chat da SUA live dispara o mesmo efeito do
# presente, sem gastar moeda.
#
# So' funcionam pra quem esta' na lista de donos (por padrao, so' voce). Isso
# nao e' paranoia: o comando faz de graca exatamente o que o presente faz pago
# -- liberar pro publico mataria o motivo de alguem mandar presente.
COMANDOS = {
    "!teste": ("Teste", 1),
    "!medio": ("Teste Medio", 10),
    "!grande": ("Teste Grande", 30),
    "!enorme": ("Teste Enorme", 200),
    "!lenda": ("Teste Lenda", 1000),
}


def _arroba(valor):
    """@Fulano, Fulano, FULANO -> fulano. O TikTok manda o @ sem arroba.

    SO' PRA COMPARAR IDENTIDADE de quem aparece nos eventos (a lista de
    `donos`, que libera os comandos de teste). O @ DA LIVE passa pelo
    `conta.interpretar`, que e' bem mais rigoroso.

    A diferenca nao e' descuido: `nickname` de espectador tem acento, emoji e
    espaco, e vale como chave de comparacao do jeito que vier. Passar ele pela
    peneira de formato do conta.py transformaria "José" em vazio dos dois
    lados da comparacao -- e o dono da live perderia os proprios comandos.
    """
    return str(valor or "").strip().lstrip("@").lower()


def _nome_chave(nickname):
    """O nome de exibicao como chave de busca, ou "" se ele nao servir.

    E' a chave do indice `por_nome`, que existe porque o TikTok manda o @ em
    uns eventos e o id numerico em outros -- e o nome de exibicao e' a unica
    coisa que os dois tem em comum.

    O `casefold` e nao o `lower`: nome de espectador vem com acento, maiuscula
    grega, emoji e espaco duplo. "MARIA" e "maria" precisam bater; "Maria  "
    e "Maria" tambem.

    E ele RECUSA nome curto demais. Um nome de um ou dois caracteres ("k",
    "ㅤ", "🌸") repete numa live grande com frequencia quase certa, e cada
    repeticao seria uma chance de o presente de uma pessoa virar o avatar de
    outra. Recusar aqui e' mais barato que descobrir a ambiguidade depois --
    e o caminho de quem foi recusado continua existindo: ela comenta o nick e
    o presente guardado dela sai na hora.
    """
    limpo = " ".join(str(nickname or "").split()).casefold()
    return limpo if len(limpo) >= 3 else ""


# =========================== O tradutor ===========================

class Tradutor:
    """Guarda quem e' quem e transforma evento de live em spawn de avatar."""

    def __init__(self, url_servidor, chave, donos=(), simular_envio=False,
                 buscador=None):
        self.url = (url_servidor or "").rstrip("/")
        self.chave = chave or ""
        self.simular_envio = simular_envio
        self.buscador = buscador or nicks.Buscador()
        self.cfg = painel.ConfigDoPainel(self.url, self.chave)

        # Quem pode usar os comandos de teste. Vazio = ninguem, e esse e' o
        # padrao certo: sem dono definido, o comando nao deve funcionar pra
        # ninguem, em vez de funcionar pra todo mundo.
        self.donos = {d for d in (_arroba(x) for x in donos) if d}

        # tiktok_id -> {"nickname", "nick"}: quem comentou algo com cara de nick
        # nesta janela, esperando a consulta em lote.
        self.pendentes = {}

        # tiktok_id -> {"roblox_id", "nickname", "nick"}: o ultimo nick que a
        # pessoa comentou. E' o que os presentes dela usam, e e' sobrescrito
        # quando ela comenta outro -- entao trocar de avatar no meio da live
        # funciona sozinho.
        self.conhecidos = {}

        # A MESMA pessoa chega com chaves DIFERENTES: o TikTok manda o @ em uns
        # eventos e o id numerico em outros (comentario e presente nao batem).
        # Sem este indice, quem comentou o nick e depois mandou presente nao era
        # reconhecida e vinha com boneco generico. O nome de exibicao e' o que
        # os dois eventos tem em comum.
        self.por_nome = {}

        #[[ OS NOMES QUE NAO SERVEM MAIS DE CHAVE, E POR QUE ISSO E' UM CONSERTO
        #
        #   O indice acima resolve um problema real e cria outro: nome de
        #   exibicao do TikTok NAO E' UNICO. Duas pessoas se chamando "ana",
        #   "🦋", "user38271" ou qualquer nome repetido sao coisa de todo dia
        #   numa live grande.
        #
        #   Quando isso acontecia, o presente da segunda pessoa era atribuido
        #   ao registro da PRIMEIRA -- e o que nascia na tela era o avatar de um
        #   ESTRANHO, grande e brilhando, com o nome de quem pagou em cima da
        #   cabeca. Do lado de quem mandou o presente, a leitura e' exatamente
        #   a que chegou como queixa: "apareceu uma skin aleatoria, nao a minha".
        #
        #   A regra agora: no instante em que dois tiktok_id diferentes reivin-
        #   dicam o mesmo nome de exibicao, esse nome vira AMBIGUO e para de
        #   valer como chave -- pros dois, e pra sempre nesta sessao. O preco e'
        #   um presente que espera a pessoa comentar o nick de novo (o caminho
        #   dos orfaos, que ja' existe e ja' funciona). O preco do contrario e'
        #   mostrar a skin errada, que e' o unico erro deste kit que nao tem
        #   conserto na hora.
        self.nomes_ambiguos = set()
        # Quantas vezes o indice por nome salvou um presente, e quantas ele foi
        # recusado por ambiguidade. Aparece no resumo da janela da ponte.
        self.achados_por_nome = 0
        self.nomes_recusados = 0

        # tiktok_id -> [(efeito, nome_do_presente), ...]
        self.orfaos = {}
        self.orfaos_expiram = {}

        # tiktok_id -> curtidas acumuladas que ainda nao viraram avatar.
        self.curtidas = {}

        self.chuvas = []      # chuvas em andamento
        self.saida = []       # spawns prontos, esperando o laco de envio

        self.credito = 0.0
        self.enviados = 0
        self.sem_nick = 0
        self.descartados = 0
        self._falhas_servidor = 0

        # Relogio do ULTIMO sinal de vida vindo do TikTok (ver `_vigiar_silencio`).
        #
        # E' `monotonic` e nao `time()` de proposito: este numero so' serve pra
        # medir DURACAO, e o relogio comum do Windows pula pra tras quando o PC
        # acerta a hora pela internet -- um pulo desses faria o vigia concluir
        # que a live esta' muda ha' horas e derrubar uma conexao boa.
        #
        # Comeca em None: sem conexao ainda, nao existe silencio pra medir.
        self.ultimo_evento = None

        # O que sobe pro painel no proximo laco. Trava propria (e nao a do
        # painel de configuracao) porque quem escreve aqui sao os callbacks da
        # TikTokLive, que podem rodar noutra thread.
        self._trava_diario = threading.Lock()
        self._diario = []
        self._jogadores = {}
        self._presentes_vistos = {}

    # ---------- o que o PAINEL ve' ----------
    #
    # Tudo aqui e' "melhor esforco": nada nesta secao pode atrasar ou derrubar
    # a live. As linhas se acumulam em memoria e sobem de uma vez, por um laco
    # proprio -- fazer HTTP no caminho de cada comentario transformaria um
    # servidor lento num chat travado.

    def contar(self, texto, nivel="info"):
        """Uma linha pro diario do painel."""
        with self._trava_diario:
            if len(self._diario) < 300:
                self._diario.append({"nivel": nivel, "origem": "ponte",
                                     "texto": texto, "quando": time.time()})

    def marcar_jogador(self, tiktok_id, nickname, conhecido, presentes=0, moedas=0):
        """Soma a participacao desta pessoa na lista de jogadores do painel."""
        with self._trava_diario:
            linha = self._jogadores.get(tiktok_id)
            if linha is None:
                linha = {"tiktok_id": tiktok_id, "nickname": "",
                         "nick_roblox": "", "roblox_id": 0,
                         "presentes": 0, "moedas": 0}
                self._jogadores[tiktok_id] = linha
            linha["nickname"] = nickname or linha["nickname"]
            if conhecido:
                linha["nick_roblox"] = conhecido.get("nick") or linha["nick_roblox"]
                linha["roblox_id"] = conhecido.get("roblox_id") or linha["roblox_id"]
            linha["presentes"] += max(0, int(presentes or 0))
            linha["moedas"] += max(0, int(moedas or 0))

    def registrar_presente_visto(self, presente_id, nome, moedas, imagem=""):
        """Este presente existe, e esta e' a cara dele.

        A FIGURA VEM JUNTO porque o painel precisa dela e nao tem como
        descobri-la sozinho: a imagem de um presente do TikTok mora num CDN
        deles, com um endereco que muda de presente pra presente e de regiao
        pra regiao. O unico lugar do kit por onde esse endereco passa e' o
        evento da live -- aqui. Nao capturando agora, ele se perde, e a ficha
        do presente no painel fica sendo um numero e um nome em ingles.
        """
        if not presente_id:
            return
        with self._trava_diario:
            self._presentes_vistos[str(presente_id)] = (nome, moedas, imagem)

    def _drenar_painel(self):
        """Tira da memoria tudo que o painel precisa saber. Chamado pelo laco."""
        with self._trava_diario:
            linhas, self._diario = self._diario, []
            jogadores = list(self._jogadores.values())
            self._jogadores = {}
            vistos, self._presentes_vistos = self._presentes_vistos, {}
        return linhas, jogadores, vistos

    def publicar(self, caminho, corpo):
        """POST no servidor local. Bloqueia -- quem chama poe numa thread."""
        req = urllib.request.Request(
            self.url + caminho, data=json.dumps(corpo).encode(), method="POST",
            headers={"Content-Type": "application/json", "X-Chave": self.chave})
        return _post(req)

    def buscar_json(self, caminho):
        """GET no servidor local. Bloqueia -- quem chama poe numa thread."""
        req = urllib.request.Request(self.url + caminho,
                                     headers={"X-Chave": self.chave})
        return _ler_json(req)

    def relatar_conexao(self, estado, conta, detalhe=""):
        """Conta ao painel o que esta' acontecendo com a live do TikTok.

        Silencioso em falha e chamado de dentro de um `try` de proposito: o
        relato de estado nunca pode ser o motivo de a ponte parar. O painel ja'
        sabe lidar com silencio -- ele mostra ha' quanto tempo foi o ultimo
        sinal, e um relato que nao chegou vira "ponte muda", que e' a verdade.
        """
        try:
            self.publicar("/conexao", {"estado": estado, "conta": conta,
                                       "detalhe": str(detalhe)[:200]})
        except Exception:
            pass

    # ---------- memoria de quem e' quem ----------

    def _quem_e(self, tiktok_id, nickname=None):
        """Quem e' esta pessoa, ou None. Ver `_quem_e_e_como`."""
        achado, _origem = self._quem_e_e_como(tiktok_id, nickname)
        return achado

    def _quem_e_e_como(self, tiktok_id, nickname=None):
        """(registro, origem). origem: "id", "nome" ou None.

        A ORIGEM IMPORTA PRA QUEM CHAMA, e nao e' detalhe de implementacao:
        casar pelo ID e' certeza, casar pelo NOME e' aposta. O presente -- que
        e' o unico evento pago -- registra no painel quando foi aposta, pra
        quem esta' transmitindo conseguir ligar uma queixa de "apareceu outra
        skin" ao que de fato aconteceu, em vez de ficar sem nenhuma pista.
        """
        achado = self.conhecidos.get(tiktok_id)
        if achado:
            return achado, "id"

        chave = _nome_chave(nickname)
        if not chave:
            return None, None
        if chave in self.nomes_ambiguos:
            # Duas pessoas com este nome de exibicao: preferir NINGUEM a
            # arriscar a skin de um estranho. Ver `nomes_ambiguos`.
            self.nomes_recusados += 1
            return None, None

        achado = self.por_nome.get(chave)
        if achado:
            self.achados_por_nome += 1
            return achado, "nome"
        return None, None

    def _lembrar(self, tiktok_id, registro):
        """Grava pelas DUAS chaves de uma vez.

        Usar sempre isto em vez de mexer no `conhecidos` direto -- senao a
        segunda chave fica pra tras e o bug reaparece exatamente onde ele e'
        mais dificil de ver: no presente de quem ja' tinha comentado.

        O `dono` gravado dentro do registro e' o que permite perceber a
        AMBIGUIDADE: quando um nome de exibicao ja' pertence a outro tiktok_id,
        ele deixa de servir de chave pros dois (ver `nomes_ambiguos`).
        """
        registro["dono"] = tiktok_id
        self.conhecidos[tiktok_id] = registro

        chave = _nome_chave(registro.get("nickname"))
        if not chave or chave in self.nomes_ambiguos:
            return registro

        anterior = self.por_nome.get(chave)
        if anterior is not None and anterior.get("dono") != tiktok_id:
            self.nomes_ambiguos.add(chave)
            del self.por_nome[chave]
            self.contar(
                f"duas pessoas diferentes usam o nome \"{registro.get('nickname')}\" "
                f"-- deste ponto em diante o presente de quem tem esse nome so' "
                f"vale depois de ela comentar o nick de novo (e' o que impede a "
                f"skin de um estranho de aparecer no lugar da dela)",
                nivel="aviso")
            return registro

        self.por_nome[chave] = registro
        return registro

    # ---------- entrada de eventos ----------

    def ao_evento(self, evento, agora=None):
        """Consome um evento normalizado. NUNCA levanta.

        `agora` e' injetavel (em vez de lido de time.time() la' dentro) porque a
        chuva agenda spawns no futuro: sem um relogio unico atravessando o
        caminho inteiro, ela seria agendada num relogio e drenada em outro, e
        ficaria impossivel de testar sem esperar 30 segundos de verdade.
        """
        agora = time.time() if agora is None else agora
        # Marca o sinal de vida ANTES de olhar o tipo, e sem filtrar nada: um
        # "kkkk" que o jogo ignora prova que o websocket esta' vivo do mesmo
        # jeito que um presente. Contar so' o que vira avatar faria o vigia
        # derrubar a conexao de uma live cheia de gente conversando sem nick.
        self.ultimo_evento = time.monotonic()
        try:
            tipo = evento.get("tipo")
            if tipo == "comentario":
                self._ao_comentario(evento, agora)
            elif tipo == "presente":
                self._ao_presente(evento, agora)
            elif tipo == "curtida":
                self._ao_curtida(evento, agora)
            elif tipo in ("seguiu", "compartilhou"):
                self._ao_social(evento, tipo, agora)
        except Exception as e:
            # Um evento torto nao pode derrubar a live. Imprime e segue.
            print(f"[ponte] evento ignorado ({type(e).__name__}: {e})", flush=True)

    def _ao_comentario(self, evento, agora):
        tiktok_id = str((evento.get("user") or {}).get("id") or "")
        if not tiktok_id:
            return
        user = evento.get("user") or {}
        texto = str(evento.get("texto") or "")

        if self._talvez_comando(tiktok_id, user, texto, agora):
            return

        nick = nicks.achar_nick(texto)
        if not nick:
            self.sem_nick += 1
            return

        # O ULTIMO comentario vence: quem digitou o nick errado e corrige na
        # linha seguinte e' atendido pela correcao.
        self.pendentes[tiktok_id] = {
            "nickname": user.get("nickname") or tiktok_id,
            "nick": nick,
        }
        self.contar(f"{user.get('nickname') or tiktok_id} comentou "
                    f"\"{texto[:60]}\" -> nick lido: {nick}")

    def _talvez_comando(self, tiktok_id, user, texto, agora):
        """Comando de teste no chat (!grande, !lenda...).

        Devolve True se o texto ERA um comando -- inclusive quando foi recusado
        por nao ser de um dono. Assim um "!lenda" de espectador nao escorrega
        pro extrator de nick e vira avatar por acidente.

        Aceita um nick junto: "!lenda Player123" usa esse nick. Sem nick, usa o
        ultimo que a pessoa comentou.
        """
        partes = texto.strip().split()
        if not partes:
            return False
        cmd = partes[0].lower()
        if cmd not in COMANDOS:
            return False

        if _arroba(tiktok_id) not in self.donos and \
           _arroba(user.get("nickname")) not in self.donos:
            print(f"[ponte] comando {cmd} ignorado: {tiktok_id} nao e' dono", flush=True)
            return True

        nome_presente, moedas = COMANDOS[cmd]
        efeito = self.cfg.efeito_do_presente(nome_presente, moedas)
        nickname = user.get("nickname") or tiktok_id

        nick_pedido = nicks.achar_nick(partes[1]) if len(partes) > 1 else None
        if nick_pedido:
            achados = self.buscador.buscar([nick_pedido], agora=agora)
            roblox_id = achados.get(nick_pedido)
            if not roblox_id:
                print(f"[ponte] comando {cmd}: o nick '{nick_pedido}' nao existe "
                      f"no Roblox", flush=True)
                return True
            self._lembrar(tiktok_id, {"roblox_id": roblox_id, "nickname": nickname,
                                      "nick": nick_pedido})
            nick_dela = nick_pedido
        else:
            conhecido = self._quem_e(tiktok_id, nickname)
            if not conhecido:
                print(f"[ponte] comando {cmd}: comente seu nick antes, ou use "
                      f"'{cmd} SeuNick'", flush=True)
                return True
            roblox_id = conhecido["roblox_id"]
            nick_dela = conhecido.get("nick") or ""

        print(f"[ponte] COMANDO {cmd} -> {nome_presente} ({moedas} moedas), "
              f"escala {efeito['escala']}x", flush=True)
        self._enfileirar(tiktok_id, nickname, roblox_id, efeito, moedas, agora,
                         nick_roblox=nick_dela, presente=nome_presente,
                         tipo="presente")
        return True

    def _ao_presente(self, evento, agora):
        """Cada unidade de um combo spawna um avatar NOVO. x5 rosas = 5 bonecos."""
        user = evento.get("user") or {}
        tiktok_id = str(user.get("id") or "")
        if not tiktok_id:
            return

        total = max(0, int(evento.get("moedas_total") or 0))
        if total <= 0:
            return

        # `moedas` e' o valor POR UNIDADE e `vezes` e' o tamanho do combo. O
        # efeito sai do UNITARIO -- senao um combo de 10 rosas de 1 moeda viraria
        # um presente de 10 moedas, que e' outra faixa inteira.
        unitario = max(0, int(evento.get("moedas") or 0)) or total
        vezes = max(1, int(evento.get("vezes") or 1))
        nome = str(evento.get("presente") or "")
        presente_id = str(evento.get("presente_id") or "")

        # O combo inteiro conta pra PRIORIDADE (combo maior fura mais a fila),
        # mas a faixa do presente sai do valor unitario.
        efeito = self.cfg.efeito_do_presente(nome, unitario, total_combo=total,
                                             presente_id=presente_id)

        # Avisa o painel de que este presente existe, com o ID de verdade. E'
        # o que transforma "descobrir o ID do presente" -- que hoje exige
        # procurar em lista de terceiro -- em ler a propria live.
        self.registrar_presente_visto(presente_id, nome, unitario,
                                      evento.get("imagem") or "")

        etiqueta = f"'{nome}'" + (f" (id {presente_id})" if presente_id else "")
        self.contar(f"presente {etiqueta} {unitario} moedas x{vezes} "
                    f"-> nasce {efeito['escala']}x, cresce +{efeito['crescimento']}",
                    nivel="ok")
        print(f"[ponte] presente {etiqueta} {unitario} moedas x{vezes} "
              f"(total {total}) -> escala {efeito['escala']}x "
              f"cresce +{efeito['crescimento']} prio {efeito['prio']} "
              f"segura {efeito['segura']}s", flush=True)

        teto = self.cfg.geral("combo_max", regras.COMBO_MAX)
        conhecido, origem = self._quem_e_e_como(tiktok_id, user.get("nickname"))
        if origem == "nome":
            # Casou pelo NOME DE EXIBICAO, e nao pelo id: e' o unico caminho
            # que pode errar de pessoa. Fica escrito no painel pra uma queixa
            # de "apareceu outra skin" ter onde ser conferida.
            self.contar(f"{user.get('nickname')} mandou {etiqueta} e foi "
                        f"reconhecida pelo NOME (o id do presente veio "
                        f"diferente do id do comentario) -> avatar de "
                        f"{conhecido.get('nick') or '?'}")

        if not conhecido:
            # Ainda nao sabemos a skin dela: guarda os presentes esperando ela
            # comentar o nick. A tripla (efeito, nome, id) e nao so' o efeito
            # porque o NOME e' o que deixa a voz reconhecer o presente quando a
            # camera parar neste avatar, mesmo tendo sido guardado minutos
            # antes -- e o ID e' o que o painel usa pra mostrar de onde veio.
            fila = self.orfaos.setdefault(tiktok_id, [])
            for _ in range(min(vezes, teto)):
                fila.append((efeito, nome, presente_id))
            self.orfaos_expiram[tiktok_id] = agora + VALIDADE_ORFAO_S
            self.pendentes.setdefault(tiktok_id, {
                "nickname": user.get("nickname") or tiktok_id,
                "nick": None,
            })
            self.contar(f"{user.get('nickname') or tiktok_id} mandou "
                        f"{etiqueta} mas ainda nao comentou o nick do Roblox -- "
                        f"guardado por {VALIDADE_ORFAO_S // 60} minutos",
                        nivel="aviso")
            return

        nickname = user.get("nickname") or conhecido["nickname"]
        self.marcar_jogador(tiktok_id, nickname, conhecido, presentes=vezes,
                            moedas=total)
        for i in range(min(vezes, teto)):
            self._enfileirar(tiktok_id, nickname, conhecido["roblox_id"], efeito,
                             unitario, agora,
                             nick_roblox=conhecido.get("nick") or "",
                             repeticao=(i > 0), presente=nome, tipo="presente",
                             combo=i, presente_id=presente_id)

    def _ao_curtida(self, evento, agora):
        """Curtida e' o evento mais FREQUENTE da live -- uma pessoa segurando o
        coracao manda dezenas por segundo. Um avatar por curtida entupiria a
        fila na hora, entao acumula e so' spawna a cada N."""
        efeito, a_cada = self.cfg.efeito_curtida()
        if efeito is None:
            return  # desligado no painel

        user = evento.get("user") or {}
        tiktok_id = str(user.get("id") or "")
        if not tiktok_id:
            return
        conhecido = self._quem_e(tiktok_id, user.get("nickname"))
        if not conhecido:
            return  # ainda nao sabemos a skin dela; curtida nao vale espera

        quantas = max(1, int(evento.get("quantas") or 1))
        self.curtidas[tiktok_id] = self.curtidas.get(tiktok_id, 0) + quantas
        while self.curtidas[tiktok_id] >= a_cada:
            self.curtidas[tiktok_id] -= a_cada
            # curtidas=a_cada, e nao 1: este avatar REPRESENTA as N curtidas que
            # foram acumuladas pra ele nascer.
            self._enfileirar(tiktok_id, user.get("nickname") or conhecido["nickname"],
                             conhecido["roblox_id"], efeito, 0, agora,
                             nick_roblox=conhecido.get("nick") or "",
                             tipo="curtida", curtidas=a_cada)

    def _ao_social(self, evento, chave, agora):
        """Seguir e compartilhar: raros e valiosos, entao cada um vira um avatar
        direto, sem acumular como a curtida."""
        efeito = self.cfg.efeito_social(chave)
        if efeito is None:
            return
        user = evento.get("user") or {}
        tiktok_id = str(user.get("id") or "")
        if not tiktok_id:
            return
        conhecido = self._quem_e(tiktok_id, user.get("nickname"))
        if not conhecido:
            return
        self._enfileirar(tiktok_id, user.get("nickname") or conhecido["nickname"],
                         conhecido["roblox_id"], efeito, 0, agora,
                         nick_roblox=conhecido.get("nick") or "", tipo=chave)

    # ---------- saida ----------

    def _enfileirar(self, tiktok_id, nickname, roblox_id, efeito, moedas, agora,
                    nick_roblox="", repeticao=False, presente="",
                    tipo="comentario", curtidas=0, combo=0, presente_id=""):
        """Poe um spawn na fila e, se o efeito tiver chuva, abre a chuva.

        `repeticao` marca as unidades 2 em diante de um combo, e zera as duas
        coisas que NAO podem se repetir por unidade:

        A CENA, senao um combo de 50 rosquinhas rodaria 50 cinematicas em fila e
        a live ficaria minutos travada num combo so'. A primeira unidade tem o
        momento; as outras 49 entram direto na multidao.

        A CHUVA, pelo mesmo motivo elevado ao quadrado: cada chuva cospe um
        avatar a cada 1,5s por 30s. Dez galaxias combadas abririam DEZ chuvas
        simultaneas -- 200 avatares de uma pessoa so', enchendo a grade inteira
        e sufocando todo o resto da live por meio minuto. Uma pessoa que manda
        dez galaxias merece um momento maior, e nao um monopolio da tela.
        """
        if repeticao:
            efeito = dict(efeito, cena=0, chuva=0,
                          segura=min(efeito.get("segura", 0), 1.0))

        self.saida.append(regras.montar_spawn(
            tiktok_id, nickname, roblox_id, efeito, moedas,
            nick_roblox=nick_roblox, presente=presente, tipo=tipo,
            curtidas=curtidas, combo=combo, presente_id=presente_id))

        # Teto de chuvas simultaneas. Mesmo vindo de pessoas DIFERENTES, tres
        # chuvas ao mesmo tempo ja' entregam mais avatares por segundo do que o
        # jogo consegue montar -- e a quarta so' faria a fila crescer sem
        # aparecer nada a mais na tela.
        if efeito.get("chuva", 0) > 0 and len(self.chuvas) < 3:
            self.chuvas.append({
                "ate": agora + efeito["chuva"],
                "proximo": agora + CHUVA_INTERVALO_S,
                "tiktok_id": tiktok_id,
                "nickname": nickname,
                "roblox_id": roblox_id,
                "nick_roblox": nick_roblox,
                "moedas": moedas,
                "presente": presente,
                "presente_id": presente_id,
                # A chuva nao se auto-alimenta (chuva=0) e os avatares dela NAO
                # ganham cena: 20 cinematicas de 9s enfileiradas travariam a
                # camera por tres minutos. So' o primeiro avatar tem o momento;
                # o resto entra rapido, formando o volume.
                "efeito": dict(efeito, chuva=0, segura=0.4, cena=0),
            })

    def _tickar_chuvas(self, agora):
        for c in list(self.chuvas):
            if agora >= c["ate"]:
                self.chuvas.remove(c)
                continue
            if agora >= c["proximo"]:
                c["proximo"] = agora + CHUVA_INTERVALO_S
                self.saida.append(regras.montar_spawn(
                    c["tiktok_id"], c["nickname"], c["roblox_id"], c["efeito"],
                    c["moedas"], nick_roblox=c.get("nick_roblox", ""),
                    presente=c.get("presente", ""), tipo="presente", combo=1,
                    presente_id=c.get("presente_id", "")))

    def _limpar_orfaos(self, agora):
        for k in [k for k, exp in self.orfaos_expiram.items() if agora >= exp]:
            del self.orfaos_expiram[k]
            self.orfaos.pop(k, None)

    def fechar_janela(self, agora=None):
        """Resolve os nicks acumulados e devolve os spawns de comentario.

        Bloqueia (faz HTTP), entao quem chama roda isto numa thread -- senao ela
        travaria o laco da live e os eventos se acumulariam.
        """
        agora = time.time() if agora is None else agora
        self._limpar_orfaos(agora)
        self._tickar_chuvas(agora)
        if not self.pendentes:
            return []

        lote, self.pendentes = self.pendentes, {}

        # So' vai a' API quem trouxe um nick NOVO. Quem repetiu o nick que ja'
        # resolvemos nesta live nao gasta requisicao.
        a_perguntar = []
        for tid, v in lote.items():
            nick = v.get("nick")
            if not nick:
                continue
            ja = self.conhecidos.get(tid)
            if ja and (ja.get("nick") or "").lower() == nick.lower():
                continue
            a_perguntar.append(nick)

        achados = self.buscador.buscar(a_perguntar, agora=agora) if a_perguntar else {}

        spawns = []
        for tiktok_id, v in lote.items():
            nick = v.get("nick")
            roblox_id = None

            if nick:
                ja = self.conhecidos.get(tiktok_id)
                if ja and (ja.get("nick") or "").lower() == nick.lower():
                    roblox_id = ja["roblox_id"]
                else:
                    roblox_id = achados.get(nick)
            else:
                # Entrou na lista por causa de um presente, sem nick proprio.
                ja = self._quem_e(tiktok_id, v.get("nickname"))
                if ja:
                    roblox_id = ja["roblox_id"]

            if not roblox_id:
                self.sem_nick += 1
                if nick:
                    # ISTO E' DIFERENTE de "comentou 'kkkk'". A pessoa digitou
                    # algo com cara de nick, o Roblox respondeu que a conta nao
                    # existe, e do lado dela a impressao e' que o kit ignorou.
                    # E' o unico erro do fluxo que ela pode CORRIGIR sozinha --
                    # entao ele precisa aparecer no painel com o nick escrito.
                    self.contar(f"o nick \"{nick}\" (de {v.get('nickname')}) nao "
                                f"existe no Roblox -- nenhum avatar criado",
                                nivel="aviso")
                continue

            nickname = v["nickname"]
            self._lembrar(tiktok_id, {
                "roblox_id": roblox_id,
                "nickname": nickname,
                "nick": nick or (self.conhecidos.get(tiktok_id) or {}).get("nick", ""),
            })

            # Os presentes que ela mandou ANTES de dizer o nick: agora que
            # sabemos quem ela e', cada um vira um avatar.
            orfaos = self.orfaos.pop(tiktok_id, [])
            self.orfaos_expiram.pop(tiktok_id, None)
            if orfaos:
                self.contar(f"{nickname} comentou o nick e recebeu os "
                            f"{len(orfaos)} presente(s) que tinham ficado "
                            f"guardados", nivel="ok")
            for i, (efeito, nome_presente, id_presente) in enumerate(orfaos):
                self._enfileirar(tiktok_id, nickname, roblox_id, efeito, 0, agora,
                                 nick_roblox=nick or "", repeticao=(i > 0),
                                 presente=nome_presente, tipo="presente",
                                 combo=i, presente_id=id_presente)

            # E o proprio comentario spawna o dela -- sempre, mesmo que ela ja'
            # tenha avatares na tela.
            if nick:
                self.marcar_jogador(tiktok_id, nickname,
                                    {"nick": nick, "roblox_id": roblox_id})
                efeito = self.cfg.efeito_do_comentario()
                if efeito is not None:  # None = comentario desligado no painel
                    self.contar(f"{nickname} -> avatar de {nick} "
                                f"(roblox {roblox_id}) a caminho do jogo",
                                nivel="ok")
                    spawns.append(regras.montar_spawn(
                        tiktok_id, nickname, roblox_id, efeito, 0,
                        nick_roblox=nick, tipo="comentario"))
        return spawns

    def escolher(self, candidatos, dt=JANELA_S):
        """O que cabe no orcamento desta janela.

        Presente passa SEMPRE: e' raro e foi pago. Ele consome credito, mas
        nunca e' barrado por falta dele.

        O resto preenche o que sobrar, do MAIS NOVO pro mais velho. Numa
        enxurrada, mostrar quem acabou de comentar vale mais do que mostrar quem
        comentou ha' 30 segundos e talvez nem esteja mais assistindo.

        A SEPARACAO E' PELO `tipo`, E NAO PELA PRIORIDADE. ISSO E' UM CONSERTO.

        Antes a conta era `prio > 0`, e ela abria um buraco enorme sem parecer
        que abria: a CURTIDA nasce com prio 1 e o SEGUIU com prio 2, entao os
        dois caiam no balde dos "pagos" e passavam pelo teto de taxa como se
        fossem presente. Curtida e' o evento mais frequente de uma live inteira
        -- uma pessoa segurando o coracao manda dezenas por segundo -- e o
        limitador que existe justamente pra segurar isso era o unico lugar do
        caminho que nao a segurava. Com as curtidas ligadas no painel, o teto
        de 1,8 spawns por segundo simplesmente nao valia, a fila do jogo
        enchia, e a live ficava minutos atrasada em relacao ao chat.

        Pelo `tipo`, so' o que foi realmente pago fura a fila.
        """
        self.credito = min(self.credito + TETO_POR_SEGUNDO * dt, CREDITO_MAX)

        pagos = [e for e in candidatos if e.get("tipo") == "presente"]
        livres = [e for e in candidatos if e.get("tipo") != "presente"]

        sobra = max(0, int(self.credito) - len(pagos))
        #[[ O que sobrou do orcamento vai pro MAIS VALIOSO e, em empate, pro
        #   MAIS NOVO.
        #
        #   A ordem por valor entrou junto com a correcao acima. Com curtida e
        #   seguiu saindo do balde dos pagos, eles passaram a disputar as vagas
        #   livres com os comentarios -- e comentario e' o evento mais comum de
        #   todos. Sem desempate por prioridade, um "seguiu" (que acontece
        #   poucas vezes numa live inteira) era descartado sempre que dois
        #   comentarios chegassem depois dele.
        #
        #   `enumerate` antes do sort porque o sort do Python e' estavel mas a
        #   chave precisa inverter a ordem de chegada dentro da mesma
        #   prioridade, e negar o indice e' mais barato que reverter a lista. ]]
        ordenados = sorted(enumerate(livres),
                           key=lambda par: (par[1].get("prio", 0), par[0]),
                           reverse=True)
        aceitos = [ev for _, ev in ordenados[:sobra]]
        escolhidos = pagos + aceitos

        # O credito nunca fica negativo: um combo grande nao pode "dever"
        # credito e travar os comentarios dos proximos segundos.
        self.credito = max(0.0, self.credito - len(escolhidos))

        fora = len(livres) - len(aceitos)
        if fora:
            self.descartados += fora
        return escolhidos

    async def enviar(self, spawns):
        if not spawns:
            return
        for e in spawns:
            extra = f" segura {e['segura']}s" if e.get("segura") else ""
            print(f"[ponte] -> {e['nickname']} (roblox {e['roblox_id']}) "
                  f"prio={e['prio']} escala={e['escala']}x{extra}", flush=True)

        if self.simular_envio:
            self.enviados += len(spawns)
            return

        corpo = json.dumps({"eventos": spawns}).encode()
        req = urllib.request.Request(
            self.url + "/eventos", data=corpo, method="POST",
            headers={"Content-Type": "application/json", "X-Chave": self.chave})
        try:
            await asyncio.to_thread(_post, req)
            self.enviados += len(spawns)
            self._falhas_servidor = 0
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                TimeoutError) as e:
            # Servidor fora do ar nao pode derrubar a ponte: a live continua e o
            # proximo evento tenta de novo. Mas se esta' falhando SEMPRE, voce
            # precisa saber -- senao fica olhando um jogo parado sem entender.
            self._falhas_servidor += 1
            if self._falhas_servidor == 5:
                deps.caixa("O JOGO NAO ESTA RECEBENDO -- o servidor nao responde", [
                    "A live esta' chegando aqui, mas nao consigo entregar pro",
                    'jogo. O servidor e a janela preta que diz "SERVIDOR DA LIVE".',
                    "",
                    "O que costuma ser:",
                    "  - a janela do servidor fechou, ou nem chegou a abrir;",
                    "  - antivirus bloqueando a conexao local.",
                    "",
                    "Feche tudo e rode o 2-COMECAR-LIVE.bat de novo.",
                    "",
                    f"Erro: {e}",
                ])
            else:
                print(f"[ponte] servidor falhou ({e}) -- seguindo", flush=True)


def _post(req):
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read()


# =========================== TikTok ao vivo ===========================

def _pessoa(ev):
    """O usuario de um evento da TikTokLive, num formato so'.

    getattr com padrao em tudo de proposito: a biblioteca muda de versao com
    frequencia e um campo renomeado nao pode derrubar a live -- vira um evento
    com nome vazio, que ainda funciona.
    """
    u = getattr(ev, "user", None)
    if u is None:
        return {"id": "", "nickname": "anonimo"}
    uid = getattr(u, "unique_id", "") or getattr(u, "id", "")
    return {"id": str(uid), "nickname": getattr(u, "nickname", None) or str(uid) or "anonimo"}


def _figura_do_presente(presente):
    """A URL da imagem do presente, ou "".

    POR QUE ELA E' PROCURADA EM VARIOS LUGARES

    A TikTokLive troca de nome de campo entre versoes, e a imagem e' o campo
    que mais mudou: ja' foi `image`, ja' foi `icon`, e dentro dela ja' foi
    `url_list` e `urls`. Um caminho unico escrito na mao quebraria calado na
    proxima atualizacao da biblioteca -- e "calado" aqui significa fichas de
    presente sem figura no painel, sem nenhuma mensagem dizendo por que.

    Tentar os quatro caminhos custa nada (roda uma vez por presente NOVO, nao
    por evento) e sobrevive a' proxima renomeacao. Falhou em todos? Devolve
    vazio, e o painel mostra o emoji -- que e' o comportamento de antes.
    """
    if presente is None:
        return ""
    for campo in ("image", "icon"):
        figura = getattr(presente, campo, None)
        if figura is None:
            continue
        for lista in ("url_list", "urls", "url_listList"):
            enderecos = getattr(figura, lista, None)
            if not enderecos:
                continue
            try:
                primeiro = str(enderecos[0] or "")
            except (IndexError, TypeError):
                continue
            if primeiro.startswith("http"):
                return primeiro[:400]
    return ""


async def dormir_ou_mudanca(estado, segundos):
    """Dorme ate' `segundos`, ou acorda na hora se o painel mexer.

    E' o que faz o botao do painel responder na hora. Sem isto, a ponte passa
    a maior parte da vida dormindo -- entre tentativas de conexao a espera
    chega a cinco minutos -- e um clique em "desconectar" so' valeria quando a
    soneca terminasse. O painel diria "desconectado" e os avatares
    continuariam nascendo, que e' o pior tipo de mentira que um painel pode
    contar.

    Devolve True se quem acordou foi o painel.
    """
    try:
        await asyncio.wait_for(estado["mudou"].wait(), timeout=segundos)
    except asyncio.TimeoutError:
        return False
    estado["mudou"].clear()
    return True


async def _derrubar(cliente, tarefa):
    """Fecha uma conexao do TikTok sem deixar tarefa orfa pra tras.

    A ordem importa: `disconnect` primeiro (pra biblioteca fechar o websocket
    de forma limpa), `cancel` depois como garantia. Só cancelar deixaria o
    socket aberto ate' o coletor de lixo passar -- e um socket vivo continua
    recebendo eventos da live ANTIGA, que e' exatamente como uma troca de
    conta acaba com as duas contas mandando avatar pro mesmo jogo.
    """
    try:
        await cliente.disconnect()
    except Exception:
        pass
    tarefa.cancel()
    try:
        await tarefa
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def _descartar(*tarefas):
    """Cancela tarefas e ESPERA elas morrerem.

    So' chamar `.cancel()` marca o pedido e devolve na hora -- a tarefa ainda
    nao acabou. Sem o `await` de baixo, a que sobrou continua viva mais um
    instante e o asyncio ainda solta "Task exception was never retrieved" no
    meio da janela da live, que parece erro e nao e'.
    """
    for t in tarefas:
        t.cancel()
    for t in tarefas:
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception:
            pass


# Quanto tempo de silencio TOTAL derruba a conexao e manda reconectar.
#
# POR QUE ISTO EXISTE -- e' o conserto de "a ponte desconecta sozinha".
#
# O relato era sempre o mesmo: no meio da live os avatares param de aparecer, a
# janela preta nao mostra erro nenhum, o painel continua dizendo "conectada", e
# so' fechar tudo e abrir de novo resolve.
#
# A causa e' um socket MEIO ABERTO. Quando o Wi-Fi pisca, o PC dorme, ou o
# roteador esquece a conexao (NAT domestico derruba conexao parada em 5-30 min),
# o TCP dos dois lados nao e' avisado: o nosso lado acha que esta' conectado e
# fica esperando dados que nunca mais chegam. O `connect()` da TikTokLive nao
# devolve, nao levanta excecao, e nao ha' nada no codigo antigo que percebesse
# -- a ponte esperava, em silencio, pra sempre.
#
# Medir o silencio resolve porque nao depende da biblioteca perceber nada: se
# NENHUM sinal chega ha' muito tempo, a conexao nao serve, esteja ela "aberta"
# ou nao. Reconectar custa poucos segundos e e' invisivel na live.
#
# 5 MINUTOS, e nao menos: uma live pequena de verdade passa minutos sem
# ninguem digitar, e derrubar uma conexao boa por isso trocaria um bug raro por
# um pior -- reconexao em looping, que ainda gasta o servico de assinatura do
# TikTok (o mesmo que responde erro quando a gente martela).
SILENCIO_MAX_S = 300.0

# De quanto em quanto tempo o vigia confere. Nao precisa ser fino: ele mede uma
# espera de minutos, e acordar de 15 em 15 segundos ja' da' a pontaria toda.
SILENCIO_PASSO_S = 15.0


async def _vigiar_silencio(tradutor):
    """Devolve quando a live fica muda tempo demais. Ate' la', nao devolve."""
    while True:
        await asyncio.sleep(SILENCIO_PASSO_S)
        marca = tradutor.ultimo_evento
        # Sem marca = ainda nao conectou de fato. Nao ha' silencio pra medir, e
        # chutar um comeco aqui derrubaria a conexao antes de ela nascer.
        if marca is None:
            continue
        if time.monotonic() - marca >= SILENCIO_MAX_S:
            return


async def _esta_ao_vivo(cliente, pular=False):
    """A conta esta' ao vivo? EM DUVIDA, responde que SIM.

    A pergunta continua valendo a pena (ver quem chama), mas as duas respostas
    erradas custam coisas MUITO diferentes, e antes elas custavam igual:

      - um "nao" errado para a ponte por 30 segundos e escreve "voce nao esta'
        AO VIVO" pra quem esta', naquele momento, ao vivo. E' o pior erro que
        esta funcao pode cometer.
      - um "sim" errado custa uma tentativa de conexao que falha com
        UserOfflineError -- que o laco la' embaixo ja' trata com a frase certa.

    Por isso o `except` devolve True: se a propria pergunta falhou (internet
    piscando, TikTok lento), a ponte tenta conectar e deixa o connect decidir.

    `pular=True` vem da reconexao depois de uma queda. Logo depois de o socket
    morrer, o TikTok ainda responde "essa conta nao esta' ao vivo" por um tempo
    -- a sala demora a atualizar do lado deles. Acreditar nessa resposta e'
    exatamente o que fazia a ponte cair e ficar 30 em 30 segundos repetindo que
    a live estava fechada com a live aberta na tela.
    """
    if pular:
        return True
    try:
        return bool(await cliente.is_live())
    except asyncio.CancelledError:
        raise
    except Exception:
        return True


async def laco_tiktok(tradutor, estado):
    """Mantem a ponte na conta que o painel pediu.

    O `estado` e' a ordem vinda do painel (ver `laco_controle`): que conta, e
    se e' pra estar ligada. Este laco e' o unico lugar que conecta e
    desconecta de verdade.
    """
    from TikTokLive import TikTokLiveClient
    from TikTokLive.client.errors import (SignAPIError, UserNotFoundError,
                                          UserOfflineError)
    from TikTokLive.events import (CommentEvent, ConnectEvent, FollowEvent,
                                   GiftEvent, LikeEvent, ShareEvent)

    laco = asyncio.get_running_loop()

    def entregar(evento):
        # Os callbacks da TikTokLive podem rodar noutra thread. Marcar o
        # relogio aqui, e nao la' dentro, mantem a ordem dos eventos coerente.
        laco.call_soon_threadsafe(tradutor.ao_evento, evento)

    def registrar(cliente, arroba):
        @cliente.on(ConnectEvent)
        async def _(e):
            nonlocal espera_assinatura, espera_conta
            # A conexao NASCE AQUI, pro vigia de silencio ter de onde contar.
            # Sem esta linha o vigia so' comecaria a contar no primeiro
            # comentario -- e uma live que conecta e ja' entra muda (o caso
            # exato do socket meio aberto) nunca seria recuperada.
            tradutor.ultimo_evento = time.monotonic()
            # Conectar PROVA que o servico de assinatura voltou. Sem zerar aqui,
            # uma instabilidade la' no comeco da live deixava a espera em 5
            # minutos pelo resto da noite: a proxima queda, mesmo boba,
            # demoraria 5 minutos pra ser tentada de novo.
            espera_assinatura = 30
            # Mesma ideia pro relogio da conta: conectar PROVA que o TikTok
            # voltou a responder sobre ela, entao a proxima recusa comeca do
            # comeco em vez de herdar dois minutos de uma instabilidade velha.
            espera_conta = 30
            tradutor.relatar_conexao("conectada", arroba.lstrip("@"))
            tradutor.contar(f"conectado na live de {arroba}", nivel="ok")
            deps.caixa(f"PONTE NO AR -- conectada na live de {arroba}", [
                "Os comentarios e presentes da sua live ja' estao chegando no",
                "jogo. Deixe esta janela aberta durante a live inteira.",
                "",
                "Abaixo aparece cada evento na hora em que acontece. Se nada",
                "aparecer, e' porque ninguem interagiu ainda.",
            ])

        @cliente.on(CommentEvent)
        async def _(e):
            entregar({"tipo": "comentario", "user": _pessoa(e),
                      "texto": getattr(e, "comment", "") or ""})

        @cliente.on(GiftEvent)
        async def _(e):
            presente = getattr(e, "gift", None)
            # Presente "streakable" (a rosa, por exemplo) chega VARIAS vezes
            # enquanto a pessoa segura o combo, e so' o evento final traz a
            # contagem certa. Emitir os intermediarios multiplicaria o efeito.
            if presente is not None and getattr(presente, "streakable", False) \
               and getattr(e, "streaking", False):
                return
            moedas = int(getattr(presente, "diamond_count", 0) or 0) if presente else 0
            vezes = int(getattr(e, "repeat_count", 1) or 1)
            nome = getattr(presente, "name", "") if presente else ""
            # O ID NUMERICO do presente. E' o unico identificador que nao muda
            # de regiao pra regiao -- o nome muda, e e' por isso que ele nao
            # basta. Vai pro painel pra voce cadastrar o gatilho pelo ID certo
            # em vez de descobrir o nome que a sua audiencia recebe.
            presente_id = str(getattr(presente, "id", "") or "") if presente else ""
            entregar({"tipo": "presente", "user": _pessoa(e),
                      "presente": nome, "presente_id": presente_id,
                      # A FIGURA do presente, pro painel mostrar a ficha com a
                      # cara dele em vez de so' um numero. Ver
                      # `_figura_do_presente`.
                      "imagem": _figura_do_presente(presente),
                      "moedas": moedas, "vezes": vezes,
                      "moedas_total": moedas * vezes})

        @cliente.on(LikeEvent)
        async def _(e):
            entregar({"tipo": "curtida", "user": _pessoa(e),
                      "quantas": int(getattr(e, "count", 1) or 1)})

        @cliente.on(FollowEvent)
        async def _(e):
            entregar({"tipo": "seguiu", "user": _pessoa(e)})

        @cliente.on(ShareEvent)
        async def _(e):
            entregar({"tipo": "compartilhou", "user": _pessoa(e)})

    # Quanto esperar depois de um erro do SERVICO DE ASSINATURA. Cresce a cada
    # falha seguida: se o problema e' limite de uso, martelar de 30 em 30
    # segundos so' piora.
    espera_assinatura = 30

    # Quanto esperar depois de o TikTok RECUSAR a consulta da conta (o
    # `UserNotFoundError` que nao e' culpa do @ -- ver o `except` la' embaixo).
    # Tem relogio proprio, e nao o da assinatura, porque sao dois servicos
    # diferentes: um pode estar de pe' com o outro no chao, e herdar a espera
    # do vizinho faria a ponte esperar dois minutos por um problema que ja'
    # tinha passado.
    espera_conta = 30

    parada_relatada = False

    # A ultima conexao caiu SOZINHA, com a live no ar? (ver o vigia de silencio)
    # Muda o que fazer na volta: nesse caso a pergunta "voce esta' ao vivo?" nao
    # e' confiavel, e a explicacao esta' logo abaixo, onde ela e' usada.
    reconectando = False

    while True:
        #[[ DESLIGADA: nao conecta, e nao fica perguntando nada ao TikTok.
        #
        #   A espera e' longa (1h) porque quem acorda daqui e' o PAINEL, pelo
        #   `mudou`, e nao o relogio. Um numero curto aqui seria uma pesquisa
        #   inutil de segundo em segundo sem nenhuma chance de mudar nada. ]]
        if not estado["ligado"] or not estado["conta"]:
            if not parada_relatada:
                parada_relatada = True
                tradutor.relatar_conexao("parada", estado["conta"])
                print("[ponte] desconectada. Conecte pelo painel "
                      "(http://localhost:8000/painel).", flush=True)
            await dormir_ou_mudanca(estado, 3600)
            continue

        parada_relatada = False
        conta = estado["conta"]
        arroba = "@" + conta
        cliente = TikTokLiveClient(unique_id=arroba)
        registrar(cliente, arroba)
        espera = 10

        try:
            # PERGUNTA ANTES DE CONECTAR se a live existe. Sem isto, com a live
            # fechada, o connect() pede assinatura do webcast e o servico
            # responde erro 500 -- que aparece como um susto tecnico em vez do
            # simples "voce nao esta' ao vivo". Esta pergunta nao passa pelo
            # servico de assinatura, entao e' confiavel ate' quando ele esta' mal.
            tradutor.relatar_conexao("conectando", conta)
            if not await _esta_ao_vivo(cliente, pular=reconectando):
                tradutor.relatar_conexao(
                    "offline", conta, "a conta nao esta' ao vivo neste momento")
                print(f"[ponte] {arroba} nao esta' AO VIVO agora. Deixe esta "
                      f"janela aberta: eu conecto sozinho quando voce abrir a "
                      f"live (confiro a cada 30s)...", flush=True)
                await dormir_ou_mudanca(estado, 30)
                continue

            # A partir daqui a pergunta ja' foi feita (ou pulada de proposito).
            # Zerar AGORA, e nao no fim, porque qualquer caminho de erro abaixo
            # sai do laco -- e uma volta que herdasse o "pular" faria a ponte
            # deixar de conferir a live pro resto da noite.
            reconectando = False

            print(f"[ponte] conectando em {arroba}...", flush=True)

            #[[ O `connect()` so' devolve quando a live acaba -- ou seja, ele
            #   pode ficar horas dentro deste `await`. Esperar OS TRES (a
            #   conexao, o painel e o vigia) e' o que permite sair do meio.
            #
            #   Sem o painel nesta corrida, o unico jeito de trocar de conta
            #   seria fechar a janela preta e rodar tudo de novo, que e'
            #   precisamente o que este painel existe pra evitar.
            #
            #   Sem o VIGIA, um socket meio aberto deixa o `connect()` esperando
            #   pra sempre: nao chega evento, nao chega erro, e nao existe mais
            #   nada nesta funcao capaz de acordar a ponte. ]]
            #
            # O relogio do vigia comeca A CADA tentativa, e comeca AGORA.
            #
            # Duas coisas de uma vez. Primeira: o silencio que interessa e' o
            # DESTA conexao -- herdar a marca da anterior faria o vigia derrubar
            # a conexao nova por causa do silencio da velha, virando um laco de
            # reconexao sem fim.
            #
            # Segunda, e menos obvia: marcar AQUI (e nao so' quando o
            # ConnectEvent chega) e' o que cobre o aperto de mao que TRAVA. Se a
            # marca ficasse vazia ate' conectar, uma conexao que nunca completa
            # deixaria o vigia sem nada pra medir -- justamente o caso que ele
            # existe pra resolver.
            tradutor.ultimo_evento = time.monotonic()
            conectar = asyncio.create_task(cliente.connect())
            mudanca = asyncio.create_task(estado["mudou"].wait())
            vigia = asyncio.create_task(_vigiar_silencio(tradutor))
            prontas, _ = await asyncio.wait(
                {conectar, mudanca, vigia}, return_when=asyncio.FIRST_COMPLETED)

            if mudanca in prontas:
                estado["mudou"].clear()
                await _descartar(vigia)
                await _derrubar(cliente, conectar)
                tradutor.contar(f"desconectado de {arroba} a pedido do painel")
                continue

            if vigia in prontas:
                # A conexao esta' "aberta" e ha' minutos nao chega nada. Derruba
                # e reconecta -- e' o unico jeito de sair de um socket morto.
                #
                # Nao vira caixa de erro na tela: nao houve erro nenhum, e
                # assustar quem esta' ao vivo com um quadro vermelho por uma
                # reconexao de tres segundos seria pior que o proprio problema.
                await _descartar(mudanca)
                await _derrubar(cliente, conectar)
                minutos = int(SILENCIO_MAX_S // 60)
                print(f"[ponte] nada chegou da live nos ultimos {minutos} min. "
                      f"A conexao deve ter caido sem avisar -- reconectando...",
                      flush=True)
                tradutor.contar("a conexao ficou muda; reconectando sozinho")
                tradutor.relatar_conexao("conectando", conta,
                                         "a conexao ficou muda; reconectando")
                reconectando = True
                espera = 3
                await dormir_ou_mudanca(estado, espera)
                continue

            await _descartar(mudanca, vigia)
            # Levanta a excecao da conexao, se houve -- e' o que faz os
            # `except` abaixo continuarem valendo depois de o connect ter
            # virado tarefa.
            conectar.result()

            print("[ponte] conexao encerrada (a live terminou?).", flush=True)
            tradutor.relatar_conexao("offline", conta, "a live terminou")
            espera = 10
            espera_assinatura = 30

        except UserOfflineError:
            tradutor.relatar_conexao("offline", conta,
                                     "a conta nao esta' ao vivo")
            print(f"[ponte] {arroba} nao esta' AO VIVO. Nova tentativa em 30s...",
                  flush=True)
            espera = 30
        except UserNotFoundError:
            #[[ ═══════════════════════════════════════════════════════════
            #   ESTE ERRO NAO QUER DIZER "esse @ nao existe"
            #   ═══════════════════════════════════════════════════════════
            #
            #   Ele quer dizer tres coisas ao mesmo tempo (ver o cabecalho de
            #   ponte/conta.py): o @ nao existe, o @ existe mas a conta nunca
            #   teve LIVE liberada, ou o TikTok simplesmente RECUSOU a
            #   consulta -- captcha, limite de uso, bloqueio de IP.
            #
            #   Ate' aqui o painel escrevia "confira o @" nos tres casos, e o
            #   terceiro e' o mais comum de todos numa live que reconecta. A
            #   pessoa passava a live inteira conferindo a unica coisa que
            #   estava certa. A propria biblioteca avisa disso em comentario:
            #   "Do not raise on UserNotFoundError as this can be a captcha
            #   issue".
            #
            #   Entao a gente PERGUNTA, pela pagina publica do perfil -- que
            #   nao passa pelo servico de assinatura e continua respondendo
            #   quando a conexao da live nao sobe. So' um 404 de verdade
            #   autoriza a frase que manda conferir a digitacao.
            #
            #   Roda em thread porque e' HTTP com bloqueio, e este laco nao
            #   pode parar: e' ele que ouve o painel. ]]
            veredito = await asyncio.to_thread(tiktok.conferir, conta)

            if veredito == tiktok.NAO_EXISTE:
                recado = (f"o @ {arroba} nao existe no TikTok -- confira a "
                          f"digitacao no campo Conta.")
                tradutor.relatar_conexao("erro", conta, recado)
                tradutor.contar(recado, nivel="erro")
                print(f"[ponte] {recado} Nova tentativa em 30s...", flush=True)
                espera = 30
            else:
                #[[ O perfil respondeu (ou nem isso): a culpa NAO e' do @.
                #
                #   Fica em "conectando", e nao em "erro", porque e' a
                #   verdade: a ponte segue tentando sozinha. Um cracha
                #   vermelho aqui ensinaria a pessoa a fechar tudo e reiniciar
                #   no meio da live, que e' justamente o que nao resolve. ]]
                onde = ("o TikTok recusou a consulta desta conta agora"
                        if veredito == tiktok.EXISTE
                        else "nao consegui confirmar o @ com o TikTok")
                recado = (f"{onde}. O @ {arroba} nao e' o problema. Tentando "
                          f"de novo em {espera_conta}s. Se a conta for nova ou "
                          f"pequena, pode ser que o TikTok ainda nao tenha "
                          f"liberado LIVE nela.")
                tradutor.relatar_conexao("conectando", conta, recado)
                tradutor.contar(recado, nivel="aviso")
                print(f"[ponte] {recado}", flush=True)
                espera = espera_conta
                # Cresce a cada recusa seguida: se o motivo for limite de uso,
                # bater de 30 em 30 segundos so' prolonga o bloqueio.
                espera_conta = min(espera_conta * 2, 120)
        except SignAPIError:
            # NAO e' problema do seu PC nem do jogo: e' o servico de fora que
            # assina a conexao com o TikTok, fora do ar ou limitando uso. So'
            # resta esperar -- mas esperando cada vez mais.
            tradutor.relatar_conexao(
                "erro", conta,
                f"o servico de assinatura do TikTok esta' instavel; "
                f"nova tentativa em {espera_assinatura}s")
            deps.caixa("PONTE ESPERANDO -- o servico do TikTok esta' instavel", [
                "Nao e' o seu computador e nao e' o jogo: e' um servico de fora,",
                "que o TikTok exige pra liberar a conexao. Ele cai ou fica lento",
                "de vez em quando, pra todo mundo.",
                "",
                f"Tento de novo sozinho em {espera_assinatura}s. Deixe a janela aberta.",
                "",
                "Se passar de uns 15 minutos assim, ai' sim tem algo errado:",
                deps.SUPORTE,
            ])
            espera = espera_assinatura
            espera_assinatura = min(espera_assinatura * 2, 300)
        except asyncio.CancelledError:
            # A ponte inteira esta' sendo encerrada. Nao vira "erro na live".
            raise
        except Exception as e:
            tradutor.relatar_conexao("erro", conta, f"{type(e).__name__}: {e}")
            tradutor.contar(f"erro ao falar com o TikTok: "
                            f"{type(e).__name__}: {e}", nivel="erro")
            deps.caixa("PONTE COM PROBLEMA -- tentando de novo em 30s", [
                "Aconteceu um erro ao falar com o TikTok. Nao fecho a janela:",
                "fico tentando sozinho, e costuma voltar.",
                "",
                "Confira enquanto isso:",
                "  - a sua internet esta' de pe'?",
                f"  - o @ digitado esta' certo? (voce digitou {arroba})",
                "  - a live esta' mesmo aberta no TikTok?",
                "",
                f"Erro: {type(e).__name__}: {e}",
            ])
            espera = 30

        await dormir_ou_mudanca(estado, espera)


# =========================== Simulador ===========================

# Nicks do Roblox que existem de verdade e sao publicos. Servem so' pro modo
# simulacao ter avatares de verdade pra montar -- sem eles a simulacao mostraria
# bonecos vazios e nao provaria nada.
NICKS_TESTE = ("Roblox", "builderman", "Shedletsky", "Matt_Dusek", "Sorcus")

# Os QUATRO presentes que sustentam a live, um de cada faixa. A rosa aparece
# UMA vez: ela e' um presente so', e repeti-la aqui so' faria a simulacao gastar
# metade dos eventos no caso mais barato -- justamente o que menos precisa ser
# visto funcionando.
PRESENTES_TESTE = (("Rose", 1), ("Doughnut", 30),
                   ("Sunglasses", 199), ("Galaxy", 1000))


async def laco_simulacao(tradutor, intervalo):
    deps.caixa("MODO SIMULACAO -- nada disto vem da sua live", [
        "Estou inventando comentarios e presentes pra voce ver o jogo",
        "funcionando e configurar o painel do seu jeito.",
        "",
        "Quando estiver do jeito que voce quer, feche tudo e rode o",
        "2-COMECAR-LIVE.bat pra valer.",
    ])
    # Todo mundo comenta o nick uma vez antes de qualquer presente, igual a uma
    # live de verdade: sem isso os presentes cairiam todos como orfaos e o
    # simulador testaria so' metade do caminho.
    for i, nick in enumerate(NICKS_TESTE):
        tradutor.ao_evento({"tipo": "comentario",
                            "user": {"id": f"teste{i}", "nickname": f"Espectador {i + 1}"},
                            "texto": nick})
        await asyncio.sleep(0.3)

    while True:
        i = random.randrange(len(NICKS_TESTE))
        user = {"id": f"teste{i}", "nickname": f"Espectador {i + 1}"}
        sorte = random.random()

        if sorte < 0.55:
            tradutor.ao_evento({"tipo": "comentario", "user": user,
                                "texto": NICKS_TESTE[i]})
        elif sorte < 0.75:
            tradutor.ao_evento({"tipo": "curtida", "user": user,
                                "quantas": random.randint(20, 80)})
        elif sorte < 0.82:
            tradutor.ao_evento({"tipo": "seguiu", "user": user})
        else:
            nome, moedas = random.choice(PRESENTES_TESTE)
            vezes = random.choice((1, 1, 1, 3, 10))
            tradutor.ao_evento({"tipo": "presente", "user": user,
                                "presente": nome, "moedas": moedas,
                                "vezes": vezes, "moedas_total": moedas * vezes})

        await asyncio.sleep(intervalo * random.uniform(0.4, 1.6))


# =========================== Lacos de apoio ===========================

async def laco_janela(tradutor):
    """O UNICO ponto de saida: drena a fila e fecha a janela de comentarios.

    A resolucao de nicks e' bloqueante (HTTP), entao vai pra thread -- senao
    travaria o laco da live e os eventos se acumulariam ate' a ponte nunca mais
    alcancar o chat.
    """
    while True:
        await asyncio.sleep(JANELA_S)
        try:
            urgentes, tradutor.saida = tradutor.saida, []
            spawns = await asyncio.to_thread(tradutor.fechar_janela)
            await tradutor.enviar(tradutor.escolher(urgentes + spawns))
        except Exception as e:
            print(f"[ponte] erro na janela: {type(e).__name__}: {e}", flush=True)


async def laco_testes(tradutor):
    """Busca os presentes que o PAINEL injetou pelo botao de testar.

    Eles chegam CRUS (nome e moedas) e passam pelo mesmo caminho de um presente
    de verdade -- traduzir aqui, e nao no servidor, e' o que garante que o que
    voce testa no painel e' exatamente o que vai acontecer ao vivo.
    """
    if tradutor.simular_envio:
        return
    while True:
        await asyncio.sleep(1.0)
        try:
            req = urllib.request.Request(tradutor.url + "/testes",
                                         headers={"X-Chave": tradutor.chave})
            dados = await asyncio.to_thread(_ler_json, req)
        except Exception:
            continue
        for pedido in (dados or {}).get("lista") or []:
            agora = time.time()
            nick = pedido.get("nick") or ""
            if nick:
                achados = await asyncio.to_thread(tradutor.buscador.buscar, [nick])
                roblox_id = achados.get(nick)
                if not roblox_id:
                    print(f"[ponte] teste do painel: o nick '{nick}' nao existe",
                          flush=True)
                    continue
                tradutor._lembrar("painel", {"roblox_id": roblox_id,
                                             "nickname": "Painel", "nick": nick})
            conhecido = tradutor._quem_e("painel")
            if not conhecido:
                print("[ponte] teste do painel: informe um nick do Roblox no painel",
                      flush=True)
                continue

            moedas = int(pedido.get("moedas") or 0)
            nome = pedido.get("presente") or "Teste"
            efeito = tradutor.cfg.efeito_do_presente(nome, moedas)

            #[[ O TESTE DE UMA DANCA SO'.
            #
            #   O painel manda o nome do passo e o resto do caminho continua
            #   igual ao de um presente de verdade -- mesma fila, mesma camera,
            #   mesmo avatar. E' o que faz o botao "ver como fica" responder a
            #   pergunta certa: nao "esta danca existe?", e sim "e' esta que eu
            #   quero na minha live?".
            #
            #   Passa pelo `limitar` de novo porque um nome que nao esta' na
            #   lista de dancas validas precisa virar "" (a danca padrao) antes
            #   de descer pro Roblox. Sem isso, um nome torto viraria um boneco
            #   PARADO EM PE' no meio da formacao -- o Roblox aceita animacao
            #   que nao existe sem reclamar. ]]
            danca = str(pedido.get("danca") or "").strip().lower()
            if danca:
                efeito = regras.limitar(dict(efeito, danca=danca))
            for i in range(max(1, int(pedido.get("vezes") or 1))):
                tradutor._enfileirar("painel", "Painel", conhecido["roblox_id"],
                                     efeito, moedas, agora,
                                     nick_roblox=conhecido.get("nick") or "",
                                     repeticao=(i > 0), presente=nome,
                                     tipo=pedido.get("tipo") or "presente",
                                     combo=i)


def _ler_json(req):
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


# =========================== O que o painel ve' ===========================

async def laco_painel(tradutor):
    """Sobe diario, jogadores e presentes vistos pro painel, 1x por segundo.

    UM LACO SO', E NAO UM ENVIO POR EVENTO.

    Mandar cada linha de log na hora em que ela acontece pareceria mais
    simples, e seria o erro classico: numa live movimentada sao dezenas de
    eventos por segundo, e cada um viraria uma requisicao HTTP no meio do
    caminho que processa o chat. O primeiro soluco do servidor local viraria
    atraso na live inteira -- ou seja, o RECURSO DE DIAGNOSTICO passaria a ser
    a causa do problema que ele deveria ajudar a achar.

    Tudo aqui e' descartavel: se o envio falhar, as linhas daquele segundo se
    perdem e a live nao percebe. E' de proposito.
    """
    if tradutor.simular_envio:
        return
    while True:
        await asyncio.sleep(1.0)
        linhas, jogadores, vistos = tradutor._drenar_painel()
        if not linhas and not jogadores and not vistos:
            continue
        try:
            if linhas:
                await asyncio.to_thread(tradutor.publicar, "/logs",
                                        {"linhas": linhas})
            if jogadores:
                await asyncio.to_thread(tradutor.publicar, "/jogadores",
                                        {"lista": jogadores})
            for pid, (nome, moedas, imagem) in vistos.items():
                await asyncio.to_thread(
                    tradutor.publicar, "/presentes-vistos",
                    {"id": pid, "nome": nome, "moedas": moedas,
                     "imagem": imagem})
        except Exception:
            # Diagnostico nao derruba live. Nem loga o proprio erro: um log que
            # falha registrando que o log falhou e' um laco infinito garantido.
            pass


# =========================== O painel manda na conexao ===========================

async def laco_controle(tradutor, estado):
    """Pergunta ao painel em que conta a ponte deveria estar.

    O `estado` e' compartilhado com o laco do TikTok. A conversa entre os dois
    e' de UMA via so': aqui a gente so' ANOTA o que o painel quer, e quem
    conecta ou desconecta e' o laco de la'. Fazer as duas coisas neste laco
    exigiria cancelar a conexao de dentro de outra tarefa, que e' de onde vem
    a classe inteira de bug de "desconectei e ficou conectado".
    """
    if tradutor.simular_envio:
        return
    while True:
        try:
            dados = await asyncio.to_thread(
                tradutor.buscar_json, "/controle")
        except Exception:
            dados = None
        if isinstance(dados, dict):
            revisao = int(dados.get("revisao") or 0)
            if revisao != estado["revisao"]:
                estado["revisao"] = revisao
                # `tiktok.limpar`, e nao o `_arroba` daqui: o que chega nesta
                # rota e' texto COLADO por uma pessoa (link do perfil,
                # caractere invisivel junto), e nao um @ que a biblioteca do
                # TikTok ja' entregou pronto. Ver ponte/conta.py.
                estado["conta"] = tiktok.limpar(dados.get("conta"))
                estado["ligado"] = bool(dados.get("ligado"))
                # O laco do TikTok esta' quase sempre dormindo (esperando a
                # proxima tentativa, ou dentro de um connect que dura a live
                # inteira). Sem este aviso, uma troca de conta so' valeria
                # quando a espera atual terminasse -- ate' cinco minutos depois
                # do clique, com o painel dizendo que ja' mudou.
                estado["mudou"].set()
        await asyncio.sleep(1.0)


# De quanto em quanto tempo o resumo aparece, e quantos comentarios ignorados
# bastam pra ele valer a pena. 30s pra nao virar ruido; 5 porque com menos que
# isso ainda pode ser so' o comeco da live.
RESUMO_S = 30.0
RESUMO_MINIMO = 5


async def laco_resumo(tradutor):
    """Conta em voz alta o que esta' sendo IGNORADO.

    Neste jogo um comentario so' vira avatar se ELE FOR um nick do Roblox -- a
    graca e' mostrar a skin da pessoa. "oi", "kkkk" e "salve" nao viram nada, de
    proposito.

    So' que isso era invisivel: numa live com o chat andando e a tela vazia, nao
    ha' como distinguir "ninguem comentou o nick" de "a ponte quebrou" -- e as
    duas coisas se parecem exatamente com nada acontecendo.
    """
    visto = 0
    while True:
        await asyncio.sleep(RESUMO_S)
        novos = tradutor.sem_nick - visto
        if novos < RESUMO_MINIMO:
            continue
        visto = tradutor.sem_nick
        print(f"\n[ponte] {novos} comentario(s) nos ultimos {int(RESUMO_S)}s NAO "
              f"eram nick do Roblox,\n"
              f"        entao nao viraram avatar. Isso e' normal: so' quem "
              f"comenta o\n"
              f"        PROPRIO nick do Roblox entra no jogo.\n", flush=True)


# =========================== Entrada ===========================

async def principal():
    ap = argparse.ArgumentParser(description="Ponte TikTok Live -> Roblox")
    ap.add_argument("--usuario", default=os.environ.get("TIKTOK_USUARIO", ""),
                    help="seu @ do TikTok")
    ap.add_argument("--simular", action="store_true",
                    help="inventa eventos, sem live de verdade")
    ap.add_argument("--intervalo", type=float, default=1.2,
                    help="segundos entre eventos falsos (modo simular)")
    ap.add_argument("--servidor", default=os.environ.get("SERVIDOR_URL",
                                                         "http://127.0.0.1:8000"))
    ap.add_argument("--chave", default=os.environ.get("CHAVE_ESCRITA", "escrita-local"))
    ap.add_argument("--donos", default=os.environ.get("DONOS", ""),
                    help="quem pode usar os comandos de teste, separado por virgula")
    ap.add_argument("--so-console", action="store_true",
                    help="nao fala com o servidor, so' imprime")
    args = ap.parse_args()

    # O @ vem de um .bat, de uma variavel de ambiente ou de alguem colando na
    # mao -- e nos tres casos ele chega com espaco, @ sobrando, o link inteiro
    # do perfil ou um caractere invisivel de brinde. Limpar AQUI, e nao em cada
    # lugar que usa, porque o sintoma de nao limpar e' o pior tipo: o TikTok
    # responde "usuario nao encontrado" e o nome impresso na tela esta'
    # visivelmente CERTO, porque espaco e invisivel nao aparecem.
    digitou_alguma_coisa = bool(str(args.usuario or "").strip())
    args.usuario, recado_da_conta = tiktok.interpretar(args.usuario)
    if recado_da_conta and digitou_alguma_coisa:
        # Nao derruba a ponte: sem @ valido ela sobe DESCONECTADA e espera o
        # painel, que e' um estado legitimo (ver o bloco logo abaixo). O aviso
        # existe pra a pessoa nao ficar olhando pro painel sem entender por que
        # ele abriu vazio depois de ela ter digitado alguma coisa no .bat.
        #
        # O `digitou_alguma_coisa` importa: rodar SEM @ e' o caso normal da
        # segunda live em diante, e avisar ali seria alarme falso toda vez.
        print(f"[ponte] o @ que voce digitou nao serve: {recado_da_conta}\n"
              f"        Subindo desconectada -- digite o @ no painel.",
              flush=True)

    #[[ O @ NAO E' MAIS OBRIGATORIO NA LINHA DE COMANDO.
    #
    #   Ele passou a ser um ajuste do painel, e o painel lembra dele entre uma
    #   live e outra. Exigir aqui significaria que abrir o kit sem digitar nada
    #   e' um erro -- quando na verdade e' o caso normal da segunda vez em
    #   diante. Sem @ em lugar nenhum, a ponte sobe DESCONECTADA e espera voce
    #   clicar em Conectar, que e' um estado legitimo e visivel no painel. ]]
    donos = [d for d in (args.donos or "").split(",") if d.strip()]
    if args.usuario:
        donos.append(args.usuario)

    deps.caixa("PONTE DA LIVE -- iniciando", [
        "Modo : " + ("SIMULACAO (eventos inventados)" if args.simular else "LIVE DE VERDADE"),
        "Conta: " + (args.usuario or "(vem do painel)"),
        deps.python_em_uso(),
    ])

    tradutor = Tradutor(args.servidor, args.chave, donos=donos,
                        simular_envio=args.so_console)
    tradutor.cfg.iniciar()

    tarefas = [laco_janela(tradutor), laco_resumo(tradutor), laco_testes(tradutor),
               laco_painel(tradutor)]

    if args.simular:
        tarefas.append(laco_simulacao(tradutor, args.intervalo))
    else:
        estado = {"conta": "", "ligado": False, "revisao": -1,
                  "mudou": asyncio.Event()}

        #[[ O @ da linha de comando entra como um PEDIDO ao painel, e nao como
        #   um atalho por fora dele.
        #
        #   Assim existe UMA fonte da verdade sobre em que conta a ponte
        #   deveria estar. Se o argumento valesse por fora, o painel abriria
        #   dizendo "desconectado" com a ponte conectada -- e clicar em
        #   Conectar depois disso produziria duas conexoes na mesma conta. ]]
        if args.usuario:
            try:
                await asyncio.to_thread(
                    tradutor.publicar, "/controle",
                    {"conta": args.usuario, "ligado": True})
            except Exception as e:
                print(f"[ponte] nao consegui avisar o painel da conta "
                      f"({e}). Conecte pelo painel.", flush=True)

        tarefas.append(laco_controle(tradutor, estado))
        tarefas.append(laco_tiktok(tradutor, estado))

    await asyncio.gather(*tarefas)


if __name__ == "__main__":
    try:
        asyncio.run(principal())
    except KeyboardInterrupt:
        print("\n[ponte] encerrada.")
    except SystemExit:
        raise  # deps.erro_fatal ja' explicou; nao virar "erro inesperado"
    except Exception as e:
        import traceback
        deps.erro_fatal("A PONTE PAROU POR UM ERRO INESPERADO", [
            "Isso nao e' normal e nao e' culpa da sua configuracao.",
            "Mande um print desta janela inteira pro suporte -- o texto la'",
            "embaixo diz exatamente o que aconteceu.",
        ], detalhe=f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

