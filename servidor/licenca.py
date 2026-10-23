"""A LICENÇA — o lado do APP.

O app busca um MANIFESTO no GitHub, confere a assinatura, e tira dele duas
coisas: se a chave desta máquina é válida, e o CONTEÚDO PROTEGIDO (os IDs
das animações de terceiro e as paletas das cenas).

O QUE ACONTECE QUANDO A CHAVE NÃO VALE
--------------------------------------
O app NÃO QUEBRA. Ele continua funcionando: a formação, a câmera, a aura, os
rótulos, os overlays do OBS, a música. O que falta é o que mora no
manifesto — as danças de presente e as cenas.

Isso é de propósito. Um app que grita "LICENÇA EXPIRADA" na cara de quem
está no meio da live faz duas coisas ruins: derruba a live e ensina a pessoa
a não confiar em você. Um app que degrada em silêncio faz uma coisa boa: a
pessoa percebe que algo falta, e vem perguntar. Aí a resposta está no
painel, em uma linha.

O COMO A CHEGA NO APP
---------------------
    app -> busca o manifesto (GitHub) -> confere a assinatura
        -> acha a entrada do código -> confere a validade
        -> decifra o conteúdo com (código + ativação + mês)

Nenhum servidor, nenhum plano pago, nenhuma chamada por segundo. Uma
requisição na hora de subir, e uma a cada poucas horas depois.

A TOLERÂNCIA
------------
Se o GitHub estiver fora do ar (ou bloqueado na rede do comprador), o app
usa o manifesto que está em CACHE no disco, enquanto ele não estiver
velho demais. Perder a live por causa de uma queda do GitHub seria pior do
que a licença.

A PARTILHA DE CHAVE
-------------------
O conteúdo é cifrado com o par (código + código de ativação). Quem tem só
o código não decifra nada — e o produto fica degradado, que é
indetectável para quem não sabe o que está faltando. É o que impede o
compartilhamento simples.
"""

import base64
import hashlib
import hmac
import json
import os
import platform
import socket
import time
import urllib.error
import urllib.request

import manifesto

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# Onde o manifesto é buscado por padrão. É o repositório de licenças; o
# repositório do APP é outro, e é de lá que o cliente baixa o programa.
#
# Trocar isso aqui é coisa do VENDEDOR, e só do vendedor: a chave pública
# que confere a assinatura mora no código, e o endereço do manifesto também
# (para o caso de alguém apontar o app para outro lugar — a assinatura
# impede que isso sirva para alguma coisa).
MANIFESTO_PADRAO = ("https://raw.githubusercontent.com/tecnosh97/"
                    "YouPI-PG-licencas/main/licencas.json")

# A CHAVE PÚBLICA que confere a assinatura do manifesto.
#
# Ela é pública de propósito: a assinatura do manifesto é o que impede
# que alguém ALTERE o manifesto (inclusive de se auto-autorizar). A chave
# PRIVADA é a do vendedor, e nunca sai do app KEY.
#
# ESTE ARQUIVO VAI PARA O GITHUB. A chave privada, NÃO.
CHAVE_PUBLICA_PADRAO = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEASCel2rFGiZR5rc//JNXs5YrTpA4pWYnVB3RjFpYIsig=
-----END PUBLIC KEY-----"""


class ErroLicenca(Exception):
    """A licença não vale. A mensagem é a que o usuário lê."""

    def __init__(self, mensagem, codigo="invalida"):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo


# ═══════════════════════════════════════════════════════════════════
#  A MÁQUINA
# ═══════════════════════════════════════════════════════════════════

def id_maquina():
    """Um id estável desta máquina, que não diz NADA sobre ela.

    O id é o hash de duas coisas que o Windows não deixa trocar de graça:
    o MachineGuid do registro e o número de série do volume do sistema.
    O hash é de uma via só: o id que circula não é o MachineGuid, e não
    dá pra voltar do id até o guid.

    Quem não está no Windows cai no nome da máquina e no endereço MAC.
    """
    pedacos = [platform.system(), platform.node()]

    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Cryptography") as k:
                guid = str(winreg.QueryValueEx(k, "MachineGuid")[0])
            pedacos.append(guid)
        except Exception:
            pass
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(261)
            fs = ctypes.windll.kernel32.GetVolumeInformationW(
                None, buf, 261, None, None, None, None, 0)
            if fs:
                pedacos.append(buf.value)
        except Exception:
            pass

    try:
        pedacos.append(socket.gethostname())
    except Exception:
        pass

    return hashlib.sha256("|".join(pedacos).encode("utf-8")).hexdigest()[:32]


# ═══════════════════════════════════════════════════════════════════
#  O CLIENTE
# ═══════════════════════════════════════════════════════════════════

class ClienteLicenca:
    """Fala com o manifesto no GitHub."""

    def __init__(self, url="", codigo="", ativacao="", chave_publica=None,
                 cache_horas=6, cache=None, timeout=12, maquina=None):
        self.url = str(url or MANIFESTO_PADRAO)
        self.codigo = str(codigo or "")
        self.ativacao = str(ativacao or "")
        self.chave_publica = chave_publica or CHAVE_PUBLICA_PADRAO
        self.cache_horas = float(cache_horas or 6)
        self.cache = cache or os.path.join(RAIZ, "config", "licenca-cache.json")
        self.timeout = timeout
        self.maquina = maquina or id_maquina()

        self.manifesto = None
        self.conteudo = None
        self.estado = "sem_manifesto"
        self.motivo = "a licenca ainda nao foi conferida"
        self.expira = ""
        self.ultimo_fetch = 0.0

    # ─────────────── o configuration ───────────────

    @classmethod
    def do_arquivo(cls, caminho, timeout=12):
        """Lê a configuração da licença e monta o cliente.

        O `utf-8-sig` não é um detalhe: o Bloco de Notas do Windows grava
        JSON COM BOM, e um BOM no começo do arquivo faz o `json.load`
        recusar o arquivo inteiro. Quem edita a chave no Bloco de Notas
        (que é o jeito normal) perderia a licença sem nenhum aviso.
        """
        dados = {}
        try:
            with open(caminho, "r", encoding="utf-8-sig") as f:
                dados = json.load(f)
        except (OSError, ValueError):
            dados = {}
        return cls(url=dados.get("manifesto") or "",
                   codigo=dados.get("chave") or "",
                   ativacao=dados.get("ativacao") or "",
                   chave_publica=dados.get("chave_publica") or None,
                   cache_horas=dados.get("cache_horas", 6),
                   timeout=timeout,
                   cache=os.path.join(os.path.dirname(caminho),
                                      "licenca-cache.json"))

    def gravar(self, codigo=None, ativacao=None, url=None):
        """Grava a configuração. A máquina é preenchida na primeira vez."""
        dados = {}
        try:
            with open(os.path.join(RAIZ, "config", "licenca.json"),
                      "r", encoding="utf-8-sig") as f:
                dados = json.load(f)
        except (OSError, ValueError):
            dados = {}
        if url is not None:
            dados["manifesto"] = url
            self.url = url
        if codigo is not None:
            dados["chave"] = codigo
            self.codigo = codigo
        if ativacao is not None:
            dados["ativacao"] = ativacao
            self.ativacao = ativacao
        dados.setdefault("maquina", self.maquina)
        caminho = os.path.join(RAIZ, "config", "licenca.json")
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return dados

    # ─────────────── o manifesto ───────────────

    def _ler_cache(self):
        try:
            with open(self.cache, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
            if isinstance(d, dict) and d.get("manifesto"):
                return d
        except (OSError, ValueError):
            pass
        return None

    def _gravar_cache(self, manifesto_bruto):
        try:
            os.makedirs(os.path.dirname(self.cache), exist_ok=True)
            with open(self.cache, "w", encoding="utf-8") as f:
                json.dump({"manifesto": manifesto_bruto,
                           "quando": time.time()}, f, ensure_ascii=False)
        except OSError:
            pass

    def _buscar(self):
        """Busca o manifesto na rede. Devolve (manifesto, erro).

        O `?v=` no final é um ESCAPE DO CACHE do GitHub. O
        `raw.githubusercontent.com` é servido por uma CDN que guarda a
        resposta por alguns minutos — e sem isso, uma chave newly-vendida
        podia demorar ate' cinco minutos para ser vista pelo app do
        cliente. Numa venda, cinco minutos e' uma eternidade.

        O app ja' guarda o manifesto em cache local por horas, entao o
        cache-buster so' custa uma requisicao a cada poucas horas.
        """
        url = self.url
        separador = "&" if "?" in url else "?"
        url = f"{url}{separador}v={int(time.time())}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "YouPI-PG/1.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                bruto = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return None, f"o servidor do manifesto respondeu {e.code}"
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return None, f"nao consegui buscar o manifesto: {e}"
        try:
            return json.loads(bruto), None
        except ValueError:
            return None, "o manifesto veio ilegivel"

    def carregar(self, forcar_rede=False):
        """Busca (ou usa o cache) e confere a assinatura.

        `forcer_rede=True` ignora o manifesto em cache e vai na rede.

        Devolve (ok, motivo).
        """
        cache = self._ler_cache()
        idade = (time.time() - float((cache or {}).get("quando") or 0)) \
            if cache else 1e9
        dentro = idade < self.cache_horas * 3600

        if cache and dentro and not forcar_rede:
            ok, motivo = manifesto.conferir(cache["manifesto"], self.chave_publica)
            if ok:
                self.manifesto = cache["manifesto"]
                self.ultimo_fetch = float(cache.get("quando") or 0)
                return True, "ok (do cache)"

        # 2. a rede
        m, erro = self._buscar()
        if m is not None:
            ok, motivo = manifesto.conferir(m, self.chave_publica)
            if ok:
                self.manifesto = m
                self.ultimo_fetch = time.time()
                self._gravar_cache(m)
                return True, "ok"
            # veio algo, mas não confere: o cache ainda é melhor que nada
            if cache and dentro:
                ok2, _ = manifesto.conferir(cache["manifesto"], self.chave_publica)
                if ok2:
                    self.manifesto = cache["manifesto"]
                    self.ultimo_fetch = float(cache.get("quando") or 0)
                    return True, "ok (cache; o novo nao confere)"
            return False, f"a assinatura do manifesto nao confere: {motivo}"

        # 3. sem rede: o cache velho ainda serve, DENTRO da tolerancia
        #
        # O prazo importa: sem ele, o cache seria um buraco permanente -- o
        # cliente buscaria o manifesto uma vez e nunca mais, e a licenca
        # valeria para sempre.
        #
        # Repare que a tolerancia NAO estende a licenca: a data de vencimento
        # esta DENTRO do manifesto, e e' ela que decide. O cache so' protege
        # contra o GitHub estar fora do ar.
        if cache and dentro:
            ok2, _ = manifesto.conferir(cache["manifesto"], self.chave_publica)
            if ok2:
                self.manifesto = cache["manifesto"]
                self.ultimo_fetch = float(cache.get("quando") or 0)
                return True, "ok (cache; a rede falhou)"
            return False, "o manifesto em cache nao confere"

        return False, erro or "nao consegui achar o manifesto"

    # ─────────────── a conferência ───────────────

    def conferir(self):
        """Confere a licença e busca o conteúdo protegido.

        Devolve (ok, motivo, conteudo). O conteúdo é None quando a
        licença não vale — e isso NÃO é erro: é a degradação silenciosa.
        """
        if not self.codigo:
            self.estado = "sem_chave"
            self.motivo = "Nenhuma chave de licenca configurada."
            return False, self.motivo, None

        ok, motivo = self.carregar()
        if not ok:
            self.estado = "sem_manifesto"
            self.motivo = motivo
            return False, motivo, None

        entrada = manifesto.entrada_de(self.manifesto, self.codigo)
        vencida = manifesto.vencida(entrada) if entrada else True

        #[[ SE A CHAVE NAO ESTA' NO CACHE, VAI NA REDE ANTES DE RECUSAR.
        #
        #   O manifesto em cache pode ser de ANTES da compra: o cliente
        #   renovou, o vendedor publicou, e o app ainda tem o manifesto
        #   velho guardado. Recusar a chave nesse caso seria o pior
        #   defeito possível: o cliente pagou, e o app diz que não.
        #
        #   Por isso: achou no cache E nao venceu -> usa. Nao achou ou
        #   venceu -> busca o de verdade, e so THEN recusa. ]]
        if (not entrada) or vencida:
            ok_rede, _ = self.carregar(forcar_rede=True)
            if ok_rede:
                entrada = manifesto.entrada_de(self.manifesto, self.codigo)
                vencida = manifesto.vencida(entrada) if entrada else True

        if not entrada:
            self.estado = "desconhecida"
            self.motivo = ("Esta chave nao esta' liberada. Confira se digitou "
                           "certinho, ou peca uma nova.")
            return False, self.motivo, None

        if vencida:
            self.estado = "vencida"
            self.expira = str(entrada.get("ate") or "")
            self.motivo = ("A licenca venceu em " + (self.expira[:10] or "?")
                           + ". Pegue a renovacao com quem te vendeu.")
            return False, self.motivo, None

        conteudo = manifesto.conteudo_de(entrada, self.codigo, self.ativacao)
        if conteudo is None:
            self.estado = "ativacao"
            self.motivo = ("O codigo de ativacao nao confere com esta chave.")
            return False, self.motivo, None

        self.estado = "ok"
        self.motivo = "licenca valida"
        self.expira = str(entrada.get("ate") or "")
        self.conteudo = conteudo
        return True, self.motivo, conteudo

    def estado_para_painel(self):
        """O que o painel mostra: o estado, o motivo e a validade."""
        return {"ok": self.estado == "ok", "codigo": self.estado,
                "motivo": self.motivo, "expira": self.expira,
                "maquina": self.maquina}
