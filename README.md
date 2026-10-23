# LiveBridge Local

Sistema local independente para ligar TikTok LIVE -> Python -> Roblox Studio.

## 1. Instalar

Execute `instalar.bat`.

## 2. Configurar TikTok

Abra `config/config.json` e coloque o @ da conta em `tiktok.username`.

## 3. Testar sem TikTok

Execute `testar.bat`.
Depois abra:

`http://127.0.0.1:5000/test?user=JogadorTeste&gift=rose`

O servidor deve responder `ok: true`.

## 4. Roblox Studio

1. Abra seu jogo.
2. Em Game Settings -> Security, habilite `Allow HTTP Requests`.
3. Crie um Script dentro de `ServerScriptService`.
4. Cole o conteúdo de `roblox/LiveBridge.server.lua`.
5. Rode o jogo no Studio.
6. Deixe `iniciar-servidor.bat` aberto.

O Script consulta `http://127.0.0.1:5000/eventos` e cria os avatares/eventos.

## 5. Live real

Depois do teste, execute `iniciar-live.bat`.

Para associar uma pessoa do TikTok a um avatar Roblox, ela pode comentar:

`!roblox SeuNomeRoblox`

O sistema procura o usuário Roblox e guarda a associação durante a execução.
Depois os presentes daquela pessoa usam esse avatar.

## Arquitetura

TikTok LIVE -> TikTokLive -> tiktok_bridge.py -> server.py -> HttpService -> Roblox Studio.

Não há servidor de licença, chave de ativação ou dependência de licença.
