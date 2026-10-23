--!strict
--[[
	Cria e remove os avatares.

	COMO A SKIN REAL DA PESSOA VIRA UM BONECO DANCANDO

	  GetHumanoidDescriptionFromUserIdAsync(id)              a aparencia dela
	  CreateHumanoidModelFromDescriptionAsync(desc, R15)     o corpo montado

	Dois passos, e nao o CreateHumanoidModelFromUserIdAsync direto, por um motivo
	so': aquele devolve o rig que a PESSOA usa, R6 ou R15, e nao deixa escolher.
	Uma formacao com R6 e R15 misturados nao consegue dancar a mesma animacao --
	metade ficaria parada no meio da coreografia. Passando pela description, todo
	mundo sai R15 e a formacao dança junta.

	TUDO AQUI PODE FALHAR. As duas chamadas fazem HTTP por baixo e sao limitadas
	pela Roblox. Cada uma vai de pcall, e um avatar que nao carrega e' so' um
	avatar que nao aparece -- nunca um erro que derruba a live.
]]

local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Config"))

local Avatares = {}

export type Avatar = {
	modelo: Model,
	--[[ A posicao dele na lista da Formacao. -1 = fora da grade (o colosso).

		E' um INDICE e nao uma posicao no mundo porque a posicao muda: quando um
		vizinho cresce, a formacao inteira se reacomoda e o CFrame deste avatar
		passa a ser outro. Guardar o CFrame aqui deixaria as duas metades em
		desacordo -- e o sintoma seria um boneco parado no lugar antigo,
		atravessado no novo vizinho. ]]
	indice: number,
	tiktok_id: string,
	nascido: number,
	vida: number,
	prio: number,
	-- O tamanho ATUAL, ja' com todo o crescimento aplicado.
	escala: number,
	--[[ O tamanho que o CORPO tem neste instante.

		Diferente do `escala` durante os poucos decimos de segundo de uma
		animacao de crescimento: o `escala` ja' vale o destino (a formacao
		precisa reservar o espaco antes), enquanto este acompanha o corpo. E' o
		que decide a que altura plantar os pes -- usar o destino aqui faria o
		boneco flutuar acima do palco ate' a animacao alcancar. ]]
	escalaVisual: number,
	-- Um crescimento em andamento cancela o anterior. Ver `Avatares.crescer`.
	geracao: number,
}

--[[ As animacoes existem como INSTANCIAS FIXAS, criadas uma vez.

	Trocar o AnimationId de uma Animation ja' carregada nao afeta as faixas que
	ja' sairam dela, e as proximas cargas viriam de um cache confuso -- o tipo de
	bug que aparece como "as vezes a danca certa, as vezes a antiga". Uma
	instancia por danca mantem cada uma com a sua identidade. ]]
local function novaAnimacao(nome: string, id: number): Animation
	local anim = Instance.new("Animation")
	anim.Name = nome
	anim.AnimationId = "rbxassetid://" .. tostring(id)
	return anim
end

local animacaoPrincipal = novaAnimacao("Principal", Config.ANIMACAO)
local animacaoReserva = novaAnimacao("Reserva", Config.ANIMACAO_RESERVA)
local animacaoEspecial = novaAnimacao("Especial", Config.ANIMACAO_ESPECIAL)

--[[ Uma danca por PRESENTE: "rosquinha", "oculos", "galaxia".

	E' o que faz o presente ser visivel de longe. Quem assiste nao le' o nome do
	presente no rotulo -- ele e' pequeno demais no video de um celular. O que se
	ve' e' o PASSO mudar: chegou alguem dancando diferente do resto da formacao,
	entao alguem pagou por alguma coisa.

	Montado a partir do Config.DANCAS, e nao escrito na mao aqui, pra adicionar
	uma danca nova ser uma linha no Config -- e nao uma linha no Config mais
	outra aqui que alguem vai esquecer. ]]
local dancasDePresente: { [string]: Animation } = {}
for nome, id in pairs(Config.DANCAS) do
	dancasDePresente[nome] = novaAnimacao("Danca_" .. nome, id)
end

-- Qual danca vale de verdade. Decidido UMA vez, na subida (ver `escolherDanca`).
local animacaoNormal = animacaoPrincipal

-- Qual danca vale AGORA. Vale tambem pra quem nascer no meio da troca: e'
-- sempre esta variavel que o `dancar` consulta.
local naEspecial = false
local jaAvisouDaAnimacao = false

--[[ O RELOGIO COMUM DA DANCA.

	Todo mundo toca a mesma animacao a partir deste instante de referencia. E' o
	que permite um avatar que chegou agora entrar no MESMO PASSO de quem ja'
	estava dancando: em vez de comecar do zero, ele entra no ponto em que a
	musica ja' esta'.

	Sem isso, cada avatar comeca a coreografia no proprio tempo e a formacao vira
	cem pessoas dancando desencontradas -- que e' exatamente o oposto do efeito
	que faz a live parecer produzida. ]]
function Avatares.iniciarRelogio()
	workspace:SetAttribute("EpocaDanca", workspace:GetServerTimeNow())
end

--[[ A animacao principal carrega mesmo? Se nao, cai pra reserva.

	POR QUE ESTE TESTE PRECISA EXISTIR

	`LoadAnimation` NAO falha quando o asset e' inacessivel. Ele devolve um
	AnimationTrack normal, o `Play()` funciona, o `IsPlaying` diz true -- e o
	boneco fica parado em pe'. O download do asset acontece depois, por baixo, e
	quando ele e' negado ninguem avisa o codigo.

	O unico sinal confiavel e' o `Length`: enquanto o asset nao chega, ele fica
	em 0. Asset que nunca chega fica em 0 pra sempre.

	Isso importa porque a danca principal e' de TERCEIRO (ver o Config). Se a
	permissao dela cair no meio de uma live, sem este teste a formacao inteira
	congela sem uma linha de erro. Com ele, a live troca de danca sozinha e
	segue.

	Roda UMA vez, na subida, num boneco de mentira que e' destruido logo depois. ]]
local ESPERA_DE_CARGA_S = 6

--[[ Relogio de PAREDE, e nao os.clock.

	Em Luau o os.clock devolve tempo de CPU, e nao tempo que passou de verdade.
	Num servidor de Studio parado esperando download de asset -- que e'
	exatamente a situacao aqui -- ele anda MUITO mais devagar que o relogio: a
	espera de "6 segundos" virava dezenas de segundos reais, e a primeira coisa
	que quem comprou via ao apertar Play era um Studio aparentemente travado,
	antes do primeiro boneco. ]]
local function relogio(): number
	return workspace:GetServerTimeNow()
end

local function carrega(anim: Animation): boolean
	local modelo = Instance.new("Model")
	-- Nome de verdade: durante os 6 segundos do teste estes bonecos de mentira
	-- aparecem no Explorer do Studio, e "Model, Model, Model" no meio da subida
	-- parece coisa quebrada.
	modelo.Name = "TesteDeDanca_" .. anim.Name
	local humanoide = Instance.new("Humanoid")
	humanoide.Parent = modelo
	local animador = Instance.new("Animator")
	animador.Parent = humanoide
	-- Precisa estar no DataModel: um Animator solto nao baixa asset nenhum.
	modelo.Parent = workspace

	local carregou = false
	local ok, faixa = pcall(function()
		return animador:LoadAnimation(anim)
	end)
	if ok and faixa then
		local limite = relogio() + ESPERA_DE_CARGA_S
		while faixa.Length == 0 and relogio() < limite do
			task.wait(0.1)
		end
		carregou = faixa.Length > 0
	end

	modelo:Destroy()
	return carregou
end

--[[ Confere TODAS as dancas de uma vez, e derruba pro padrao as que falharem.

	EM PARALELO, e isso importa: cada conferencia espera ate' 6 segundos pelo
	download. Uma depois da outra, seis dancas dariam mais de meio minuto de tela
	preta na subida -- e quem comprou o kit veria o Studio "travado" logo no
	primeiro Play, que e' o pior primeiro minuto possivel. Todas juntas, a espera
	continua sendo a de uma so'.

	Uma danca de presente que nao carrega vira a danca padrao em vez de virar um
	boneco parado em pe'. E' a mesma decisao da reserva la' de cima: a live nunca
	para por causa de um asset. ]]
function Avatares.escolherDanca()
	local resultado: { [string]: boolean } = {}
	local faltam = 0

	local function conferir(chave: string, anim: Animation)
		faltam += 1
		task.spawn(function()
			resultado[chave] = carrega(anim)
			faltam -= 1
		end)
	end

	conferir("principal", animacaoPrincipal)
	conferir("especial", animacaoEspecial)
	for nome, anim in pairs(dancasDePresente) do
		conferir("presente:" .. nome, anim)
	end

	-- A folga de 2s cobre o tempo entre agendar as tarefas e elas comecarem; sem
	-- ela, uma subida engasgada sairia daqui achando que tudo falhou.
	local limite = relogio() + ESPERA_DE_CARGA_S + 2
	while faltam > 0 and relogio() < limite do
		task.wait(0.1)
	end

	if resultado["principal"] then
		animacaoNormal = animacaoPrincipal
		print("[avatares] danca principal OK (" .. tostring(Config.ANIMACAO) .. ")")
	else
		animacaoNormal = animacaoReserva
		warn("[avatares] a danca principal (" .. tostring(Config.ANIMACAO) .. ") nao "
			.. "carregou -- usando a reserva da Roblox (" .. tostring(Config.ANIMACAO_RESERVA)
			.. "). Isso e' PERMISSAO do asset: ele e' de outro criador, e precisa ser "
			.. "compartilhado com esta experiencia pelo Creator Hub.")
	end

	if not resultado["especial"] then
		animacaoEspecial = animacaoReserva
		warn("[avatares] a danca ESPECIAL (" .. tostring(Config.ANIMACAO_ESPECIAL)
			.. ") nao carregou -- a troca geral vai usar a reserva.")
	end

	local ligadas = {}
	for nome, _ in pairs(dancasDePresente) do
		if resultado["presente:" .. nome] then
			table.insert(ligadas, nome)
		else
			-- Tirar do mapa E' o fallback: o `dancaDe` nao acha a chave e devolve
			-- a danca padrao, sem nenhum `if` extra no caminho quente.
			dancasDePresente[nome] = nil
			warn("[avatares] a danca do presente '" .. nome .. "' nao carregou -- "
				.. "quem mandar esse presente vai dancar a danca padrao. Confira o "
				.. "ID em Config.luau (DANCAS).")
		end
	end
	table.sort(ligadas)
	print("[avatares] dancas de presente prontas: " ..
		(if #ligadas > 0 then table.concat(ligadas, ", ") else "nenhuma"))
end

function Avatares.epoca(): number
	return (workspace:GetAttribute("EpocaDanca") :: number) or 0
end

function Avatares.trocarDanca(especial: boolean)
	naEspecial = especial
end

--[[ "FF2D6F" -> Color3. Lixo vira branco.

	Nome sem cor e' muito melhor que avatar sem nome: um hexadecimal torto vindo
	do painel nao pode fazer o rotulo inteiro sumir. ]]
local function corDoHex(hex: string?): Color3
	local limpo = string.gsub(tostring(hex or ""), "#", "")
	if #limpo ~= 6 then
		return Color3.new(1, 1, 1)
	end
	local n = tonumber(limpo, 16)
	if not n then
		return Color3.new(1, 1, 1)
	end
	return Color3.fromRGB(math.floor(n / 65536) % 256, math.floor(n / 256) % 256, n % 256)
end

--[[ A marca que o CLIENTE usa pra achar todos os rotulos sem varrer o Workspace.

	O nome esta' escrito igual no Rotulos.client.luau, e os dois PRECISAM
	combinar: uma letra diferente e o cliente simplesmente nao acha rotulo
	nenhum, sem erro em lugar nenhum -- os baloes ficam todos ligados e o
	excesso volta calado.

	CollectionService, e nao um Folder com referencias: o ciclo apaga cem
	avatares de uma vez, e a marca sai junto com o objeto destruido sozinha. Uma
	lista na mao ficaria segurando cem baloes mortos na memoria. ]]
local MARCA_ROTULO = "RotuloDaLive"

--[[ O balao com o nome, em cima da cabeca.

	Duas linhas: o @ do TikTok em cima e o nick do Roblox embaixo. As duas
	importam, e por motivos diferentes -- o @ e' como a pessoa se reconhece no
	chat, e o nick e' a prova de que aquele boneco e' mesmo a skin dela. ]]
--[[ Poe o balao no tamanho e na altura certos pro tamanho ATUAL do boneco.

	SEPARADO DA CRIACAO PORQUE O TAMANHO MUDA DEPOIS.

	Tanto o tamanho quanto a altura do balao sao medidos em STUDS DO MUNDO --
	eles NAO crescem junto quando o modelo cresce. Enquanto o avatar nascia e
	morria do mesmo tamanho, calcular isto uma vez bastava. Com o crescimento
	por presente, nao basta mais: o boneco que recebeu quatro galaxias fica
	quatro vezes maior e o balao dele continuaria do tamanho de nascimento --
	um selo minusculo perdido no peito de um gigante, justamente no avatar que
	mais interessa ler.

	Entao esta funcao roda no nascimento E a cada crescimento.

	A raiz quadrada na LARGURA e' de proposito. A altura precisa crescer junto
	com o corpo (senao o balao entra na cabeca), mas a largura crescer igual
	faria o rotulo de um gigante tapar os vizinhos dos dois lados. ]]
local function ajustarRotulo(balao: BillboardGui, escala: number)
	local tamanho = math.max(escala, 1)
	balao.Size = UDim2.fromScale(
		Config.ROTULO.LARGURA * math.sqrt(tamanho), 2.2 * math.sqrt(tamanho))
	balao.StudsOffsetWorldSpace = Vector3.new(0, Config.ROTULO.ALTURA * tamanho, 0)

	--[[ O ALCANCE deste rotulo: de que distancia ele ainda aparece.

		RAIZ QUADRADA, e nao proporcional, porque e' a MESMA LEI QUE A CAMERA
		USA PRA RECUAR de um boneco grande (ver `destinoSeguir` no
		Camera.client.luau). As duas contas se cancelam: o avatar de escala 4
		fica duas vezes mais longe da lente, e o rotulo dele alcanca duas vezes
		mais longe -- entao ele fica legivel na mesma medida que o de escala 1.

		Sem isso, o presente MAIS CARO da live era justamente o unico a ficar
		sem nome: o colosso empurra a camera pra alem de 130 studs, e um alcance
		fixo de 68 nunca chegava la'.

		E COM TETO (ROTULO.ESCALA_TETO), senao o colosso de escala 40 ganhava um
		rotulo visivel de qualquer canto do mapa -- inclusive no plano aberto,
		onde a regra e' que os nomes somem.

		Gravado como ATRIBUTO porque quem decide de verdade se este rotulo
		aparece agora e' o cliente (Rotulos.client.luau): a distancia da camera
		muda 60 vezes por segundo, e isso e' conta do lado de quem esta' vendo,
		nao do servidor. O MaxDistance abaixo continua como rede de seguranca --
		se o script do cliente nao subir, o motor da Roblox ainda corta os
		rotulos de longe sozinho, em vez de desenhar cem deles. ]]
	local alcance = Config.ROTULO.DISTANCIA_MAX
		* math.sqrt(math.clamp(tamanho, 1, Config.ROTULO.ESCALA_TETO))
	balao:SetAttribute("Alcance", alcance)
	balao.MaxDistance = alcance
end

local function porRotulo(modelo: Model, spawn: any, cor: Color3, escala: number)
	local cabeca = modelo:FindFirstChild("Head")
	if not cabeca or not cabeca:IsA("BasePart") then
		return
	end

	local balao = Instance.new("BillboardGui")
	balao.Name = "Rotulo"
	balao.AlwaysOnTop = true
	ajustarRotulo(balao, escala)
	CollectionService:AddTag(balao, MARCA_ROTULO)
	balao.Parent = cabeca

	local fundo = Instance.new("Frame")
	fundo.Size = UDim2.fromScale(1, 1)
	fundo.BackgroundColor3 = Config.ROTULO.FUNDO
	fundo.BackgroundTransparency = Config.ROTULO.TRANSPARENCIA
	fundo.BorderSizePixel = 0
	fundo.Parent = balao

	local canto = Instance.new("UICorner")
	canto.CornerRadius = UDim.new(0, 8)
	canto.Parent = fundo

	local temNick = spawn.nick_roblox ~= ""

	local arroba = Instance.new("TextLabel")
	arroba.BackgroundTransparency = 1
	arroba.Size = UDim2.fromScale(1, if temNick then 0.55 else 1)
	arroba.Position = UDim2.fromScale(0, 0)
	arroba.Text = spawn.nickname
	-- A cor do presente sobe pro nome: e' o sinal mais barato de "esta pessoa
	-- pagou", legivel de relance mesmo num celular assistindo a live.
	arroba.TextColor3 = cor
	arroba.TextScaled = true
	arroba.Font = Enum.Font.GothamBold
	arroba.TextStrokeTransparency = 0.4
	arroba.Parent = fundo

	if temNick then
		local nick = Instance.new("TextLabel")
		nick.BackgroundTransparency = 1
		nick.Size = UDim2.fromScale(1, 0.45)
		nick.Position = UDim2.fromScale(0, 0.55)
		nick.Text = spawn.nick_roblox
		nick.TextColor3 = Config.ROTULO.COR_NICK
		nick.TextScaled = true
		nick.Font = Enum.Font.Gotham
		nick.TextStrokeTransparency = 0.5
		nick.Parent = fundo
	end
end

--[[ ───────────────────────── A AURA ─────────────────────────

	SO' pra quem mandou presente. Quem so' comentou nunca brilha, e isso e'
	regra: se todo mundo brilha, o brilho deixa de significar alguma coisa -- e a
	aura existe justamente pra separar, num relance, quem pagou de quem nao
	pagou.

	E' UM Highlight, E MAIS NADA.

	Ja' foi um SelectionBox por peca do corpo. Aquilo nao desenhava contorno:
	desenhava um CAIXOTE DE ARAME em volta de cada peca -- uma caixa no braco,
	outra na perna, outra na cabeca, e mais uma em cada acessorio, cabelo e
	chapeu. O boneco aparecia dentro de uma gaiola retangular, e o "brilho" so'
	atrapalhava a skin, que e' o produto inteiro deste jogo.

	Depois foi contorno + luz + faiscas. Tambem saiu. Luz de verdade nao respeita
	o corpo de ninguem: ela vaza pro chao, pinta os vizinhos e lava a cor da
	roupa da pessoa. Com cem bonecos, cem luzes coloridas viram uma mancha onde
	nao da' pra distinguir mais ninguem -- inclusive quem pagou.

	O Highlight faz o que as duas versoes tentavam fazer, e so' isso: segue a
	SILHUETA do modelo, acessorio incluido, e para exatamente onde o boneco para.
	Um objeto por avatar, sem particula, sem luz.

	E o Occluded (em vez de AlwaysOnTop) e' o que impede a aura de quem esta' na
	ULTIMA fileira de atravessar as fileiras da frente. Com AlwaysOnTop a
	multidao vira uma sopa de contornos flutuando por cima uns dos outros. ]]

-- Marca pra contar as auras vivas sem guardar contador nenhum: um ciclo apaga
-- cem avatares de uma vez, e um contador na mao ficaria dessincronizado na
-- primeira limpeza -- justamente onde ninguem olharia.
local MARCA_CONTORNO = "AuraContorno"

local function aurasVivas(): { Instance }
	local vivas = {}
	for _, item in ipairs(CollectionService:GetTagged(MARCA_CONTORNO)) do
		-- Filtra o que ja' saiu do jogo. Destruir tira as marcas sozinho, mas
		-- depender disso deixaria o teto errado por um detalhe do motor que
		-- ninguem lembraria de conferir.
		if item.Parent then
			table.insert(vivas, item)
		end
	end
	return vivas
end

--[[ Cabe mais uma aura? Se nao couber, o presente MAIS FORTE toma o lugar.

	O motor da Roblox desenha no maximo 31 Highlight de cada vez, e do 32 em
	diante ele nao desenha -- sem erro, sem aviso. Um teto simples ("cheio, entao
	este fica sem") daria o pior resultado possivel numa live cheia: vinte rosas
	de 1 moeda chegam primeiro, enchem o orcamento, e a galaxia de 1000 que
	chegar depois e' justamente a que fica sem aura nenhuma.

	Tirando a mais fraca, o orcamento sempre fica com os presentes que mais
	importam. Quem perde a aura e' sempre o mais barato que ainda esta' na tela. ]]
local function cabeAura(forca: number): boolean
	local vivas = aurasVivas()
	if #vivas < Config.BRILHO.MAX_CONTORNOS then
		return true
	end

	local maisFraca, menorForca = nil, math.huge
	for _, item in ipairs(vivas) do
		local f = tonumber(item:GetAttribute("Forca")) or 0
		if f < menorForca then
			menorForca, maisFraca = f, item
		end
	end

	-- `<` e nao `<=`: em empate quem ja' esta' na tela fica. Trocar auras entre
	-- iguais so' faria a formacao piscar sem mudar nada de util.
	if maisFraca and menorForca < forca then
		maisFraca:Destroy()
		return true
	end
	return false
end

local function porBrilho(modelo: Model, forca: number, cor: Color3)
	if forca < Config.BRILHO.CONTORNO_DESDE or forca <= 0 then
		return
	end
	if not cabeAura(forca) then
		return
	end

	--[[ Nada de caixa, nada de moldura, nada de sobra pra fora: o Highlight
		desenha exatamente a silhueta do modelo, braco por braco, cabelo, chapeu
		e acessorio incluidos. Se a pessoa esta' de asas, a aura tem asas.

		A cor vem inteira do presente -- vale igual pra rosa, rosquinha, oculos e
		galaxia, e pra qualquer cor que voce puser no painel. Nao existe nenhuma
		cor tratada de forma especial aqui.

		Nada disto depende do TAMANHO do boneco: o contorno e' desenhado em cima
		da geometria, entao um colosso ganha um colosso contornado sem precisar
		de nenhum ajuste de escala -- que era o que a luz e as faiscas exigiam. ]]
	local contorno = Instance.new("Highlight")
	contorno.Name = "AuraContorno"
	contorno.Adornee = modelo
	contorno.DepthMode = Enum.HighlightDepthMode.Occluded
	contorno.OutlineColor = cor
	contorno.FillColor = cor
	contorno.OutlineTransparency = math.clamp(
		Config.BRILHO.LINHA_BASE - Config.BRILHO.LINHA_POR_FORCA * forca, 0, 1)
	contorno.FillTransparency = math.clamp(
		Config.BRILHO.PREENCHIMENTO_BASE
			- Config.BRILHO.PREENCHIMENTO_POR_FORCA * forca, 0.85, 1)
	-- A forca fica gravada: e' por ela que o `cabeAura` sabe qual sacrificar.
	contorno:SetAttribute("Forca", forca)
	CollectionService:AddTag(contorno, MARCA_CONTORNO)
	contorno.Parent = modelo
end

--[[ Qual danca este boneco deve estar dancando AGORA.

	A ordem manda: a troca geral (o presente que muda a formacao inteira) vence
	tudo, porque ela e' um momento da live e nao uma caracteristica do avatar.
	Fora dela, cada um volta pra danca do PROPRIO presente -- que fica guardada
	no atributo, e nao numa tabela paralela, justamente pra sobreviver a' troca
	geral e voltar certa quando ela acabar.

	Guardar numa tabela `modelo -> danca` teria um custo escondido: a formacao e'
	apagada inteira a cada ciclo, e a tabela ficaria segurando cem modelos
	destruidos na memoria ate' alguem lembrar de limpa-la. ]]
--[[ A danca escolhida no PAINEL pra um papel (padrao ou especial), se ela
	existir e tiver carregado. nil = usa a do Config.

	As dancas que nao carregaram foram TIRADAS do `dancasDePresente` la' no
	`escolherDanca` -- entao um nome que nao esta' mais no mapa cai sozinho na
	reserva, sem nenhum `if` extra aqui. E' a mesma rede que protege o campo
	`danca` de um presente. ]]
local function dancaDoPainel(atributo: string): Animation?
	local nome = workspace:GetAttribute(atributo)
	if type(nome) == "string" and nome ~= "" then
		return dancasDePresente[nome]
	end
	return nil
end

local function dancaDe(modelo: Model): Animation
	if naEspecial then
		return dancaDoPainel("DancaEspecial") or animacaoEspecial
	end
	local nome = modelo:GetAttribute("Danca")
	if type(nome) == "string" and nome ~= "" then
		local propria = dancasDePresente[nome]
		if propria then
			return propria
		end
	end
	--[[ A DANCA DE QUEM SO' COMENTOU tambem sai do painel.

		Ela era fixa no Config (`ANIMACAO`), e isso deixava o painel oferecendo
		escolha de passo pra presente e nenhuma pra o passo que a MAIORIA da
		formacao dança -- que e' o que aparece na tela 90% do tempo. Escolhida
		no painel, trocar o clima da live inteira e' um clique.

		A ANIMACAO do Config continua sendo o padrao e a reserva: sem escolha no
		painel, ou com uma escolha que nao carregou, e' ela que toca. ]]
	return dancaDoPainel("DancaPadrao") or animacaoNormal
end

--[[ Poe o avatar pra dancar, no passo em que a formacao ja' esta'.

	`TimePosition` e' o pulo do gato: em vez de comecar do zero, o avatar entra no
	ponto da coreografia que o relogio comum indica. ]]
local function dancar(modelo: Model)
	local humanoide = modelo:FindFirstChildOfClass("Humanoid")
	if not humanoide then
		return
	end

	local animador = humanoide:FindFirstChildOfClass("Animator")
	if not animador then
		animador = Instance.new("Animator")
		animador.Parent = humanoide
	end

	--[[ PARA o que ja' estava tocando ANTES de por a proxima.

		Sem isto, cada troca de danca SOMA uma faixa em cima da anterior em vez
		de substitui-la. Duas animacoes tocando no mesmo Humanoid nao dao erro:
		elas se misturam por peso, e o boneco fica tremendo entre dois passos --
		um defeito que so' aparece DEPOIS da primeira troca geral da live, ou
		seja, exatamente no momento mais caro dela, e que some quando voce testa
		de novo do zero. ]]
	for _, tocando in ipairs((animador :: Animator):GetPlayingAnimationTracks()) do
		tocando:Stop(0.15)
	end

	local ok, faixa = pcall(function()
		return (animador :: Animator):LoadAnimation(dancaDe(modelo))
	end)

	if not ok or not faixa then
		-- Avisa UMA vez. Sem o `jaAvisouDaAnimacao`, cem avatares que falham
		-- viram cem warnings identicos e o Output fica ilegivel justamente
		-- quando voce precisa dele.
		if not jaAvisouDaAnimacao then
			jaAvisouDaAnimacao = true
			warn("[avatares] a animacao nao carregou. Se o ID for de um emote "
				.. "do catalogo (tipo 61), ele NAO funciona aqui -- so' o ID da "
				.. "Animation (tipo 24) que mora dentro dele. Veja o Config.luau.")
		end
		return
	end

	faixa.Looped = true
	faixa:Play(0.2)

	-- Entra no passo em que todo mundo ja' esta'.
	local decorrido = workspace:GetServerTimeNow() - Avatares.epoca()
	if faixa.Length > 0 then
		faixa.TimePosition = decorrido % faixa.Length
	end
end

--[[ ═══════════ A APARENCIA REAL DA PESSOA ═══════════

	ESTE BLOCO E' O CONSERTO DE "APARECEU UM BONECO QUE NAO E' O MEU".

	O relato era sempre o mesmo: a pessoa comentava o nick e o avatar dela
	nascia certo; quando ela mandava um PRESENTE, nascia um segundo boneco --
	maior, com o nome dela no rotulo -- vestindo uma pele laranja e nenhuma
	roupa. Ou seja: o corpo PADRAO da Roblox no lugar da skin dela.

	A CAUSA E' O LIMITE DE REQUISICAO, E ELE BATE JUSTAMENTE NO PRESENTE

	Montar um avatar sao duas chamadas HTTP por baixo (a description e o
	modelo), e a Roblox limita as duas por servidor. Um comentario avulso passa
	folgado. Um presente NAO vem sozinho: ele vem em combo, com chuva, e no
	modo "ambos" ainda nasce um boneco novo por unidade. Sao dezenas de
	montagens em poucos segundos -- e e' ai' que as chamadas comecam a voltar
	pela metade: o modelo vem, o Humanoid vem, e a ROUPA nao.

	Nada disso levanta erro. O pcall passa, o boneco nasce, dança junto com
	todo mundo -- pelado, com a cor de pele padrao. Do lado de quem pagou, a
	leitura e' de que o jogo trocou a pessoa.

	TRES DEFESAS, NESTA ORDEM:

	1. CACHE POR PESSOA. A aparencia de quem ja' apareceu nesta live nao e'
	   perguntada de novo -- e quem manda presente e' exatamente quem ja'
	   apareceu. Um combo de 20 rosas passou a custar UMA consulta em vez de
	   vinte, e o teto da Roblox deixa de ser alcancado.

	2. TENTA DE NOVO. Falhou, espera e tenta outra vez, com a espera crescendo.
	   E se a consulta falhar mas a pessoa ja' tiver aparecido antes, vale a
	   aparencia guardada: velha por alguns minutos e' infinitamente melhor que
	   nenhuma.

	3. CONFERE SE VEIO VESTIDO. Se a description diz que a pessoa tem roupa e o
	   modelo saiu sem nenhuma, o modelo esta' errado: e' jogado fora e montado
	   de novo. Na ultima tentativa a roupa e' aplicada na mao com o
	   `ApplyDescription`, ja' com o boneco dentro do jogo -- e' o que ele
	   precisa pra baixar os assets.

	E se nem assim vier vestido, o avatar NAO nasce. Um boneco pelado com o
	nome de quem pagou em cima da cabeca e' pior que um boneco a menos. ]]

local TENTATIVAS_DE_MONTAGEM = 3

--[[ Quanto esperar antes de tentar de novo, MULTIPLICADO pela tentativa.

	0.25 e' curto de proposito, e o motivo e' o laco de spawn: ele monta um
	avatar de cada vez, entao todo segundo gasto tentando de novo e' um segundo
	em que NINGUEM nasce. Num apagao de API (que e' quando as tentativas
	acontecem em serie) uma espera generosa aqui vira uma live parada.

	Com 0.25 o pior caso de um avatar que nao vai nascer de jeito nenhum e'
	0.25 + 0.5 nas descricoes e o mesmo nas montagens -- pouco mais de um
	segundo e meio, na mesma ordem de grandeza do `segura` que a live ja' tem
	entre um spawn e outro.

	E a espera NAO acontece depois da ultima tentativa: ali nao existe proxima
	vez, e esperar seria so' atrasar a resposta "nao deu". ]]
local ESPERA_ENTRE_TENTATIVAS = 0.25

--[[ Quanto tempo a aparencia guardada continua valendo.

	Dez minutos: tempo de sobra pra cobrir um combo inteiro (que e' o caso que
	importa) e curto o bastante pra quem trocou de roupa no meio da live
	aparecer com a roupa nova na proxima vez que comentar. ]]
local VALIDADE_APARENCIA_S = 600

--[[ Teto do cache. Uma live de seis horas passa por milhares de pessoas, e
	guardar todas seria segurar milhares de HumanoidDescription na memoria do
	servidor pra sempre. No teto ele e' esvaziado inteiro, e isso e' de
	proposito: quem ainda estiver participando volta pro cache na primeira
	consulta seguinte, e quem foi embora nao volta nunca. ]]
local MAX_APARENCIAS = 400

local aparencias: { [number]: { desc: HumanoidDescription, ate: number } } = {}
local quantasAparencias = 0

--[[ Diagnostico. Quem le' e' o Principal, que manda pro painel: sem isto, um
	avatar que nao nasce e' silencio absoluto dos dois lados da tela. ]]
Avatares.montados = 0
Avatares.remontados = 0
Avatares.falhas = 0

local function aparenciaDe(id: number): HumanoidDescription?
	local guardada = aparencias[id]
	if guardada and relogio() < guardada.ate then
		return guardada.desc
	end

	for tentativa = 1, TENTATIVAS_DE_MONTAGEM do
		local ok, desc = pcall(function()
			return Players:GetHumanoidDescriptionFromUserIdAsync(id)
		end)
		if ok and desc then
			if quantasAparencias >= MAX_APARENCIAS then
				aparencias = {}
				quantasAparencias = 0
			end
			aparencias[id] = { desc = desc, ate = relogio() + VALIDADE_APARENCIA_S }
			quantasAparencias += 1
			return desc
		end
		if tentativa < TENTATIVAS_DE_MONTAGEM then
			task.wait(ESPERA_ENTRE_TENTATIVAS * tentativa)
		end
	end

	-- A consulta nao passou agora, mas esta pessoa ja' apareceu nesta live: a
	-- aparencia vencida vale muito mais que nenhuma.
	return if guardada then guardada.desc else nil
end

--[[ A pessoa tem ALGUMA coisa vestida? (camisa, calca, estampa ou acessorio)

	Existe pra o conferidor nao reprovar quem de fato usa o corpo padrao sem
	roupa nenhuma -- conta nova, avatar recem-criado. Nesse caso "pelado" E' a
	skin real dela, e remontar tres vezes nao mudaria nada alem de gastar o
	limite de requisicao de quem esta' na fila atras. ]]
local function temRoupa(desc: HumanoidDescription): boolean
	if desc.Shirt ~= 0 or desc.Pants ~= 0 or desc.GraphicTShirt ~= 0 then
		return true
	end
	local ok, lista = pcall(function()
		return desc:GetAccessories(true)
	end)
	return ok and type(lista) == "table" and #lista > 0
end

--[[ O modelo que a Roblox devolveu saiu vestido?

	GetChildren e nao GetDescendants: camisa, calca, estampa e acessorio sao
	todos filhos DIRETOS do modelo, e varrer a arvore inteira de um R15 (umas
	oitenta instancias) por avatar seria pagar caro por uma resposta que esta'
	no primeiro nivel. ]]
local function veioVestido(modelo: Model): boolean
	for _, item in ipairs(modelo:GetChildren()) do
		if item:IsA("Shirt") or item:IsA("Pants") or item:IsA("ShirtGraphic")
			or item:IsA("Accessory") then
			return true
		end
	end
	return false
end

local function montar(descricao: HumanoidDescription): Model?
	local ok, modelo = pcall(function()
		return Players:CreateHumanoidModelFromDescriptionAsync(
			descricao, Enum.HumanoidRigType.R15)
	end)
	return if ok then modelo else nil
end

--[[ O tamanho final de um avatar. UM lugar so', e por um motivo concreto.

	Antes esta conta existia em dois lugares: o Principal calculava o tamanho do
	COLOSSO pra saber quantos slots reservar, e o Avatares calculava o dele
	sozinho pra chamar o ScaleTo. So' que o de ca' lia `spawn.escala` e limitava
	em 4 -- entao o colosso, que vem em `spawn.colosso` e pode chegar a 40,
	NUNCA crescia. Ele nascia do tamanho de gente normal, atras da formacao
	inteira, onde ninguem via.

	O presente mais caro do painel simplesmente nao fazia nada, e nao havia erro
	nenhum apontando pra isso. Com a conta num lugar so', os dois lados nao tem
	como discordar de novo.

	O TETO DA ESCALA E' 6, E NAO 4 -- E ISSO TAMBEM ERA UM PAINEL MENTINDO.

	O `ESCALA_MAX` do ponte/regras.py sempre foi 6.0, e a galaxia sai de la'
	com escala 6. Cortando em 4 aqui, o painel mostrava 6, o arquivo gravava 6
	e o jogo desenhava 4: o presente mais caro da live nascia do tamanho do
	segundo mais caro, sem uma linha em lugar nenhum dizendo por que. Os tres
	tetos precisam ser o mesmo numero -- este, o `escala` do Servidor.luau (que
	corta o evento na entrada) e o ESCALA_MAX do Python. ]]
function Avatares.escalaDe(spawn: any): number
	local colosso = tonumber(spawn.colosso) or 0
	if colosso > 0 then
		return math.clamp(colosso, 0.5, 40)
	end
	return math.clamp(tonumber(spawn.escala) or 1, 0.5, 6)
end

--[[ Monta um avatar. Devolve nil se nao deu -- e nao dar continua sendo normal.

	As duas chamadas da Roblox falham de verdade sob limite de requisicao. O que
	mudou (ver o bloco da APARENCIA aqui em cima) e' que agora elas sao
	repetidas, a aparencia e' reaproveitada entre os avatares da mesma pessoa, e
	um boneco que sai sem a roupa dela nao entra em cena. ]]
function Avatares.criar(spawn: any, posicao: CFrame, pai: Instance): Model?
	--[[ O id vem de fora (ponte -> servidor -> HTTP). Zero, negativo ou
		fracionario nao e' "avatar padrao": e' pedido torto, e pedido torto nao
		pode virar um boneco generico com o nome de alguem em cima. ]]
	local id = math.floor(tonumber(spawn.roblox_id) or 0)
	if id <= 0 then
		return nil
	end

	local descricao = aparenciaDe(id)
	if not descricao then
		Avatares.falhas += 1
		return nil
	end
	local vestida = temRoupa(descricao)

	local modelo: Model? = nil
	for tentativa = 1, TENTATIVAS_DE_MONTAGEM do
		local candidato = montar(descricao)
		if candidato then
			if not vestida or veioVestido(candidato) then
				modelo = candidato
				break
			end

			Avatares.remontados += 1
			if tentativa == TENTATIVAS_DE_MONTAGEM then
				--[[ ULTIMO RECURSO: veste na mao.

					O `ApplyDescription` baixa os assets por conta propria, e
					pra isso o boneco precisa estar DENTRO do jogo. Ele entra
					ja' plantado no lugar da grade e com a raiz ancorada --
					solto, ele cairia pelo palco durante o segundo que a
					aplicacao leva, e o que apareceria na live seria um boneco
					afundando no chao. ]]
				local raizTemp = candidato:FindFirstChild("HumanoidRootPart")
				if raizTemp and raizTemp:IsA("BasePart") then
					raizTemp.Anchored = true
				end
				pcall(function()
					candidato:PivotTo(posicao + Vector3.new(0, 3, 0))
				end)
				candidato.Parent = pai

				local humanoideTemp = candidato:FindFirstChildOfClass("Humanoid")
				if humanoideTemp then
					pcall(function()
						humanoideTemp:ApplyDescription(descricao)
					end)
				end
				if veioVestido(candidato) then
					modelo = candidato
					break
				end
			end
			candidato:Destroy()
		end
		if tentativa < TENTATIVAS_DE_MONTAGEM then
			task.wait(ESPERA_ENTRE_TENTATIVAS * tentativa)
		end
	end

	if not modelo then
		Avatares.falhas += 1
		return nil
	end
	Avatares.montados += 1

	modelo.Name = "Avatar_" .. tostring(id)

	local humanoide = modelo:FindFirstChildOfClass("Humanoid")
	if humanoide then
		-- Nada de barra de vida nem de nome padrao: o rotulo proprio ja' diz
		-- quem e', e os dois juntos ficam empilhados e ilegiveis.
		humanoide.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
		humanoide.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
		-- Sem isto o boneco pode ser empurrado pelo vizinho e a formacao
		-- desmancha sozinha ao longo da live.
		humanoide.WalkSpeed = 0
		humanoide.JumpPower = 0
	end

	local escala = Avatares.escalaDe(spawn)
	if escala ~= 1 then
		pcall(function()
			modelo:ScaleTo(escala)
		end)
	end

	--[[ ANCORA SO' O HumanoidRootPart. NUNCA o corpo inteiro.

		Este e' o erro que faz o boneco APARECER e ficar PARADO, congelado numa
		pose, sem nenhuma mensagem de erro em lugar nenhum.

		O motivo: a animacao de um rig R15 acontece pelos Motor6D, que giram uma
		peca em relacao a' outra. E uma peca ANCORADA nao obedece a Motor6D
		nenhum -- ancorar tudo trava a coreografia inteira. A animacao carrega,
		toca, o AnimationTrack diz que esta' rodando, e mesmo assim nada se mexe.

		Ancorando so' a raiz: ela segura o boneco parado no lugar da grade (sem
		cair, sem ser empurrado pelo vizinho) e o resto do corpo continua livre
		pros Motor6D animarem. E' o jeito padrao de fazer figurante estatico.

		Tudo isto DEPOIS do ScaleTo -- redimensionar com peca ancorada briga com
		a fisica e o boneco sai torto ou atravessa o chao. ]]
	for _, peca in ipairs(modelo:GetDescendants()) do
		if peca:IsA("BasePart") then
			peca.Anchored = false
			-- Ninguem colide com ninguem: cem bonecos com colisao ligada se
			-- empurram e a formacao desmancha sozinha em segundos.
			peca.CanCollide = false
			peca.Massless = true
		end
	end

	local raiz = modelo:FindFirstChild("HumanoidRootPart")
	if raiz and raiz:IsA("BasePart") then
		raiz.Anchored = true
	end

	-- PivotTo e nao CFrame direto: o pivo de um modelo R15 esta' no
	-- HumanoidRootPart, e mover peca por peca desmontaria o boneco.
	Avatares.plantar(modelo, posicao, escala)

	--[[ A danca deste presente fica GRAVADA no boneco, antes de ele entrar em
		cena. E' o que faz ele voltar pra danca certa quando uma troca geral
		acaba -- sem isto, todo mundo voltaria pra danca padrao e a rosquinha
		perderia a dela pro resto da vida do avatar. ]]
	modelo:SetAttribute("Danca", tostring(spawn.danca or ""))
	modelo.Parent = pai

	local cor = corDoHex(spawn.cor)
	porRotulo(modelo, spawn, cor, escala)
	porBrilho(modelo, tonumber(spawn.brilho) or 0, cor)
	dancar(modelo)

	return modelo
end

--[[ ───────────────────── O CRESCIMENTO ─────────────────────

	O que o telao promete: "envie presentes e seu personagem cresce".

	COMO UM BONECO CRESCE SEM QUEBRAR

	`Model:ScaleTo` e' o unico caminho certo aqui, e nao mexer no tamanho das
	pecas na mao: ele escala os Motor6D, os Attachment e os acessorios junto.
	Redimensionar peca por peca deixaria o cabelo flutuando ao lado da cabeca e
	a animacao andando em passos do tamanho antigo -- o boneco "cresceria"
	desmontado.

	Tres cuidados que este codigo tem e que nao sao obvios:

	1. OS PES VOLTAM PRO CHAO A CADA PASSO. O ScaleTo escala em torno do PIVO,
	   que num R15 fica na cintura. Sem reposicionar, metade do corpo que
	   cresceu vai pra baixo do piso -- o boneco afunda no palco conforme
	   cresce.

	2. O ROTULO E' REAJUSTADO JUNTO. Ele vive em studs do mundo e nao escala com
	   o modelo (ver `ajustarRotulo`).

	3. UM CRESCIMENTO CANCELA O ANTERIOR. Numa live real chegam varios presentes
	   da mesma pessoa em segundos, e duas interpolacoes rodando ao mesmo tempo
	   no mesmo boneco disputam o ScaleTo a cada quadro: o resultado e' um
	   avatar tremendo entre dois tamanhos, e o final e' o da tarefa que
	   terminar por ultimo -- ou seja, as vezes MENOR do que ja' estava. A
	   `geracao` resolve: cada crescimento novo invalida o que estava correndo.

	Devolve o tamanho final (ja' aplicado logicamente, mesmo que a animacao
	ainda esteja correndo). Quem chama precisa dele na hora pra reacomodar a
	formacao -- esperar a animacao terminar pra so' entao abrir espaco faria o
	boneco crescer POR CIMA dos vizinhos durante a animacao inteira. ]]
local PASSOS_DO_CRESCIMENTO = 14

function Avatares.crescer(avatar: Avatar, destino: number, segundos: number,
	aoPassar: ((number) -> ())?)
	local de = avatar.escala
	local ate = math.max(destino, 0.1)
	if math.abs(ate - de) < 0.01 then
		return
	end

	avatar.geracao += 1
	local minha = avatar.geracao
	-- A escala LOGICA vale desde ja': a formacao precisa reservar o espaco do
	-- tamanho final antes de o corpo chegar la'.
	avatar.escala = ate

	task.spawn(function()
		local modelo = avatar.modelo
		local passos = math.max(1, math.floor(PASSOS_DO_CRESCIMENTO))
		local intervalo = math.max(segundos, 0) / passos

		for i = 1, passos do
			-- Outro presente chegou e comecou um crescimento novo: este aqui
			-- para AGORA, sem tocar em mais nada. Continuar escreveria um
			-- tamanho velho por cima do novo.
			if avatar.geracao ~= minha or not modelo.Parent then
				return
			end

			--[[ Suavizacao "ease-out": rapido no comeco, desacelerando no fim.
				Linear parece mecanico; comecar rapido e' o que faz o
				crescimento ser PERCEBIDO por quem esta' assistindo pelo
				celular, que e' o ponto de ele existir. ]]
			local t = i / passos
			local suave = 1 - (1 - t) * (1 - t)
			local agora = de + (ate - de) * suave

			local ok = pcall(function()
				modelo:ScaleTo(agora)
			end)
			if not ok then
				return
			end
			if aoPassar then
				aoPassar(agora)
			end
			if intervalo > 0 then
				task.wait(intervalo)
			end
		end
	end)
end

--[[ Poe o boneco em pe' no chao, na posicao da grade, no tamanho que ele tem.

	O `3 * escala` e' a distancia do pivo (a cintura de um R15) ate' a sola do
	pe'. Um lugar so' pra esta conta porque ela e' usada no nascimento E a cada
	passo do crescimento, e as duas discordarem faria o boneco afundar no palco
	enquanto cresce. ]]
function Avatares.plantar(modelo: Model, posicao: CFrame, escala: number)
	pcall(function()
		modelo:PivotTo(posicao + Vector3.new(0, 3 * escala, 0))
	end)
end

--[[ O balao deste avatar, pra reajustar quando ele cresce. nil se nao tem. ]]
function Avatares.rotuloDe(modelo: Model): BillboardGui?
	local cabeca = modelo:FindFirstChild("Head")
	if not cabeca then
		return nil
	end
	local balao = cabeca:FindFirstChild("Rotulo")
	return if balao and balao:IsA("BillboardGui") then balao else nil
end

function Avatares.ajustarRotulo(modelo: Model, escala: number)
	local balao = Avatares.rotuloDe(modelo)
	if balao then
		ajustarRotulo(balao, escala)
	end
end

--[[ Em que FILEIRA este avatar esta' agora.

	O cliente le' isto pra mostrar os nomes de uma fileira por vez (ver
	Rotulos.client.luau). Precisa ser reescrito a cada re-layout da formacao:
	quando alguem cresce, os que vinham depois podem mudar de fileira, e um
	rotulo marcado com a fileira antiga apareceria fora da vez -- um nome
	solto no meio de uma fileira sem nomes. ]]
function Avatares.marcarFileira(modelo: Model, fileira: number)
	local balao = Avatares.rotuloDe(modelo)
	if balao then
		balao:SetAttribute("Fileira", fileira)
	end
end

--[[ Troca a danca de TODA a formacao que ja' esta' na tela.

	Reinicia o relogio junto: sem isso, os que ja' estavam entrariam na animacao
	nova no ponto da ANTIGA, e a troca sairia desencontrada logo no instante em
	que ela mais precisa parecer coreografada.

	Na VOLTA (especial = false) cada um pega a propria danca de novo, e nao a
	padrao: quem chegou de galaxia continua sendo quem chegou de galaxia depois
	que o momento passa. Quem cuida disso e' o `dancaDe`, lendo o atributo. ]]
function Avatares.trocarDancaDeTodos(pasta: Instance, especial: boolean)
	Avatares.trocarDanca(especial)
	Avatares.redancarTodos(pasta)
end

--[[ Poe todo mundo pra dancar de novo, sem mexer no modo especial.

	Existe pro painel: quando voce troca a danca padrao no meio da live, os cem
	bonecos que ja' estao na tela continuariam no passo antigo -- so' quem
	nascesse depois pegaria o novo, e a formacao ficaria metade num passo e
	metade no outro por varios minutos. Chamado pelo `lacoAjustes` quando a
	escolha muda.

	Reinicia o relogio comum junto, pelo mesmo motivo da troca geral: sem isso
	os que ja' estavam entrariam na animacao nova no ponto da ANTIGA, e a
	formacao sairia desencontrada exatamente no instante em que ela deveria
	mudar junta. ]]
function Avatares.redancarTodos(pasta: Instance)
	Avatares.iniciarRelogio()
	for _, modelo in ipairs(pasta:GetChildren()) do
		if modelo:IsA("Model") then
			dancar(modelo)
		end
	end
end

return Avatares
