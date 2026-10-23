--!nocheck
--[[
	Teste do enquadramento da camera. Roda FORA do Roblox.

		ferramentas\luau.exe roblox\testes\enquadramento.spec.luau

	(ou, mais facil, pelo TESTES-INTERNOS.bat, que roda esta suite junto com as
	de Python.)

	POR QUE ESTE TESTE EXISTE

	O enquadramento e' a parte do kit em que um erro custa mais caro e aparece
	menos. Um telao meio cortado nao levanta excecao, nao entra em log nenhum e
	nao aparece em nenhuma tela de diagnostico -- so' e' percebido por quem
	esta' assistindo, que nao vai avisar: vai so' sair da live.

	Cada caso aqui e' uma situacao REAL da transmissao, e o que se afirma sobre
	ela e' o que o pedido do produto exige: telao no quadro, avatar inteiro no
	quadro, e o boneco nem minusculo nem estourando a tela.
]]

-- Sem a extensao: e' assim que o `require` do luau resolve caminho relativo.
local Enquadramento = require("../src/ReplicatedStorage/Enquadramento")

-- ─────────────────── O cenario real, medido no mapa ───────────────────
--
-- Estes numeros saem do roblox/src/Workspace/Cenario.model.json (a peca
-- "Telao": centro em y=25, z=-74, tamanho 148 x 14) e do Config.luau.
--
-- O `Telao` e' so' a JANELA DO MEIO da parede de LED -- a que carrega texto.
-- Abaixo e acima dela ficam PainelInferior e PainelSuperior, que a camera nao
-- promete enquadrar. Ver o bloco TELAO do Config.luau pra o porque.

local TELAO_Z = -74
local TELAO_TOPO = 32          -- 25 + 14/2
local TELAO_LARGURA = 148

local FOV_DEITADO = 40
local FOV_EM_PE = 40
local MARGEM = 4
local ALTURA_BASE = 1
local PARTIDA = 13
local MINIMO, MAXIMO = 9, 120

local ALTURA_R15 = 6           -- um avatar de escala 1.0

--[[ ─────────── O BALAO DO NOME ───────────

	ESTE BLOCO EXISTE POR CAUSA DE UM DEFEITO QUE ESTE TESTE DEIXOU PASSAR.

	O teste conferia pes e cabeca no quadro, e passava. Mas o NICK -- a coisa
	que a live inteira pede que a pessoa comente -- mora num balao ACIMA da
	cabeca, e ninguem conferia se ele cabia. Enquanto a lente ficava longe
	sobrava quadro de sobra em cima e o defeito nao aparecia. Quando a camera
	chegou perto, a borda de cima passou a cortar exatamente a faixa do nome: o
	boneco aparecia inteiro e ANONIMO.

	Um teste que afirma "o avatar esta' no quadro" e ignora o nome dele esta'
	medindo a coisa errada. Agora ele mede as duas.

	Os numeros saem do `ajustarRotulo` (Avatares.luau): o balao fica
	ROTULO_ALTURA x escala acima do CENTRO da cabeca, tem 2.2 x raiz(escala) de
	altura, e o centro da cabeca de um R15 fica a ~78% da altura do boneco. ]]
local ROTULO_ALTURA = 2.2

local function topoDoBalao(pes: number, topo: number, escala: number): number
	return pes + (topo - pes) * 0.78 + ROTULO_ALTURA * escala
		+ 1.1 * math.sqrt(escala)
end

-- Ate' onde o telao pode empurrar a lente (Config.CAMERA.TELAO_RECUO_MAX).
local TELAO_RECUO_MAX = 22
-- O piso da busca no close de chegada (Config.CAMERA.ZOOM_DISTANCIA) e a
-- folga apertada dele (Config.CAMERA.ZOOM_MARGEM_GRAUS).
local ZOOM_DISTANCIA = 9
local ZOOM_MARGEM = 2

local falhas = 0
local total = 0

local function afirmar(condicao: boolean, descricao: string)
	total += 1
	if not condicao then
		falhas += 1
		print("  FALHOU: " .. descricao)
	end
end

local function pedido(zFileira: number, escala: number, fov: number)
	local topo = ALTURA_R15 * escala
	return {
		alvoZ = zFileira,
		alvoPes = 0,
		alvoTopo = topo,
		alvoTopoQuadro = topoDoBalao(0, topo, escala),
		telaoZ = TELAO_Z,
		telaoTopo = TELAO_TOPO,
		fov = fov,
		margem = MARGEM,
		alturaBase = ALTURA_BASE,
		partida = PARTIDA,
		minimo = MINIMO,
		maximo = MAXIMO,
		tetoComTelao = TELAO_RECUO_MAX,
	}
end

--[[ O CLOSE DE CHEGADA. Mesmo solver, tres diferencas: parte de muito mais
	perto, aperta a folga, e NAO pede o telao (tetoComTelao = 0 faz o solver
	desistir do fundo na hora em vez de recuar pra tentar caber os dois).

	O QUE ELE NAO FAZ MAIS e' cortar na cintura. Cortava, pra chegar mais
	perto, e o preco foi um quadro OLHANDO PRA CIMA: com o enquadramento indo
	da cintura ao topo do balao, o meio do que precisa caber fica na altura da
	cabeca e o eixo optico vai atras. Do pe' ao balao, as duas pontas ficam a
	mesma distancia da altura da lente e o eixo sai reto sozinho. ]]
local function pedidoZoom(zFileira: number, escala: number, fov: number)
	local p = pedido(zFileira, escala, fov)
	p.partida = ZOOM_DISTANCIA * escala
	p.margem = ZOOM_MARGEM
	p.tetoComTelao = 0
	-- A lente no MEIO do que precisa caber: e' o que faz o eixo sair reto em
	-- qualquer escala. Ver `destinoZoom` no Camera.client.luau.
	p.alturaBase = (p.alvoTopoQuadro - p.alvoPes) / 2 - (p.alvoTopo - p.alvoPes) * 0.5
	return p
end

--[[ Confere um caso inteiro e imprime a medida, pra o teste servir tambem
	como a tabela de referencia do enquadramento. ]]
local function conferir(nome: string, zFileira: number, escala: number,
	fov: number, proporcao: number, exigirTelao: boolean, p: any?)
	p = p or pedido(zFileira, escala, fov)
	local plano = Enquadramento.resolver(p)

	local meiaV = fov / 2
	local zCam = zFileira + plano.distancia

	-- Onde cada coisa cai no quadro, em graus a partir do centro da tela.
	local aTopoTelao = Enquadramento.elevacao(TELAO_TOPO, TELAO_Z, plano.altura, zCam)
		- plano.eixo
	local aPes = Enquadramento.elevacao(p.alvoPes, zFileira, plano.altura, zCam)
		- plano.eixo
	local aCabeca = Enquadramento.elevacao(ALTURA_R15 * escala, zFileira,
		plano.altura, zCam) - plano.eixo
	-- O TOPO DO BALAO DO NOME: o nick precisa caber, nao so' o boneco.
	local aNome = Enquadramento.elevacao(p.alvoTopoQuadro, zFileira,
		plano.altura, zCam) - plano.eixo

	-- Quanto o avatar ocupa da ALTURA do quadro.
	local alturaVisivel = 2 * plano.distancia * math.tan(math.rad(meiaV))
	local fatia = (ALTURA_R15 * escala) / alturaVisivel * 100

	-- Quanto da LARGURA do telao aparece.
	local larguraTelao = Enquadramento.larguraVisivel(fov, proporcao, zCam - TELAO_Z)
	local pctTelao = math.min(100, larguraTelao / TELAO_LARGURA * 100)

	print(string.format(
		"  %-32s d=%5.1f  eixo=%6.2f  avatar=%5.1f%%  telao_larg=%5.1f%%",
		nome, plano.distancia, plano.eixo, fatia, pctTelao))

	afirmar(math.abs(aPes) <= meiaV, nome .. ": a base do avatar saiu do quadro")
	afirmar(math.abs(aCabeca) <= meiaV, nome .. ": a cabeca do avatar saiu do quadro")
	--[[ A AFIRMACAO QUE FALTAVA. Sem ela, todo o resto podia passar com o nick
		cortado pela borda de cima -- e foi exatamente o que aconteceu. ]]
	afirmar(math.abs(aNome) <= meiaV,
		nome .. ": o BALAO DO NOME saiu do quadro -- o nick nao aparece")
	if exigirTelao then
		afirmar(math.abs(aTopoTelao) <= meiaV,
			nome .. ": o TOPO DO TELAO saiu do quadro")
		afirmar(plano.comTelao, nome .. ": o solver desistiu do telao")
	end
	afirmar(plano.distancia >= MINIMO and plano.distancia <= MAXIMO,
		nome .. ": distancia fora dos limites")

	return plano, fatia, pctTelao
end

print("")
print("HORIZONTAL 16:9 -- OBS deitado")
print(string.rep("-", 86))
local _, _, pctTelaoDeitado =
	conferir("fileira 0, avatar normal", 0, 1, FOV_DEITADO, 16 / 9, true)
--[[ PRESENTE GRANDE NAO EXIGE MAIS O TELAO, e a mudanca e' de POLITICA.

	Antes o telao era obrigatorio em todo plano, e ele saia caro: enquadrar um
	boneco de 2,8x JUNTO com uma parede 74 studs atras custava dezenas de studs
	de recuo, e a live inteira ficava longe por causa do fundo. O pedido do
	dono foi o oposto -- camera perto do boneco -- entao o telao virou o
	segundo item da lista (ver CAMERA.TELAO_RECUO_MAX).

	O que continua garantido: o avatar e o NOME dele no quadro, sempre, e o
	telao no quadro sempre que couber dentro do teto de recuo -- que e' o caso
	de quem so' comentou, ou seja, a maior parte da live. ]]
conferir("fileira 0, rosquinha 2.8x", 0, 2.8, FOV_DEITADO, 16 / 9, false)
conferir("fileira 0, oculos 4x", 0, 4, FOV_DEITADO, 16 / 9, false)
conferir("fileira 0, no teto 6x", 0, 6, FOV_DEITADO, 16 / 9, false)
conferir("fileira 4, avatar normal", 36, 1, FOV_DEITADO, 16 / 9, true)
conferir("fileira 9, avatar normal", 72, 1, FOV_DEITADO, 16 / 9, true)
conferir("fileira 9, no teto 6x", 72, 6, FOV_DEITADO, 16 / 9, false)

print("")
print("VERTICAL 9:16 -- TikTok Live")
print(string.rep("-", 86))
local _, fatiaVertical, pctTelaoVertical =
	conferir("fileira 0, avatar normal", 0, 1, FOV_EM_PE, 9 / 16, true)
conferir("fileira 0, oculos 4x", 0, 4, FOV_EM_PE, 9 / 16, false)
conferir("fileira 0, no teto 6x", 0, 6, FOV_EM_PE, 9 / 16, false)
conferir("fileira 9, avatar normal", 72, 1, FOV_EM_PE, 9 / 16, true)
conferir("fileira 9, no teto 6x", 72, 6, FOV_EM_PE, 9 / 16, false)

print("")
print("O CLOSE DE CHEGADA -- o zoom rapido de quem acabou de comentar")
print(string.rep("-", 86))
--[[ O QUE ESTE BLOCO GARANTE

	Que o close CHEGA PERTO de verdade e que o nick cabe nele. Sao as duas
	unicas coisas que o dono pediu, e as duas sao mediveis: a distancia tem que
	ser bem menor que a do plano normal, e o balao do nome tem que estar dentro
	do quadro.

	O piso de 55% da altura existe porque "zoom" que nao aumenta o boneco na
	tela nao e' zoom -- e' so' a camera andando. ]]
local zoomEscalas = { 1, 2, 3, 4, 6 }
for _, escala in ipairs(zoomEscalas) do
	local p = pedidoZoom(0, escala, FOV_EM_PE)
	local _, fatiaZoom = conferir(
		string.format("close 9:16, escala %g", escala),
		0, escala, FOV_EM_PE, 9 / 16, false, p)
	afirmar(fatiaZoom >= 55, string.format(
		"close de escala %g: o boneco ocupa so' %.1f%% da altura -- nao e' close",
		escala, fatiaZoom))

	--[[ E A LARGURA? No 9:16 ela e' o lado apertado, e o solver so' olha a
		ALTURA -- ele resolve elevacoes. Foi assim que o nick sumiu pela borda
		de cima; a mesma cegueira, girada 90 graus, corta o boneco pelos lados.

		O que se exige aqui e' o TRONCO (uns 2,4 studs por unidade de escala),
		e nao a envergadura da danca (uns 6). Cortar a ponta do braco aberto
		num close e' enquadramento; cortar o ombro e' defeito. ]]
	local planoZ = Enquadramento.resolver(p)
	local meiaLargura = planoZ.distancia
		* math.tan(math.rad(Enquadramento.meiaAberturaHorizontal(FOV_EM_PE, 9 / 16)))
	afirmar(meiaLargura >= 1.2 * escala, string.format(
		"close de escala %g: so' cabem %.1f studs de meia largura -- corta o tronco",
		escala, meiaLargura))

	--[[ E O CLOSE PRECISA SAIR RETO.

		"nao quero que o zoom seja em cima, quero que ele seja reto, focando
		tipo no peito" -- o pedido, literal. Um eixo optico inclinado poe o
		peito fora do centro e o boneco escorrega pro rodape do quadro.

		Meio grau de tolerancia, e nao dois: a altura da lente do close e'
		CALCULADA como o meio do que precisa caber, entao o eixo sai reto por
		construcao e nao por sorte. Se este teste comecar a falhar, alguem
		trocou essa conta por um numero fixo. ]]
	afirmar(math.abs(planoZ.eixo) <= 0.5, string.format(
		"close de escala %g: o eixo saiu a %.1f graus -- o zoom nao esta' reto",
		escala, planoZ.eixo))
end

--[[ E o close precisa ser MAIS PERTO que o plano normal. Sem esta comparacao,
	os dois poderiam convergir pro mesmo numero numa mexida futura e o "zoom"
	viraria um corte pra lugar nenhum -- sem erro, sem aviso, so' a live sem
	close. ]]
local planoNormal = Enquadramento.resolver(pedido(0, 1, FOV_EM_PE))
local planoZoom = Enquadramento.resolver(pedidoZoom(0, 1, FOV_EM_PE))
afirmar(planoZoom.distancia < planoNormal.distancia * 0.8, string.format(
	"o close (d=%.1f) precisa ser bem mais perto que o plano normal (d=%.1f)",
	planoZoom.distancia, planoNormal.distancia))
print(string.format("  %-32s normal d=%.1f  ->  close d=%.1f",
	"aproximacao", planoNormal.distancia, planoZoom.distancia))

print("")
print("CASOS EXTREMOS")
print(string.rep("-", 86))

--[[ O COLOSSO. Um boneco de 40x tem 240 studs de altura. Nao existe distancia
	dentro do limite que o enquadre JUNTO com o telao, e o certo e' o solver
	perceber isso e priorizar o avatar -- em vez de recuar 600 studs e deixar
	os dois do tamanho de uma unha. ]]
local colosso = Enquadramento.resolver(pedido(0, 40, FOV_DEITADO))
afirmar(not colosso.comTelao,
	"colosso: o solver deveria ter desistido do telao")
afirmar(colosso.distancia <= MAXIMO,
	"colosso: nao pode passar do limite de recuo")
print(string.format("  %-32s d=%5.1f  desistiu do telao=%s",
	"colosso 40x", colosso.distancia, tostring(not colosso.comTelao)))

--[[ A GARANTIA CENTRAL DO SOLVER: afastar nunca piora.

	Se um dia alguem trocar a bissecao por outra coisa, este e' o teste que
	pega o erro. A bissecao SO' e' valida porque a abertura cai
	monotonicamente com a distancia; se essa propriedade quebrar, ela pode
	devolver um ponto qualquer do intervalo e o quadro sairia errado de um
	jeito dificil de reproduzir. ]]
local pMono = pedido(0, 3, FOV_DEITADO)
local anterior = math.huge
local monotona = true
for d = 24, 120, 4 do
	local menor, maior = Enquadramento.abertura(pMono, d, 25, true)
	local largura = maior - menor
	if largura > anterior + 1e-9 then
		monotona = false
	end
	anterior = largura
end
afirmar(monotona, "a abertura precisa CAIR conforme a camera se afasta")
print("  abertura cai monotonicamente com a distancia: " .. tostring(monotona))

--[[ A LARGURA UTIL DO TELAO EM 9:16.

	Este numero e' o que define a zona segura da mensagem no telao: e' o
	`SEGURA` do ferramentas/gerar-cenario.py, e tudo que precisa ser LIDO mora
	dentro dele. Se ele cair abaixo do que a composicao assume, a chamada passa
	a ser cortada nas pontas num video em pe' -- e o convite da live inteira
	deixa de ser lido.

	O PISO CAIU DE 50% PRA 22%, e a queda e' consequencia direta da camera
	nova: uma lente de 40 graus a ~20 studs enxerga uma fatia bem mais estreita
	do fundo que a de 68 graus a 38. A resposta nao foi abrir a lente de volta
	-- foi reescrever a mensagem numa COLUNA CENTRAL estreita, que e' como ela
	esta' montada agora. Este teste e' o que garante que a coluna continua
	cabendo: mexeu na camera e este numero caiu? A mensagem precisa afinar
	junto, ou ela sai cortada sem ninguem perceber. ]]
afirmar(pctTelaoVertical >= 22, string.format(
	"em 9:16 so' %.1f%% da largura do telao aparece -- a mensagem nao cabe",
	pctTelaoVertical))

--[[ A LARGURA UTIL DO TELAO EM 16:9 -- a lista lateral de presentes.

	Os quatro chips com "o que cada presente faz" moram FORA da coluna central,
	ate' 55 studs de cada lado do meio (o `ASA_FORA` do gerar-cenario.py). Pra
	eles aparecerem inteiros, o quadro deitado precisa enxergar pelo menos
	2 x 55 / 148 = 74% da largura da parede.

	Sem este piso, a lista some pelas bordas exatamente como a chamada sumia
	antes -- e do jeito mais traicoeiro, porque o 16:9 e' o formato em que
	ninguem espera que falte largura. ]]
afirmar(pctTelaoDeitado >= 74, string.format(
	"em 16:9 so' %.1f%% da largura do telao aparece -- a lista lateral corta",
	pctTelaoDeitado))

--[[ O AVATAR NAO PODE FICAR MINUSCULO -- NEM ESTOURAR O QUADRO.

	O piso de 8% era a unica exigencia enquanto a camera era distante: 8% da
	altura num video de 1920px sao ~150 pixels, o suficiente pra reconhecer a
	skin. Com a lente perto, o risco virou o oposto, entao agora existe TETO
	tambem: passando de 70%, o boneco de quem chegou tapa a multidao, e a
	multidao e' o argumento que faz a proxima pessoa comentar. ]]
afirmar(fatiaVertical >= 8, string.format(
	"o avatar ocupa so' %.1f%% da altura -- pequeno demais", fatiaVertical))
afirmar(fatiaVertical <= 70, string.format(
	"o avatar ocupa %.1f%% da altura -- tapa a multidao", fatiaVertical))

print("")
print(string.rep("=", 86))
if falhas == 0 then
	print(string.format("ENQUADRAMENTO: %d verificacoes, todas passaram.", total))
else
	print(string.format("ENQUADRAMENTO: %d de %d FALHARAM.", falhas, total))
end
print(string.rep("=", 86))

if falhas > 0 then
	error("teste de enquadramento falhou", 0)
end
