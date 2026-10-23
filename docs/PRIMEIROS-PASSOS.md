# Os primeiros passos — do zero até a primeira venda

Faz nessa ordem. Cada passo depende do anterior.

Todos os comandos são rodados **na sua máquina**, no terminal. Nenhum
token ou cookie passa pelo chat.

---

## PASSO 1 — O git saber quem você é

Duas linhas, **uma vez só**. Sem isso, o primeiro commit falha.

```powershell
git config --global user.name "Seu Nome"
git config --global user.email "voce@email.com"
```

**Esperado:** nada. É silencioso, e é assim que deve ser.

---

## PASSO 2 — Autenticar no GitHub

```powershell
winget install GitHub.cli
```

Feche e abra o terminal (o `gh` precisa entrar no PATH), e:

```powershell
gh auth login
gh auth setup-git
```

O `gh auth login` abre o navegador: você autoriza, e **o token fica na sua
máquina** — nem você precisa ver ele, e eu nunca vou.

Escolha: **GitHub.com** → **HTTPS** → **login pelo navegador**.

**Esperado:**
```
✓ Logged in as tecnosh97
```

> **Alternativa**, se você não quiser instalar o `gh`: crie um token
> clássico em github.com/settings/tokens, escopo `public_repo`, e use
>   `set YOUPI_GITHUB_TOKEN=github_pat_...`
> Ele nunca é gravado em arquivo.

---

## PASSO 3 — Criar os dois repositórios

```powershell
cd "D:\winrar\Nova pasta\LiveBridge_Local_Corrigido\LiveBridge_Local_Corrigido\appnovo"
python ferramentas\criar_repos.py
```

**Esperado:**
```
  YouPI-PG-Live          criado  https://github.com/tecnosh97/YouPI-PG-Live
  YouPI-PG-licencas      criado  https://github.com/tecnosh97/YouPI-PG-licencas
```

O `-Live` fica **vazio** (o primeiro commit é o do empacotador). O
`-licencas` já vem com a branch `main` — que é o que a API do GitHub exige
para aceitar o primeiro arquivo.

---

## PASSO 4 — O endereço público

O cliente precisa **chegar** na loja, e o provedor de PIX precisa **chamar**
o webhook. Os dois são o mesmo endereço: o do app KEY.

### Para TESTAR (URL aleatória, serve para hoje)

```powershell
winget install Cloudflare.cloudflared
cloudflared --url http://localhost:8099
```

Ele imprime uma URL do tipo `https://palavra-palavra.trycloudflare.com`.
**Copie ela** — é o seu `url_publica`.

> Essa URL **muda** toda vez que você reinicia o túnel. Serve para
> testar. Para vender, veja o item seguinte.

### Para VENDER (URL fixa)

Você precisa de um **domínio** (uns US$ 10/ano) na Cloudflare, e de um
túnel com nome:

```powershell
cloudflared tunnel login
cloudflared tunnel create youpi-pg
cloudflared tunnel route dns youpi-pg pay.seudominio.com
cloudflared tunnel run youpi-pg
```

Aí o endereço é `https://pay.seudominio.com`, **para sempre**.

---

## PASSO 5 — Ajustar o app KEY

Edite `YouPI-KEY\config.json`:

```json
"url_publica": "https://pay.seudominio.com",
"token": "",
```

O `token` é o **PAT** do GitHub (com escrita só no `-licencas`). Se você
usou o `gh auth login`, o token já está no ambiente — nesse caso, deixe o
campo vazio e o `gh` resolve. (Hoje o app KEY usa a variável
`YOUPI_GITHUB_TOKEN`; com o `gh` instalado, basta autenticar.)

**Esperado:** o resto do arquivo fica como está. O `sim_segredo` já é um
segredo de verdade (64 caracteres) — **não mexa nele**.

---

## PASSO 6 — Publicar o manifesto

```powershell
cd "..\YouPI-KEY"
python chave.py publicar
```

**Esperado:**
```
   publicado em tecnosh97/YouPI-PG-licencas/main/licencas.json
```

É este arquivo que o app do cliente busca para saber se a chave vale.

---

## PASSO 7 — Publicar o programa

```powershell
cd "..\appnovo"
python ferramentas\empacotar.py --saida ..\YouPI-PG-Live --publicar `
    --repo "tecnosh97/YouPI-PG-Live" `
    --url-loja "https://pay.seudominio.com" `
    --preco "29.90" --moeda "BRL"
```

O empacotador tira o conteúdo protegido, limpa o seu @ do TikTok, confere
que **nenhum segredo seu sobrou**, sobe a versão e faz o push.

**Esperado:**
```
   Tudo certo: nenhum segredo do vendedor na build.
   ...
   publicado no GitHub.
```

---

## PASSO 8 — Testar a venda inteira

```powershell
cd "..\YouPI-KEY"
python chave.py gui
```

1. Abra `https://pay.seudominio.com` no navegador.
2. Ponha um e-mail seu e clique em **Pagar no PIX**.
3. Vai abrir o **checkout simulado** (não cobra nada) → clique em
   **Simular o pagamento**.
4. Volte à janela do app KEY: a chave aparece em **"Para entregar"**.

Se aparecer, **a venda inteira funciona**: pagamento → chave → manifesto
→ conteúdo protegido.

---

## PASSO 9 — Mercado Pago (quando a conta ficar pronta)

1. Crie a conta em **mercadopago.com.br** (CPF ou CNPJ, grátis).
2. Em **Suas integrações → Webhooks → Configurar notificação**, gere o
   **secret signature** e copie o **access token** (o de teste primeiro).
3. No `YouPI-KEY\config.json`:

```json
"pagamento": "mercadopago",
"mp_access_token": "APP_USR-...",
"mp_webhook_secret": "o secret signature do painel",
"mp_notification_url": "https://pay.seudominio.com/webhook"
```

4. Cadastre a `mp_notification_url` no painel do Mercado Pago.
5. Reinicie o app KEY e teste de novo.

> **Atenção:** a integração com o Mercado Pago foi escrita seguindo a
> documentação oficial, mas **não foi testada contra a API real** (não há
> conta). É a primeira coisa a testar quando a conta existir.

---

## PASSO 10 — Como o cliente compra

1. Baixa o programa do `tecnosh97/YouPI-PG-Live` (botão **Code → Download ZIP**).
2. Extrai, roda o `1-INSTALACAO.bat`.
3. Roda o `2-COMECAR-LIVE-TIKTOK.bat`.
4. No painel, aba **Conexão**: cola o **código de licença** e o **código de
   ativação** → **Liberar**.

Em até 5 segundos o conteúdo extra aparece.

---

## TODO MÊS

```powershell
cd YouPI-KEY
python chave.py gui
```

1. Para cada cliente: ponha o e-mail → **Gerar / renovar licença** → copie
   os dois códigos.
2. Mande em **duas mensagens** (o código de ativação vai separado).
3. **PUBLICAR no GitHub**.

A chave **só troca quando a licença venceu** — quem renovou cedo mantém a
chave e ganha prazo. É isso que faz a mensalidade valer: uma cópia parada
do app não serve para o mês seguinte.

---

## Se algo der errado

| O que aparece | O que fazer |
|---|---|
| `O GIT NAO SABE QUEM VOCE E` | Passe 1 |
| `sem token do GitHub` | Passe 2, e confira o `token` no config |
| `a assinatura do manifesto nao confere` | O `sim_segredo` do config mudou depois do manifesto ser assinado. Reconfigure e publique de novo. |
| `chave invalida` no app do cliente | A chave não está no manifesto. Rode `chave.py publicar` e confira se o `url_publica` do config bate com o do `appnovo\config\licencas.json`. |
| `O APP KEY NAO SUBIU` | O `sim_segredo` ainda é o de exemplo. Rode o comando deSecrets do passo 5. |
| `a loja nao foi encontrada` | O `config.json` do app KEY está com o caminho de `app` errado. |
