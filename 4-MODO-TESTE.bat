@echo off
setlocal
title Modo teste - Live Interativa Monster
color 0E

rem --- desbloqueio dos arquivos (gerado pelo empacotador) ---
rem Arquivo vindo de .zip BAIXADO nasce marcado pelo Windows. Enquanto a
rem marca estiver la, .bat pede confirmacao e .exe sem assinatura pode ser
rem segurado pelo SmartScreen. E a diferenca entre esta pasta e uma copia
rem feita na mao. Tirar a marca uma vez resolve a pasta inteira.
if not exist "%~dp0.liberado" (
    echo   Liberando os arquivos do download... ^(so na primeira vez^)
    set "LIB_PASTA=%~dp0"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath $env:LIB_PASTA -Recurse -Force -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1
    echo liberado> "%~dp0.liberado"
)
rem --- fim do desbloqueio dos arquivos ---


rem ============================================================
rem  MODO TESTE -- sem live, sem TikTok, sem espectador.
rem
rem  Inventa comentarios e presentes pra voce ver o jogo
rem  funcionando e configurar o painel do seu jeito ANTES da
rem  primeira live de verdade.
rem
rem  Configurar no ar, com gente assistindo, e' o caminho mais
rem  rapido pra uma live ruim.
rem
rem  NAO LIGUE `enabledelayedexpansion` AQUI. Com ela o cmd come o
rem  "!" de dentro de tudo que expande -- inclusive do %~dp0. Numa
rem  pasta chamada "LIVE!" o caminho chegava mutilado nos
rem  `if exist`, e o kit acusava "KIT INCOMPLETO" com os arquivos
rem  todos no lugar. Nada aqui precisa dela: os lacos abaixo sao
rem  de `goto`, e `goto` rele' a linha a cada volta.
rem ============================================================

set "CHAVE_ESCRITA=escrita-local"
set "CHAVE_LEITURA=leitura-local"
set "SERVIDOR_URL=http://127.0.0.1:8000"

echo.
echo   ============================================================
echo    MODO TESTE
echo   ============================================================
echo.
echo    Nada aqui vem do TikTok. Sao eventos inventados, pra voce
echo    ver o jogo rodando e mexer no painel a vontade.
echo.

rem ---------- o kit chegou inteiro? ----------
rem
rem A mesma conferencia do INSTALAR e do INICIAR-LIVE, e ela precisa estar nos TRES.
rem Sem ela, uma pasta faltando so' aparece la' embaixo como "o sistema nao
rem pode encontrar o caminho especificado", numa janela que fecha antes de dar
rem pra ler.

set "FALTA="
if not exist "%~dp0servidor\servidor.py" set "FALTA=%FALTA% servidor\servidor.py"
if not exist "%~dp0servidor\web\painel.html" set "FALTA=%FALTA% servidor\web\painel.html"
if not exist "%~dp0ponte\ponte.py" set "FALTA=%FALTA% ponte\ponte.py"
if not exist "%~dp0roblox\default.project.json" set "FALTA=%FALTA% roblox\default.project.json"

if defined FALTA (
    call :kit_incompleto
    exit /b 1
)

rem ---------- achar o Python ----------

set "PY="
set "PY_ANTIGO="
for %%C in (py python python3) do if not defined PY call :testar_python "%%C"

if not defined PY (
    call :sem_python
    exit /b 1
)

echo   Limpando processos de sessoes anteriores...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8000"') do taskkill /PID %%p /T /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":34872"') do taskkill /PID %%p /T /F >nul 2>&1

rem As janelas pretas que sobraram, e nao so' os programas dentro delas -- senao
rem elas se acumulam a cada partida e voce nao acha mais qual e' a desta sessao.
rem
rem O /T faltava, e a falta tinha consequencia: sem ele o taskkill mata o
rem cmd.exe da janela e deixa VIVO o programa de dentro. Era assim que sobrava
rem um rojo.exe orfao, sem janela na tela, ainda segurando a porta 34872.
taskkill /FI "WINDOWTITLE eq 0 - Rojo*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 1 - SERVIDOR DA LIVE*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 2 - PONTE*" /T /F >nul 2>&1
taskkill /IM rojo.exe /F >nul 2>&1

if not exist "%~dp0ferramentas\rojo.exe" (
    echo   AVISO: o Rojo nao esta' instalado ^(rode o 1-INSTALACAO.bat^).
)

rem O jogo e o Rojo sao montados pelo 3-ABRIR-JOGO.bat, chamado la' embaixo --
rem num lugar so'. Antes eles subiam AQUI tambem, e o ABRIR-JOGO matava este
rem Rojo pra subir o dele: dois servidores na mesma porta, um derrubando o
rem outro com o Studio abrindo no meio. Quem clicasse Connect na hora errada
rem pegava o que estava morrendo, e o erro ("connection lost") nao apontava
rem pra causa nenhuma.

start "1 - SERVIDOR DA LIVE" /D "%~dp0servidor" cmd /k "chcp 65001 >nul && set CHAVE_ESCRITA=%CHAVE_ESCRITA%&& set CHAVE_LEITURA=%CHAVE_LEITURA%&& "%PY%" servidor.py"

rem Espera o servidor ATENDER, em vez de chutar 3 segundos. Sem isto, quando ele
rem nao subia a simulacao abria tudo mesmo assim -- navegador numa pagina morta,
rem ponte acumulando erro numa janela que ninguem olhava -- e nada dizia qual
rem das tres janelas era o problema.
echo   Esperando o servidor subir...
set "TENTATIVAS=0"

:esperar_servidor
netstat -ano | findstr "LISTENING" | findstr "127.0.0.1:8000" >nul 2>&1
if not errorlevel 1 goto servidor_no_ar
set /a TENTATIVAS+=1
if %TENTATIVAS% geq 20 goto servidor_mudo
timeout /t 1 /nobreak >nul
goto esperar_servidor

:servidor_mudo
echo.
echo   ============================================================
echo    O SERVIDOR DA LIVE NAO SUBIU
echo   ============================================================
echo.
echo    Esperei 20 segundos e a porta 8000 nao respondeu. A resposta
echo    esta' na janela "1 - SERVIDOR DA LIVE", que abriu junto com
echo    esta: e' ela que diz o que aconteceu.
echo.
echo    O mais comum e' outra sessao da live ainda aberta segurando a
echo    porta. Feche todas as janelas pretas e tente de novo.
echo.
pause
exit /b 1

:servidor_no_ar
echo   Servidor no ar.

start "" "http://localhost:8000/painel"

start "2 - PONTE (simulacao)" /D "%~dp0ponte" cmd /k "chcp 65001 >nul && set SERVIDOR_URL=%SERVIDOR_URL%&& set CHAVE_ESCRITA=%CHAVE_ESCRITA%&& "%PY%" ponte.py --simular"

echo.
echo   ============================================================
echo    ABRINDO O JOGO
echo   ============================================================
echo.
echo    Se ja' tiver outro lugar aberto no Studio, FECHE ele:
echo    um lugar com outro codigo dentro briga com este.
echo.
timeout /t 3 /nobreak >nul
call "%~dp03-ABRIR-JOGO.bat"
echo    Quando o Studio abrir, aperte PLAY.
echo    Em poucos segundos os bonecos comecam a aparecer sozinhos.
echo.
echo    O painel ja' abriu no navegador: mexa nos numeros, salve, e
echo    veja a mudanca acontecer no jogo em ate' 5 segundos.
echo.
pause
exit /b 0


rem ============================================================
rem  SUB-ROTINAS
rem ============================================================

:kit_incompleto
rem Distingue os DOIS casos, porque a solucao de um nao resolve o outro.
set "ONDE=%~dp0"
set "NO_TEMP="
if not "%ONDE%"=="%ONDE:\AppData\Local\Temp\=%" set "NO_TEMP=1"
if not "%ONDE%"=="%ONDE:Rar$=%" set "NO_TEMP=1"
if not "%ONDE%"=="%ONDE:\7z=%" set "NO_TEMP=1"

echo   ============================================================
echo    O KIT ESTA INCOMPLETO
echo   ============================================================
echo.
echo    Nao encontrei:%FALTA%
echo.
if defined NO_TEMP (
    echo    JA' SEI O QUE ACONTECEU. Voce deu dois cliques neste arquivo
    echo    DE DENTRO do ZIP, sem extrair antes.
    echo.
    echo    O Windows deixa voce abrir o ZIP e ver os arquivos, mas quando
    echo    voce clica num deles ele copia SO' AQUELE arquivo pra uma pasta
    echo    temporaria e roda de la'. O resto do kit fica dentro do ZIP.
    echo.
    echo    COMO RESOLVER:
    echo.
    echo      1^) Feche esta janela
    echo      2^) Clique com o BOTAO DIREITO no arquivo .zip
    echo      3^) Escolha "Extrair Tudo..." e confirme
    echo      4^) Abra a pasta que apareceu e rode o 4-MODO-TESTE.bat de la'
    echo.
    echo    A pasta certa e' a que tem o 4-MODO-TESTE.bat E as pastas
    echo    "servidor", "ponte" e "roblox" juntos.
) else (
    echo    Faltam arquivos nesta pasta:
    echo      %~dp0
    echo.
    echo    Duas causas possiveis:
    echo.
    echo      1^) O ZIP foi extraido pela metade. Extraia de novo, inteiro.
    echo.
    echo      2^) O antivirus apagou algum arquivo. Se foi isso, ele avisou
    echo         em alguma notificacao. Restaure a partir da quarentena, ou
    echo         extraia o ZIP de novo numa pasta fora do Desktop.
)
echo.
pause
exit /b 1


:sem_python
echo.
echo   ============================================================
echo    O PYTHON NAO FOI ENCONTRADO
echo   ============================================================
echo.
if defined PY_ANTIGO (
    echo    Achei um Python instalado, mas ele e' antigo demais pro kit
    echo    ^(%PY_ANTIGO%^). O kit precisa do Python 3.10 ou mais novo.
    echo.
    echo    Rode o 1-INSTALACAO.bat: ele instala uma versao nova do lado,
    echo    sem mexer na que ja' esta' ai'.
) else (
    echo    Rode o 1-INSTALACAO.bat primeiro -- ele baixa e instala o
    echo    Python pra voce.
    echo.
    echo    Se ja' rodou: FECHE esta janela e abra de novo. O Windows
    echo    so' enxerga programas recem-instalados em janelas abertas
    echo    DEPOIS da instalacao.
)
echo.
pause
exit /b 1


:testar_python
rem Recebe um comando (py, python, python3) e SO' aceita se ele for um Python
rem de verdade e novo o bastante. Igual ao do 1-INSTALACAO.bat -- se mexer num,
rem mexa nos dois.
rem
rem POR QUE NAO BASTA `--version`: o Windows 10/11 tem um ATALHO FALSO chamado
rem python.exe dentro de WindowsApps, que so' abre a Microsoft Store. Em algumas
rem versoes do Windows ele responde com codigo de saida ZERO, e ai' o kit o
rem aceitava como Python valido -- a Store abria sozinha e nada funcionava.
rem Aqui a gente manda ele EXECUTAR codigo: o atalho falso nao executa nada.
rem
rem O piso de 3.10 tambem nao e' opcional: a TikTokLive 6.6.6 declara
rem "Requires-Python: >=3.10", e a ponte usa asyncio.to_thread (3.9). Sem esta
rem barreira o kit subia inteiro e quebrava na primeira live, com um erro que
rem nao fala de versao do Python em lugar nenhum.
set "VNUM="
"%~1" -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" > "%TEMP%\kit-pyver.txt" 2>nul
if errorlevel 1 goto :testar_python_fim
rem `for /f` e nao `set /p`: o print do Python termina em CRLF, e o `set /p`
rem deixa o CR pendurado no valor em algumas versoes do Windows -- um CR
rem invisivel reprovaria a conferencia de digitos logo abaixo.
for /f "usebackq delims=" %%v in ("%TEMP%\kit-pyver.txt") do set "VNUM=%%v"
if not defined VNUM goto :testar_python_fim

rem Se sobrou qualquer coisa que nao seja digito, nao foi o nosso print que
rem respondeu -- descarta em vez de comparar e explodir com erro de sintaxe.
for /f "delims=0123456789" %%x in ("%VNUM%") do set "VNUM="
if not defined VNUM goto :testar_python_fim

if %VNUM% LSS 310 (
    set "PY_ANTIGO=%~1"
    goto :testar_python_fim
)
set "PY=%~1"

:testar_python_fim
del "%TEMP%\kit-pyver.txt" >nul 2>&1
exit /b 0
