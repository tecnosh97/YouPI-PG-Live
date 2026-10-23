@echo off
setlocal
title Verificacao - Live Interativa Monster
color 0B

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
rem  VERIFICADOR
rem
rem  Confere UMA POR UMA as pecas que a live precisa e diz, de
rem  cada uma, se esta' pronta -- e o que fazer quando nao esta'.
rem
rem  POR QUE ELE EXISTE
rem
rem  Quando a live nao funciona, o sintoma e' quase sempre o
rem  mesmo: "apertei Play e nao acontece nada". Esse sintoma tem
rem  pelo menos oito causas diferentes (Python faltando, pip que
rem  instalou no Python errado, rojo bloqueado pelo antivirus,
rem  plugin do Rojo ausente, porta ocupada por sessao anterior,
rem  HttpService desligado, cenario apagado, @ digitado errado) e
rem  cada uma tem uma solucao que nao serve pras outras.
rem
rem  Sem este arquivo, descobrir QUAL das oito e' um trabalho de
rem  tentativa e erro no meio da transmissao. Aqui ele e' uma
rem  lista com um X do lado da que esta' errada.
rem
rem  NAO USE `setlocal enabledelayedexpansion` NESTE ARQUIVO.
rem  Com ela ligada o cmd come o "!" de dentro de tudo que
rem  expande -- inclusive do %~dp0. Numa pasta chamada "LIVE!" o
rem  caminho chega mutilado nos `if exist` e a verificacao acusa
rem  arquivos faltando com todos eles no lugar.
rem ============================================================

set "PROBLEMAS=0"
set "AVISOS=0"

echo.
echo   ============================================================
echo    VERIFICACAO DA LIVE INTERATIVA - Monster
echo   ============================================================
echo.
echo    Conferindo tudo que a live precisa. Leva uns 20 segundos.
echo.

rem ============================================================
rem  1. OS ARQUIVOS DO KIT
rem ============================================================

echo   [1] Arquivos do kit
set "FALTA="
if not exist "%~dp0servidor\servidor.py" set "FALTA=%FALTA% servidor\servidor.py"
if not exist "%~dp0servidor\web\painel.html" set "FALTA=%FALTA% servidor\web\painel.html"
if not exist "%~dp0ponte\ponte.py" set "FALTA=%FALTA% ponte\ponte.py"
if not exist "%~dp0ponte\regras.py" set "FALTA=%FALTA% ponte\regras.py"
if not exist "%~dp0roblox\default.project.json" set "FALTA=%FALTA% roblox\default.project.json"
if not exist "%~dp0roblox\src\Workspace\Cenario.model.json" set "FALTA=%FALTA% roblox\src\Workspace\Cenario.model.json"

if defined FALTA (
    echo       [X] FALTANDO:%FALTA%
    echo           O ZIP foi extraido pela metade, ou o antivirus apagou
    echo           alguma coisa. Extraia o ZIP de novo, inteiro.
    set /a PROBLEMAS+=1
) else (
    echo       [OK] todos os arquivos no lugar
)

rem ============================================================
rem  2. O PYTHON
rem ============================================================

echo.
echo   [2] Python
set "PY="
set "PY_ANTIGO="
for %%C in (py python python3) do if not defined PY call :testar_python "%%C"

if not defined PY (
    if defined PY_ANTIGO (
        echo       [X] o Python instalado e' ANTIGO demais ^(%PY_ANTIGO%^)
        echo           O kit precisa do 3.10 ou mais novo. Rode o 1-INSTALACAO.bat:
        echo           ele instala uma versao nova do lado, sem mexer na atual.
    ) else (
        echo       [X] Python nao encontrado
        echo           Rode o 1-INSTALACAO.bat. Se ja' rodou, FECHE esta janela e
        echo           abra de novo -- o Windows so' mostra programa novo pras
        echo           janelas abertas DEPOIS da instalacao.
    )
    set /a PROBLEMAS+=1
    goto depois_do_python
)

rem A saida do Python vai pra um ARQUIVO e e' lida de la', em vez de capturada
rem direto no `for /f`. Nao e' rodeio: com o %PY% podendo ser um caminho
rem completo entre aspas, o `for /f ('...')` precisa de tres niveis de aspas e
rem falha CALADO -- a variavel sai vazia e o kit imprime "Python " sem versao
rem nenhuma, que foi exatamente o que aconteceu na primeira versao deste
rem arquivo. E' o mesmo padrao do :testar_python aqui embaixo.
set "VERPY="
set "ONDEPY="
"%PY%" -c "import sys;print(sys.version.split()[0]);print(sys.executable)" > "%TEMP%\kit-pyinfo.txt" 2>nul
rem Sem `skip=`: o `skip=0` que estava aqui NAO e' "nao pule nada" -- ele e'
rem invalido, e o cmd responde `delims=" foi inesperado neste momento`, aborta
rem a linha e segue em frente. O resultado era a versao do Python saindo vazia,
rem com um erro no meio da tela que nao dizia de onde vinha.
for /f "usebackq delims=" %%v in ("%TEMP%\kit-pyinfo.txt") do (
    if not defined VERPY (set "VERPY=%%v") else if not defined ONDEPY set "ONDEPY=%%v"
)
del "%TEMP%\kit-pyinfo.txt" >nul 2>&1
echo       [OK] Python %VERPY%
if defined ONDEPY echo            %ONDEPY%

rem ---------- a biblioteca do TikTok ----------
rem
rem Conferida pelo IMPORT e nao pelo `pip show`: com mais de um Python na
rem maquina, o pip pode ter instalado no OUTRO -- e ai' o `pip show` diz que
rem esta' tudo certo e o kit quebra na primeira live.
echo.
echo   [3] Biblioteca do TikTok
"%PY%" -c "import TikTokLive" >nul 2>&1
if errorlevel 1 (
    echo       [X] TikTokLive nao instalada ^(ou instalada em outro Python^)
    echo           Rode o 1-INSTALACAO.bat, ou na mao:
    echo             "%PY%" -m pip install --user TikTokLive
    set /a PROBLEMAS+=1
) else (
    echo       [OK] TikTokLive instalada
)

:depois_do_python

rem ============================================================
rem  4. O ROJO
rem ============================================================
rem
rem TRES LUGARES, NESTA ORDEM. O kit sempre preferiu o rojo.exe da pasta
rem `ferramentas`, e essa continua sendo a escolha certa (versao conhecida,
rem sem depender do PATH). Mas muita gente ja' tem Rojo instalado pelo
rem Rokit/Aftman/Foreman ou solto no PATH, e antes o kit ignorava esse --
rem entao um antivirus que comesse o rojo.exe da pasta deixava a pessoa sem
rem Rojo nenhum, com um Rojo funcionando na maquina dela.

echo.
echo   [4] Rojo ^(leva o jogo pro Roblox Studio^)

set "ROJO="
if exist "%~dp0ferramentas\rojo.exe" (
    "%~dp0ferramentas\rojo.exe" --version >nul 2>&1
    if not errorlevel 1 set "ROJO=%~dp0ferramentas\rojo.exe"
)

if not defined ROJO (
    where rojo.exe >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%f in ('where rojo.exe 2^>nul') do if not defined ROJO set "ROJO=%%f"
    )
)

if not defined ROJO (
    if exist "%~dp0ferramentas\rojo.exe" (
        echo       [X] o rojo.exe existe na pasta mas NAO EXECUTA
        echo           Isso e' antivirus em praticamente todos os casos.
        echo           Abra a Seguranca do Windows ^> Protecao contra virus ^>
        echo           Historico de protecao, restaure o rojo.exe e marque
        echo           como permitido. Depois rode o 1-INSTALACAO.bat de novo.
    ) else (
        echo       [X] Rojo nao encontrado
        echo           Rode o 1-INSTALACAO.bat -- ele baixa pra pasta ferramentas\.
    )
    echo.
    echo           ISTO NAO IMPEDE A SUA LIVE: o JOGO-DA-LIVE.rbxlx ja' vem
    echo           pronto. O Rojo so' serve pra EDITAR o codigo do jogo.
    set /a AVISOS+=1
    goto depois_do_rojo
)

for /f "delims=" %%v in ('"%ROJO%" --version 2^>nul') do set "VERROJO=%%v"
echo       [OK] %VERROJO%
echo            %ROJO%

rem ---------- o projeto MONTA? ----------
rem
rem Esta e' a conferencia que mais vale a pena, e a que faltava: "o rojo.exe
rem roda" e "o projeto deste kit monta" sao perguntas diferentes. Um .luau
rem editado com erro de sintaxe passa na primeira e reprova na segunda -- e o
rem sintoma dela e' cruel, porque o ABRIR-JOGO abre o arquivo ANTIGO e voce
rem testa a versao anterior achando que testa a nova.
echo.
echo   [5] O projeto do jogo monta?
"%ROJO%" build "%~dp0roblox" --output "%TEMP%\verificar-live.rbxlx" >"%TEMP%\verificar-rojo.txt" 2>&1
if errorlevel 1 (
    echo       [X] o Rojo NAO conseguiu montar o jogo
    echo           A mensagem dele:
    echo.
    type "%TEMP%\verificar-rojo.txt"
    echo.
    echo           Quase sempre e' um arquivo da pasta roblox\ editado com erro.
    set /a PROBLEMAS+=1
) else (
    echo       [OK] monta sem erro
)
del "%TEMP%\verificar-live.rbxlx" >nul 2>&1
del "%TEMP%\verificar-rojo.txt" >nul 2>&1

rem ---------- o PLUGIN dentro do Studio ----------
rem
rem O "rojo serve" e' so' metade: quem conversa com ele e' um PLUGIN que roda
rem dentro do Studio. Sem o plugin, o servidor fica no ar falando sozinho, o
rem botao Connect nao existe em lugar nenhum, e o sintoma e' "o Rojo nao
rem conecta" -- sem uma linha de erro que aponte pra causa.
echo.
echo   [6] Plugin do Rojo no Studio
if exist "%LOCALAPPDATA%\Roblox\Plugins\RojoManagedPlugin.rbxm" (
    echo       [OK] instalado
) else (
    echo       [!] nao encontrado
    echo           Sem ele o botao Connect nao aparece no Studio. Instale com:
    echo             "%ROJO%" plugin install
    echo           E FECHE o Studio antes -- ele so' carrega plugin ao iniciar.
    set /a AVISOS+=1
)

:depois_do_rojo

rem ============================================================
rem  7. AS PORTAS
rem ============================================================
rem
rem Nao basta dizer "a porta esta' ocupada": a acao muda conforme QUEM ocupa.
rem Se for uma sessao anterior da propria live, fechar as janelas pretas
rem resolve. Se for outro programa, e' preciso trocar a porta ou fechar ele --
rem e sem o nome do processo nao ha' como saber qual dos dois casos e'.

echo.
echo   [7] Portas
call :conferir_porta 8000 "o servidor da live"
call :conferir_porta 34872 "o Rojo"

rem ============================================================
rem  8. O ROBLOX STUDIO
rem ============================================================

echo.
echo   [8] Roblox Studio
set "STUDIO="
for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO=%%f"
if not defined STUDIO (
    for /f "delims=" %%f in ('dir /b /s "%ProgramFiles(x86)%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO=%%f"
)
if not defined STUDIO (
    echo       [X] nao encontrado neste computador
    echo           Instale em https://create.roblox.com/
    set /a PROBLEMAS+=1
) else (
    echo       [OK] instalado
)

rem ============================================================
rem  O VEREDITO
rem ============================================================

echo.
echo   ============================================================
if "%PROBLEMAS%"=="0" (
    if "%AVISOS%"=="0" (
        echo    TUDO CERTO -- pode rodar o 4-MODO-TESTE.bat ou o 2-COMECAR-LIVE.bat
    ) else (
        echo    NADA IMPEDE A LIVE, mas leia os %AVISOS% aviso^(s^) marcados com [!]
        echo.
        echo    Cada aviso diz o que fazer. Porta ocupada por uma sessao
        echo    anterior o 2-COMECAR-LIVE.bat resolve sozinho; porta ocupada por
        echo    OUTRO programa, nao -- esse voce precisa fechar na mao.
    )
) else (
    echo    %PROBLEMAS% PROBLEMA^(S^) IMPEDEM A LIVE DE FUNCIONAR
    echo.
    echo    Resolva os itens marcados com [X] acima e rode este
    echo    5-VERIFICAR.bat de novo.
)
echo   ============================================================
echo.
pause
exit /b 0


rem ============================================================
rem  SUB-ROTINAS
rem ============================================================

:conferir_porta
rem  %~1 = numero da porta     %~2 = pra que ela serve
set "PORTA=%~1"
set "PARAQUE=%~2"
set "DONO="
set "PIDDONO="

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORTA% "') do set "PIDDONO=%%p"

if not defined PIDDONO (
    echo       [OK] porta %PORTA% livre ^(%PARAQUE%^)
    exit /b 0
)

rem Descobre o NOME do programa. E' o que transforma "a porta esta' ocupada"
rem numa instrucao: python.exe ou rojo.exe = sessao anterior do kit, feche as
rem janelas pretas. Qualquer outra coisa = outro programa, e ai' e' outro
rem assunto.
for /f "tokens=1" %%n in ('tasklist /FI "PID eq %PIDDONO%" /NH 2^>nul') do set "DONO=%%n"

echo       [!] porta %PORTA% OCUPADA por %DONO% ^(PID %PIDDONO%^) -- %PARAQUE%
if /i "%DONO%"=="python.exe" goto porta_do_kit
if /i "%DONO%"=="pythonw.exe" goto porta_do_kit
if /i "%DONO%"=="rojo.exe" goto porta_do_kit
if /i "%DONO%"=="cmd.exe" goto porta_do_kit

echo           Isto e' OUTRO programa, e nao uma sobra da live. Feche ele
echo           antes de comecar, senao o kit nao consegue subir.
set /a AVISOS+=1
exit /b 0

:porta_do_kit
echo           E' uma sessao anterior da propria live que ficou aberta.
echo           Feche TODAS as janelas pretas do kit. Pra encerrar agora:
echo             taskkill /PID %PIDDONO% /T /F
set /a AVISOS+=1
exit /b 0


:testar_python
rem Recebe um comando (py, python, python3) e SO' aceita se ele for um Python
rem de verdade e novo o bastante. Igual ao do 1-INSTALACAO.bat e do 2-COMECAR-LIVE.bat
rem -- se mexer num, mexa nos tres.
rem
rem POR QUE NAO BASTA `--version`: o Windows 10/11 tem um ATALHO FALSO chamado
rem python.exe dentro de WindowsApps, que so' abre a Microsoft Store. Em algumas
rem versoes do Windows ele responde com codigo de saida ZERO, e ai' o kit o
rem aceitava como Python valido -- a Store abria sozinha e nada funcionava.
rem Aqui a gente manda ele EXECUTAR codigo: o atalho falso nao executa nada.
set "VNUM="
"%~1" -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" > "%TEMP%\kit-pyver.txt" 2>nul
if errorlevel 1 goto :testar_python_fim
for /f "usebackq delims=" %%v in ("%TEMP%\kit-pyver.txt") do set "VNUM=%%v"
if not defined VNUM goto :testar_python_fim
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
