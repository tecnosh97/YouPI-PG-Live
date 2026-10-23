@echo off
setlocal
title Abrindo o jogo no Roblox Studio

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
rem  ABRE O JOGO NO ROBLOX STUDIO -- COM O ROJO JUNTO
rem
rem  Faz, nesta ordem:
rem
rem    1. remonta o JOGO-DA-LIVE.rbxlx (mapa + codigo)
rem    2. sobe o Rojo e CONFERE que ele atendeu
rem    3. abre o Studio com o jogo
rem
rem  Os tres passos moram AQUI, e nao espalhados pelo INICIAR-LIVE e
rem  pelo TESTAR, porque quem so' quer abrir o jogo clicava neste
rem  arquivo e ficava sem Rojo nenhum -- editava um .luau, apertava
rem  Play, e nada mudava. Agora e' o mesmo caminho para todos.
rem
rem  SEM `enabledelayedexpansion`, e isso e' de proposito: com ela
rem  ligada o cmd come o "!" de dentro de tudo que expande --
rem  inclusive do %~dp0. Numa pasta chamada "LIVE!" o caminho do
rem  JOGO-DA-LIVE.rbxlx chegava mutilado aqui e o script dizia que
rem  o arquivo do jogo nao existia, com ele ali do lado. Os lacos
rem  daqui sao de `goto`, e `goto` rele' a linha a cada volta.
rem
rem  POR QUE ISTO EXISTE EM VEZ DE "de dois cliques no .rbxlx":
rem
rem  A extensao .rbxlx NAO vem associada ao Studio em muitos
rem  Windows. Nessas maquinas, dois cliques no arquivo nao fazem
rem  absolutamente nada -- sem erro, sem janela, sem nada. E' um
rem  dos sintomas mais desnorteantes que existem, porque parece
rem  que o kit esta' quebrado quando o problema e' o Windows nao
rem  saber com o que abrir o arquivo.
rem
rem  Aqui a gente acha o Studio e chama ele direto, passando o
rem  arquivo como argumento. Funciona com ou sem associacao.
rem ============================================================

set "JOGO=%~dp0JOGO-DA-LIVE.rbxlx"
set "PROJETO=%~dp0roblox"
set "PLUGIN=%LOCALAPPDATA%\Roblox\Plugins\RojoManagedPlugin.rbxm"

rem ============================================================
rem  ONDE ESTA' O ROJO
rem ============================================================
rem
rem DOIS LUGARES, NESTA ORDEM.
rem
rem 1) ferramentas\rojo.exe -- o que o 1-INSTALACAO.bat baixa. E' o preferido
rem    porque a versao e' conhecida e nao depende do PATH do sistema.
rem
rem 2) o rojo.exe do PATH -- quem ja' usa Roblox costuma ter um, instalado
rem    pelo Rokit, Aftman ou Foreman.
rem
rem O segundo caminho e' NOVO, e ele conserta um caso que acontecia de
rem verdade: o antivirus come o rojo.exe da pasta `ferramentas` (executavel
rem baixado da internet, sem assinatura -- e' o perfil classico de falso
rem positivo), e o kit passava a dizer "o Rojo nao esta' instalado" numa
rem maquina que tinha Rojo funcionando e no PATH.
rem
rem E nao basta o arquivo EXISTIR: um download interrompido ou um arquivo em
rem quarentena deixa um rojo.exe do tamanho certo que nao executa. Por isso
rem cada candidato e' testado com `--version` antes de ser aceito.

set "ROJO="
if exist "%~dp0ferramentas\rojo.exe" (
    "%~dp0ferramentas\rojo.exe" --version >nul 2>&1
    if not errorlevel 1 set "ROJO=%~dp0ferramentas\rojo.exe"
)
if not defined ROJO (
    for /f "delims=" %%f in ('where rojo.exe 2^>nul') do if not defined ROJO set "ROJO=%%f"
)
if defined ROJO echo   Rojo: %ROJO%

rem ============================================================
rem  1. REMONTAR O ARQUIVO DO JOGO
rem ============================================================
rem
rem Refeito a CADA vez de proposito. Se ficasse so' no instalador, quem mexesse
rem num arquivo .luau -- ou no mapa -- continuaria abrindo a versao velha e
rem juraria que a mudanca nao funcionou.
rem
rem A saida do Rojo aparece NA TELA, sem `>nul`. Antes ela era engolida, e um
rem erro no projeto virava o pior tipo de falha silenciosa: o build morria, o
rem Studio abria o arquivo ANTIGO, e voce testava a versao anterior achando que
rem estava testando a nova.

if not defined ROJO goto sem_rojo

echo.
echo   Montando o arquivo do jogo (mapa + codigo)...
"%ROJO%" build "%PROJETO%" --output "%JOGO%"
if errorlevel 1 (
    echo.
    echo   ============================================================
    echo    O ROJO NAO CONSEGUIU MONTAR O ARQUIVO DO JOGO
    echo   ============================================================
    echo.
    echo    A mensagem do Rojo esta' logo acima -- e' ela que diz o que
    echo    aconteceu. Quase sempre e' um arquivo da pasta "roblox"
    echo    editado com erro, ou o antivirus segurando o rojo.exe.
    echo.
    if exist "%JOGO%" (
        echo    Vou abrir o arquivo ANTERIOR, que ainda esta' aqui. ATENCAO:
        echo    ele NAO tem as suas mudancas mais recentes.
        echo.
    ) else (
        echo    E nao existe nenhum arquivo de jogo anterior pra abrir.
        echo    Rode o 1-INSTALACAO.bat e tente de novo.
        echo.
        pause
        exit /b 1
    )
    pause
) else (
    echo   Pronto: JOGO-DA-LIVE.rbxlx
)

rem ============================================================
rem  2. O ROJO NO AR
rem ============================================================
rem
rem O `rojo serve` e' o que deixa voce EDITAR o codigo com o jogo aberto. Ele e'
rem opcional pra fazer live, mas quando ele falha o sintoma nao parece com falha
rem nenhuma -- o botao Connect do Studio simplesmente da' erro, ou pior:
rem conecta no servidor ERRADO. Por isso os tres cuidados abaixo.

rem ---------- 2a. o plugin ----------
rem
rem ISTO E' OBRIGATORIO E QUASE TODO MUNDO ESQUECE.
rem
rem O "rojo serve" e' so' metade: ele abre um servidor e espera. Quem conversa
rem com ele e' um PLUGIN que roda DENTRO do Roblox Studio. Sem o plugin, o
rem servidor fica no ar falando sozinho, o botao Connect nao existe em lugar
rem nenhum, e o sintoma e' "o Rojo nao conecta" -- sem uma linha de erro que
rem aponte pra ca'.
rem
rem O 1-INSTALACAO.bat ja' instala. A conferencia se repete aqui porque o plugin
rem some com mais frequencia do que parece: reinstalacao do Studio, limpeza de
rem disco e antivirus levam a pasta de plugins junto.

call :garantir_plugin

rem ---------- 2b. matar o Rojo da sessao anterior ----------
rem
rem ESTE E' O MOTIVO NUMERO 1 DE "O ROJO NAO CONECTA", E O KIT MESMO CRIAVA A
rem SITUACAO.
rem
rem So' pode existir UM programa escutando a porta 34872. Sobrando um `rojo
rem serve` de antes, o novo morre no primeiro segundo com "os error 10048" numa
rem janela que ninguem esta' olhando -- e o VELHO continua no ar. O Studio
rem conecta nele sem erro nenhum e sincroniza a pasta da OUTRA sessao: voce
rem edita um arquivo aqui, o Studio nao muda, e o Rojo esta' verde, conectado,
rem no lugar errado.
rem
rem A limpeza antiga tinha um BURACO, e ele era demonstravel: matar a janela
rem pelo titulo (`taskkill /FI "WINDOWTITLE ..."`) mata o cmd.exe e NAO mata o
rem rojo.exe que roda dentro dele. O rojo ficava orfao, sem janela nenhuma na
rem tela, ainda segurando a porta 34872 -- invisivel na barra de tarefas e
rem impossivel de fechar "fechando as janelas pretas", que e' o que o manual
rem manda fazer.
rem
rem Agora sao tres redes, nesta ordem, e a terceira e' a que faltava:
rem   1. mata quem estiver escutando a porta, pelo PID;
rem   2. mata a janela COM a arvore de processos dela (/T);
rem   3. mata qualquer rojo.exe que tenha sobrado orfao (/IM).
rem E so' depois disso espera a porta ficar LIVRE de verdade.

echo   Limpando o Rojo de sessoes anteriores...

rem `:34872` e nao `127.0.0.1:34872`: um rojo subido com outro endereco (ou em
rem IPv6, que aparece como [::1]:34872) tambem segura a porta, e o filtro antigo
rem passava direto por ele.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":34872"') do taskkill /PID %%p /T /F >nul 2>&1

rem O /T e' o que estava faltando: sem ele so' o cmd.exe morre e o rojo.exe
rem continua vivo, segurando a porta.
taskkill /FI "WINDOWTITLE eq 0 - Rojo*" /T /F >nul 2>&1

rem A rede final. Vale so' pra este kit: se voce usa o Rojo em OUTRO projeto ao
rem mesmo tempo, ele fecha aquele tambem -- de proposito, porque dois rojos na
rem mesma porta e' exatamente o defeito que esta linha existe pra apagar.
taskkill /IM rojo.exe /F >nul 2>&1

rem ---------- 2c. esperar a porta ficar LIVRE ----------
rem
rem Matar um processo nao devolve a porta no mesmo instante -- o Windows leva
rem uns segundos pra soltar o socket. Subindo em cima disso, o rojo novo morre
rem com 10048 e a janela fecha antes de dar pra ler. Este laco troca a corrida
rem por uma espera curta e previsivel.

set "ESPERA=0"

:esperar_porta_livre
netstat -ano | findstr "LISTENING" | findstr ":34872" >nul 2>&1
if errorlevel 1 goto porta_livre
set /a ESPERA+=1
if %ESPERA% geq 8 goto porta_livre
timeout /t 1 /nobreak >nul
goto esperar_porta_livre

:porta_livre

rem ---------- 2d. subir e CONFERIR DE VERDADE ----------
rem
rem O projeto vai por caminho completo, e nao "a pasta atual": assim o servidor
rem nunca sobe apontando pro lugar errado, mesmo que alguem chame este .bat de
rem outra pasta.
rem
rem ---------- O ENDERECO: E' AQUI QUE O "ROJO NAO CONECTA" NASCIA ----------
rem
rem O plugin do Rojo dentro do Studio procura por "localhost". O rojo.exe
rem tambem diz que sobe em "localhost". Parece o mesmo lugar, e nao e':
rem
rem   o rojo.exe resolve "localhost" preferindo IPv4  -> escuta em 127.0.0.1
rem   o Windows/Studio resolve "localhost" pelo IPv6  -> procura em [::1]
rem
rem Os dois estao certos, cada um pela sua regra, e o resultado e' o pior tipo
rem de defeito: o servidor esta' NO AR, a porta responde, o netstat mostra
rem LISTENING, o kit diz "Rojo no ar" -- e o Connect do plugin falha com um
rem erro de conexao que nao menciona IPv6 em lugar nenhum.
rem
rem A versao anterior deste arquivo ja' conhecia o problema, e a solucao era
rem uma FRASE NA TELA pedindo pra trocar "localhost" por "127.0.0.1" na mao,
rem dentro do plugin. Quem le' a janela preta ate' o fim resolve; todo mundo
rem clica em Connect, ve' falhar, e reclama que "o Rojo nao conecta".
rem
rem Agora o kit PERGUNTA pro proprio Windows pra onde "localhost" aponta nesta
rem maquina, e sobe o Rojo exatamente la'. O plugin conecta com o valor de
rem fabrica dele, sem ninguem digitar nada.
rem
rem O `ping` e nao o PowerShell de proposito: ele existe em qualquer Windows e
rem nao depende de politica de execucao de script (que em PC de escola e de
rem empresa vem travada). A saida dele e' traduzida, mas o "[::1]" e' igual em
rem todo idioma.

set "ROJO_ADDR=127.0.0.1"
set "ROJO_HOST=127.0.0.1"
ping -n 1 localhost 2>nul | findstr /c:"[::1]" >nul
if errorlevel 1 goto endereco_escolhido
set "ROJO_ADDR=::1"
set "ROJO_HOST=[::1]"

:endereco_escolhido
echo   Nesta maquina "localhost" aponta pra %ROJO_ADDR% -- subindo o Rojo ali.

:subir_rojo
start "0 - Rojo (so' pra editar o codigo)" /D "%PROJETO%" cmd /k ""%ROJO%" serve "%PROJETO%\default.project.json" --address %ROJO_ADDR% --port 34872"

echo   Esperando o Rojo atender na porta 34872...
set "TENTATIVAS=0"

:esperar_rojo
rem PERGUNTA DE VERDADE pro servidor, em vez de so' olhar o netstat.
rem
rem "A porta esta' escutando" e "o Rojo esta' pronto pra conectar" nao sao a
rem mesma coisa, e a diferenca aparecia no pior momento: com um rojo orfao
rem segurando a porta, o netstat dizia LISTENING, este .bat dizia "Rojo no ar",
rem e o Studio conectava no servidor errado. Perguntando pelo /api/rojo, quem
rem responde e' o servidor deste projeto ou ninguem.
call :perguntar_ao_rojo
if "%ROJO_OK%"=="1" goto rojo_no_ar
set /a TENTATIVAS+=1
if %TENTATIVAS% geq 12 goto rojo_mudo
timeout /t 1 /nobreak >nul
goto esperar_rojo

:rojo_mudo
rem Escolhemos o IPv6 e ele nao atendeu? Antes de desistir, tenta o IPv4.
rem
rem A deteccao acima acerta na esmagadora maioria das maquinas, mas "o Windows
rem resolve localhost pelo IPv6" e "o rojo.exe CONSEGUE escutar em IPv6" sao
rem duas coisas diferentes -- uma pilha IPv6 desligada por politica derruba a
rem segunda sem mexer na primeira. Cair de volta no IPv4 custa 12 segundos e
rem cobre esse caso; sem isso, trocariamos um defeito por outro.
if not "%ROJO_ADDR%"=="::1" goto rojo_mudo_de_vez
echo   O IPv6 nao atendeu -- tentando de novo em 127.0.0.1...
taskkill /FI "WINDOWTITLE eq 0 - Rojo*" /F >nul 2>&1
set "ROJO_ADDR=127.0.0.1"
set "ROJO_HOST=127.0.0.1"
goto subir_rojo

:rojo_mudo_de_vez
echo.
echo   ============================================================
echo    O ROJO NAO SUBIU
echo   ============================================================
echo.
echo    A porta 34872 nao respondeu em 12 segundos. A mensagem esta'
echo    na janela "0 - Rojo", que abriu junto com esta.
echo.
echo    ISTO NAO IMPEDE A SUA LIVE: o jogo ja' foi montado com todo o
echo    codigo e o mapa dentro. O Rojo so' serve pra EDITAR o codigo
echo    com o jogo aberto.
echo.
echo    O que costuma ser:
echo      - antivirus segurando o rojo.exe;
echo      - outro programa usando a porta 34872.
echo.
goto abrir_studio

:rojo_no_ar
echo   Rojo no ar e respondendo (%ROJO_HOST% : 34872).
echo.
echo   Pra EDITAR o codigo com o jogo aberto (opcional):
echo     aba PLUGINS ^> Rojo ^> Connect
echo.
echo   Pode deixar o que vier preenchido: o Rojo subiu no mesmo endereco
echo   que o plugin procura. Se por acaso o campo estiver em branco,
echo   Address: %ROJO_ADDR%     Port: 34872
echo.
goto abrir_studio

:sem_rojo
echo.
echo   ============================================================
echo    O ROJO NAO ESTA DISPONIVEL
echo   ============================================================
echo.
echo    Procurei em dois lugares e nao achei um rojo.exe que EXECUTE:
echo      1^) %~dp0ferramentas\rojo.exe
echo      2^) qualquer rojo.exe no PATH do Windows
echo.
echo    Se o arquivo existe na pasta mas nao roda, e' antivirus --
echo    restaure ele da quarentena e marque como permitido.
echo    Se nao existe, rode o 1-INSTALACAO.bat.
echo.
echo    ISTO NAO IMPEDE A SUA LIVE: o JOGO-DA-LIVE.rbxlx ja' vem com
echo    todo o codigo e o mapa dentro. So' nao vou conseguir remontar
echo    o arquivo com mudancas que voce tenha feito no codigo.
echo.
echo    Rode o 5-VERIFICAR.bat pra um diagnostico completo.
echo.

:abrir_studio

if not exist "%JOGO%" (
    echo.
    echo   ERRO: nao achei o JOGO-DA-LIVE.rbxlx
    echo.
    echo   Ele e' montado pelo Rojo, que vem no 1-INSTALACAO.bat.
    echo   Rode o 1-INSTALACAO.bat primeiro.
    echo.
    pause
    exit /b 1
)

rem ============================================================
rem  3. O ROBLOX STUDIO
rem ============================================================

rem Procura o Studio. A pasta tem o numero da versao no nome, que muda a cada
rem atualizacao da Roblox -- por isso a busca, em vez de um caminho fixo.
rem O ultimo que o `for` achar vence: e' o mais recente na ordem do `dir`.
set "STUDIO="
for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO=%%f"

if not defined STUDIO (
    for /f "delims=" %%f in ('dir /b /s "%ProgramFiles(x86)%\Roblox\Versions\RobloxStudioBeta.exe" 2^>nul') do set "STUDIO=%%f"
)

if not defined STUDIO (
    echo.
    echo   ============================================================
    echo    NAO ACHEI O ROBLOX STUDIO NESTE COMPUTADOR
    echo   ============================================================
    echo.
    echo    Instale o Roblox Studio primeiro:
    echo      https://create.roblox.com/
    echo.
    echo    Se ele ja' estiver instalado, abra o Studio na mao e use:
    echo      File ^> Open from File...
    echo    e escolha este arquivo:
    echo      %JOGO%
    echo.
    pause
    exit /b 1
)

rem ---------- ja' tem um Studio aberto? ----------
rem
rem Sem esta conferencia, cada partida abre MAIS UM Roblox Studio. Dois
rem rodando ao mesmo tempo e' pior do que parece: os dois disputam memoria, e
rem -- o que realmente estraga a live -- o Studio ERRADO pode estar em Play,
rem com outro codigo dentro, batendo no mesmo servidor local. Voce aperta Play
rem numa janela e olha a outra.

rem findstr, e NAO find. O `find` do Windows tem um xara do mundo Unix, e quem
rem tem Git, MSYS ou WSL instalado costuma ter esse outro na frente no PATH.
rem Quando isso acontece, o `/I` e' lido como nome de arquivo, o comando falha,
rem e a conferencia inteira passa batido: o script conclui que nao ha' Studio
rem aberto e abre um SEGUNDO. O `findstr` nao tem esse problema -- ele so'
rem existe no Windows.
tasklist /FI "IMAGENAME eq RobloxStudioBeta.exe" 2>nul | findstr /I /C:"RobloxStudioBeta.exe" >nul
if not errorlevel 1 (
    echo.
    echo   ============================================================
    echo    FECHE O ROBLOX STUDIO E RODE ISTO DE NOVO
    echo   ============================================================
    echo.
    echo    Ja' existe um Studio aberto, e nao vou abrir um segundo:
    echo    dois ao mesmo tempo disputam memoria, e voce corre o risco
    echo    de apertar Play na janela errada.
    echo.
    echo    ATENCAO -- ISTO VALE MESMO QUE ELE JA' ESTEJA COM O
    echo    JOGO-DA-LIVE ABERTO:
    echo.
    echo    O Studio carrega o codigo do jogo UMA VEZ, na hora em que
    echo    abre o arquivo. Apertar Play de novo NAO recarrega nada.
    echo    Como o arquivo do jogo e' remontado a cada partida, um
    echo    Studio que ja' estava aberto continua rodando a versao
    echo    ANTIGA -- e voce jura que mexeu no codigo e nada mudou.
    echo.
    echo    Feche o Roblox Studio INTEIRO e rode este 3-ABRIR-JOGO.bat
    echo    outra vez.
    echo.
    pause
    exit /b 0
)

echo.
echo   Abrindo o jogo no Roblox Studio...
echo   ^(pode levar de 10 a 40 segundos^)
echo.

start "" "%STUDIO%" "%JOGO%"

echo   ============================================================
echo    QUANDO O STUDIO ABRIR: APERTE PLAY
echo   ============================================================
echo.
echo    O botao PLAY e' o triangulo azul no topo da tela.
echo.
echo    O mapa ja' aparece antes do Play: palco, telao e arquibancada.
echo    Os bonecos comecam a chegar alguns segundos depois do Play.
echo.
timeout /t 8 /nobreak >nul
exit /b 0


rem ============================================================
rem  SUB-ROTINAS
rem ============================================================

:garantir_plugin
rem
rem REINSTALA SEMPRE, e nao so' quando o arquivo falta.
rem
rem O plugin e o rojo.exe conversam por um protocolo com numero de versao. Um
rem plugin de OUTRA versao -- o da Creator Store, o que sobrou de um projeto de
rem meses atras, o de um kit antigo -- e' um dos motivos de "aperto Connect e
rem nao acontece nada": ele conecta e recusa por versao incompativel, e a
rem mensagem aparece dentro do Studio, num painel que ninguem esta' olhando.
rem
rem Regravar o arquivo custa um piscar e garante que o plugin e' EXATAMENTE o
rem par do rojo.exe que vem nesta pasta. O Studio so' le' plugin ao iniciar,
rem entao regravar com ele aberto nao atrapalha nada -- vale na proxima vez.

set "PLUGIN_FALTAVA="
if not exist "%PLUGIN%" set "PLUGIN_FALTAVA=1"

"%ROJO%" plugin install >nul

if not exist "%PLUGIN%" (
    echo   AVISO: nao consegui instalar o plugin do Rojo.
    echo   Sem ele o botao Connect nao aparece no Studio. A live
    echo   funciona assim mesmo; so' a edicao ao vivo do codigo nao.
    exit /b 0
)

if defined PLUGIN_FALTAVA (
    echo   Plugin do Rojo instalado agora. Se o Studio ja' estiver ABERTO,
    echo   feche e abra de novo -- ele so' carrega plugin novo ao iniciar.
) else (
    echo   Plugin do Rojo: conferido.
)
exit /b 0


:perguntar_ao_rojo
rem
rem PERGUNTA DE VERDADE, em vez de so' olhar o netstat.
rem
rem "A porta esta' escutando" e "o Rojo deste projeto esta' pronto" nao sao a
rem mesma coisa. Com um rojo orfao de outra pasta segurando a 34872, o netstat
rem dizia LISTENING, o kit dizia "Rojo no ar", e o Studio conectava no servidor
rem errado -- sincronizando outro projeto, sem erro nenhum na tela. O /api/rojo
rem so' responde se quem estiver ali for um servidor Rojo de verdade.
rem
rem curl.exe primeiro porque ele vem no Windows 10/11 e responde em
rem milissegundos; o PowerShell e' a reserva pra Windows mais antigo, e leva
rem quase um segundo so' pra abrir.

set "ROJO_OK="
where curl.exe >nul 2>&1
if errorlevel 1 goto perguntar_com_powershell

rem O endereco vem do %ROJO_HOST% (127.0.0.1 ou [::1], escolhido la' em cima).
rem Perguntar sempre no IPv4 era outra forma do mesmo engano: o kit aprovava um
rem servidor que o Studio nao alcancava.
curl.exe -s -o nul -m 3 "http://%ROJO_HOST%:34872/api/rojo" 2>nul
if errorlevel 1 exit /b 0
set "ROJO_OK=1"
exit /b 0

:perguntar_com_powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$null=Invoke-WebRequest -Uri 'http://%ROJO_HOST%:34872/api/rojo' -UseBasicParsing -TimeoutSec 3;exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 exit /b 0
set "ROJO_OK=1"
exit /b 0
