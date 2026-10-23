"""A configuracao que o PAINEL salvou, lida do servidor local.

POR QUE ISTO EXISTE
-------------------
A tabela de efeitos vive em regras.py. Se fosse so' ela, mexer no equilibrio da
live seria editar Python e reiniciar tudo -- no meio da transmissao, com a
galera assistindo. Aqui a tabela mora no servidor e voce mexe pelo painel, ao
vivo, sem fechar nada.

O regras.py NAO morreu: ele continua sendo o padrao de fabrica e a rede de
seguranca. Servidor fora do ar, resposta torta, painel nunca aberto -- em todos
esses casos a ponte cai na tabela de sempre e a live segue. Nunca e' o painel
que decide se a live FUNCIONA; so' o quanto ela e' sua.

A busca roda numa thread separada porque o laco da ponte nao pode esperar HTTP:
uma live com combo entrando trava feio se o laco principal parar 2 segundos pra
buscar configuracao.
"""

import json
import threading
import time
import urllib.error
import urllib.request

import regras

# De quanto em quanto tempo reconsultar. 5s e' rapido o bastante pra voce sentir
# que "salvou e ja' valeu", e leve o bastante pra nao pesar em nada.
INTERVALO_S = 5.0


def _texto_do_id(valor):
    """O ID de um presente como TEXTO comparavel, ou "".

    Existe porque o mesmo ID chega de tres formas diferentes no caminho: numero
    inteiro (da biblioteca do TikTok), numero com ponto flutuante (depois de
    passar por JSON em alguns clientes) e texto (digitado no painel). Sem
    normalizar, 5655, 5655.0 e "5655" seriam tres presentes distintos, e o
    gatilho que voce cadastrou no painel simplesmente nao pegaria -- sem erro
    nenhum, porque "nao casou por ID" e' um caminho valido que cai na faixa.
    """
    if valor is None or isinstance(valor, bool):
        return ""
    if isinstance(valor, float):
        # 5655.0 -> "5655"; um ID nunca e' fracionario.
        if valor != valor or valor in (float("inf"), float("-inf")):
            return ""
        valor = int(valor)
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto if texto.isdigit() else ""


class ConfigDoPainel:
    """Guarda a ultima configuracao boa e responde na hora, sem HTTP no caminho."""

    def __init__(self, url, chave, intervalo_s=INTERVALO_S):
        self.url = (url or "").rstrip("/")
        self.chave = chave or ""
        self.intervalo_s = intervalo_s
        self._cfg = None
        self._trava = threading.Lock()
        self._ja_reclamou = False
        # Sobe de 1 em 1 a cada configuracao NOVA. E' o que o indice por ID usa
        # pra saber que precisa ser refeito -- ver `_indice_por_id`.
        self._versao = 0
        self._indice = None
        self._indice_versao = -1

    # ---------- busca ----------

    def buscar(self):
        """Uma consulta. True se atualizou. Nunca levanta."""
        if not self.url:
            return False
        try:
            req = urllib.request.Request(self.url + "/ajustes",
                                         headers={"X-Chave": self.chave})
            with urllib.request.urlopen(req, timeout=5) as r:
                dados = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                TimeoutError, ValueError) as e:
            if not self._ja_reclamou:
                self._ja_reclamou = True
                print(f"[painel] nao consegui ler os ajustes ({e}) -- usando a "
                      f"tabela padrao ate' o painel voltar.", flush=True)
            return False

        if not isinstance(dados, dict):
            return False

        with self._trava:
            primeira = self._cfg is None
            self._cfg = dados
            self._versao += 1

        if self._ja_reclamou or primeira:
            self._ja_reclamou = False
            quantos = len(dados.get("presentes") or {})
            print(f"[painel] ajustes carregados ({quantos} presente(s) com "
                  f"gatilho proprio).", flush=True)
        return True

    def iniciar(self):
        """Sobe a thread que mantem a configuracao fresca."""
        self.buscar()  # a primeira e' sincrona: a live ja' comeca configurada

        def laco():
            while True:
                time.sleep(self.intervalo_s)
                self.buscar()

        threading.Thread(target=laco, daemon=True).start()
        return self

    def _cru(self):
        with self._trava:
            return self._cfg

    # ---------- consultas ----------

    def efeito_do_presente(self, nome, moedas, total_combo=None, presente_id=None):
        """Nome (+ ID) + moedas -> efeito, respeitando o painel.

        A ORDEM DE CASAMENTO, E POR QUE ELA E' ESTA

          1. ID do presente     numero do TikTok. Nao muda de regiao pra
                                regiao nem quando eles traduzem o nome, entao
                                e' o unico casamento que nunca sai do lugar.
          2. APELIDO            o nome em minusculas. Serve enquanto voce ainda
                                nao cadastrou o ID.
          3. FAIXA DE PRECO     a rede de seguranca: presente que voce nunca
                                viu ja' nasce funcionando pelo valor dele.
          4. TABELA DE FABRICA  se o painel nao respondeu nada util.

        Nenhum presente sai daqui sem efeito.
        """
        cfg = self._cru()
        if not cfg:
            return regras.efeito_do_presente(nome, moedas, total_combo, presente_id)

        try:
            m = max(0, int(moedas))
        except (TypeError, ValueError):
            m = 0
        nome_baixo = str(nome or "").strip().lower()
        extra = regras.bonus_de_combo(m if total_combo is None else total_combo)
        presentes = cfg.get("presentes") or {}

        # 1) Pelo ID. As chaves do catalogo sao apelidos, entao o indice por ID
        # e' montado uma vez por configuracao nova e guardado -- refaze-lo a
        # cada presente seria varrer o catalogo inteiro no caminho quente.
        chave_id = _texto_do_id(presente_id)
        if chave_id:
            achado = self._indice_por_id().get(chave_id)
            if isinstance(achado, dict):
                return regras.limitar(achado, extra)

        # 2) Pelo apelido.
        proprio = presentes.get(nome_baixo)
        if isinstance(proprio, dict):
            return regras.limitar(proprio, extra)

        # 3) O servidor entrega as faixas da mais cara pra mais barata, entao a
        # primeira que couber e' a certa.
        for faixa in cfg.get("faixas") or []:
            if not isinstance(faixa, dict):
                continue
            try:
                minimo = float(faixa.get("min", 0))
            except (TypeError, ValueError):
                continue
            if m >= minimo:
                return regras.limitar(faixa.get("efeito"), extra)

        return regras.efeito_do_presente(nome, moedas, total_combo, presente_id)

    def _indice_por_id(self):
        """{id_do_presente: efeito}, montado uma vez por configuracao.

        `_versao` muda toda vez que o `buscar` troca a configuracao. Comparar a
        versao (e nao o conteudo) e' o que deixa o indice ser reaproveitado
        entre presentes sem nunca ficar velho: salvar no painel invalida o
        indice no mesmo instante em que a configuracao nova chega.
        """
        with self._trava:
            if self._indice_versao == self._versao and self._indice is not None:
                return self._indice
            indice = {}
            for efeito in (self._cfg or {}).get("presentes", {}).values():
                if not isinstance(efeito, dict):
                    continue
                chave = _texto_do_id(efeito.get("id"))
                if chave:
                    indice[chave] = efeito
            self._indice, self._indice_versao = indice, self._versao
            return indice

    def _acao(self, chave, padrao, ligado_sem_painel=True):
        """(efeito, ligado). Sempre passa pelo limitar, ate' sem painel: o
        resto da ponte espera o dicionario COMPLETO, e devolver o cru daqui
        deixaria um formato diferente escapar por um caminho so'.

        O `ligado_sem_painel` E' A CORRECAO DE UM BUG QUE APARECIA AO VIVO.

        Antes, os dois caminhos de "nao sei o que o painel diz" -- ajustes ainda
        nao carregados, servidor fora do ar por um instante, secao ausente --
        devolviam LIGADO. Ou seja: a duvida abria a porteira. Uma curtida
        desligada no painel voltava a spawnar sozinha no primeiro soluco de
        rede, e como curtida nao aparece no chat, quem estava transmitindo via
        bonecos nascendo do nada, sem nenhuma explicacao possivel na tela.

        Agora cada acao diz o que fazer na duvida, e as tres que nao dependem do
        chat (curtida, seguiu, compartilhou) dizem NAO. Comentario e presente
        continuam dizendo sim, porque eles SAO o produto: falhar fechado neles
        deixaria a live muda, que e' o defeito oposto e igualmente ruim.
        """
        cfg = self._cru()
        if not cfg:
            return regras.limitar(padrao), ligado_sem_painel
        bruto = (cfg.get("acoes") or {}).get(chave)
        if not isinstance(bruto, dict):
            return regras.limitar(padrao), ligado_sem_painel
        # `ativo` desligado no painel = a acao nao spawna ninguem.
        return regras.limitar(bruto), bruto.get("ativo", ligado_sem_painel) is not False

    def efeito_do_comentario(self):
        # Comentario com nick do Roblox e' A promessa do kit. Na duvida, LIGADO.
        efeito, ligado = self._acao("comentario", regras.COMENTARIO,
                                    ligado_sem_painel=True)
        return efeito if ligado else None

    def efeito_social(self, chave):
        """`chave` e' "seguiu" ou "compartilhou". None = desligado no painel."""
        # Na duvida, DESLIGADO: seguir e compartilhar nao passam pelo chat, e
        # quem esta' transmitindo nao tem como ligar o boneco ao que aconteceu.
        efeito, ligado = self._acao(chave, regras.BARATO, ligado_sem_painel=False)
        return efeito if ligado else None

    def efeito_curtida(self):
        """(efeito, a_cada). efeito None = curtida desligada no painel."""
        # Na duvida, DESLIGADO. A curtida e' o evento mais frequente de uma live
        # -- dezenas por segundo -- entao ela e' justamente a que nao pode
        # voltar sozinha: em segundos ela enche a formacao com o chat parado.
        efeito, ligado = self._acao("curtida", regras.BARATO,
                                    ligado_sem_painel=False)
        cfg = self._cru() or {}
        bruto = (cfg.get("acoes") or {}).get("curtida") or {}
        try:
            a_cada = int(bruto.get("a_cada", 200))
        except (TypeError, ValueError):
            a_cada = 200
        return (efeito if ligado else None), max(1, min(a_cada, 100_000))

    def geral(self, chave, padrao):
        cfg = self._cru()
        if not cfg:
            return padrao
        try:
            return int((cfg.get("geral") or {}).get(chave, padrao))
        except (TypeError, ValueError):
            return padrao

    def geral_decimal(self, chave, padrao):
        """Igual ao `geral`, sem arredondar.

        Existe porque `tamanho_max` e `crescimento_suave` sao fracionarios, e
        passar os dois pelo `int()` do metodo acima transformaria um teto de
        6.0 em 6 (inofensivo) e uma animacao de 0.6s em ZERO -- ou seja, o
        crescimento suave viraria um salto seco, e o ajuste do painel pareceria
        nao funcionar.
        """
        cfg = self._cru()
        if not cfg:
            return padrao
        try:
            return float((cfg.get("geral") or {}).get(chave, padrao))
        except (TypeError, ValueError):
            return padrao
