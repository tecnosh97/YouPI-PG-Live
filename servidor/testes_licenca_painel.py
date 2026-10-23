"""Testa o caminho da chave pelo painel: gravar, conferir, e o que o
cliente ve.

    python servidor\\testes_licenca_painel.py

O que ele prova:
  1. sem chave, o servidor diz que nao ha chave
  2. uma chave errada e' recusada, e a mensagem diz o motivo
  3. a chave certa e' aceita, e o conteudo protegido vem junto
  4. a chave fica gravada no config (e sobrevive ao reinicio)
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

import manifesto as manifesto_mod   # noqa: E402
import servidor as srv             # noqa: E402


class TestePainelDaLicenca(unittest.TestCase):
    """A chave entrando pelo painel, como o cliente faz."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="painel-")
        self.arq = os.path.join(self.pasta, "licenca.json")

        # Um manifesto local, servido por um HTTP local, com uma chave valida.
        self.codigo = "ABCDE-FGHIJ-KLMNO-PQRST-UVWXY-Z2345"
        self.ativacao = "AAAAA-BBBBB-CCCCC-DDDDD"
        chave_cifra = manifesto_mod.derivar_chave(self.codigo, self.ativacao,
                                                  manifesto_mod.mes_atual())
        m = manifesto_mod.montar([{
            "codigo": self.codigo,
            "ate": "2099-12-31",
            "mes": manifesto_mod.mes_atual(),
            "conteudo": manifesto_mod.cifrar(
                {"dancas": {"festa": 507776879},
                 "cenas": {"neon": {"cores": {}}},
                 "animacao": 83796130837213}, chave_cifra),
        }])
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
        m["assinatura"] = manifesto_mod.assinar(m, self.privada)

        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        fora = {"m": m}

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                corpo = json.dumps(fora["m"]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url_manifesto = f"http://127.0.0.1:{self.srv.server_address[1]}/m.json"

        with open(self.arq, "w", encoding="utf-8") as f:
            json.dump({"manifesto": self.url_manifesto, "chave": "",
                       "ativacao": "", "chave_publica": self.publica}, f)

        srv.ARQ_LICENCA = self.arq
        srv.LICENCA = srv.Licenca(self.arq)
        # a primeira conferida: e' ela que establish o estado inicial
        # (sem isso, o estado ficaria em "verificando" e o teste nao
        # diria nada)
        srv.LICENCA.conferir()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def _estado(self):
        return srv.LICENCA.ler(com_pacote=True)

    def test_sem_chave_o_servidor_diz_que_nao_tem(self):
        d = self._estado()
        self.assertFalse(d["ok"])
        self.assertEqual(d["codigo"], "sem_chave")

    def test_chave_errada_e_recusada(self):
        srv.LICENCA.gravar_chave("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX", "errada")
        ok = srv.LICENCA.conferir()
        d = self._estado()
        self.assertFalse(ok)
        self.assertIn(d["codigo"], ("desconhecida", "ativacao"))

    def test_a_chave_certa_abre_o_conteudo(self):
        srv.LICENCA.gravar_chave(self.codigo, self.ativacao)
        ok = srv.LICENCA.conferir()
        d = self._estado()
        self.assertTrue(ok, d.get("motivo"))
        self.assertEqual(d["codigo"], "ok")
        protegido = d.get("protegido") or {}
        self.assertEqual(protegido.get("dancas", {}).get("festa"), 507776879)
        self.assertEqual(protegido.get("animacao"), 83796130837213)

    def test_a_chave_fica_gravada_no_config(self):
        srv.LICENCA.gravar_chave(self.codigo, self.ativacao)
        with open(self.arq, encoding="utf-8-sig") as f:
            dados = json.load(f)
        self.assertEqual(dados["chave"], self.codigo)
        self.assertEqual(dados["ativacao"], self.ativacao)

    def test_a_chave_sobrevive_ao_reinicio(self):
        """O `config` nao pode ser reescrito pela atualizacao.

        E' por isso que a atualizacao copia por cima sem apagar, e sem
        tocar no `config`: a chave do cliente vive la.
        """
        srv.LICENCA.gravar_chave(self.codigo, self.ativacao)
        # um "reinicio" do servidor le o config de novo
        novo = srv.Licenca(self.arq)
        self.assertEqual(novo.cliente.codigo, self.codigo)
        self.assertEqual(novo.cliente.ativacao, self.ativacao)
        self.assertTrue(novo.conferir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
