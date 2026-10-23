# As Cenas — o kit de temas do cenário

A cor do set, trocada ao vivo, sem reiniciar nada.

---

## O que é

O mapa do kit foi desenhado com **uma** paleta só: o salão claro, o rosa e o
ciano. Até aqui, trocar a cor do set significava editar o gerador do cenário e
remontar o arquivo do jogo — ou seja, reiniciar a live no meio da
transmissão, que é a hora em que a live está cara.

Nas Cenas, a cor deixa de ser do **mapa** e passa a ser um **dado**. O mapa
continua igual; o que muda é a cor que cada peça recebe enquanto o jogo
está rodando.

| | |
|---|---|
| Trocar de cena | painel → aba **Cenas**, ou `!cena neon` no chat |
| Quanto tempo leva | até **5 segundos** |
| Precisa reiniciar | **não** |
| Custa moeda | **não** |
| Quem pode trocar | só o **dono** da live |

---

## As seis cenas

| | | |
|---|---|---|
| **Padrão** | o set como ele foi desenhado | o botão de volta |
| **Neon** | set azul-escuro com magenta e ciano | a aura dos presentes aparece mais: contra um set escuro, o contorno de quem pagou vira o ponto mais claro do quadro |
| **Matrix** | verde de terminal, bem escuro | o mais escura de todas — num set escuro, o brilho da aura e o tile aceso viram os únicos pontos de luz |
| **Pôr do sol** | laranja, rosa e terra batida | combina com a hora do dia em que a live costuma começar |
| **Gelo** | azul e branco, set claro e frio | para live de dia, quando o set original estoura embaixo de luz natural |
| **Carvão** | quase preto, com o acento em vermelho | tira todo o resto do caminho: o quadro fica com a pessoa no centro |

---

## Como usar

### No painel

1. Abra o painel (ele abre sozinho com a live).
2. Vá na aba **Cenas**.
3. Clique na cena.

A tira de cores de cada cartão **é a cena de verdade** — a mesma tabela que o
jogo recebe. O que aparece ali é o que o jogo pinta.

### No chat da live

```
!cena neon
```

Aceita o nome curto (`neon`) e o nome de verdade (`Pôr do sol`). Com
`!temas` o jogo lista os nomes disponíveis, na janela `2 - PONTE DO TIKTOK`.

Só o dono da live consegue. Um espectador que escreve `!cena` mudaria o set
de todo mundo — e o set é do dono.

---

## O que a cena mexe — e o que ela não mexe

A cena troca **cor**. Ela não mexe em material, nem em posição, nem em
tamanho, nem no mapa.

Uma coisa ela **não** mexe de propósito: a **luz ambiente**. A luz ambiente
continua sendo sua, na aba "Câmera e luz". São dois controles do mesmo
lugar, e se os dois brigassem, um sobrescreveria o outro a cada 5 segundos.

---

## Como funciona por dentro

### A cor é um papel, não uma cor

Cada peça do set tem um **papel** — "isto é a parede", "isto é o acento
quente", "isto é o tile que acende" — e não uma cor. A paleta de cada cena é
uma tabela de **papel → cor**.

Por isso uma cena nova não redesenha o mapa: ela só diz que *"a parede"
passa a ser verde*, e todas as paredes ficam verdes de uma vez, juntas.

São 23 papéis:

```
SALAO  PALCO  REJUNTE  PISTA_A  PISTA_B  PISTA_ACESA
DEGRAU_A  DEGRAU_B  PAREDE  PAREDE_ESC
ESTRUTURA  ESTRUTURA_ESC  MADEIRA
NEON_A  NEON_B  NEON_A_VIVO  NEON_B_VIVO
LENTE_QUENTE  LENTE_FRIA  TELA  PAINEL_ALTO
LUZ_QUENTE  LUZ_FRIA
```

### Onde a paleta mora

Em **um** lugar só: `servidor/cenas.py`.

- O **painel** lê de lá para desenhar a prévia.
- O **jogo** recebe a mesma tabela pelo `/ajustes`.

Não há cópia da paleta em JavaScript nem em Luau. Uma cor trocada no servidor
aparece nos dois lados no mesmo instante, e uma cena nova é um item novo
naquela lista.

### O caminho completo

```
painel (clique)  ──POST /cena──►  servidor  ──/ajustes (a cada 5s)──►  jogo
chat  (!cena)   ──POST /cena──►      │                                  │
                                    └── grava em config/ajustes.json    │
                                                                 ▼
                                                              o set é repintado
```

O jogo pergunta o `/ajustes` a cada 5 segundos e repinta o set **só** quando
a cena muda de verdade — repintar é uma passada por ~400 peças, e num PC
fraco isso aparece como um engasgo na hora em que a formação está cheia.

### O acento que acende tem cor própria

O set tem dois acentos: o de **metal** (o rodapé, o nariz do degrau) e o que
**acende** (as faixas da pista, os frisos, as lentes).

Em Neon, uma cor clara acende como **branco** — e branco no meio do quadro é
um clarão, não um acento. Por isso o acento que acende tem um papel próprio,
sempre mais escuro. É a regra que impede a cena de virar um borrão de luz.

### O teto de 234

Nenhuma cor de **superfície** passa de 234. Acima disso, a peça estoura em
branco sob a luz do set — e a pista ocupa o terço de baixo do quadro o tempo
todo, então um tile estourado ali é um borrão branco no meio da multidão.

O teto é 234 porque é o maior valor que o próprio set de fábrica usa: a
parede clara é `#E4E5EA`, e o azul dela é 234.

---

## Para quem for mexer

### Trocar as cores de uma cena

`servidor/cenas.py`. Cada cena é uma tabela de papel → cor (0 a 255):

```python
"neon": _cena(
    "Neon", {
        "SALAO": (28, 32, 44),
        "PISTA_A": (52, 60, 82),
        # ...
    },
    atmo=(120, 90, 170), decay=0.62, haze=0.5,
    tint=(255, 235, 255), bloom=0.24, saturacao=0.28, contraste=0.1,
),
```

O bloco `luz` é o que a cena mexe na luz: a cor do ar (`atmo`), o quanto ele
pesa (`decay`), o quanto embaça (`haze`), a tonalidade da correção de cor
(`tint`), o brilho (`bloom`), a saturação e o contraste.

### Criar uma cena nova

1. Escreva a paleta em `servidor/cenas.py`, com os 23 papéis.
2. Ponha o nome dela na `ORDEM` (é a ordem em que aparecem no painel).
3. Não precisa mexer em mais nada: o painel lê a lista, e o jogo recebe pelo
   `/ajustes`.

### Se o mapa ganhar uma peça nova

A peça nova precisa de um papel. A regra mora em
`roblox/src/ReplicatedStorage/Cenas.luau` (a tabela `REGRAS`), e o teste de
Python acusa na hora se alguma peça do mapa ficou sem regra:

```
python servidor\testes_cenas.py
```

A regra nova é uma linha:

```lua
{"^NomeDaPeca%d+$", "ESTRUTURA"},
```

A ordem importa: a primeira regra que casa é a que vale, então os nomes
genéricos ficam no fim.

---

## Os testes

| O quê | Como rodar |
|---|---|
| As regras do set (o nome de cada peça → o papel dela) | `ferramentas\luau.exe roblox\testes\cenas.spec.luau` |
| A paleta contra o mapa (a cena de fábrica reproduz o set exato) | `python servidor\testes_cenas.py` |
| O jogo inteiro ainda compila | `ferramentas\luau.exe roblox\testes\compila.spec.luau` |

O primeiro e o segundo são as duas metades da mesma corrente: o primeiro
confere o **nome**, o segundo confere a **cor**. Um deles sozinho deixaria
passar metade dos defeitos.

---

## Se a cena não mudar

1. **O jogo pegou?** Olhe o Output do Roblox Studio. A linha
   `[cena] 'neon' aplicada em 411 pecas` aparece quando ele pegou. O mesmo
   texto vai para a aba **Logs** do painel.
2. **O servidor tem a cena?** A aba **Cenas** do painel mostra qual está no
   ar, com o cartão ativo marcado.
3. **A luz está estourando?** Trocar a cena não mexe na luz ambiente. Se o
   set ficou claro demais, mexa na aba "Câmera e luz".
