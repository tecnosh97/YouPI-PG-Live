# A Loja — do PIX até a chave na mão do cliente

Documento de **venda**. Junta as duas peças do negócio, que moram em pastas
irmãs:

```
LiveBridge_Local_Corrigido\
    appnovo\            o programa (vai para o GitHub)
    YouPI-KEY\          o app KEY: a loja, o carrinho, o gerador de chaves
```

> **O gateway UPI não faz parte deste fluxo.** O `YouPI-PG-Gateway` (Node,
> UPI, dinheiro indiano) foi a primeira tentativa, e serve enquanto a sua
> clientela for brasileira — não serve. A pasta está lá, mas nada depende
> dela.

---

## O caminho inteiro, de ponta a ponta

```
  cliente paga no PIX
        │
        ▼
  o provedor confirma  →  chama o app KEY
        │  POST https://SEU-ENDERECO/webhook
        │  (assinatura HMAC conferida sobre o corpo cru)
        ▼
  o app KEY gera a chave → assina o manifesto → publica no GitHub
        │
        ▼
  o app do cliente busca o manifesto, confere a assinatura
  e decifra o conteúdo com (chave + ativação + mês)
        │
        ▼
  o extra aparece: as danças de presente e as cenas
```

A chave chega ao cliente **por WhatsApp ou e-mail**, mandada por você. O app
KEY não tem servidor de e-mail, e não precisa ter: a lista "Para entregar"
na janela do app KEY é a fila de trabalho.

---

## O que o app KEY faz

Ele é o **carrinho** e o **gerador de chave**, na mesma porta:

| Endereço | O que é |
|---|---|
| `GET /` | **a loja**. A página que o cliente abre. |
| `POST /pedido` | cria o pedido e devolve onde pagar |
| `POST /webhook` | o aviso do provedor. É aqui que a chave nasce. |
| `GET /pendentes` | as chaves que estão esperando você mandar |
| `GET /saude` | o estado do serviço |

Tudo na mesma origem, então **não há CORS** e não há script externo: é o
app KEY servindo a própria loja.

---

## Montando (uma vez)

### 1. O provedor de PIX

Há dois provedores no `YouPI-KEY\pix.py`:

| `pagamento` | O que é | Custa |
|---|---|---|
| `simulado` | **Não cobra nada.** O pedido é criado local e a confirmação chega por um endpoint local. Serve para testar o caminho inteiro antes de ter conta em provedor nenhum. | zero |
| `mercadopago` | PIX nativo, checkout hospedado, webhook assinado com HMAC, e o pagamento é confirmado **sozinho**. | taxa pequena por venda |

**Para começar: `simulado`.** Você vende os primeiros clientes por fora, e
decide o provedor com o primeiro dinheiro na mão.

Quando for trocar para o Mercado Pago:

**O caminho curto (dois cliques):**

1. Crie a conta em mercadopago.com.br (CPF ou CNPJ) e verifique o email.
2. Dê dois cliques em `YouPI-KEY\configurar-mp.bat`.
   Ele pergunta o **access token**, o **secret signature** e a **URL de
   notificação**, e grava tudo no `config.json`. Os segredos são digitados
   na tela — não passam pelo chat, nem por log, nem por histórico.
3. Dê dois cliques em `YouPI-KEY\testar-mp.bat`.
   Ele cria um PIX de **R$ 0,01** de verdade, salva o QR code em PNG,
   espera o Mercado Pago aprovar e confere se o aviso chegou, se a chave
   nasceu e se foi para o manifesto no GitHub.

**O caminho manual (se quiser fazer na mão):**

1. Crie a conta em mercadopago.com.br (CPF ou CNPJ).
2. Em **Suas integrações → Webhooks → Configurar notificação**, gere o
   **secret signature**.
3. Copie o **access token** (de teste, primeiro).
4. No `YouPI-KEY\config.json`:

```json
"pagamento": "mercadopago",
"mp_access_token": "APP_USR-...",
"mp_webhook_secret": "o secret signature do painel",
"mp_notification_url": "https://SEU-ENDERECO/webhook"
```

5. Cadastre a `mp_notification_url` no painel do Mercado Pago.

> A assinatura do Mercado Pago é o HMAC-SHA256 de
> `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`, com o secret como
> chave. A comparação é em tempo constante, e o corpo conferido é o **cru**.
> Está em `pix.py`, em `_mp_conferir`.

### 2. Os dois repositórios

O script cria os dois, e a autenticação fica com você — nenhum token
passa pelo chat:

```powershell
cd appnovo
python ferramentas\criar_repos.py
```

Ele usa o **GitHub CLI** se estiver instalado (e aí o login é pelo
navegador, e o token nem aparece). Se não houver `gh`, ele usa um token
clássico da variável `YOUPI_GITHUB_TOKEN`.

> **Por que não um cookie.** Um cookie de sessão do GitHub é uma
> credencial de portador: quem tem, faz tudo que você faz, e ela dura
> meses sem aviso. Um token é limitado, revoga em dois cliques, e — no
> jeito do `criar_repos.py` — **nunca passa pelo chat**: sai do seu
> disco para o seu GitHub e morre ali.

Depois de criados:

```powershell
cd ..\YouPI-KEY
python chave.py publicar          # o manifesto vai para o -licencas
```

```powershell
cd ..\appnovo
python ferramentas\empacotar.py --saida ..\YouPI-PG-Live --publicar `
    --repo "tecnosh97/YouPI-PG-Live" `
    --url-loja "https://SEU-ENDERECO" `
    --preco "29.90" --moeda "BRL"
```

O empacotador tira o conteúdo protegido, limpa o seu @ do TikTok, confere
que nenhum segredo seu sobrou, **sobe a versão** e faz o push. O `git init`
e o `remote` ele faz sozinho.

### 3. O endereço público

O cliente precisa **chegar** na loja, e o provedor precisa **chamar** o
webhook. Os dois são o mesmo endereço, e é o seu app KEY.

O jeito mais simples é um túnel:

```powershell
cloudflared --url http://localhost:8099
```

Ele te dá um endereço `https://algo-aleatorio.trycloudflare.com`. Ponha no
`config.json`:

```json
"url_publica": "https://seu-dominio.com"
```

(um túnel com endereço fixo precisa de um domínio — e aí o `cloudflared`
com um túnel nomeado resolve).

### 4. O GitHub

```json
"repo": "tecnosh97/YouPI-PG-licencas",
"token": "o PAT com escrita só nesse repositório"
```

O PAT com escopo de escrita **só** no repositório do manifesto. Se o PAT
vazar, o estrago é só o manifesto — que é público de qualquer jeito.

### 5. Rodar

```powershell
cd YouPI-KEY
python chave.py gui
```

A janela sobe **com o carrinho junto** (não é uma segunda janela para
lembrar). Ela mostra:

- **Clientes** — quem tem licença e até quando;
- **Para entregar** — as chaves que acabaram de ser geradas, prontas para
  copiar e mandar.

---

## O dia a dia

```
1. o cliente paga na loja (PIX)
2. o provedor confirma e chama o app KEY
3. a chave aparece em "Para entregar"
4. você copia e manda no WhatsApp, em DUAS mensagens:
     mensagem 1: o código de licença
     mensagem 2: o código de ativação
5. o cliente cola os dois no config\licenca.json do app
6. em até 5 segundos, o extra aparece
```

### No fim do mês

```
1. no app KEY, ponha o e-mail de cada cliente e aperte "Gerar / renovar"
2. mande o código novo para cada um
3. "PUBLICAR no GitHub"
```

> A chave **só troca quando a licença venceu**. Quem renovou cedo mantém a
> chave e ganha prazo; quem renovou depois do vencimento ganha uma chave
> nova — e a antiga deixa de valer. É isso que dá valor à mensalidade: uma
> cópia parada do app não serve para o mês seguinte.

---

## Um aviso sobre a moeda

Agora é **BRL** e **PIX** — que é o que o cliente brasileiro usa, sem
esforço nenhum (app do banco, igual qualquer compra). O preço é o que você
pôr em `preco` no `config.json` e no empacotador.

---

## Quando algo dá errado

| O sintoma | O que é |
|---|---|
| "assinatura invalida" no log do app KEY | O segredo do webhook não bate. Confira `mp_webhook_secret` (ou `sim_segredo`). |
| O provedor não chama o webhook | O endereço não é público, ou o `mp_notification_url` cadastrado está errado. |
| A chave é gerada mas o cliente não usa | Falta o **código de ativação**. São duas mensagens separadas, de propósito. |
| "chave inválida" no app do cliente | A chave não está no manifesto. O `publicar` do app KEY falhou? (falta o PAT do GitHub) |
| "a assinatura do manifesto não confere" | O manifesto é de outra chave de assinatura. Acontece se a `chave_privada.pem` foi trocada sem trocar a pública no programa. |
| O cliente renova e a chave antiga morre | É o comportamento certo: a chave só troca depois do vencimento. Se foi antes, foi bug — me avise. |

---

## Os testes

```powershell
cd YouPI-KEY
python webhook_teste.py
```

O teste roda o caminho inteiro **sem provedor nenhum**: cria o pedido, paga
no checkout simulado, e confere que a chave nasceu, que o mesmo pedido de
novo **não** muda a chave (idempotência), que o manifesto leva a chave, e
que o par (chave + ativação) abre o conteúdo.

> O provedor simulado não é um atalho: o aviso é assinado com o mesmo
> segredo e pelo mesmo esquema, e o webhook não tem como saber que ele é
> simulado. É o mesmo caminho de código.

---

## O que este fluxo NÃO protege

A **ponte** do app. Ela é Python na máquina do cliente, e quem tem o
arquivo tem o código. A licença protege o **conteúdo** (as danças de
terceiro e as cenas), e é isso que faz a pirataria perder o sentido: sem
chave válida, o produto é o de graça — e o de graça não tem as cenas nem
as danças.

Se um dia você quiser parede de verdade, o caminho é o **modo publicado**
(o lugar na Roblox), que exige o Premium do Roblox, um VPS e um túnel do
cliente. Está explicado em [`LICENCA.md`](LICENCA.md).
