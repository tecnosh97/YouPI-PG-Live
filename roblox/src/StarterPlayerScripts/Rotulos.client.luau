--!strict
--[[
	QUEM APAGA OS NOMES QUANDO A CAMERA ESTA' LONGE.

	O PROBLEMA QUE ISTO RESOLVE

	Cada avatar nasce com um balao de nome em cima da cabeca. Um balao e' otimo.
	Cem baloes nao sao cem vezes melhor -- sao uma parede preta.

	Com o limite antigo (80 studs, fixo, decidido so' pelo motor da Roblox), a
	camera de perto -- que fica a uns 45 studs de quem ela segue -- alcancava a
	pessoa seguida MAIS quatro fileiras atras dela. Quarenta, cinquenta rotulos
	desenhados juntos, encavalados, cada um do tamanho de uma unha na tela de
	quem assiste pelo celular. Nao dava pra ler nenhum, nem o de quem a camera
	estava seguindo -- que e' o unico que precisava ser lido. E a multidao do
	fundo, que e' o argumento que faz a proxima pessoa comentar, ficava escondida
	atras do texto.

	No plano aberto do fim do ciclo era pior ainda: e' o momento de mostrar
	QUANTA gente entrou, e ele saia coberto de nomes ilegiveis.

	A REGRA, EM QUATRO LINHAS

	  1. so' a FILEIRA DA FRENTE tem nome -- e ela inteira;
	  2. passou do alcance do rotulo, ele some;
	  3. chegando perto do limite, ele APAGA aos poucos em vez de piscar;
	  4. e nenhum nome cai EM CIMA de outro (ver "O CHOQUE ENTRE FILEIRAS").

	E o item 1 e' o que faz o resultado ser bom e nao so' "menos pior": a
	formacao cresce PARA A FRENTE (cada fileira nova nasce mais perto da
	camera), entao a fileira da frente e' sempre a de quem acabou de chegar.
	Quem comentou agora ve' o proprio nome; quem esta' na live ha' cinco
	minutos continua na tela, dancando, mas sem competir por espaco com quem
	chegou.

	Fora de todas elas fica QUEM A CAMERA ESTA' MOSTRANDO: esse acende sempre.
	A camera marca o balao dele, e este arquivo obedece sem perguntar.

	POR QUE NO CLIENTE

	A distancia da camera muda 60 vezes por segundo, e a camera e' propriedade do
	cliente. Fazer esta conta no servidor exigiria replicar posicao de camera o
	tempo todo pra chegar sempre atrasado.

	POR QUE NAO BASTA O `MaxDistance`

	Ele existe e continua ligado aqui como rede de seguranca (o servidor o
	configura junto com o balao). Mas ele so' sabe cortar por distancia: nao
	tem teto de quantidade, nao apaga aos poucos, e liga tudo que estiver dentro
	do raio. Numa fileira de dez, "dentro do raio" e' dez rotulos de uma vez.

	SE ESTE ARQUIVO NAO SUBIR, a live NAO quebra: os rotulos ficam como eram
	antes, cortados so' pelo MaxDistance. E' de proposito -- nenhum enfeite deste
	kit pode ser capaz de derrubar uma transmissao.
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Config"))

--[[ Escrito IGUAL no Avatares.luau (MARCA_ROTULO). Os dois precisam combinar:
	uma letra diferente e este arquivo nao acha rotulo nenhum -- sem erro, sem
	aviso, e o excesso volta calado. ]]
local MARCA_ROTULO = "RotuloDaLive"

local ROTULO = Config.ROTULO

--[[ De que fracao do alcance o rotulo comeca a apagar.

	Guardado como FRACAO, e nao em studs, porque cada rotulo tem o proprio
	alcance (o do boneco grande e' maior). Assim a faixa de apagamento acompanha
	o alcance de cada um, em vez de ser larga num e inexistente no outro.

	O teto de 0.95 nao e' capricho: se alguem puser DISTANCIA_SUAVE igual (ou
	maior) que DISTANCIA_MAX no Config, a conta do `alpha` la' embaixo dividiria
	por zero e todo rotulo viraria NaN -- ou seja, sumiriam TODOS, com o Config
	parecendo inofensivo. ]]
local INICIO_DO_FADE = math.clamp(
	(tonumber(ROTULO.DISTANCIA_SUAVE) or 0) / math.max(ROTULO.DISTANCIA_MAX, 1),
	0, 0.95)

--[[ Quantos slots do FIM do teto entram apagando.

	Sem esta folga o teto de quantidade cortaria seco: o 13o rotulo mais perto
	sumiria de um quadro pro outro enquanto a camera anda, e um rotulo piscando
	na gravacao chama mais atencao que o excesso que este arquivo veio resolver.
	Com ela, os ultimos do orcamento entram e saem apagando. ]]
local FOLGA_DO_TETO = 3

-- Intervalo entre duas contas. 0.06s (~16 vezes por segundo) e' de sobra pra
-- um apagamento parecer continuo, e custa quase nada com cem baloes. Refazer
-- a conta a cada quadro seria trabalho jogado fora: rotulo nao e' animacao.
local INTERVALO = 0.06

local camera = workspace.CurrentCamera

--[[ As transparencias ORIGINAIS de cada balao.

	Precisam ser lidas UMA vez, na primeira vez que vemos o balao, e guardadas:
	depois disso quem mexe nelas e' este arquivo, e reler viraria uma cobra
	comendo o proprio rabo -- o valor "original" seria o que sobrou do quadro
	anterior, e o rotulo iria apagando ate' sumir de vez sem nunca mais voltar.

	Tabela de chave FRACA: o ciclo apaga cem avatares de uma vez, e sem isto ela
	seguraria cem baloes destruidos na memoria ate' o fim da live. ]]
type Pintura = {
	fundo: Frame?,
	fundoBase: number,
	textos: { { rotulo: TextLabel, textoBase: number, tracoBase: number } },
}

local pinturas: { [Instance]: Pintura } = setmetatable({}, { __mode = "k" }) :: any

local function pinturaDe(balao: BillboardGui): Pintura
	local guardada = pinturas[balao]
	if guardada then
		return guardada
	end

	local nova: Pintura = { fundo = nil, fundoBase = 0, textos = {} }
	local fundo = balao:FindFirstChildOfClass("Frame")
	if fundo then
		nova.fundo = fundo
		nova.fundoBase = fundo.BackgroundTransparency
		for _, filho in ipairs(fundo:GetChildren()) do
			if filho:IsA("TextLabel") then
				table.insert(nova.textos, {
					rotulo = filho,
					textoBase = filho.TextTransparency,
					tracoBase = filho.TextStrokeTransparency,
				})
			end
		end
	end

	pinturas[balao] = nova
	return nova
end

--[[ Pinta o balao com `alpha` de opacidade: 1 = como o servidor o criou,
	0 = invisivel.

	Apaga o FUNDO e o TEXTO juntos, e nao so' o texto. Um balao preto vazio
	flutuando em cima da cabeca de alguem e' pior que o nome: vira um borrao sem
	informacao nenhuma, e a formacao continua parecendo uma parede. ]]
local function pintar(balao: BillboardGui, alpha: number)
	if alpha <= 0.02 then
		if balao.Enabled then
			balao.Enabled = false
		end
		return
	end

	if not balao.Enabled then
		balao.Enabled = true
	end

	local pintura = pinturaDe(balao)
	local fundo = pintura.fundo
	if fundo and fundo.Parent then
		fundo.BackgroundTransparency = 1 - (1 - pintura.fundoBase) * alpha
	end
	for _, item in ipairs(pintura.textos) do
		if item.rotulo.Parent then
			item.rotulo.TextTransparency = 1 - (1 - item.textoBase) * alpha
			item.rotulo.TextStrokeTransparency = 1 - (1 - item.tracoBase) * alpha
		end
	end
end

--[[ Onde este rotulo esta' no mundo.

	O Adornee vem primeiro porque e' ele quem manda quando existe; o Parent e' o
	caminho normal aqui (o balao mora dentro da Head). Devolve nil pra balao que
	ja' saiu do jogo -- e sair do jogo e' rotina: a formacao inteira e' apagada a
	cada ciclo. ]]
local function ondeEsta(balao: BillboardGui): Vector3?
	local ancora = balao.Adornee or balao.Parent
	if ancora and ancora:IsA("BasePart") then
		return ancora.Position
	end
	if ancora and ancora:IsA("Model") then
		local ok, pivo = pcall(function()
			return ancora:GetPivot().Position
		end)
		if ok and pivo then
			return pivo
		end
	end
	return nil
end

-- Reaproveitada entre as voltas em vez de criada de novo a cada 0.06s: cem
-- tabelas por segundo jogadas fora dao trabalho ao coletor de lixo bem no meio
-- da transmissao.
local candidatos: { {
	balao: BillboardGui,
	razao: number,
	fileira: number?,
	ancora: Vector3,
} } = {}

local function fileiraDaFrente(): number?
	if ROTULO.SO_FILEIRA_DA_FRENTE == false then
		return nil          -- desligado: vale o comportamento antigo
	end
	local quantas = tonumber(workspace:GetAttribute("FileirasNaTela")) or 0
	if quantas <= 0 then
		return nil
	end
	-- `FileirasNaTela` e' a CONTAGEM; a da frente e' a ultima, entao -1.
	return quantas - 1
end

--[[ ═══════════════════════════════════════════════════════════════════
	O CHOQUE ENTRE FILEIRAS
	═══════════════════════════════════════════════════════════════════

	As regras acima decidem QUANTOS nomes aparecem. Nenhuma delas olha ONDE
	eles caem na tela -- e e' ai' que nasce o embolamento.

	A conta que explica: com a lente na altura do peito, todo balao esta' na
	mesma altura do MUNDO (uns 8 studs). Quanto mais longe, menor a elevacao --
	entao o balao da fileira de tras desce na tela e vai pousar exatamente em
	cima da cabeca de quem esta' na frente. Nao e' acaso nem azar de posicao: e'
	geometria, e acontece toda vez.

	A resposta e' medir o RETANGULO de cada balao na tela e dar o lugar a quem
	esta' mais perto. Quem chegou depois e cairia por cima simplesmente nao
	acende -- e' melhor um nome a menos que dois ilegiveis empilhados.

	POR QUE ISTO NAO SUBSTITUI AS OUTRAS REGRAS: elas resolvem outra coisa. O
	SO_FILEIRA_DA_FRENTE escolhe QUEM tem direito a nome, o MAX_NA_TELA limita
	o CUSTO de desenho, e isto aqui cuida da LEITURA. Os tres juntos e' que
	fazem a tela ficar limpa.

	E os tres podem discordar: uma fileira de dez cabe no teto e mesmo assim
	dois vizinhos podem se encostar num angulo fechado. Quando isso acontece,
	quem esta' mais perto da lente fica. ]]

-- Os retangulos ja' ocupados nesta volta. Reaproveitado entre as voltas pelo
-- mesmo motivo da tabela `candidatos`: nao dar trabalho ao coletor de lixo no
-- meio da transmissao.
local ocupados: { { x: number, y: number, l: number, a: number } } = {}

--[[ O retangulo que este balao ocupa na tela, em pixels. `nil` se ele esta'
	atras da lente ou fora do quadro.

	O CENTRO E' O DO BALAO, e nao o da cabeca: o balao mora `StudsOffsetWorldSpace`
	acima do ponto de ancoragem, e medir o choque na altura errada deixaria
	passar exatamente as sobreposicoes que este codigo veio evitar.

	O tamanho sai da propria peca: um BillboardGui com Size em `fromScale` mede
	STUDS DO MUNDO, entao os pixels na tela sao os studs vezes a escala da
	perspectiva -- que e' a mesma conta que o motor faz pra desenha-lo. Assim o
	balao do gigante (que e' maior de proposito) reserva o espaco que ele
	realmente ocupa. ]]
local function retanguloDe(balao: BillboardGui, ancora: Vector3)
	: { x: number, y: number, l: number, a: number }?
	local centro = ancora + balao.StudsOffsetWorldSpace
	local ponto, naTela = camera:WorldToViewportPoint(centro)
	if not naTela then
		return nil
	end

	local tela = camera.ViewportSize
	local meia = math.tan(math.rad(camera.FieldOfView) / 2)
	if ponto.Z <= 0.01 or meia <= 0 then
		return nil
	end
	-- Quantos pixels vale um stud a esta profundidade.
	local porStud = tela.Y / (2 * ponto.Z * meia)

	local folga = tonumber(ROTULO.FOLGA_SOBREPOR) or 6
	local l = balao.Size.X.Scale * porStud + folga
	local a = balao.Size.Y.Scale * porStud + folga
	return { x = ponto.X - l / 2, y = ponto.Y - a / 2, l = l, a = a }
end

local function bateEm(r: any, outro: any): boolean
	return r.x < outro.x + outro.l
		and outro.x < r.x + r.l
		and r.y < outro.y + outro.a
		and outro.y < r.y + r.a
end

--[[ Guarda o lugar se ele estiver livre. Devolve `false` quando o balao cairia
	por cima de um que ja' esta' aceso -- e ai' quem chama simplesmente nao
	acende este. ]]
local function reservar(r: any?): boolean
	if not r then
		return false
	end
	if ROTULO.SEM_SOBREPOR == false then
		return true
	end
	for _, outro in ipairs(ocupados) do
		if bateEm(r, outro) then
			return false
		end
	end
	table.insert(ocupados, r)
	return true
end

local function atualizar()
	--[[ A camera pode trocar (o Studio troca ao entrar e sair do Play). Reler o
		CurrentCamera a cada volta evita o caso em que este arquivo fica medindo
		distancia a partir de uma camera que nao existe mais -- e ai' os rotulos
		somem todos, ou aparecem todos, sem nada explicando por que. ]]
	camera = workspace.CurrentCamera
	if not camera then
		return
	end

	local deOnde = camera.CFrame
	local olho = deOnde.Position

	table.clear(candidatos)
	table.clear(ocupados)
	local daFrente = fileiraDaFrente()

	for _, item in ipairs(CollectionService:GetTagged(MARCA_ROTULO)) do
		local balao = item :: BillboardGui
		if balao:IsA("BillboardGui") and balao.Parent then
			--[[ QUEM A CAMERA ESTA' MOSTRANDO PASSA NA FRENTE DE TUDO.

				Sem rodizio, sem teto de quantidade, sem apagamento por
				distancia. A marca vem do proprio Camera.client.luau (ver
				`marcarAlvo` la'), que e' quem SABE quem esta' em cena -- todas
				as regras deste arquivo sao aproximacoes disso.

				E' a resposta final pra "o nick de quem comentou nao aparece":
				enquanto a lente estiver nele, o nome esta' aceso, por
				construcao e nao por coincidencia de numeros. ]]
			if balao:GetAttribute("AlvoDaCamera") then
				pintar(balao, 1)
				--[[ E RESERVA O LUGAR DELE ANTES DE TODO MUNDO. Ele acende de
					qualquer jeito, entao quem tem que sair da frente sao os
					outros -- sem isto, um balao da fileira de tras poderia
					pousar exatamente em cima do unico nome que a live PRECISA
					mostrar. ]]
				local ancora = ondeEsta(balao)
				if ancora then
					reservar(retanguloDe(balao, ancora))
				end
				continue
			end
			--[[ A FILEIRA entra como DADO, e nao como filtro.

				Antes o rodizio cortava aqui, antes de medir distancia. Era mais
				barato e estava errado: cortando neste ponto, nao havia como
				saber se o balao que estava sendo apagado era justamente o de
				quem a camera estava mostrando. Agora a fileira viaja junto com
				o candidato e quem decide e' o laco de baixo, que ja' tem a
				ordem de quem esta' mais perto da lente.

				O `colosso` continua de fora do rodizio de proposito: ele nasce
				atras da grade, sem fileira nenhuma, e e' o presente mais caro
				da live -- deixa-lo esperando a vez de uma fileira que ele nao
				tem faria o gigante ficar anonimo pra sempre. ]]
			local minha = tonumber(balao:GetAttribute("Fileira"))

			local posicao = ondeEsta(balao)
			if posicao then
				local alcance = tonumber(balao:GetAttribute("Alcance"))
					or ROTULO.DISTANCIA_MAX
				local distancia = (posicao - olho).Magnitude

				--[[ O que esta' ATRAS da camera nao entra na conta.

					Nao e' economia de CPU: e' o teto de quantidade. Um rotulo
					atras da lente nao aparece na tela de jeito nenhum, mas se
					ele contasse, ocuparia um dos lugares do teto -- e o resultado
					seria uma formacao com espaco sobrando na tela e rotulos
					desligados "sem motivo". No Roblox o -Z do CFrame e' pra
					onde a camera olha, entao Z positivo no espaco dela e'
					exatamente o que ficou pra tras. ]]
				local relativo = deOnde:PointToObjectSpace(posicao)
				if relativo.Z <= 0 and distancia < alcance then
					table.insert(candidatos, {
						balao = balao,
						--[[ RAZAO, e nao a distancia crua. Cada rotulo tem o
							proprio alcance, e ordenar por distancia faria o
							boneco grande -- que enxerga mais longe de proposito
							-- perder o lugar pro vizinho de tamanho normal que
							esta' dois studs mais perto. Dividindo pelo alcance,
							a comparacao passa a ser "o quao perto do LIMITE
							DELE cada um esta'", que e' a pergunta certa. ]]
						razao = distancia / math.max(alcance, 1),
						fileira = minha,
						ancora = posicao,
					})
				else
					pintar(balao, 0)
				end
			end
		end
	end

	table.sort(candidatos, function(a, b)
		return a.razao < b.razao
	end)

	local teto = math.max(1, math.floor(tonumber(ROTULO.MAX_NA_TELA) or 12))

	for posto, item in ipairs(candidatos) do
		--[[ A FILEIRA DA FRENTE INTEIRA acende; o resto, nao.

			Sem teto de quantos da fileira e sem revezamento entre eles: se dez
			pessoas estao na fileira que esta' entrando, os dez nicks aparecem.
			Era o pedido, e e' o que a live promete. ]]
		local foraDaVez = daFrente ~= nil
			and item.fileira ~= nil
			and item.fileira ~= daFrente

		--[[ E, POR FIM, O LUGAR NA TELA. Vem depois das outras regras de
			proposito: nao adianta reservar espaco pra um balao que a regra da
			fileira ou o teto ja' iam apagar -- ele estaria segurando um lugar que outro
			poderia usar. Como a lista esta' ordenada por proximidade, quem
			ganha o lugar disputado e' sempre o mais perto da lente. ]]
		if posto > teto or foraDaVez
			or not reservar(retanguloDe(item.balao, item.ancora)) then
			pintar(item.balao, 0)
		else
			-- Quanto o LIMITE de distancia ja' apagou este rotulo.
			local porDistancia = math.clamp(
				(1 - item.razao) / (1 - INICIO_DO_FADE), 0, 1)

			--[[ Quanto o TETO DE QUANTIDADE ja' apagou. Os ultimos lugares do
				orcamento entram e saem apagando em vez de piscar. ]]
			local porPosto = 1
			if posto > teto - FOLGA_DO_TETO then
				porPosto = (teto - posto + 1) / (FOLGA_DO_TETO + 1)
			end

			-- O MENOR dos dois manda: basta um dos limites pedir pra apagar.
			pintar(item.balao, math.min(porDistancia, porPosto))
		end
	end
end

local acumulado = 0

RunService.RenderStepped:Connect(function(dt)
	acumulado += dt
	if acumulado < INTERVALO then
		return
	end
	acumulado = 0

	--[[ Sob pcall porque isto roda pra sempre, a cada 0.06s, no meio de uma
		transmissao ao vivo. Um avatar destruido no instante exato entre o
		`GetTagged` e a leitura da posicao dele levantaria um erro, o
		RenderStepped desconectaria a funcao, e a partir dali TODOS os rotulos
		ficariam congelados no estado em que estavam -- um defeito que aparece
		uma vez a cada mil ciclos e some quando voce vai testar. ]]
	pcall(atualizar)
end)
