# Live Interativa Monster — TikTok + Roblox

*O espectador comenta o nick dele e se vê dançando no Roblox, com a skin real.*

Leia esta página inteira uma vez antes de começar. São uns 10 minutos de
instalação, e depois é só clicar num arquivo pra abrir a live.

---

## O que você vai precisar

- **Windows** (10 ou 11)
- **Roblox Studio** instalado
- Uma conta de **TikTok que possa fazer live**
- Internet

Não precisa saber programar. Não precisa publicar jogo nenhum na Roblox.

---

## Antes de tudo: extraia o ZIP

Se você recebeu o kit em `.zip`, **extraia antes de clicar em qualquer coisa**:
botão direito no arquivo → **Extrair Tudo…**

Isso não é detalhe. O Windows deixa você abrir o ZIP e ver os arquivos lá
dentro, mas quando você dá dois cliques num `.bat` **de dentro do ZIP**, ele
copia só aquele arquivo pra uma pasta temporária e roda de lá — sem o resto do
kit junto. O sintoma é a mensagem **"O KIT ESTÁ INCOMPLETO"**, e ela não tem
nada a ver com o download ter vindo quebrado.

A pasta certa é a que tem o `1-INSTALACAO.bat` **e** as pastas `servidor`, `ponte` e
`roblox` juntos.

---

## Passo 1 — Instale o que falta

Dê **dois cliques em `1-INSTALACAO.bat`**.

Vai abrir uma janela preta com texto correndo. É normal — é o computador
baixando o que o kit usa:

- **Python** — lê o chat da sua live. Se ele não estiver no computador, o
  `1-INSTALACAO.bat` **baixa e instala sozinho**, do site oficial (python.org).
  Ele pergunta antes, e a barrinha de progresso do Python aparece numa janela
  própria — deixe terminar.
- **Rojo** — leva o jogo pra dentro do Roblox Studio *(opcional: serve só pra
  quem for editar o código; o `JOGO-DA-LIVE.rbxlx` já vem pronto na pasta)*

Pode levar alguns minutos. Se o Windows perguntar se pode instalar, aceite.

> **Se o download automático do Python não der certo** (internet caindo,
> antivírus bloqueando, rede de escola/empresa), o próprio instalador te mostra
> o passo manual: baixe em
> [python.org/downloads](https://www.python.org/downloads/), **marque a
> caixinha "Add python.exe to PATH"** na primeira tela, e depois **feche a
> janela preta e rode o `1-INSTALACAO.bat` de novo**.
>
> Fechar e reabrir não é frescura: o Windows só mostra um programa
> recém-instalado pras janelas abertas *depois* da instalação.

O kit precisa do **Python 3.10 ou mais novo**. Se você já tem um mais velho, o
`1-INSTALACAO.bat` avisa e instala uma versão nova do lado, sem mexer na antiga.

---

## Passo 2 — Teste antes de ir ao vivo

**Não abra live pra testar.** Dê dois cliques em **`4-MODO-TESTE.bat`**.

Ele inventa comentários e presentes, e você vê tudo funcionando sem ninguém
assistindo. É a melhor hora pra deixar o painel do seu jeito.

Vão abrir umas janelas pretas e o painel no navegador. O **Roblox Studio abre
sozinho**, com o jogo dentro — você não precisa procurar arquivo nenhum.

Quando ele abrir, aperte **Play** (o botão ▶ azul no topo).

Em poucos segundos os bonecos começam a aparecer sozinhos.

> **Não abra o `JOGO-DA-LIVE.rbxlx` com dois cliques.** Em muitos Windows a
> extensão `.rbxlx` não está associada ao Studio, e dois cliques não fazem
> absolutamente nada — sem erro, sem janela, sem nada. Use sempre o
> **`3-ABRIR-JOGO.bat`**: ele encontra o Studio e chama ele direto, com ou sem
> associação.

> ### Se já tiver outro lugar aberto no Studio, feche antes
>
> Um lugar aberto com **outro código dentro** briga com este, e o sintoma é
> exatamente "não acontece nada". Feche o Studio inteiro e abra pelo
> `3-ABRIR-JOGO.bat`.

O arquivo `JOGO-DA-LIVE.rbxlx` já vem com **todo o código dentro**, e é refeito
toda vez que você roda o `2-COMECAR-LIVE.bat` ou o `4-MODO-TESTE.bat`. Você não precisa
conectar nada nem criar lugar nenhum.

---

## Quer usar o SEU lugar em vez do arquivo pronto?

Se você já tem um lugar salvo na Roblox e quer o código lá dentro, use o
**Rojo** — ele sincroniza o código pro lugar que estiver aberto no Studio.

1. Rode o `1-INSTALACAO.bat` (ele instala o plugin do Rojo no Studio). No fim ele
   **sobe o Rojo de verdade e confere se ele responde** — se aparecer
   "Rojo conectou", essa parte já está resolvida antes de você precisar dela.
2. **Feche e abra o Roblox Studio.** Isso não é opcional: o Studio só carrega
   plugin novo quando inicia. Com ele aberto, o plugin não aparece.
3. Rode o `2-COMECAR-LIVE.bat` ou o `4-MODO-TESTE.bat` — a janela `0 - Rojo` sobe junto
4. No Studio, abra o seu lugar
5. Aba **Plugins** → botão **Rojo** → **Connect**
6. Aperte **Play**

> ### Se o Connect falhar, troque `localhost` por `127.0.0.1`
>
> É o primeiro a tentar, e resolve a maioria dos casos. O plugin costuma vir
> com **Address: localhost**, e em algumas máquinas o Windows resolve
> `localhost` primeiro pelo **IPv6** (`::1`) enquanto o Rojo escuta em IPv4.
> São o mesmo computador, mas por caminhos diferentes — e a mensagem de erro
> não fala nada disso.
>
> Os valores certos aparecem escritos na janela do `3-ABRIR-JOGO.bat` toda vez
> que ele sobe:
>
> ```
> Address: 127.0.0.1     Port: 34872
> ```

> ### O erro que come horas
>
> `rojo serve` é **metade** da coisa. Ele abre um servidor e fica esperando.
> Quem conversa com ele é um **plugin dentro do Studio**. Sem o plugin
> instalado, o servidor fica no ar falando sozinho, o botão Connect não existe
> em lugar nenhum, e o sintoma é "não acontece nada" — sem uma linha de erro
> que aponte pra causa.
>
> Confira se ele está lá: deve existir o arquivo
> `RojoManagedPlugin.rbxm` em `%LOCALAPPDATA%\Roblox\Plugins\`.

**Se o seu lugar já tem código de outro projeto dentro**, apague antes:
`ServerScriptService`, `ReplicatedStorage` e `StarterPlayer > StarterPlayerScripts`.
Dois projetos no mesmo lugar brigam, e o sintoma é o jogo pedindo endereços
que este servidor não conhece.

---

## Passo 3 — A live de verdade

Dê dois cliques em **`2-COMECAR-LIVE.bat`** e digite o seu @ do TikTok.

Depois é o mesmo do teste: o Studio abre sozinho, e você aperte **Play**.

> ### O jogo TEM que rodar no Studio, em modo Play
>
> O jogo **publicado** na Roblox roda na nuvem deles e **não enxerga o seu PC** —
> com ele, nada aparece, e não existe configuração que resolva. No Studio em modo
> Play o servidor do jogo roda na sua máquina, e é por isso que funciona.

---

## As janelas que ficam abertas

Cada uma tem um número no título. **Não feche nenhuma** enquanto estiver ao vivo:

| Janela | O que é | Se fechar |
|---|---|---|
| `1 - SERVIDOR DA LIVE` | o coração do kit | nada mais aparece no jogo |
| `2 - PONTE DO TIKTOK` | lê o chat da sua live | os eventos param de chegar |
| `0 - Rojo` | só serve pra **editar o código** | nada, se você não edita |

---

## O painel de controle

Abre sozinho em **http://localhost:8000/painel**.

É lá que você ajusta tudo **durante a live**, sem reiniciar nada. Salvou, vale em
até 5 segundos.

No alto do painel tem o diagnóstico. Ele responde a pergunta mais importante
quando algo dá errado — **de que lado está o problema?**

- 🟢 verde = falou agora
- 🟡 amarelo = está demorando
- 🔴 vermelho = não está falando

---

## Overlays pro OBS

Ponha como **Fonte de Navegador** no OBS:

```
http://localhost:8000/placar.html?tipo=moedas
http://localhost:8000/placar.html?tipo=curtidas
http://localhost:8000/placar.html?tipo=presenca
```

Use **localhost**, nunca `127.0.0.1` — o navegador de dentro do OBS trata os dois
como coisas diferentes, e metade dos casos de "a fonte fica preta" é isso.

O fundo já é transparente: o quadro flutua por cima do gameplay.

---

## Comandos de teste no chat

Digite no chat da **sua** live pra disparar o efeito sem gastar moeda:

| Comando | O que faz |
|---|---|
| `!teste` | presente barato |
| `!medio` | presente médio, segura a câmera |
| `!grande` | presente grande |
| `!enorme` | derruba a formação inteira |
| `!lenda` | chuva de avatares por 30 segundos |

Só funcionam **pra você**. Isso é de propósito: o comando faz de graça
exatamente o que o presente faz pago — se qualquer um pudesse usar, ninguém
mandaria presente.

Na primeira vez, comente seu nick do Roblox antes. Ou mande junto:
`!lenda SeuNickDoRoblox`

---

## Cada presente tem a sua dança

Quem só comenta entra na dança padrão. Quem manda presente entra **dançando
outro passo**, e é isso que faz o presente aparecer no vídeo:

| Presente | Dança | Aura |
|---|---|---|
| 🌹 Rosa | a padrão | contorno leve |
| 🍩 Rosquinha | própria | contorno médio |
| 🕶️ Óculos | própria | contorno forte |
| 🌌 Galáxia | própria | contorno cheio |

Ninguém precisa ler o nome do presente na tela — e ninguém lê, num vídeo de
celular. O que se vê de longe é **o passo mudar** no meio da formação.

A aura é **o contorno do próprio corpo** — braço, cabelo, chapéu, acessório —
na cor do presente. Não é luz, não pinta o chão e não vaza pros vizinhos: ela
para exatamente onde o boneco para. O que muda entre um presente e outro é só
o quanto a linha fecha.

Vale também pra presente que você nunca cadastrou: a dança acompanha a **faixa
de preço**, então um presente novo do TikTok, ou o mesmo presente com outro nome
na sua região, já entra dançando o passo da faixa dele.

Pra trocar qual dança é qual: **painel → aba Danças**. A tabela de cima lista
os presentes cadastrados com a figura de cada um, e você escolhe o passo ali
mesmo, sem abrir a ficha. Vale em até 5 segundos, sem reiniciar nada.

São oito passos pra escolher: Moonwalk, Gangnam Style, Macarena, Festa, Disco,
Solto, Passinho e Swing. Os cinco últimos são animações da **própria Roblox** —
funcionam sempre, sem depender da permissão de criador nenhum. O botão **Ver
como cada dança fica** põe um avatar de teste no jogo dançando o passo, agora,
pra você escolher olhando em vez de adivinhando.

Na mesma aba ficam as duas danças que não pertencem a presente nenhum:

- **Dança padrão** — o passo de quem só comentou o nick. É o que a maior parte
  da formação dança quase o tempo todo, e agora dá pra trocar sem mexer em
  arquivo nenhum.
- **Dança especial** — pra onde a formação **inteira** troca quando chega um
  presente com "troca a dança de todos", e de onde ela volta sozinha depois.

> A **aura** é só de quem mandou presente, e isso é regra: se todo mundo
> brilhasse, o brilho não separaria mais quem pagou de quem não pagou.

---

## Como funciona, em quatro linhas

1. A ponte lê o chat da sua live e procura nicks de Roblox nos comentários
2. O nick vira um UserId, e o avatar **real** daquela pessoa é carregado
3. O espectador se vê dançando na tela
4. Ele comenta de novo, chama amigo, e a live cresce

---

## Deu erro? Procure aqui

### Nada aparece no jogo

Olhe o **diagnóstico no alto do painel**. Ele diz de que lado está o problema,
e isso corta o tempo de busca pela metade:

- **"Roblox Studio: não conectou"** → o jogo não está falando com o servidor.
  Quase sempre é um **lugar errado aberto no Studio**. Feche o Studio inteiro e
  abra pelo `3-ABRIR-JOGO.bat`. Confira também se você apertou **Play**.
- **"Ponte do TikTok: nunca falou"** → a ponte não está entregando. Veja a
  janela `2 - PONTE DO TIKTOK`: o erro de verdade está escrito lá.
- **Os dois verdes e mesmo assim nada** → você está no jogo **publicado** em vez
  do Studio em modo Play. O publicado roda na nuvem da Roblox e não alcança o
  seu PC.

> **Como saber se é o lugar errado:** se o Studio estiver com outro projeto
> aberto, ele fica pedindo endereços que este servidor não conhece, e o
> diagnóstico nunca sai de "não conectou" por mais que você aperte Play.

### Quem vira boneco — e quem não vira

**Só o chat faz alguém aparecer.** Duas coisas, e mais nenhuma:

1. **comentar o próprio nick do Roblox**;
2. **mandar presente** — depois de já ter comentado o nick uma vez (antes disso
   o presente fica guardado esperando o nick chegar).

**Curtida, seguir e compartilhar NÃO fazem boneco nascer.** Elas vêm
**desligadas de fábrica**, e isso é decisão de produto, não esquecimento:
curtida é o evento mais frequente de uma live — uma pessoa segura o coração e
manda dezenas por segundo. Com elas ligadas, bastava alguém ter comentado o
nick uma vez para a formação ir enchendo sozinha, com o chat parado. Quem está
transmitindo vê bonecos surgindo do nada e não tem como descobrir de onde vêm,
porque curtida não aparece no chat.

E tem o motivo maior: se o boneco aparece de qualquer jeito, o pedido no
microfone — *"comenta o seu nick que você aparece na tela"* — deixa de ser
verdade. É esse pedido que faz a live crescer.

Elas continuam no painel, com os números prontos: **painel → Ações → Curtida /
Seguiu / Compartilhou → ligar**. Aí é escolha sua, e não surpresa no meio da
primeira live.

### O painel diz que não encontrou o usuário do TikTok

**Na maioria das vezes o @ está certo e o problema é outro.** Esse recado tem
três causas diferentes, e o painel agora sabe separá-las — leia a frase inteira
que aparece na caixa **Live do TikTok**:

| O que o painel diz | O que é |
|---|---|
| `o @ … não existe no TikTok — confira a digitação` | Aí sim é o @. O kit **perguntou** ao TikTok pelo perfil e recebeu um "não existe" de verdade. |
| `o TikTok recusou a consulta desta conta agora` | O @ existe. O TikTok bloqueou a pergunta (captcha, limite de uso, IP). A ponte segue tentando sozinha, com espera crescente. Não feche nada. |
| `não consegui confirmar o @ com o TikTok` | Nem a pergunta chegou lá — internet, ou o TikTok fora do ar. Também tenta de novo sozinho. |

> **Por que isso mudou.** A biblioteca que fala com o TikTok devolve o mesmo
> erro para as três situações, e o kit repassava sempre a mesma frase:
> "usuário não encontrado — confira o @". Como a causa mais comum das três é o
> **bloqueio temporário**, o recado mandava conferir justamente a única coisa
> que estava certa. Agora o kit confirma no perfil público antes de acusar a
> sua digitação.

Duas coisas que ajudam:

- **Pode colar o link do perfil inteiro** no campo Conta
  (`tiktok.com/@seu_arroba`) — o kit tira o @ de dentro dele. Link **curto**
  (`vm.tiktok.com/…`) não serve: ele não carrega o @ dentro.
- **O campo já vem preenchido** com a conta da última live. Não precisa digitar
  de novo — e não digitar de novo é o que evita o erro de digitação.

### Minha live está tomando restrição

O jogo não escreve **nada** na tela: o cenário não tem uma letra sequer, e isso
é decisão de projeto, não esquecimento. Texto pedindo interação dentro do
quadro (`COMENTE SEU NICK`, lista de presentes com preço) é lido pela
plataforma como isca de engajamento e solicitação de presente — a live perde
alcance e chega a ser derrubada no meio.

Se você quiser a chamada na tela, **ponha no overlay do OBS**, fora do jogo: lá
dá para ligar e desligar na hora, sem regerar o mapa nem reabrir o Studio.

### O chat anda mas ninguém aparece

Normal. Só vira avatar quem comenta o **próprio nick do Roblox**. "oi", "kkkk" e
"salve" não viram nada, de propósito.

A janela da ponte avisa isso a cada 30 segundos, dizendo quantos comentários
foram ignorados.

### O Rojo não conecta

Vá pela ordem — a primeira linha resolve a maioria dos casos:

1. **Troque `localhost` por `127.0.0.1`** no campo Address do plugin. Porta
   `34872`.
2. **Feche e abra o Studio.** Ele só carrega plugin quando inicia — se o
   `1-INSTALACAO.bat` acabou de rodar, o plugin ainda não está lá dentro.
3. **Rode o `3-ABRIR-JOGO.bat` e leia a janela dele.** Ele diz, com todas as
   letras, se o Rojo subiu e respondeu (`Rojo no ar e respondendo`) ou não.
4. Se ele disser que **não subiu**, a mensagem de verdade está na janela
   `0 - Rojo`.

> **Fechar a janela `0 - Rojo` no X nem sempre fechava o Rojo.** O programa
> ficava rodando sem janela nenhuma, segurando a porta 34872 — e a sessão
> seguinte não conseguia subir o dele. Isso está corrigido: o kit agora derruba
> o Rojo antigo (inclusive o invisível) e **espera a porta ficar livre** antes
> de subir o novo. Se você ainda tiver um preso de uma versão anterior,
> reiniciar o PC resolve de uma vez.

### Os nomes em cima da cabeça

Eles **somem quando a câmera está longe**, e isso é de propósito: cem balões
desenhados juntos viram uma parede preta onde não se lê nenhum — nem o de quem
a câmera está seguindo. No plano aberto do fim do ciclo eles somem todos, para
não tapar a multidão.

Na prática aparecem os **12 mais perto da câmera**, que numa formação que
cresce para a frente são sempre os que acabaram de chegar. Para mudar:
`Config.luau` → `ROTULO.MAX_NA_TELA` e `ROTULO.DISTANCIA_MAX`.

### `A PORTA 8000 JA ESTA OCUPADA`

Sobrou uma janela de uma sessão anterior. Feche todas as janelas pretas e rode o
`2-COMECAR-LIVE.bat` de novo. Se não achar as janelas, reiniciar o PC resolve.

### A tela fica cinza, sem chão nem bonecos

Em `Workspace`, a opção **StreamingEnabled** precisa estar **desligada**. O kit
já vem assim, mas se você mexeu num lugar existente, confira.

### `O KIT ESTA INCOMPLETO`

Quase sempre você clicou no `.bat` **de dentro do ZIP**, sem extrair. Extraia o
ZIP inteiro (botão direito → **Extrair Tudo…**) e rode da pasta que aparecer.
A própria mensagem na janela preta diz qual dos dois casos é o seu.

Se o ZIP **foi** extraído inteiro e a mensagem continua, é antivírus: ele
apagou algum arquivo e avisou numa notificação. Restaure da quarentena, ou
extraia de novo numa pasta fora do Desktop.

### `O PYTHON NAO FOI ENCONTRADO`

Rode o `1-INSTALACAO.bat` — ele baixa e instala o Python pra você.

Se já rodou, **feche todas as janelas pretas e abra de novo** — o Windows só
enxerga programas recém-instalados em janelas abertas *depois* da instalação.

> Cuidado com um detalhe do Windows: existe um `python.exe` **falso** que só
> abre a Microsoft Store. Ele não é o Python. O kit sabe distinguir os dois (ele
> manda o programa *executar código*, não só responder `--version`), então se a
> Store abrir sozinha, ignore: quem instala o Python aqui é o `1-INSTALACAO.bat`.

### `ESTE PYTHON E ANTIGO DEMAIS PRO KIT`

O kit precisa do **Python 3.10 ou mais novo** — é o que a biblioteca que lê o
chat do TikTok exige. Rode o `1-INSTALACAO.bat`: ele instala uma versão nova do
lado, sem mexer na antiga.

### A dança não toca

O jogo vem com animações **gratuitas da Roblox**, que funcionam sempre. Se você
trocou o ID no `roblox/src/ReplicatedStorage/Config.luau`, leia o comentário que
está lá: o ID do **emote do catálogo** não funciona — só o da **Animation** que
mora dentro dele. E animação de terceiro precisa da autorização do criador.

Na subida, o jogo **testa todas as danças** e escreve o resultado no Output do
Studio. Procure a linha `[avatares] dancas de presente prontas:` — o que não
estiver ali não carregou, e o aviso logo acima diz qual e por quê. Quem manda
esse presente continua aparecendo; só dança o passo padrão.

### Mudei o código e o jogo continua igual

O Studio roda o código que estava lá **quando você abriu o arquivo**. Apertar
Play de novo não recarrega nada.

Feche o **Roblox Studio inteiro** e abra pelo `3-ABRIR-JOGO.bat`. É o único jeito
de o jogo pegar código novo — e é a explicação de quase todo "mexi e não mudou".

### Todo mundo dança o mesmo passo

Confira no painel se o campo **Dança deste presente** não está em "Padrão".
Se estiver certo lá e mesmo assim não mudar, é o teste de subida acima: a
animação daquele presente não carregou e o jogo caiu no passo padrão de
propósito, pra não deixar o boneco parado em pé no meio da formação.

---

## Onde mexer em cada coisa

| Quero mudar | Arquivo |
|---|---|
| o que cada presente faz | o **painel**, no navegador |
| qual dança cada presente usa | o **painel** → aba **Danças** |
| a dança de quem só comenta | o **painel** → aba **Danças** |
| a câmera: close, suavidade, plano aberto | o **painel** → aba **Câmera e luz** |
| a live estar escura ou estourada | o **painel** → aba **Câmera e luz** (luz ambiente + exposição) |
| a câmera girar no presente caro | o **painel** → aba **Câmera e luz** (vem desligada) |
| o mapa (a pista, as luzes, as cores) | `ferramentas/gerar-cenario.py` — mexa e rode `python ferramentas/gerar-cenario.py` |
| quantos nomes aparecem na tela | `Config.luau` → `ROTULO.MAX_NA_TELA` |
| de que distância o nome some | `Config.luau` → `ROTULO.DISTANCIA_MAX` |
| os IDs das animações | `roblox/src/ReplicatedStorage/Config.luau` (`DANCAS`) |
| a força da aura | `roblox/src/ReplicatedStorage/Config.luau` (`BRILHO`) |
| formação e rótulo | `roblox/src/ReplicatedStorage/Config.luau` |
| os valores de fábrica dos presentes | `ponte/regras.py` |
| os comandos de chat | `ponte/ponte.py`, lá no alto |

> **Criou uma dança nova?** O nome dela precisa existir nos **dois** lados:
> em `DANCAS` (`Config.luau`, onde mora o ID) e em `DANCAS_VALIDAS`
> (`ponte/regras.py`, que barra nome errado). Só num lado, ela nunca é usada.
