--!strict
--[[
	A conta que decide onde a camera fica.

	MODULO PURO: so' numeros entram e so' numeros saem. Nenhum servico da
	Roblox, nenhum Instance, nenhum estado global.

	POR QUE ELE E' SEPARADO DA CAMERA

	Porque assim ele pode ser TESTADO. O enquadramento e' a parte do kit em que
	um erro custa mais caro e aparece menos: um telao meio cortado nao levanta
	excecao nenhuma, nao entra em log nenhum, e so' e' percebido por quem
	assiste -- que nao vai avisar, vai so' sair da live. Deixar essa conta
	dentro de um script de cliente significaria que a unica forma de conferi-la
	seria abrir o Studio e olhar, toda vez.

	Aqui ela roda no `luau` puro, sem Roblox nenhum, e tem uma suite de casos
	em roblox/testes/enquadramento.spec.luau que cobre avatar normal, avatar
	crescido, colosso, primeira e ultima fileira, em 16:9 e em 9:16.

	═══════════════════════════════════════════════════════════════════
	O PROBLEMA, EM UMA FRASE
	═══════════════════════════════════════════════════════════════════

	Onde por a lente pra que o TELAO (la' no fundo, alto) e o AVATAR (na frente,
	de tamanho variavel) apareçam os dois no mesmo quadro, sem que nenhum dos
	dois fique pequeno demais?

	A resposta e' um par (distancia, inclinacao). A inclinacao e' facil depois
	que a distancia esta' escolhida: e' o meio do caminho entre o ponto mais
	alto e o mais baixo que precisam aparecer. A distancia e' o problema de
	verdade, e e' resolvida por bissecao -- ver `resolver`.
]]

local Enquadramento = {}

export type Pedido = {
	-- ONDE ESTA' O ALVO, em coordenadas do mundo.
	alvoZ: number,
	alvoPes: number,
	alvoTopo: number,
	--[[ O TOPO DO BALAO DO NOME. Opcional; sem ele vale o `alvoTopo`.

		ELE EXISTE PORQUE O NOME SUMIA DO QUADRO.

		O balao mora ACIMA da cabeca (ROTULO.ALTURA studs de folga, mais a
		altura do proprio balao), e o enquadramento so' declarava pes e cabeca.
		Enquanto a lente ficava longe isso nao aparecia: sobrava quadro de
		sobra em cima. Conforme a camera foi chegando perto -- que e' o pedido
		do produto -- a borda de cima passou a cortar exatamente a faixa onde
		o nick estava escrito. O boneco aparecia inteiro e ANONIMO, que e' o
		contrario do que esta live faz.

		SEPARADO do `alvoTopo` porque os dois respondem perguntas diferentes:
		este diz o que precisa CABER, e o `alvoTopo` diz onde fica o meio do
		CORPO -- que e' o que decide a altura da lente. Juntar os dois faria a
		camera subir pra altura do balao e olhar o boneco de cima de novo. ]]
	alvoTopoQuadro: number?,
	-- ONDE ESTA' O TELAO, em coordenadas do mundo.
	telaoZ: number,
	telaoTopo: number,
	-- A LENTE.
	fov: number,
	margem: number,
	-- A CAMERA.
	alturaBase: number,
	partida: number,
	minimo: number,
	maximo: number,
	--[[ Ate' onde o TELAO pode empurrar a lente. Opcional; sem ele vale o
		`maximo`, que e' o comportamento antigo.

		Existe porque o telao mandava no plano inteiro: ele fica 74 studs atras
		da formacao, e caber o topo dele junto com o avatar custava dezenas de
		studs de recuo -- a live ficava longe por causa do FUNDO. Com um teto
		proprio, o telao vira o que ele e': o segundo item da lista de
		prioridades, nao o primeiro. ]]
	tetoComTelao: number?,
}

export type Plano = {
	distancia: number,
	-- Elevacao do eixo optico, em graus. Negativo = olhando pra baixo.
	eixo: number,
	altura: number,
	-- `false` quando nao houve distancia que coubesse os dois e o solver
	-- priorizou o avatar. Quem chama pode querer avisar; a camera nao avisa,
	-- so' entrega o melhor quadro possivel.
	comTelao: boolean,
}

--[[ A elevacao de um ponto visto da camera, em graus. Positivo = acima.

	So' o plano vertical (Z e Y) importa: no modo seguir a camera fica sempre no
	mesmo X do alvo, entao o enquadramento e' um problema bidimensional. ]]
function Enquadramento.elevacao(yPonto: number, zPonto: number,
	yCam: number, zCam: number): number
	-- O piso de 0.01 evita o atan2(algo, 0) de uma camera exatamente em cima do
	-- ponto -- que nao acontece na live, mas acontece num teste com numeros
	-- redondos, e uma divisao por zero num teste e' um teste que mente.
	local dz = math.max(zCam - zPonto, 0.01)
	return math.deg(math.atan2(yPonto - yCam, dz))
end

--[[ O maior e o menor angulo que o quadro precisa cobrir, nesta distancia.

	TUDO AQUI E' Y DO MUNDO, e nao altura relativa ao alvo. A distincao parece
	pedante ate' voce misturar as duas: o topo do telao e' um Y absoluto, entao
	medir o avatar em "altura a partir dos pes" faria duas coordenadas
	diferentes conviverem na mesma conta. Enquanto o palco tem o piso em y=0 os
	numeros batem por coincidencia, e o erro fica invisivel -- ate' alguem subir
	o palco um stud e o telao sair do quadro sem explicacao. ]]
function Enquadramento.abertura(p: Pedido, d: number, yCam: number,
	comTelao: boolean): (number, number)
	local zCam = p.alvoZ + d
	local pes = Enquadramento.elevacao(p.alvoPes, p.alvoZ, yCam, zCam)
	-- O topo do QUADRO e' o do balao do nome quando ele foi informado. Sem
	-- isto a borda de cima corta exatamente a faixa onde o nick esta' escrito.
	local cabeca = Enquadramento.elevacao(
		p.alvoTopoQuadro or p.alvoTopo, p.alvoZ, yCam, zCam)
	local menor = math.min(pes, cabeca)
	local maior = math.max(pes, cabeca)
	if comTelao then
		local topo = Enquadramento.elevacao(p.telaoTopo, p.telaoZ, yCam, zCam)
		menor = math.min(menor, topo)
		maior = math.max(maior, topo)
	end
	return menor, maior
end

-- Quantos passos de bissecao. 18 fecham um intervalo de 100 studs em menos de
-- meio milesimo -- muito alem do que a tela distingue, e ainda assim barato.
local PASSOS = 18

--[[ Acha a menor distancia, a partir de `partida`, em que tudo cabe.

	A busca e' uma BISSECAO e nao uma formula fechada, e o motivo e' honesto: a
	abertura necessaria em funcao da distancia e' a diferenca de dois
	arco-tangentes com centros diferentes (o alvo e o telao estao a distancias
	distintas da lente), e isolar `d` daria uma expressao que ninguem
	conseguiria conferir depois. A abertura CAI monotonicamente conforme a
	camera se afasta -- os dois arco-tangentes encolhem juntos -- entao a
	bissecao acha a resposta em 18 passos, custa nada, e da' pra explicar em
	duas linhas. ]]
local function menorQueCabe(p: Pedido, yCam: number, limite: number,
	comTelao: boolean): number?
	local function cabe(d: number): boolean
		local menor, maior = Enquadramento.abertura(p, d, yCam, comTelao)
		return (maior - menor) <= limite
	end

	-- Com o telao na conta, o recuo tem teto proprio (ver `tetoComTelao`): e'
	-- o que impede o fundo de decidir o plano da live inteira.
	local teto = if comTelao
		then math.min(p.tetoComTelao or p.maximo, p.maximo)
		else p.maximo

	if cabe(p.partida) then
		return p.partida
	end
	if teto <= p.partida or not cabe(teto) then
		return nil
	end

	local perto, longe = p.partida, teto
	for _ = 1, PASSOS do
		local meio = (perto + longe) / 2
		if cabe(meio) then
			longe = meio
		else
			perto = meio
		end
	end
	return longe
end

--[[ Resolve o plano. Nunca falha: sempre devolve um quadro utilizavel. ]]
function Enquadramento.resolver(p: Pedido): Plano
	--[[ A camera sobe junto com o alvo. Sem isto, um boneco de 36 studs seria
		olhado a partir do tornozelo: o quadro caberia (a bissecao garante), mas
		a composicao ficaria com o gigante inteiro na metade de cima e o chao
		vazio embaixo. ]]
	local yCam = p.alvoPes + p.alturaBase + (p.alvoTopo - p.alvoPes) * 0.5
	local limite = p.fov - 2 * p.margem

	local comTelao = true
	local d = menorQueCabe(p, yCam, limite, true)

	if not d then
		--[[ Nem no limite de recuo os dois cabem. Acontece com o colosso:
			enquadrar um boneco de 40x JUNTO com o telao exigiria centenas de
			studs de recuo, e ai' os dois ficariam pequenos -- o presente mais
			caro da live viraria um pontinho ao lado de um telao ilegivel.

			Priorizar o avatar entrega pelo menos uma das duas coisas grande na
			tela, e o telao continua aparecendo no fundo (so' nao inteiro). ]]
		comTelao = false
		d = menorQueCabe(p, yCam, limite, false) or p.maximo
	end

	d = math.clamp(d, p.minimo, p.maximo)
	local menor, maior = Enquadramento.abertura(p, d, yCam, comTelao)
	return {
		distancia = d,
		eixo = (menor + maior) / 2,
		altura = yCam,
		comTelao = comTelao,
	}
end

--[[ A meia-abertura HORIZONTAL, em graus, derivada da vertical.

	E' com ela que se responde "quanto do telao aparece num video em pe'?". A
	resposta e' menos do que quase todo mundo espera: num 9:16, a abertura
	horizontal e' pouco mais de um terco da de um 16:9 com a MESMA lente. Por
	isso a mensagem do telao vive numa faixa central estreita -- ver o
	Cenario.model.json. ]]
function Enquadramento.meiaAberturaHorizontal(fov: number, proporcao: number): number
	return math.deg(math.atan(math.tan(math.rad(fov / 2)) * proporcao))
end

--[[ Quantos studs de largura cabem no quadro a uma certa distancia. ]]
function Enquadramento.larguraVisivel(fov: number, proporcao: number,
	distancia: number): number
	return 2 * distancia
		* math.tan(math.rad(Enquadramento.meiaAberturaHorizontal(fov, proporcao)))
end

return Enquadramento
