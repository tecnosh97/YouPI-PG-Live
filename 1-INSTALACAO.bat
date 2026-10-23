@echo off
title Instalador - Live Interativa Monster
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


rem --- conferencia do Roblox Studio (gerado pelo empacotador) ---
set "STUDIO_ROBLOX="
for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO_ROBLOX=%%f"
if not defined STUDIO_ROBLOX for /f "delims=" %%f in ('dir /b /s "%ProgramFiles(x86)%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO_ROBLOX=%%f"
if not defined STUDIO_ROBLOX (
    echo.
    echo   ============================================================
    echo    FALTA O ROBLOX STUDIO NESTE COMPUTADOR
    echo   ============================================================
    echo.
    echo    O jogo abre DENTRO do Roblox Studio. Sem ele instalado, a
    echo    instalacao termina certinho e o jogo nao abre depois -- essa e
    echo    a causa numero 1 de "instalei tudo e nao abriu".
    echo.
    echo    Instale agora, e de graca:
    echo      https://create.roblox.com/
    echo.
    echo    Baixe, instale, e abra o Studio UMA vez para fazer o login.
    echo    Depois volte aqui e rode este instalador de novo.
    echo.
    pause
)
rem --- fim da conferencia do Roblox Studio ---


rem ============================================================
rem  INSTALADOR
rem
rem  Roda UMA vez, na primeira utilizacao. Instala:
rem    - o Python, se ele nao estiver na maquina
rem    - as bibliotecas Python que a ponte usa
rem    - o Rojo (leva o jogo pro Roblox Studio)
rem
rem  O Rojo e' baixado PRA DENTRO desta pasta, e nao pro PATH do
rem  Windows. Isso evita o problema classico de instalador que
rem  exige fechar e reabrir a janela pro sistema "enxergar" o
rem  programa novo -- aqui o caminho e' fixo e sempre funciona.
rem
rem  NAO USE `setlocal enabledelayedexpansion` NESTE ARQUIVO.
rem  Com ela ligada o cmd come o "!" de dentro de QUALQUER texto
rem  expandido -- inclusive de %~dp0. Numa pasta chamada "LIVE!"
rem  o caminho chegava mutilado nos `if exist`, o instalador
rem  concluia que os arquivos nao existiam, e o erro apontava pra
rem  todo lado menos pro nome da pasta. Nada aqui precisa dela.
rem ============================================================

echo.
echo   ============================================================
echo    INSTALADOR DA LIVE INTERATIVA - Monster
echo   ============================================================
echo.
echo    Isto roda uma vez so'. Leva de 1 a 5 minutos.
echo.

rem ---------- 0. o kit chegou inteiro? ----------
rem
rem Esta conferencia precisa estar AQUI tambem, e nao so' no TESTAR/INICIAR-LIVE:
rem o 1-INSTALACAO.bat e' o primeiro arquivo que o comprador abre, e a causa
rem numero 1 de "kit incompleto" e' ele ter dado dois cliques no .bat DE
rem DENTRO do ZIP, sem extrair. Nesse caso o Windows copia so' o .bat pra uma
rem pasta temporaria e roda de la' -- as outras pastas ficam pra tras, e o
rem sintoma nao tem nada a ver com a causa.

set "FALTA="
if not exist "%~dp0servidor\servidor.py" set "FALTA=%FALTA% servidor\servidor.py"
if not exist "%~dp0ponte\ponte.py" set "FALTA=%FALTA% ponte\ponte.py"
if not exist "%~dp0roblox\default.project.json" set "FALTA=%FALTA% roblox\default.project.json"

if defined FALTA (
    call :kit_incompleto
    exit /b 1
)

rem ---------- 1. Achar o Python ----------

echo   [1/4] Procurando o Python...
set "PY="
set "PY_ANTIGO="
for %%C in (py python python3) do if not defined PY call :testar_python "%%C"

if not defined PY call :instalar_python
if not defined PY exit /b 1

rem Chamar direto em vez de capturar num `for /f`: com o PY sendo um caminho
rem completo (e' o que acontece logo depois de instalar o Python aqui do lado),
rem o `for /f` precisa de tres niveis de aspas e erra calado.
echo         achei:
"%PY%" --version
echo.

rem ---------- 2. Bibliotecas Python ----------

echo   [2/4] Instalando as bibliotecas da ponte...
echo         (a janela pode ficar parada um pouco; e' normal)
echo.
rem O pip se atualizando e' OPCIONAL, e agora ele falha calado de proposito.
rem Atualizar o pip em cima dele mesmo da' "Access is denied" com frequencia no
rem Windows, e o texto vermelho que aparecia assustava sem significar nada: o
rem que importa e' a biblioteca da linha seguinte, que instala igual com o pip
rem velho. Um erro que nao muda o resultado nao pode aparecer na tela de um
rem instalador -- ele so' faz o comprador parar e pedir suporte.
"%PY%" -m pip install --upgrade --disable-pip-version-check --quiet pip >nul 2>&1

rem --retries e --timeout: internet domestica cai, e sem eles um piscar de rede
rem virava "nao consegui instalar as bibliotecas".
rem --no-warn-script-location tira o aviso amarelo de "o script foi instalado
rem numa pasta fora do PATH". Ele e' informativo e nao muda nada aqui (o kit
rem chama tudo por `-m`), mas numa janela preta cheia de texto em ingles
rem qualquer linha amarela e' lida como erro.
"%PY%" -m pip install --disable-pip-version-check --quiet --retries 3 --timeout 30 --no-warn-script-location "TikTokLive>=6.6.6"

if errorlevel 1 (
    rem Segunda tentativa com --user antes de desistir. O caso e' concreto e
    rem comum: Python instalado "pra todos os usuarios" poe as bibliotecas
    rem dentro de Program Files, e ali o pip precisa de administrador. O erro
    rem que aparece e' "Access is denied" no meio de um tanto de texto em
    rem ingles, e o comprador nao tem como saber que a solucao e' uma flag.
    echo         a primeira tentativa nao passou; tentando na pasta do usuario...
    "%PY%" -m pip install --user --disable-pip-version-check --quiet --retries 3 --timeout 30 --no-warn-script-location "TikTokLive>=6.6.6"
)

rem Confere pelo IMPORT, e nao pelo codigo de saida do pip. O pip sai com 0 e
rem mesmo assim o import falha quando existe mais de um Python na maquina e a
rem biblioteca foi parar no outro. Sem esta conferencia o erro so' aparecia
rem la' na frente, no meio da live, parecendo outro problema.
"%PY%" -c "import TikTokLive" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ============================================================
    echo    NAO CONSEGUI INSTALAR AS BIBLIOTECAS
    echo   ============================================================
    echo.
    echo    Quase sempre e' uma destas:
    echo      - sem internet, ou a internet caiu no meio
    echo      - antivirus ou firewall bloqueando o Python
    echo      - mais de um Python instalado, e o pip instalou no outro
    echo.
    echo    Pra tentar na mao, abra o Prompt de Comando e rode:
    echo      "%PY%" -m pip install --user TikTokLive
    echo.
    pause
    exit /b 1
)
echo         pronto.
echo.

rem ---------- 3. Rojo ----------

echo   [3/4] Baixando o Rojo (leva o jogo pro Roblox Studio)...

if not exist "%~dp0ferramentas" mkdir "%~dp0ferramentas"

rem O rojo.exe que ja' esta' aqui SERVE MESMO?
rem
rem "O arquivo existe" nao e' a mesma pergunta que "o arquivo funciona", e a
rem diferenca aparecia como um erro sem causa aparente: antivirus e downloads
rem interrompidos deixam um rojo.exe do tamanho certo que nao executa. O
rem instalador pulava o download ("ja' estava aqui"), e o kit so' quebrava
rem depois, na hora de montar o jogo, com uma mensagem que nao falava de
rem download nenhum. Aqui a gente MANDA ELE RODAR: se nao responder a versao,
rem baixa de novo por cima.
if not exist "%~dp0ferramentas\rojo.exe" goto baixar_rojo
"%~dp0ferramentas\rojo.exe" --version >nul 2>&1
if errorlevel 1 (
    echo         o rojo.exe que estava aqui nao executa; baixando de novo.
    del /f /q "%~dp0ferramentas\rojo.exe" >nul 2>&1
    goto baixar_rojo
)
echo         ja' estava aqui e funciona, pulando o download.
goto instalar_plugin

:baixar_rojo
set "ROJO_ZIP=%TEMP%\rojo-kit.zip"
set "ROJO_TMP=%TEMP%\rojo-kit-extraido"

call :baixar "https://github.com/rojo-rbx/rojo/releases/download/v7.7.0/rojo-7.7.0-windows-x86_64.zip" "%ROJO_ZIP%"
if errorlevel 1 goto rojo_na_mao

rem Extrai pra uma pasta TEMPORARIA e so' depois copia o rojo.exe pra ca'.
rem
rem Antes a extracao ia direto pra "ferramentas". Quando ela falhava no meio --
rem disco cheio, antivirus, zip truncado -- sobrava lixo pela metade dentro da
rem pasta do kit, e a proxima execucao achava que estava tudo instalado. Assim,
rem a pasta do kit so' recebe o arquivo depois que ele existe inteiro.
if exist "%ROJO_TMP%" rmdir /s /q "%ROJO_TMP%" >nul 2>&1
mkdir "%ROJO_TMP%" >nul 2>&1

rem TIRA A MARCA DE "VEIO DA INTERNET" ANTES DE ABRIR O ZIP.
rem
rem O Windows carimba todo arquivo baixado com uma etiqueta escondida (a "marca
rem da web"). Num ZIP ela e' herdada por tudo que sai de dentro dele, e o
rem rojo.exe extraido ja' nasce marcado -- ai' o SmartScreen segura na hora de
rem executar. Como o instalador confere o Rojo RODANDO ele logo abaixo, essa
rem etiqueta virava "o Rojo baixou mas nao executa" num PC onde estava tudo bem.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try{Unblock-File -LiteralPath $env:ROJO_ZIP}catch{}" >nul 2>&1

rem PRIMEIRO JEITO DE EXTRAIR: o Expand-Archive do PowerShell.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';" ^
  "Expand-Archive -LiteralPath $env:ROJO_ZIP -DestinationPath $env:ROJO_TMP -Force" >nul 2>&1

rem SEGUNDO JEITO: o tar.exe, que vem no proprio Windows e tambem abre .zip.
rem
rem Existe porque o primeiro depende do PowerShell RODAR SCRIPT, e isso e'
rem justamente o que costuma estar desligado: em PC de empresa ou escola a
rem politica de execucao vem travada por regra do administrador, e ai' nem o
rem `-ExecutionPolicy Bypass` vale. O download tinha funcionado, o ZIP estava
rem inteiro na pasta temporaria, e o kit dizia "nao consegui baixar o Rojo" --
rem apontando pro lugar errado. O tar nao e' script: e' um programa, e passa.
call :achar_rojo_extraido
if not defined ROJO_ACHADO tar.exe -x -f "%ROJO_ZIP%" -C "%ROJO_TMP%" >nul 2>&1
call :achar_rojo_extraido

if not defined ROJO_ACHADO goto rojo_na_mao
copy /y "%ROJO_ACHADO%" "%~dp0ferramentas\rojo.exe" >nul
set "ROJO_FINAL=%~dp0ferramentas\rojo.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try{Unblock-File -LiteralPath $env:ROJO_FINAL}catch{}" >nul 2>&1
rmdir /s /q "%ROJO_TMP%" >nul 2>&1
del /f /q "%ROJO_ZIP%" >nul 2>&1

if not exist "%~dp0ferramentas\rojo.exe" goto rojo_na_mao

rem Confere que o que chegou EXECUTA, e nao so' que existe.
"%~dp0ferramentas\rojo.exe" --version >nul 2>&1
if errorlevel 1 goto rojo_bloqueado
echo         pronto.
goto instalar_plugin

:rojo_bloqueado
echo.
echo   ============================================================
echo    O ROJO BAIXOU MAS NAO EXECUTA
echo   ============================================================
echo.
echo    O arquivo chegou inteiro e o Windows nao deixa ele rodar.
echo    Isso e' antivirus, em praticamente todos os casos.
echo.
echo    Como resolver:
echo      1^) abra o seu antivirus (ou a Seguranca do Windows^)
echo      2^) procure a lista de "quarentena" ou "ameacas bloqueadas"
echo      3^) restaure o rojo.exe e marque como permitido
echo      4^) rode este 1-INSTALACAO.bat de novo
echo.
echo    ISTO NAO IMPEDE A SUA LIVE: o Rojo so' serve pra EDITAR o
echo    codigo do jogo. O JOGO-DA-LIVE.rbxlx ja' vem pronto na pasta.
echo.
pause
goto fim

:rojo_na_mao
echo.
echo   ============================================================
echo    NAO CONSEGUI BAIXAR O ROJO
echo   ============================================================
echo.
echo    Isto NAO impede a sua live: o JOGO-DA-LIVE.rbxlx ja' vem
echo    pronto na pasta. O Rojo so' serve pra quem for EDITAR o
echo    codigo do jogo.
echo.
echo    Se quiser resolver, da' pra fazer na mao:
echo.
echo    1^) Abra: https://github.com/rojo-rbx/rojo/releases
echo    2^) Baixe o arquivo que termina em "windows-x86_64.zip"
echo    3^) Extraia e ponha o rojo.exe dentro da pasta:
echo       %~dp0ferramentas\
echo    4^) Rode este 1-INSTALACAO.bat de novo
echo.
pause
goto fim

:instalar_plugin
rem ---------- o PLUGIN do Rojo dentro do Studio ----------
rem
rem ISTO E' OBRIGATORIO E QUASE TODO MUNDO ESQUECE.
rem
rem O "rojo serve" e' so' metade: ele abre um servidor e espera. Quem conversa
rem com ele e' um PLUGIN que roda dentro do Roblox Studio. Sem o plugin, o
rem servidor fica no ar falando sozinho, o botao Connect nunca aparece em lugar
rem nenhum, e o sintoma e' "nao acontece nada" -- sem uma linha de erro que
rem aponte pra ca'.
rem
rem A saida do `plugin install` NAO e' mais engolida com `2>&1`. Ela era, e por
rem isso a unica coisa que sobrava quando falhava era um "AVISO" generico, sem
rem o motivo -- que costuma ser permissao de pasta ou antivirus, duas coisas
rem com solucoes diferentes.

if not exist "%~dp0ferramentas\rojo.exe" goto fim

echo.
echo   [4/4] Instalando o plugin do Rojo no Roblox Studio...

rem A pasta de plugins pode nao existir em quem nunca abriu o Studio. O rojo
rem cria sozinho, mas criar aqui antes tira um motivo de falha do caminho.
if not exist "%LOCALAPPDATA%\Roblox\Plugins" mkdir "%LOCALAPPDATA%\Roblox\Plugins" >nul 2>&1

"%~dp0ferramentas\rojo.exe" plugin install >nul

if not exist "%LOCALAPPDATA%\Roblox\Plugins\RojoManagedPlugin.rbxm" (
    echo         AVISO: nao consegui instalar o plugin.
    echo         Instale na mao: no Studio, aba Plugins ^> Manage Plugins,
    echo         ou procure "Rojo" na Creator Store.
    goto fim
)

echo         pronto.
echo.
echo         ATENCAO: se o Roblox Studio estiver ABERTO agora, feche e
echo         abra de novo. O Studio so' carrega plugin novo quando
echo         inicia -- com ele aberto, o plugin so' aparece na proxima vez.

rem ---------- o AUTOTESTE do Rojo ----------
rem
rem POR QUE ISTO EXISTE.
rem
rem Ate' aqui o instalador dizia "pronto" tendo conferido apenas que dois
rem arquivos existiam no disco. Se o Rojo nao subisse -- porta ocupada,
rem antivirus, firewall pedindo autorizacao numa janela que ninguem viu --
rem o comprador so' descobria dias depois, no meio de uma edicao, com o botao
rem Connect dando erro. E ai' o problema parecia ser do Studio.
rem
rem Aqui o instalador SOBE o Rojo de verdade, PERGUNTA pra ele pelo /api/rojo,
rem e derruba tudo em seguida. Leva uns segundos e troca um "pronto" que era
rem um palpite por um que foi conferido.

echo.
echo   Conferindo se o Rojo conecta mesmo...

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":34872"') do taskkill /PID %%p /T /F >nul 2>&1
taskkill /IM rojo.exe /F >nul 2>&1

rem O ENDERECO SAI DO PROPRIO WINDOWS, e nao de um palpite.
rem
rem O plugin do Rojo procura por "localhost". O rojo.exe resolve "localhost"
rem preferindo IPv4 e escuta em 127.0.0.1; boa parte dos Windows resolve o
rem mesmo nome pelo IPv6 e procura em [::1]. Quando os dois discordam, o
rem Connect do plugin falha com o servidor no ar -- e nada na tela fala de
rem IPv6.
rem
rem Este autoteste conferia sempre no IPv4. Numa maquina em que o Studio usa
rem IPv6 ele aprovava com folga uma instalacao em que o Connect nunca ia
rem funcionar -- ou seja, dava exatamente a falsa confianca que ele existe pra
rem impedir. Subindo no endereco que o Windows usa, o que ele aprova passa a
rem ser o que o Studio vai encontrar. (Mesma conta do 3-ABRIR-JOGO.bat.)
set "ROJO_ADDR=127.0.0.1"
set "ROJO_HOST=127.0.0.1"
ping -n 1 localhost 2>nul | findstr /c:"[::1]" >nul
if errorlevel 1 goto autoteste_endereco
set "ROJO_ADDR=::1"
set "ROJO_HOST=[::1]"

:autoteste_endereco
start "0 - Rojo (autoteste)" /MIN /D "%~dp0roblox" cmd /c ""%~dp0ferramentas\rojo.exe" serve "%~dp0roblox\default.project.json" --address %ROJO_ADDR% --port 34872"

set "TENTATIVAS=0"
:autoteste_rojo
call :perguntar_ao_rojo
if "%ROJO_OK%"=="1" goto autoteste_ok
set /a TENTATIVAS+=1
if %TENTATIVAS% geq 12 goto autoteste_falhou
timeout /t 1 /nobreak >nul
goto autoteste_rojo

:autoteste_ok
echo         Rojo conectou (%ROJO_HOST% : 34872). Esta parte esta' certa.
goto autoteste_fim

:autoteste_falhou
echo.
echo         AVISO: o Rojo nao respondeu na porta 34872.
echo.
echo         ISTO NAO IMPEDE A SUA LIVE -- o JOGO-DA-LIVE.rbxlx ja' vem
echo         com todo o codigo dentro. So' a edicao ao vivo do codigo
echo         fica de fora.
echo.
echo         O que costuma ser:
echo           - o firewall do Windows perguntou e ninguem respondeu;
echo           - antivirus segurando o rojo.exe;
echo           - outro programa ocupando a porta 34872.
echo.

:autoteste_fim
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":34872"') do taskkill /PID %%p /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 0 - Rojo*" /T /F >nul 2>&1
taskkill /IM rojo.exe /F >nul 2>&1

:fim
echo.
echo   ============================================================
echo    INSTALACAO CONCLUIDA
echo   ============================================================
echo.
echo    Proximos passos:
echo.
echo      Pra testar sem live   ^-^-^>  4-MODO-TESTE.bat
echo      Pra live de verdade   ^-^-^>  2-COMECAR-LIVE.bat
echo.
echo    Se e' a sua primeira vez, comece pelo 4-MODO-TESTE.bat.
echo.
pause
exit /b 0


rem ============================================================
rem  SUB-ROTINAS
rem ============================================================

:baixar
rem ---------- BAIXA UM ARQUIVO, COM TEIMOSIA ----------
rem
rem   %~1 = endereco     %~2 = onde salvar
rem   devolve errorlevel 0 se o arquivo chegou inteiro
rem
rem TRES COISAS QUE ESTA SUB-ROTINA CONSERTA, E QUE APARECIAM COMO "O
rem INSTALADOR DEU ERRO":
rem
rem 1. O `Invoke-WebRequest` do PowerShell desenha uma barra de progresso que
rem    custa mais que o proprio download. Num arquivo de 27 MB (o Python) isso
rem    transforma 20 segundos em varios minutos com a janela parada, e a
rem    conclusao obvia de quem esta' olhando e' que travou -- muita gente
rem    fechava a janela no meio, o que de fato quebra a instalacao. O
rem    `$ProgressPreference='SilentlyContinue'` desliga a barra e devolve a
rem    velocidade normal.
rem
rem 2. O caminho ia INTERPOLADO dentro de uma string do PowerShell. Numa pasta
rem    com apostrofo no nome -- "C:\Users\Joao D'Avila\..." -- a aspa fechava a
rem    string no meio e o PowerShell devolvia um erro de sintaxe que nao tem
rem    nada a ver com download. Agora o caminho vai por VARIAVEL DE AMBIENTE
rem    ($env:BAIXAR_DEST), onde nao existe aspa pra fechar.
rem
rem 3. Internet domestica cai. Uma tentativa unica virava "nao consegui
rem    baixar" num piscar de rede que teria funcionado dois segundos depois.
rem    Agora sao tres tentativas.
rem
rem 4. UM JEITO SO' DE BAIXAR ERA UM PONTO UNICO DE FALHA -- E ERA ELE QUE
rem    QUEBRAVA NO WINDOWS 11.
rem
rem    Antes, se o `where curl.exe` respondesse, as TRES tentativas iam pelo
rem    curl. Se o curl estivesse bloqueado, as tres morriam pelo mesmo motivo,
rem    sem nunca experimentar o PowerShell que estava logo ali embaixo.
rem
rem    E curl bloqueado nao e' hipotese: "curl.exe baixando um .exe da
rem    internet" e' exatamente o que virus fazem, entao a Seguranca do Windows
rem    e a maioria dos antivirus tratam essa chamada como suspeita e cortam. No
rem    Windows 11 isso e' bem mais frequente (a protecao vem mais fechada de
rem    fabrica), e o relato que chegava era "o instalador nao baixa nada" --
rem    so' no Windows 11, o que fazia o problema parecer coisa de outro mundo.
rem
rem    Agora cada tentativa desce uma ESCADA de tres jeitos diferentes:
rem
rem        curl.exe  ->  PowerShell  ->  BITS (o servico do Windows Update)
rem
rem    Os tres pedem a rede por caminhos diferentes, com bibliotecas de TLS
rem    diferentes e permissoes diferentes. Um bloqueio que pega um dificilmente
rem    pega os tres -- e o BITS, em particular, quase nunca e' barrado: e' o
rem    mesmo servico que o proprio Windows usa pra se atualizar.
rem
rem    Com as 3 tentativas por fora, sao ate' 9 downloads antes de desistir.

set "BAIXAR_URL=%~1"
set "BAIXAR_DEST=%~2"
set "BAIXAR_TENTATIVA=0"

:baixar_de_novo
set /a BAIXAR_TENTATIVA+=1

rem ---------- jeito 1: o curl.exe do Windows ----------
call :baixar_limpar
where curl.exe >nul 2>&1
if errorlevel 1 goto baixar_com_powershell

rem --fail e' o que impede o pior caso: sem ele, uma pagina de erro do servidor
rem (404, portal de rede de hotel, bloqueio de firewall corporativo) e' salva
rem COMO SE FOSSE o programa, e o erro so' aparece depois, na hora de executar
rem um arquivo que na verdade e' HTML.
rem
rem --ssl-no-revoke desliga a CONSULTA DE CERTIFICADO REVOGADO. Vale a pena
rem saber o que isso troca: o curl no Windows usa o Schannel, que tenta
rem perguntar a uma lista de revogacao na internet se o certificado do site
rem ainda vale. Quando essa consulta nao chega (proxy de empresa, escola,
rem antivirus que abre o HTTPS no meio, DNS de operadora), o Schannel nao
rem responde "nao sei" -- ele REPROVA a conexao, e o curl morre com uma frase
rem sobre revogacao que ninguem liga a download. O endereco aqui e' fixo e e'
rem sempre python.org ou github.com, e o que chega ainda e' conferido logo
rem abaixo, entao a troca compensa: perde-se uma checagem que ja' nao estava
rem funcionando nessas redes, e ganha-se o download.
curl.exe -L --fail --silent --show-error --ssl-no-revoke --retry 2 --connect-timeout 20 -o "%BAIXAR_DEST%" "%BAIXAR_URL%"
if errorlevel 1 goto baixar_com_powershell
call :baixar_chegou_inteiro
if not errorlevel 1 exit /b 0

:baixar_com_powershell
rem ---------- jeito 2: PowerShell ----------
rem A linha do Tls12 nao e' decoracao: o Windows 10 sem as atualizacoes mais
rem novas ainda negocia TLS 1.0 por padrao, e o GitHub recusa desde 2018. O
rem erro que aparece e' "Nao foi possivel criar um canal seguro SSL/TLS", que
rem nao tem uma unica palavra apontando pra causa.
rem
rem -UseBasicParsing porque em Windows sem o Internet Explorer configurado o
rem Invoke-WebRequest falha sem ele -- e o erro tambem nao diz isso.
call :baixar_limpar
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';" ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "Invoke-WebRequest -Uri $env:BAIXAR_URL -OutFile $env:BAIXAR_DEST -UseBasicParsing"
if errorlevel 1 goto baixar_com_bits
call :baixar_chegou_inteiro
if not errorlevel 1 exit /b 0

:baixar_com_bits
rem ---------- jeito 3: BITS, o mesmo do Windows Update ----------
rem Ultimo recurso, e o mais teimoso dos tres: quem baixa nao e' esta janela, e'
rem um servico do proprio Windows. Por isso ele costuma passar onde os outros
rem dois apanham -- regra de antivirus e de firewall quase sempre libera o
rem servico que atualiza o sistema.
rem
rem Import-Module explicito porque em algumas instalacoes o modulo nao carrega
rem sozinho, e ai' o erro que aparece e' "termo nao reconhecido", que parece
rem erro de digitacao no script.
call :baixar_limpar
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';Import-Module BitsTransfer;" ^
  "Start-BitsTransfer -Source $env:BAIXAR_URL -Destination $env:BAIXAR_DEST" >nul 2>&1
if errorlevel 1 goto baixar_falhou
call :baixar_chegou_inteiro
if not errorlevel 1 exit /b 0

:baixar_falhou
if %BAIXAR_TENTATIVA% GEQ 3 exit /b 1
echo         a tentativa %BAIXAR_TENTATIVA% nao deu certo; tentando de novo...
timeout /t 3 /nobreak >nul
goto baixar_de_novo


:baixar_limpar
rem Cada jeito comeca do zero. Sem isto, o pedaco que o jeito anterior deixou
rem pela metade viraria a "prova" de que o proximo funcionou -- o arquivo existe
rem e ate' passa do tamanho minimo, mas esta' truncado, e o erro so' aparece la'
rem na frente, na hora de executar.
if exist "%BAIXAR_DEST%" del /f /q "%BAIXAR_DEST%" >nul 2>&1
exit /b 0


:baixar_chegou_inteiro
rem Arquivo minusculo = quase sempre uma pagina de erro salva com o nome do
rem programa. Os dois arquivos que o kit baixa passam de 4 MB; 100 KB e' um
rem piso folgado que nenhum download de verdade reprova.
if not exist "%BAIXAR_DEST%" exit /b 1
set "TAMANHO=0"
call :tamanho_de "%BAIXAR_DEST%"
if %TAMANHO% LSS 100000 exit /b 1
exit /b 0


:achar_rojo_extraido
rem PROCURA o rojo.exe em vez de adivinhar onde ele caiu.
rem
rem Antes o caminho era fixo: "%ROJO_TMP%\rojo.exe". Isso amarra o instalador ao
rem formato de HOJE do pacote do Rojo -- basta uma versao nova sair com o
rem programa dentro de uma subpasta pra o instalador dizer "nao consegui
rem baixar" segurando o arquivo certo, extraido, na pasta ao lado. Procurar
rem custa um piscar de olho e nao tem esse jeito de quebrar.
set "ROJO_ACHADO="
for /f "delims=" %%f in ('dir /b /s "%ROJO_TMP%\rojo.exe" 2^>nul') do if not defined ROJO_ACHADO set "ROJO_ACHADO=%%f"
exit /b 0


:tamanho_de
rem O modificador "z" de um argumento devolve o tamanho do arquivo em bytes.
rem Ele existe SO' pra argumento de sub-rotina, e nao pra variavel comum -- por
rem isso esta funcao curta em vez de uma linha la' em cima.
rem
rem E cuidado ao editar este comentario: escrever aquele modificador solto num
rem `rem`, sem o numero do argumento colado nele, faz o cmd tentar expandir o
rem texto do proprio comentario, falhar, e derrubar a linha SEGUINTE com um
rem "foi inesperado neste momento" que aponta pra outro lugar do arquivo.
set "TAMANHO=%~z1"
if not defined TAMANHO set "TAMANHO=0"
exit /b 0


:perguntar_ao_rojo
rem PERGUNTA DE VERDADE pro servidor do Rojo, em vez de so' olhar o netstat.
rem "A porta esta' escutando" e "o Rojo esta' pronto" nao sao a mesma coisa:
rem um rojo orfao de outra pasta tambem deixa a porta escutando, e ai' o
rem instalador diria "conectou" sobre um servidor que nao e' o deste projeto.
set "ROJO_OK="
where curl.exe >nul 2>&1
if errorlevel 1 goto perguntar_com_powershell

curl.exe -s -o nul -m 3 "http://%ROJO_HOST%:34872/api/rojo" 2>nul
if errorlevel 1 exit /b 0
set "ROJO_OK=1"
exit /b 0

:perguntar_com_powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$null=Invoke-WebRequest -Uri 'http://%ROJO_HOST%:34872/api/rojo' -UseBasicParsing -TimeoutSec 3;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 exit /b 0
set "ROJO_OK=1"
exit /b 0


:kit_incompleto
rem Distingue os DOIS casos, porque a solucao de um nao resolve o outro.
set "ONDE=%~dp0"
set "NO_TEMP="
if not "%ONDE%"=="%ONDE:\AppData\Local\Temp\=%" set "NO_TEMP=1"
if not "%ONDE%"=="%ONDE:Rar$=%" set "NO_TEMP=1"
if not "%ONDE%"=="%ONDE:\7z=%" set "NO_TEMP=1"

echo.
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
    echo      4^) Abra a pasta que apareceu e rode o 1-INSTALACAO.bat de la'
    echo.
    echo    A pasta certa e' a que tem o 1-INSTALACAO.bat E as pastas
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


:testar_python
rem Recebe um comando (py, python, python3 ou um caminho completo) e SO' aceita
rem se ele for um Python de verdade e novo o bastante.
rem
rem POR QUE NAO BASTA `%%C --version`:
rem
rem O Windows 10/11 vem com um ATALHO FALSO chamado python.exe dentro de
rem WindowsApps. Ele nao e' o Python: e' um stub que abre a Microsoft Store.
rem Em algumas versoes do Windows esse stub responde com codigo de saida ZERO,
rem e ai' o instalador antigo o aceitava como Python valido. O que o comprador
rem via: a Microsoft Store abrindo sozinha, nada instalando, e a conclusao
rem obvia -- "o Python nao esta' baixando".
rem
rem Aqui a gente manda ele EXECUTAR codigo e devolver a versao. O stub nao
rem executa nada, entao nao passa. E de quebra ja' barra Python velho demais.
rem
rem O PISO E' 3.10, e o numero nao e' chutado: a TikTokLive 6.6.6 declara
rem "Requires-Python: >=3.10". Com um Python mais velho o pip recusa a instalar
rem e responde "could not find a version that satisfies the requirement" -- uma
rem frase que nao tem a palavra "versao do Python" em lugar nenhum, e que manda
rem o comprador procurar problema de internet. Barrar aqui troca isso por uma
rem frase que diz o que fazer. (A ponte tambem usa asyncio.to_thread, do 3.9.)
set "VNUM="
"%~1" -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" > "%TEMP%\kit-pyver.txt" 2>nul
if errorlevel 1 goto :testar_python_fim
rem `for /f` e nao `set /p`: o print do Python termina em CRLF, e o `set /p`
rem deixa o CR pendurado no valor em algumas versoes do Windows. Um CR invisivel
rem no fim do numero reprovaria a conferencia de digitos logo abaixo, e o kit
rem diria "Python nao encontrado" com o Python instalado na frente dele.
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


:instalar_python
rem ---------- BAIXA E INSTALA O PYTHON ----------
rem
rem Antes esta parte so' mandava o comprador pro python.org e desistia. Na
rem pratica metade parava ali: ou nao achava o botao, ou baixava e esquecia a
rem caixinha do PATH, ou instalava e nao entendia por que precisava rodar o
rem .bat de novo. O relato que chegava era sempre o mesmo -- "o Python nao
rem esta' baixando" -- e nao havia nada no kit que ajudasse a sair disso.
rem
rem Agora o kit baixa do proprio python.org e instala. O passo manual continua
rem existindo logo abaixo, pra quando o download nao der certo.

echo.
echo   ============================================================
echo    O PYTHON AINDA NAO ESTA NESTE COMPUTADOR
echo   ============================================================
echo.
if defined PY_ANTIGO (
    echo    Achei um Python instalado, mas ele e' antigo demais pro kit
    echo    ^(%PY_ANTIGO%^). Vou instalar uma versao nova do lado; a antiga
    echo    continua onde esta', sem ser mexida.
    echo.
)
echo    O Python e' o programa que le' o chat da sua live. E' gratuito
echo    e vem do site oficial: python.org
echo.
echo    Eu baixo e instalo pra voce agora. Sao uns 25 MB e leva de 2 a
echo    5 minutos. A barra de progresso do Python vai aparecer numa
echo    janela propria -- deixe ela terminar.
echo.
echo    Se preferir instalar na mao, feche esta janela e siga o
echo    passo 1 do arquivo 0-COMECE-AQUI.txt.
echo.
pause

rem A arquitetura importa: o instalador amd64 simplesmente nao roda num
rem Windows 32 bits nem num ARM, e a mensagem que ele da' nao ajuda ninguem.
set "VER_PY=3.12.10"
set "ARQ_PY=python-%VER_PY%-amd64.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARQ_PY=python-%VER_PY%-arm64.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "ARQ_PY=python-%VER_PY%.exe"

set "DESTINO=%TEMP%\%ARQ_PY%"

echo.
echo   Baixando o Python (uns 25 MB)...
call :baixar "https://www.python.org/ftp/python/%VER_PY%/%ARQ_PY%" "%DESTINO%"
if errorlevel 1 goto :python_na_mao

echo   Instalando o Python (espere a barrinha terminar)...
rem InstallAllUsers=0 de proposito: instalacao so' pra este usuario NAO pede
rem administrador. Pedir UAC aqui custaria uma tela de susto ("um programa
rem desconhecido quer alterar o computador") logo no primeiro minuto de uso do
rem kit, e e' exatamente onde as pessoas desistem.
rem PrependPath=1 e' a caixinha "Add python.exe to PATH" que todo tutorial
rem manda marcar -- aqui ela ja' vem marcada e ninguem pode esquecer.
"%DESTINO%" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 Include_test=0

rem SEGUNDA TENTATIVA SEM O LAUNCHER.
rem
rem O `py.exe` (o "launcher") e' instalado pra MAQUINA INTEIRA, e nao pro
rem usuario. Quando ja' existe um instalado por outra conta -- ou por uma
rem instalacao antiga "pra todos os usuarios" -- o instalador do Python bate
rem nisso e aborta a instalacao INTEIRA com o codigo 1603, sem instalar nada.
rem A janela some sozinha (e' /passive) e o que sobra na tela e' "nao consegui
rem instalar o Python", sem motivo nenhum. Sem o launcher, a mesma instalacao
rem passa -- e o kit nao precisa dele: ele tambem procura pelo python.exe.
if errorlevel 1 (
    echo   A primeira tentativa nao passou; tentando sem o atalho "py"...
    "%DESTINO%" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=0 Include_test=0
)
del "%DESTINO%" >nul 2>&1

echo   Conferindo...

rem O PATH DESTA JANELA continua sendo o de antes da instalacao -- o Windows
rem so' entrega o PATH novo pra janelas abertas DEPOIS. Por isso a busca aqui
rem e' pelo caminho fixo da instalacao, e nao pelo comando solto: assim o
rem instalador termina AGORA, em vez de mandar o comprador fechar tudo e rodar
rem de novo sem entender por que.
set "PY="
for %%C in (py python python3) do if not defined PY call :testar_python "%%C"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" call :testar_python "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
if not defined PY for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\Programs\Python\python.exe" 2^>nul') do if not defined PY call :testar_python "%%f"

if defined PY (
    echo         Python instalado.
    echo.
    exit /b 0
)

:python_na_mao
echo.
echo   ============================================================
echo    NAO CONSEGUI INSTALAR O PYTHON SOZINHO
echo   ============================================================
echo.
echo    Da' pra fazer na mao em 3 minutos:
echo.
echo    1^) Abra:  https://www.python.org/downloads/
echo    2^) Baixe a versao mais nova pra Windows
echo    3^) IMPORTANTE: na primeira tela do instalador, marque
echo       a caixinha "Add python.exe to PATH" antes de continuar
echo    4^) Termine a instalacao
echo    5^) FECHE esta janela e rode o 1-INSTALACAO.bat de novo
echo.
echo    O passo 5 nao e' frescura: o Windows so' mostra um programa
echo    recem-instalado pras janelas abertas DEPOIS da instalacao.
echo.
echo    O que costuma atrapalhar o download automatico:
echo      - sem internet, ou internet caindo no meio
echo      - antivirus ou firewall bloqueando o download
echo      - rede de empresa/escola que bloqueia o python.org
echo.
pause
exit /b 1

