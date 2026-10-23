"""Testes do MANIFESTO de licenças. Rodam sozinhos, sem internet.

    python servidor\\testes_manifesto.py

Estes testes sobem um servidor HTTP local que finge ser o GitHub, montam
um manifesto de verdade (assinado com uma chave de verdade) e verificam o
caminho inteiro:

  - a assinatura confere
  - a chave certa traz o CONTEÚDO PROTEGIDO
  - a ativação errada NÃO traz (e o app degrada em silêncio)
  - a chave vencida NÃO traz
  - a chave desconhecida NÃO traz
  - um manifesto adulterado é RECUSADO (é o que impede a auto-autorização)
  - o app continua funcionando sem manifesto nenhum (o cache)
"""

import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

import licenca     # noqa: E402
import manifesto   # noqa: E402


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class GitHubFalso:
    """O repositório do manifesto, servido em localhost."""

    def __init__(self):
        self.porta = porta_livre()
        self.manifesto = None
        self.erro = False
        fora = self

        class Manipulador(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if fora.erro:
                    self.send_response(500)
                    self.end_headers()
                    return
                corpo = json.dumps(fora.manifesto).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

        self.srv = ThreadingHTTPServer(("127.0.0.1", self.porta), Manipulador)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}/licencas.json"

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


class TesteManifesto(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="manifesto-")
        self.github = GitHubFalso()

        # Um par de chaves de verdade, como o app KEY gera.
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        from cryptography.hazmat.primitives import serialization

        priv = Ed25519PrivateKey.generate()
        self.privada = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()).decode()
        self.publica = priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()

        self.codigo = "ABCDE-FGHIJ-KLMNO-PQRST-UVWXY-Z2345"
        self.ativacao = "AAAAA-BBBBB-CCCCC-DDDDD"
        self.conteudo = {"dancas": {"festa": 507776879},
                         "cenas": {"neon": {"cores": {"PISTA_A": [1, 2, 3]}}},
                         "animacao": 83796130837213}

    def tearDown(self):
        self.github.fechar()

    # ─────────────── auxiliares ───────────────

    def _manifesto(self, ate=None, mes=None, conteudo=None):
        mes = mes or manifesto.mes_atual()
        ate = ate or time.strftime("%Y-%m-%d",
                                  time.localtime(time.time() + 30 * 86400))
        chave = manifesto.derivar_chave(self.codigo, self.ativacao, mes)
        m = manifesto.montar([{
            "codigo": self.codigo, "ate": ate, "mes": mes,
            "conteudo": manifesto.cifrar(
                conteudo if conteudo is not None else self.conteudo, chave),
            "notas": "C0123456",
        }])
        m["assinatura"] = manifesto.assinar(m, self.privada)
        return m

    def _cliente(self, codigo=None, ativacao=None, cache_horas=6):
        return licenca.ClienteLicenca(
            url=self.github.url,
            codigo=codigo if codigo is not None else self.codigo,
            ativacao=ativacao if ativacao is not None else self.ativacao,
            chave_publica=self.publica,
            cache_horas=cache_horas,
            cache=os.path.join(self.pasta, "cache.json"),
        )

    # ─────────────── o caminho feliz ───────────────

    def test_a_chave_certa_traz_o_conteudo_protegido(self):
        self.github.manifesto = self._manifesto()
        c = self._cliente()
        ok, motivo, conteudo = c.conferir()
        self.assertTrue(ok, motivo)
        self.assertEqual(conteudo["dancas"]["festa"], 507776879)
        self.assertEqual(conteudo["animacao"], 83796130837213)
        self.assertIn("neon", conteudo["cenas"])

    def test_a_assinatura_confere(self):
        self.github.manifesto = self._manifesto()
        c = self._cliente()
        c.carregar()
        self.assertTrue(manifesto.verificar(self.github.manifesto, self.publica))

    # ─────────────── as portas fechadas ───────────────

    def test_a_ativacao_errada_nao_traz_o_conteudo(self):
        """O código sozinho não abre nada. É o que impede o compartilhamento."""
        self.github.manifesto = self._manifesto()
        c = self._cliente(ativacao="XXXXX-XXXXX-XXXXX-XXXXX")
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        self.assertIsNone(conteudo)
        self.assertEqual(c.estado, "ativacao")

    def test_a_chave_vencida_nao_traz_o_conteudo(self):
        vencida = time.strftime("%Y-%m-%d",
                                time.localtime(time.time() - 86400))
        self.github.manifesto = self._manifesto(ate=vencida)
        c = self._cliente()
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        self.assertIsNone(conteudo)
        self.assertEqual(c.estado, "vencida")

    def test_a_chave_desconhecida_nao_traz_o_conteudo(self):
        self.github.manifesto = self._manifesto()
        c = self._cliente(codigo="ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ")
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        self.assertIsNone(conteudo)
        self.assertEqual(c.estado, "desconhecida")

    def test_um_manifesto_adulterado_e_recusado(self):
        """O comprador não pode acrescentar a chave dele no manifesto.

        É o que a assinatura protege: sem ela, bastaria acrescentar uma
        entrada com o hash da chave de quem quisesse.
        """
        self.github.manifesto = self._manifesto()

        # o comprador acrescenta a chave dele, com o conteudo dele
        m = dict(self.github.manifesto)
        chaves = dict(m["chaves"])
        outro = "ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ"
        chave = manifesto.derivar_chave(outro, self.ativacao, m["chaves"][
            list(m["chaves"])[0]]["mes"])
        chaves[manifesto.hash_codigo(outro)] = {
            "ate": time.strftime("%Y-%m-%d",
                                 time.localtime(time.time() + 30 * 86400)),
            "mes": m["chaves"][list(m["chaves"])[0]]["mes"],
            "conteudo": manifesto.cifrar(self.conteudo, chave),
        }
        m["chaves"] = chaves
        self.github.manifesto = m

        c = self._cliente(codigo=outro)
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok, "um manifesto adulterado nao pode valer")
        self.assertIsNone(conteudo)

    def test_um_manifesto_com_outra_chave_publica_e_recusado(self):
        """O canal nao pode ser sequestrado: a chave publica esta no codigo."""
        self.github.manifesto = self._manifesto()
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        from cryptography.hazmat.primitives import serialization

        outra = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()

        c = self._cliente()
        c.chave_publica = outra
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        self.assertIsNone(conteudo)

    # ─────────────── a degradação silenciosa ───────────────

    def test_sem_licenca_o_app_continua_funcionando(self):
        """A licença não vale é um ESTADO, não uma exceção.

        O app não pode quebrar por causa disso: ele continua rodando, e é
        o CONTEÚDO que falta. É o que faz a degradação ser silenciosa.
        """
        self.github.manifesto = self._manifesto()
        c = self._cliente(ativacao="ERRADA")
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        # e o cliente continua utilizável: a próxima conferência funciona
        c.ativacao = self.ativacao
        ok2, _, conteudo2 = c.conferir()
        self.assertTrue(ok2)
        self.assertIsNotNone(conteudo2)

    def test_sem_manifesto_o_app_continua_funcionando(self):
        """GitHub fora do ar não pode derrubar o app."""
        self.github.erro = True
        c = self._cliente()
        ok, motivo, conteudo = c.conferir()
        self.assertFalse(ok)
        self.assertIsNone(conteudo)
        self.assertEqual(c.estado, "sem_manifesto")

    def test_o_cache_serve_quando_a_rede_cai(self):
        """A tolerância: perder a live por causa do GitHub seria pior que
        a licença."""
        self.github.manifesto = self._manifesto()
        c = self._cliente()
        ok, _, conteudo = c.conferir()
        self.assertTrue(ok)

        self.github.erro = True
        c2 = self._cliente()
        c2.cache = c.cache
        ok2, motivo2, conteudo2 = c2.conferir()
        self.assertTrue(ok2, f"o cache devia segurar: {motivo2}")
        self.assertIsNotNone(conteudo2)

    def test_o_cache_tem_prazo(self):
        """Passou da tolerância, o app fecha. Senão o cache vira um buraco
        permanente: o cliente buscaria o manifesto uma vez e nunca mais."""
        self.github.manifesto = self._manifesto()
        c = self._cliente(cache_horas=0.0001)   # ~0,36 segundo
        ok, _, _ = c.conferir()
        self.assertTrue(ok)
        time.sleep(1.2)
        self.github.erro = True
        c2 = self._cliente(cache_horas=0.0001)
        c2.cache = c.cache
        ok2, _, conteudo2 = c2.conferir()
        self.assertFalse(ok2, "um cache velho demais nao pode valer")

    # ─────────────── a forma do manifesto ───────────────

    def test_o_codigo_e_normalizado(self):
        """O comprador digita o código do e-mail, e às vezes cola com
        espaço ou com o hífen trocado."""
        self.assertEqual(manifesto.normalizar(" abc-def "), "ABCDEF")
        self.assertEqual(manifesto.hash_codigo(" abc-def "),
                         manifesto.hash_codigo("ABCDEF"))

    def test_o_mes_roda_ano_certo(self):
        self.assertEqual(manifesto.proximo_mes("2026-12"), "2027-01")
        self.assertEqual(manifesto.proximo_mes("2026-01"), "2026-02")

    def test_a_rotação_do_mes_muda_a_chave_de_cifragem(self):
        """O blob de um mês não abre o app do mês seguinte.

        É o que faz a rotação mensal ser real, e não só de fachada."""
        chave_outubro = manifesto.derivar_chave(self.codigo, self.ativacao,
                                               "2026-10")
        chave_novembro = manifesto.derivar_chave(self.codigo, self.ativacao,
                                                 "2026-11")
        self.assertNotEqual(chave_outubro, chave_novembro)

    def test_a_assinatura_muda_quando_o_manifesto_muda(self):
        m = self._manifesto()
        a = manifesto.assinar(m, self.privada)
        m["chaves"] = {}
        b = manifesto.assinar(m, self.privada)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
