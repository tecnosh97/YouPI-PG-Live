"""A PERCURSO INTEIRA, com os dois lados de verdade.

    python servidor\\teste_ida_e_volta.py

Sobe o app KEY (que monta e assina o manifesto), serve o manifesto como se
fosse o GitHub, e pergunta ao APP se ele consegue ler o conteudo
protegido.

E' o teste que responde "a venda funciona?" — e nao "a funcao existe?".
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PASTA_KEY = os.path.join(os.path.dirname(RAIZ), "YouPI-KEY")

sys.path.insert(0, AQUI)
import licenca   # noqa: E402


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    pasta = tempfile.mkdtemp(prefix="ida-")
    print()
    print("  A PERCURSO INTEIRA")
    print("  " + "-" * 46)

    # ── 1. o app KEY monta e assina o manifesto ──
    sys.path.insert(0, PASTA_KEY)
    os.chdir(PASTA_KEY)
    import chave as keyapp

    config = keyapp.carregar_config()
    config["app"] = RAIZ
    c = keyapp.gerar_cliente("ida-e-volta@teste.com", dias=30,
                             pasta_app=RAIZ)
    m = keyapp.assinar_manifesto(keyapp.montar_manifesto(dias=30, pasta_app=RAIZ))
    print(f"  1. o app KEY gerou a chave e assinou o manifesto "
          f"({len(m.get('chaves') or {})} chave(s))")

    # ── 2. o manifesto "no GitHub" ──
    porta = porta_livre()
    fora = {"m": m}

    class Manipulador(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            corpo = json.dumps(fora["m"]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

    srv = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{porta}/licencas.json"
    print(f"  2. o manifesto está servindo em {url}")

    # ── 3. o app busca e decifra ──
    publica = keyapp.par_de_chaves()[1]
    cliente = licenca.ClienteLicenca(
        url=url, codigo=c["codigo"], ativacao=c["ativacao"],
        chave_publica=publica, cache_horas=6,
        cache=os.path.join(pasta, "cache.json"))

    ok, motivo, conteudo = cliente.conferir()
    print(f"  3. o app conferiu: {motivo}")
    if not ok or not conteudo:
        print("     FALHOU: o app nao conseguiu o conteudo")
        srv.shutdown()
        return 1

    dancas = conteudo.get("dancas") or {}
    cenas = conteudo.get("cenas") or {}
    print(f"     dancas no pacote : {len(dancas)} "
          f"(rosquinha = {dancas.get('rosquinha')})")
    print(f"     cenas no pacote  : {len(cenas)} "
          f"({', '.join(list(cenas)[:6])})")
    print(f"     animacao principal: {conteudo.get('animacao')}")

    # ── 4. e sem a ativação? ──
    cliente2 = licenca.ClienteLicenca(
        url=url, codigo=c["codigo"], ativacao="ERRADA-ERRADA-ERRADA-ERRADA",
        chave_publica=publica, cache_horas=6,
        cache=os.path.join(pasta, "cache2.json"))
    ok2, motivo2, conteudo2 = cliente2.conferir()
    print(f"  4. sem a ativação: ok={ok2}  motivo={motivo2}")
    print(f"     conteudo liberado? {conteudo2 is not None}  "
          f"(tem que ser False)")

    srv.shutdown()

    # ── 5. e com um manifesto adulterado? ──
    fora2 = {"m": dict(m)}
    chaves = dict(fora2["m"]["chaves"])
    chaves["0" * 64] = {"ate": "2099-01-01", "mes": "2026-10",
                         "conteudo": "abcd", "notas": "FALSO"}
    fora2["m"]["chaves"] = chaves
    porta2 = porta_livre()

    class M2(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            corpo = json.dumps(fora2["m"]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

    srv2 = ThreadingHTTPServer(("127.0.0.1", porta2), M2)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    cliente3 = licenca.ClienteLicenca(
        url=f"http://127.0.0.1:{porta2}/licencas.json",
        codigo=c["codigo"], ativacao=c["ativacao"],
        chave_publica=publica, cache_horas=6,
        cache=os.path.join(pasta, "cache3.json"))
    ok3, motivo3, _ = cliente3.conferir()
    print(f"  5. manifesto adulterado: ok={ok3}  motivo={motivo3}")
    srv2.shutdown()

    print()
    if ok and conteudo and not ok2 and not ok3:
        print("  TUDO CERTO: o app le o conteudo com o par certo, e nao le")
        print("  sem a ativacao nem com o manifesto adulterado.")
        return 0
    print("  ALGUMA COISA NAO DEU CERTO")
    return 1


if __name__ == "__main__":
    sys.exit(main())
