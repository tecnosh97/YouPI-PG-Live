# -*- coding: utf-8 -*-
# language: Python 3.10+ (tkinter, stdlib), file: servidor/ativador.py
# A JANELA DE ATIVACAO da licenca: o comprador cola o CODIGO e a ATIVACAO
# que recebeu na compra. A conferencia corre no SERVIDOR LOCAL (rota
# POST /licenca/chave), que assina contra o manifesto no GitHub. Esta
# janela nao abre navegador e nao fala com nada alem de localhost:8000.
import json
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request

URL_ATIVACAO = "http://localhost:8000/licenca/chave"

FUNDO = "#16161e"
CARTAO = "#22222e"
TEXTO = "#f0f0f5"
APAGADO = "#8a8a98"
OK = "#4caf6e"
ERRO = "#e0666e"
AZUL = "#5b7fd4"

_fundo = tk.Tk()
_fundo.title("YouPI-PG — ativar licenca")
_fundo.geometry("500x330")
_fundo.resizable(False, False)
_fundo.configure(bg=FUNDO)

_status = tk.StringVar(value="")

tk.Label(_fundo, text="YouPI-PG", font=("Segoe UI", 22, "bold"),
         bg=FUNDO, fg=TEXTO).pack(pady=(16, 2))
tk.Label(_fundo, text="Cole os codigos que voce recebeu na compra",
         font=("Segoe UI", 10), bg=FUNDO, fg=APAGADO).pack(pady=(0, 12))

_cartao = tk.Frame(_fundo, bg=CARTAO, padx=20, pady=16)
_cartao.pack(padx=22, fill="both")

tk.Label(_cartao, text="CODIGO DE LICENCA", font=("Segoe UI", 9, "bold"),
         bg=CARTAO, fg=APAGADO).pack(anchor="w")
_e_codigo = tk.Entry(_cartao, font=("Consolas", 13), justify="center",
                     bg="#14141c", fg=TEXTO, insertbackground=TEXTO,
                     relief="flat")
_e_codigo.pack(fill="x", ipady=5, pady=(3, 10))

tk.Label(_cartao, text="CODIGO DE ATIVACAO", font=("Segoe UI", 9, "bold"),
         bg=CARTAO, fg=APAGADO).pack(anchor="w")
_e_ativacao = tk.Entry(_cartao, font=("Consolas", 13), justify="center",
                       bg="#14141c", fg=TEXTO, insertbackground=TEXTO,
                       relief="flat")
_e_ativacao.pack(fill="x", ipady=5, pady=(3, 4))

_botao = tk.Button(_cartao, text="ATIVAR LICENCA", font=("Segoe UI", 11, "bold"),
                   bg=AZUL, fg="white", activebackground="#6b90e0",
                   activeforeground="white", relief="flat", cursor="hand2")
_botao.pack(fill="x", ipady=6, pady=(10, 0))

tk.Label(_fundo, textvariable=_status, font=("Segoe UI", 10),
         bg=FUNDO, fg=APAGADO, wraplength=460, justify="center").pack(pady=(10, 2))

tk.Label(_fundo, text="Sem licenca ainda? Comprou esta live em:\n"
                     "tecnosh97.github.io/YouPI-SITE/",
         font=("Segoe UI", 8), bg=FUNDO, fg=APAGADO,
         justify="center").pack(side="bottom", pady=(0, 10))


def _posta(chave, ativacao):
    """Manda os codigos pro servidor local; 3 tentativas em caso de queda."""
    corpo = json.dumps({"chave": chave, "ativacao": ativacao}).encode("utf-8")
    ultimo_erro = ""
    for tentativa in range(3):
        try:
            pedido = urllib.request.Request(
                URL_ATIVACAO, data=corpo,
                headers={"Content-Type": "application/json"})
            resposta = urllib.request.urlopen(pedido, timeout=12)
            return json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                return json.loads(erro.read().decode("utf-8"))
            except Exception:
                ultimo_erro = "o servidor respondeu " + str(erro.code)
        except Exception as erro:
            ultimo_erro = "sem resposta do servidor: " + str(erro)
            time.sleep(1.2)
    return {"ok": False, "erro": ultimo_erro + ("" if not ultimo_erro else
              " — o servidor da live ficou mudo (feche e rode o bat de novo).")
            }


def _no_fim(ok, mensagem):
    _botao.config(state="normal")
    if ok:
        _status.set("Licenca valida ✓ Abrindo o painel...")
        _fundo.after(1200, _fundo.destroy)
    else:
        _status.set(mensagem)


def _ativar():
    chave = _e_codigo.get().strip()
    ativacao = _e_ativacao.get().strip()
    if not chave:
        _status.set("Cola o CODIGO DE LICENCA primeiro.")
        _e_codigo.focus_set()
        return
    _botao.config(state="disabled")
    _status.set("Verificando contra o manifesto...")

    def tarefa():
        resposta = _posta(chave, ativacao)
        if isinstance(resposta, dict):
            if resposta.get("ok"):
                _fundo.after(0, _no_fim, True, "")
            else:
                motivo = (resposta.get("estado") or {}).get("motivo") \
                          or resposta.get("erro") or "licenca recusada."
                _fundo.after(0, _no_fim, False, "Nao ativou: " + motivo)
        else:
            _fundo.after(0, _no_fim, False, "Resposta estranha do servidor.")

    threading.Thread(target=tarefa, daemon=True).start()


_botao.config(command=_ativar)
_e_codigo.focus_set()
_fundo.bind("<Return>", lambda evento: _ativar())
_fundo.bind("<Escape>", lambda evento: _fundo.destroy())
_fundo.mainloop()
