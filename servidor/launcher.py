# -*- coding: utf-8 -*-
# language: Python 3.10+ (tkinter, stdlib), file: servidor/launcher.py
# O LANCADOR: uma janela unica que substitui todas as janelas pretas do
# 2-COMECAR. Ele libera os arquivos de um zip baixado, monta o jogo (rojo),
# sobe o servidor ESCONDIDO, decide a licenca (campo de ativacao proprio),
# pede o @ do TikTok, acende a ponte e abre o jogo no Studio. O antigo
# console de cada programa agora sao LINHAS dentro desta janela.
# Fechar esta janela desliga o servidor, a ponte e o rojo.
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(AQUI)
SERVIDOR = os.path.join(KIT, "servidor")
PONTE = os.path.join(KIT, "ponte")
JOGO = os.path.join(KIT, "JOGO-DA-LIVE.rbxlx")
PROJETO = os.path.join(KIT, "roblox")
MEMORIA = os.path.join(KIT, "config", "ultimo-usuario.txt")

URL = os.environ.get("SERVIDOR_URL", "http://127.0.0.1:8000")
PORTA_SERVIDOR = 8000
PORTA_ROJO = 34872
CNW = 0x08000000  # CREATE_NO_WINDOW: nenhuma janela preta de subprocesso

FUNDO = "#16161e"
CARTAO = "#22222e"
LOG_BG = "#0e0e16"
TEXTO = "#f0f0f5"
APAGADO = "#8a8a98"
OK = "#4caf6e"
ERRO = "#e0666e"
AZUL = "#5b7fd4"

CHAVE_ESCRITA = os.environ.get("CHAVE_ESCRITA", "escrita-local")

FLAG_PONTE = os.path.join(KIT, "config", "ponte-no-ar.flag")
_TRAVA_SERVIDOR = threading.Lock()


def memoria_usuario():
    """O @ guardado (config/ultimo-usuario.txt), ou ''. """
    if not os.path.isfile(MEMORIA):
        return ""
    try:
        with open(MEMORIA, encoding="utf-8") as f:
            return (f.read().splitlines() or [""])[0].strip()
    except Exception:
        return ""


def vigia():
    """Confere a si mesmo a cada 10s e ressuscita o que calou.

    O comprador (e o vendedor) matam processos no Task Manager, fecham
    janelas, clicam PARAR TUDO — o que for disso, o launcher cura sozinho:
    servidor sobe de novo, ponte acende de novo, e a live continua.
    Nao existe mais 'a sessao morreu e ninguem notou'.
    """
    while True:
        time.sleep(10)
        estado = puxa(URL + "/licenca", timeout=4)
        if not estado:
            if _TRAVA_SERVIDOR.locked():
                continue  # ja' esta' nascendo (o laco dele cuida)
            log("VIGIA: o servidor calou — subindo de novo...")
            threading.Thread(target=fase_servidor, daemon=True).start()
            continue
        if estado.get("ok") and not _licenca_ok.get():
            _licenca_ok.set(True)
            expira = ((estado.get("licenca") or {}).get("expira") or "?")
            log("Licenca: VALIDA (ate %s)." % expira, OK)
            j.after(0, _esconde_campos_lic)
            j.after(0, _habilita_botoes_base)
        if ponte_tem_dono_vivo():
            continue
        guardado = memoria_usuario()
        if guardado:
            log("VIGIA: a ponte calou — acendo de novo (@%s)..." % guardado)
            threading.Thread(target=_ponte_spawn, args=(guardado,),
                             daemon=True).start()


def ponte_tem_dono_vivo():
    """True se OUTRA janela ja' tem uma ponte acesa (PID no arquivo-flag).
    Clicou o bat duas vezes? A segunda janela ADOTA em vez de duplicar."""
    try:
        pid = int((open(FLAG_PONTE, encoding="utf-8").read() or "").strip() or 0)
    except Exception:
        return False
    if pid <= 0:
        return False
    vivo = False
    try:
        saida = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                               capture_output=True, timeout=15,
                               creationflags=CNW).stdout.decode("utf-8",
                                                                "replace")
        vivo = "python" in saida
    except Exception:
        vivo = False
    if not vivo:
        try:
            os.remove(FLAG_PONTE)
        except Exception:
            pass
    return vivo


def acha_rojo():
    """O rojo no pacote (ferramentas) ou no PATH. None se nenhum executar."""
    local = os.path.join(KIT, "ferramentas", "rojo.exe")
    candidatos = [local]
    no_path = shutil.which("rojo")
    if no_path:
        candidatos.append(no_path)
    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            try:
                r = subprocess.run([caminho, "--version"], capture_output=True,
                                   timeout=15, creationflags=CNW)
                if r.returncode == 0:
                    return caminho
            except Exception:
                pass
    return None


def acha_studio():
    """RobloxStudioBeta.exe em LOCALAPPDATA ou ProgramFiles(x86)."""
    lugares = [
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("ProgramFiles(x86)", ""),
    ]
    for raiz in lugares:
        if not raiz:
            continue
        for caminho in glob.glob(os.path.join(raiz, "Roblox", "Versions",
                                             "*", "RobloxStudioBeta.exe")):
            return caminho
    return None


def acha_edge():
    """msedge.exe: o modo --app abre o painel como JANELA PROPIA, sem abas."""
    nachei = shutil.which("msedge")
    if nachei:
        return nachei
    for raiz in [os.environ.get("ProgramFiles(x86)", ""),
                 os.environ.get("ProgramFiles", "")]:
        if raiz and os.path.isfile(os.path.join(
                raiz, "Microsoft", "Edge", "Application", "msedge.exe")):
            return os.path.join(raiz, "Microsoft", "Edge",
                                "Application", "msedge.exe")
    return None


def mata_porta(porta):
    """Mata quem estiver LISTENING na porta (dono antigo da sessao)."""
    try:
        saida = subprocess.run(["netstat", "-ano"], capture_output=True,
                               timeout=20, creationflags=CNW).stdout.decode(
                                   "utf-8", "replace").splitlines()
    except Exception:
        return
    for linha in saida:
        if f":{porta}" in linha and "LISTENING" in linha:
            pedacos = linha.split()
            if pedacos:
                try:
                    subprocess.run(["taskkill", "/PID", pedacos[-1], "/T", "/F"],
                                   capture_output=True, timeout=15,
                                   creationflags=CNW)
                except Exception:
                    pass


def puxa(url, timeout=5):
    """GET enxuto; devolve dict ou {}."""
    try:
        r = urllib.request.urlopen(url, timeout=timeout).read()
        return json.loads(r.decode("utf-8"))
    except Exception:
        return {}


# ------------------------------------------------------------------ GUI
j = tk.Tk()
j.title("YouPI-PG")
j.geometry("620x560")
j.resizable(False, False)
j.configure(bg=FUNDO)

_status = tk.StringVar(value="Preparando...")
_licenca_ok = tk.BooleanVar(value=False)

_fila = []
_fila_lock = threading.Lock()


def log(linha, cor=TEXTO):
    """Acrescenta uma linha no log da janela (thread-safe via fila)."""
    with _fila_lock:
        _fila.append((linha, cor))


def _drena_fila():
    with _fila_lock:
        itens = _fila[:]
        _fila.clear()
    for linha, cor in itens:
        _log_txt.config(state="normal")
        _log_txt.insert("end", linha + "\n")
        if cor != TEXTO:
            fim = _log_txt.index("end-1c")
            inicio = f"{fim.split('.')[0]}.0"
            _log_txt.tag_add(cor, inicio, fim)
            _log_txt.tag_config(cor, foreground=cor)
        _log_txt.see("end")
        _log_txt.config(state="disabled")
    j.after(200, _drena_fila)


tk.Label(j, text="YouPI-PG", font=("Segoe UI", 20, "bold"),
         bg=FUNDO, fg=TEXTO).pack(pady=(12, 0))
tk.Label(j, text="uma janela so -- sem janelas pretas",
         font=("Segoe UI", 9), bg=FUNDO, fg=APAGADO).pack(pady=(0, 8))

_quadro_log = tk.Frame(j, bg=CARTAO)
_quadro_log.pack(padx=16, fill="both")
_sb = tk.Scrollbar(_quadro_log)
_sb.pack(side="right", fill="y")
_log_txt = tk.Text(_quadro_log, height=11, font=("Consolas", 9),
                   bg=LOG_BG, fg=TEXTO, relief="flat", state="disabled",
                   yscrollcommand=_sb.set, wrap="word")
_log_txt.pack(side="left", fill="both", expand=True)
_sb.config(command=_log_txt.yview)

tk.Label(j, textvariable=_status, font=("Segoe UI", 10, "bold"),
         bg=FUNDO, fg=OK, wraplength=580, justify="center").pack(pady=(8, 0))

_cartao_licenca = tk.Frame(j, bg=CARTAO, padx=14, pady=10)
_cartao_licenca.pack(padx=16, fill="x", pady=(8, 0))

_titulo_lic = tk.Label(_cartao_licenca, text="LICENCA",
                       font=("Segoe UI", 9, "bold"), bg=CARTAO, fg=APAGADO)
_titulo_lic.pack(anchor="w")

_campos_lic = tk.Frame(_cartao_licenca, bg=CARTAO)
_campos_lic.pack(fill="x")

_l1 = tk.Label(_campos_lic, text="codigo", font=("Segoe UI", 9),
               bg=CARTAO, fg=APAGADO)
_l1.grid(row=0, column=0, sticky="w")
_e_codigo = tk.Entry(_campos_lic, font=("Consolas", 10), width=24,
                     bg=LOG_BG, fg=TEXTO, insertbackground=TEXTO,
                     relief="flat")
_e_codigo.grid(row=1, column=0, sticky="we", ipady=3, padx=(0, 8))

_l2 = tk.Label(_campos_lic, text="ativacao", font=("Segoe UI", 9),
               bg=CARTAO, fg=APAGADO)
_l2.grid(row=0, column=1, sticky="w")
_e_ativacao = tk.Entry(_campos_lic, font=("Consolas", 10), width=18,
                       bg=LOG_BG, fg=TEXTO, insertbackground=TEXTO,
                       relief="flat")
_e_ativacao.grid(row=1, column=1, sticky="we", ipady=3, padx=(0, 8))

_btn_lic = tk.Button(_campos_lic, text="ATIVAR LICENCA",
                     font=("Segoe UI", 9, "bold"), bg=AZUL, fg="white",
                     activebackground="#6b90e0", activeforeground="white",
                     relief="flat", cursor="hand2", state="disabled")
_btn_lic.grid(row=1, column=2, ipadx=6, ipady=3)

_campos_lic.columnconfigure(0, weight=1)

_cartao_licenca_col = tk.Frame(j, bg=FUNDO)
_cartao_licenca_col.pack(fill="x")

_cartao_usuario = tk.Frame(j, bg=CARTAO, padx=14, pady=10)
_cartao_usuario.pack(padx=16, fill="x", pady=(8, 0))

_titulo_user = tk.Label(_cartao_usuario, text="@ DO TIKTOK",
                        font=("Segoe UI", 9, "bold"), bg=CARTAO, fg=APAGADO)
_titulo_user.pack(anchor="w")

_linha_user = tk.Frame(_cartao_usuario, bg=CARTAO)
_linha_user.pack(fill="x")
_e_usuario = tk.Entry(_linha_user, font=("Consolas", 10), width=24,
                      bg=LOG_BG, fg=TEXTO, insertbackground=TEXTO,
                      relief="flat")
_e_usuario.pack(side="left", ipady=3, padx=(0, 8))
_btn_usuario = tk.Button(_linha_user, text="ENTRAR NA LIVE",
                         font=("Segoe UI", 9, "bold"), bg="#2e7d32", fg="white",
                         activebackground="#3d9d43", activeforeground="white",
                         relief="flat", cursor="hand2", state="disabled")
_btn_usuario.pack(side="left", ipadx=6, ipady=3)

_audios = tk.Frame(j, bg=FUNDO)
_audios.pack(padx=16, fill="x", pady=(8, 0))
_btn_jogo = tk.Button(_audios, text="ABRIR JOGO NO STUDIO",
                      font=("Segoe UI", 9, "bold"), bg=AZUL, fg="white",
                      activebackground="#6b90e0", activeforeground="white",
                      relief="flat", cursor="hand2", state="disabled")
_btn_jogo.pack(side="left", ipadx=8, ipady=4, padx=(0, 6))
_btn_painel = tk.Button(_audios, text="PAINEL",
                        font=("Segoe UI", 9, "bold"), bg=AZUL, fg="white",
                        activebackground="#6b90e0", activeforeground="white",
                        relief="flat", cursor="hand2", state="disabled")
_btn_painel.pack(side="left", ipadx=8, ipady=4, padx=(0, 6))
_btn_parar = tk.Button(_audios, text="PARAR TUDO",
                       font=("Segoe UI", 9, "bold"), bg="#8d3a3a", fg="white",
                       activebackground="#a84848", activeforeground="white",
                       relief="flat", cursor="hand2", state="disabled")
_btn_parar.pack(side="left", ipadx=8, ipady=4)

tk.Label(j, text="senha do painel: escrita-local (tecla uma vez; e' "
                "interna, o comprador nunca recebe senha de fachada)",
         font=("Segoe UI", 8), bg=FUNDO, fg=APAGADO).pack(pady=(6, 0))

tk.Label(j, text="OBS: as URLs do placar ficam no log acima "
                "(fonte de navegador do OBS)",
         font=("Segoe UI", 8), bg=FUNDO, fg=APAGADO).pack(pady=(2, 8))

# ------------------------------------------------------------ processos
_processos = []


def _termina_processos():
    for p in list(_processos):
        try:
            p.terminate()
        except Exception:
            pass
    _processos.clear()
    try:
        os.remove(FLAG_PONTE)
    except Exception:
        pass
    mata_porta(PORTA_SERVIDOR)
    mata_porta(PORTA_ROJO)
    try:
        subprocess.run(["taskkill", "/IM", "rojo.exe", "/F"],
                       capture_output=True, timeout=15, creationflags=CNW)
    except Exception:
        pass


def _ao_fechar():
    """Fechar a janela NAO desliga nada: a sessao vive (o PARAR TUDO
    e quem mata). Quem vem de fechar janelas pretas fecha por habito --
    e a sessao morria junto."""
    j.destroy()


j.protocol("WM_DELETE_WINDOW", _ao_fechar)


def licenca_do_local():
    """A chave gravada (config/licenca.json), ou ('','')."""
    try:
        with open(os.path.join(KIT, "config", "licenca.json"),
                  encoding="utf-8-sig") as f:
            d = json.load(f)
        return (d.get("chave") or "").strip(), (d.get("ativacao") or "").strip()
    except Exception:
        return "", ""


def posta_licenca(chave, ativacao):
    """POST /licenca/chave com 3 tentativas (a mesma voz do ativador)."""
    corpo = json.dumps({"chave": chave, "ativacao": ativacao}).encode("utf-8")
    ultimo = ""
    for _ in range(3):
        try:
            pedido = urllib.request.Request(
                URL + "/licenca/chave", data=corpo,
                headers={"Content-Type": "application/json"}, method="POST")
            return json.loads(urllib.request.urlopen(pedido, timeout=12).read()
                              .decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                return json.loads(erro.read().decode("utf-8"))
            except Exception:
                ultimo = "o servidor respondeu " + str(erro.code)
        except Exception as erro:
            ultimo = "sem resposta: " + str(erro)
            time.sleep(1.2)
    return {"ok": False, "erro": ultimo or "sem resposta do servidor."}


# ---------------------------------------------------------------- fases
def fase_liberar():
    """Zip baixado: files 'bloqueados'. LBRLFa uma vez."""
    marco = os.path.join(KIT, ".liberado")
    if os.path.isfile(marco):
        return
    log("Liberando os arquivos do download (so na primeira vez)...")
    env = dict(os.environ)
    env["LIB_PASTA"] = KIT
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command",
             "Get-ChildItem -LiteralPath $env:LIB_PASTA -Recurse -Force "
             "-File -ErrorAction SilentlyContinue | Unblock-File"],
            env=env, timeout=120, creationflags=CNW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    try:
        with open(marco, "w") as f:
            f.write("liberado\n")
    except Exception:
        pass


def fase_limpar():
    """Nao mata um servidor NOSSO que ja responde — e' o que a sessao
    anterior deixou no ar, e vai ser ADOTADO. Rojo velho de edicao, sai."""
    log("Verificando sobras de sessoes anteriores...")
    try:
        subprocess.run(["taskkill", "/IM", "rojo.exe", "/F"],
                       capture_output=True, timeout=15, creationflags=CNW)
    except Exception:
        pass
    mata_porta(PORTA_ROJO)
    if puxa(URL + "/licenca", timeout=4):
        log("O servidor da sessao anterior segue no ar — ADOTADO.", OK)
        return False
    mata_porta(PORTA_SERVIDOR)
    return True


def fase_montar():
    rojo = acha_rojo()
    if not rojo:
        if os.path.isfile(JOGO):
            log("Rojo ausente, mas o JOGO-DA-LIVE.rbxlx ja existe "
                "— segue com ele.", ERRO)
            return True
        log("Rojo nao encontrado e sem JOGO-DA-LIVE.rbxlx. "
            "Rode o 1-INSTALACAO.bat.", ERRO)
        return False
    log("Montando o jogo (rojo build)...")
    try:
        r = subprocess.run([rojo, "build", PROJETO, "--output", JOGO],
                           capture_output=True, timeout=240,
                           creationflags=CNW)
        if r.returncode != 0 and not os.path.isfile(JOGO):
            log("O rojo nao conseguiu montar o jogo "
                "(detalhes no log do launcher).", ERRO)
            return False
        if r.returncode != 0:
            log("O rojo falhou, mas segue o JOGO-DA-LIVE.rbxlx ANTERIOR "
                "(sem as suas ultimas mudancas).", ERRO)
        else:
            log("Pronto: JOGO-DA-LIVE.rbxlx", OK)
        return True
    except Exception as erro:
        log("Falha montando: %s" % erro, ERRO)
        return False


def fase_servidor():
    if puxa(URL + "/licenca", timeout=4):
        log("Servidor no ar (o vivo da sessao anterior — adotado).", OK)
        return True
    if not _TRAVA_SERVIDOR.acquire(blocking=False):
        log("Um servidor ja' esta' nascendo — espero por ele.")
        return True
    try:
        log("Subindo o servidor escondido...")
        caminho_log = os.path.join(SERVIDOR, "servidor-ultimo.log")
        try:
            arq = open(caminho_log, "w", encoding="utf-8")
            processo = subprocess.Popen(
                [sys.executable, "servidor.py"],
                cwd=SERVIDOR, stdout=arq, stderr=subprocess.STDOUT,
                creationflags=CNW, env=dict(os.environ))
            _processos.append(processo)
        except Exception as erro:
            log("O servidor nao nasceu: %s" % erro, ERRO)
            return False
        for _ in range(20):
            time.sleep(1)
            if puxa(URL + "/licenca"):
                log("Servidor no ar (porta %d)." % PORTA_SERVIDOR, OK)
                log("  log do servidor: servidor\\servidor-ultimo.log")
                return True
        log("O servidor nao respondeu em 20s. Veja "
            "servidor\\servidor-ultimo.log.", ERRO)
        return False
    finally:
        _TRAVA_SERVIDOR.release()


def fase_licenca():
    chave, ativacao = licenca_do_local()
    estado = puxa(URL + "/licenca")
    if estado.get("ok"):
        _licenca_ok.set(True)
        log("Licenca: VALIDA (ate %s)."
            % (estado.get("ate") or "?"), OK)
        j.after(0, _esconde_campos_lic)
        return True
    if chave:
        # A chave esta aqui, mas o manifesto recusou: mostrar o motivo.
        log("Licenca recusada: %s"
            % (estado.get("motivo") or "motivo desconhecido"), ERRO)
        log("Cola os codigos de novo pra conferir (ou fala com o "
            "vendedor).", ERRO)
    j.after(0, _mostra_campos_lic)
    return False


def _mostra_campos_lic():
    _e_codigo.config(state="normal")
    _e_ativacao.config(state="normal")
    _btn_lic.config(state="normal")


def _esconde_campos_lic():
    _e_codigo.delete(0, "end")
    _e_ativacao.delete(0, "end")
    _e_codigo.config(state="disabled")
    _e_ativacao.config(state="disabled")
    _btn_lic.config(state="disabled")


def piscou_para_todos():
    """Estado final da janela depois das fases automaticas."""
    j.after(0, _habilita_botoes_base)
    log("URLs pro OBS (fonte de navegador):")
    log("  %s/placar.html?tipo=moedas" % "http://localhost:8000")
    log("  %s/placar.html?tipo=curtidas" % "http://localhost:8000")
    log("  %s/placar.html?tipo=presenca" % "http://localhost:8000")
    guardado = ""
    if os.path.isfile(MEMORIA):
        try:
            with open(MEMORIA, encoding="utf-8") as f:
                guardado = (f.read().splitlines() or [""])[0].strip()
        except Exception:
            pass
    if guardado:
        log("Ponte: acendendo sozinha com o @ guardado (@%s)..." % guardado)
        threading.Thread(target=_ponte_spawn, args=(guardado,),
                         daemon=True).start()
    else:
        log("Escreve o teu @ do TikTok e aperta ENTRAR NA LIVE.")


def roda_fases():
    fase_liberar()
    fase_limpar()
    if not fase_montar():
        j.after(0, lambda: _status.set("O jogo nao montou. Leia as linhas "
                                       "acima."))
        return
    if not fase_servidor():
        j.after(0, lambda: _status.set("O servidor nao subiu. Leia as "
                                       "linhas acima."))
        return
    fase_licenca()
    j.after(0, piscou_para_todos)


# ------------------------------------------------------------- botoes
def _habilita_botoes_base():
    _btn_jogo.config(state="normal")
    _btn_painel.config(state="normal")
    _btn_parar.config(state="normal")
    if _licenca_ok.get():
        _btn_usuario.config(state="normal")
        _status.set("Servidor no ar — licenca valida")
    else:
        # A live funciona sem licenca: e' o degradar silencioso do projeto.
        _btn_usuario.config(state="normal")
        _status.set("Servidor no ar — sem licenca (subindo mesmo assim)")


def clicou_licenca():
    chave = _e_codigo.get().strip()
    ativacao = _e_ativacao.get().strip()
    if not chave:
        log("Cola o codigo da licenca.", ERRO)
        return
    _btn_lic.config(state="disabled")
    log("Verificando os codigos contra o manifesto...")

    def tarefa():
        resposta = posta_licenca(chave, ativacao)
        if resposta.get("ok"):
            _licenca_ok.set(True)
            log("Licenca valida ✓", OK)
            j.after(0, _esconde_campos_lic)
            j.after(0, _habilita_botoes_base)
        else:
            motivo = (resposta.get("erro")
                      or (resposta.get("estado") or {}).get("motivo")
                      or "licenca recusada.")
            log("Nao ativou: %s" % motivo, ERRO)
            j.after(0, lambda: _btn_lic.config(state="normal"))

    threading.Thread(target=tarefa, daemon=True).start()


_btn_lic.config(command=clicou_licenca)
_e_codigo.bind("<Return>", lambda e: clicou_licenca())


def _ponte_spawn(usuario):
    """Acende a ponte escondida. Thread target: botao e o automatico."""
    if ponte_tem_dono_vivo():
        log("A ponte ja' esta no ar (outra janela acendeu) — adotada.", OK)
        return
    caminho_log = os.path.join(PONTE, "ponte-ultimo.log")
    env = dict(os.environ)
    env["SERVIDOR_URL"] = URL
    env["CHAVE_ESCRITA"] = CHAVE_ESCRITA
    env["DONOS"] = os.environ.get("DONOS_EXTRA", "")
    try:
        arq = open(caminho_log, "w", encoding="utf-8")
        processo = subprocess.Popen(
            [sys.executable, "ponte.py", "--usuario", "@" + usuario],
            cwd=PONTE, stdout=arq, stderr=subprocess.STDOUT,
            creationflags=CNW, env=env)
        _processos.append(processo)
        try:
            os.makedirs(os.path.dirname(FLAG_PONTE), exist_ok=True)
            with open(FLAG_PONTE, "w", encoding="utf-8") as f:
                f.write(str(processo.pid))
        except Exception:
            pass
    except Exception as erro:
        log("A ponte nao nasceu: %s" % erro, ERRO)
        j.after(0, lambda: _btn_usuario.config(state="normal"))
        return
    time.sleep(3)
    if processo.poll() is None:
        log("Ponte no ar (log: ponte\\ponte-ultimo.log).", OK)
    else:
        log("A ponte morreu logo. Veja ponte\\ponte-ultimo.log.", ERRO)
        try:
            os.remove(FLAG_PONTE)
        except Exception:
            pass
        j.after(0, lambda: _btn_usuario.config(state="normal"))


def clicou_usuario():
    usuario = _e_usuario.get().strip().strip("@")
    if not usuario:
        log("Escreve o teu @ do TikTok primeiro.", ERRO)
        return
    try:
        os.makedirs(os.path.dirname(MEMORIA), exist_ok=True)
        with open(MEMORIA, "w", encoding="utf-8") as f:
            f.write(usuario + "\n")
    except Exception:
        pass
    _btn_usuario.config(state="disabled")
    log("Acendendo a ponte do TikTok (@%s)..." % usuario)
    threading.Thread(target=_ponte_spawn, args=(usuario,),
                     daemon=True).start()


_btn_usuario.config(command=clicou_usuario)


def clicou_jogo():
    _btn_jogo.config(state="disabled")
    if not os.path.isfile(JOGO):
        log("Nao achei o JOGO-DA-LIVE.rbxlx. Rode o 1-INSTALACAO.bat.", ERRO)
        _btn_jogo.config(state="normal")
        return
    studio = acha_studio()
    if not studio:
        log("Roblox Studio nao encontrado. Instala em "
            "create.roblox.com; a live usa o Studio.", ERRO)
        _btn_jogo.config(state="normal")
        return
    # Ja' aberto? Duas copias de Studio brigam e o Play vai no lugar errado.
    try:
        achou = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq RobloxStudioBeta.exe"],
            capture_output=True, timeout=15, creationflags=CNW).stdout.decode(
                "utf-8", "replace")
        if "RobloxStudioBeta.exe" in achou:
            log("O Studio JA esta aberto. Fecha ele INTEIRO e clica "
                "em ABRIR JOGO de novo — o Studio carrega o codigo "
                "uma vez so, na hora de abrir o arquivo.", ERRO)
            _btn_jogo.config(state="normal")
            return
    except Exception:
        pass
    log("Abrindo o jogo no Roblox Studio (10 a 40 segundos)...")
    subprocess.Popen([studio, JOGO], creationflags=CNW)
    log("Quando o Studio abrir: aperte PLAY (triangulo azul).", OK)
    _btn_jogo.config(state="normal")


_btn_jogo.config(command=clicou_jogo)


def clicou_painel():
    """Painel como JANELA PROPIA (modo --app do Edge): sem abas, sem barra."""
    endereco = "http://localhost:8000/painel"
    edge = acha_edge()
    if edge:
        subprocess.Popen([edge, "--app=" + endereco], creationflags=CNW)
        log("Painel aberto como janela propria.", OK)
    else:
        os.startfile(endereco)
        log("Painel aberto no navegador (Edge nao encontrado).")


_btn_painel.config(command=clicou_painel)


def clicou_parar():
    log("Parando tudo (servidor, ponte, rojo)...")
    _termina_processos()
    _btn_usuario.config(state="disabled")
    _status.set("Tudo parado.")


_btn_parar.config(command=clicou_parar)


# ---------------------------------------------------------------- arranque
if os.path.isfile(MEMORIA):
    try:
        with open(MEMORIA, encoding="utf-8") as f:
            guardado = (f.read().splitlines() or [""])[0].strip()
        if guardado:
            _e_usuario.insert(0, guardado)
    except Exception:
        pass

log("YouPI-PG — a tua live inteira nesta janela.")
_thread = threading.Thread(target=roda_fases, daemon=True)
_thread.start()
_screen = threading.Thread(target=vigia, daemon=True)
_screen.start()
_drena_fila()
j.mainloop()
