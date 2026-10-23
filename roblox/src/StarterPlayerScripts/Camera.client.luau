--!strict
--[[
	A camera da live.

	Ela e' o que separa "um monte de bonecos num campo" de uma transmissao que
	alguem assiste ate' o fim.

	  SEGUIR   o padrao, e o que roda a live quase inteira. Enquadra quem acabou
	           de chegar JUNTO COM O TELAO, e se ajusta sozinha quando o avatar
	           e' grande ou quando a formacao se aproxima.
	  ABERTA   fim do ciclo: recua e mostra a formacao inteira antes de limpar.
	  CENA     DESLIGADA por padrao (Config.CAMERA.CENA_LIGADA). Ela cortava
	           pro presente caro e girava em volta; numa live movimentada a
	           camera passava mais tempo rodando em torno de alguem do que
	           mostrando a live, e cada giro escondia a multidao do fundo.
	           O codigo continua aqui pra quem quiser ligar de volta.

	═══════════════════════════════════════════════════════════════════════
	POR QUE O ENQUADRAMENTO E' CALCULADO, E NAO UM OFFSET FIXO
	═══════════════════════════════════════════════════════════════════════

	A versao anterior punha a camera num deslocamento fixo do alvo: sempre 17
	studs acima e 42 atras, mirando no peito dele. Isso da' um quadro bonito
	numa situacao e errado em todas as outras, porque tres coisas mudam durante
	a live:

	  1. O TAMANHO DO ALVO. O avatar cresce com presente, ate' 6x. Um boneco de
	     36 studs mirado pelo peito com a lente a 42 studs sai pela borda de
	     cima do quadro.
	  2. A FILEIRA. A formacao avanca ~70 studs em direcao a' camera ao longo de
	     um ciclo, entao a distancia ate' o telao quase dobra do comeco ao fim.
	  3. O FORMATO DO VIDEO. Em 9:16 a abertura horizontal e' pouco mais de um
	     terco da de 16:9.

	O sintoma disso era concreto e constante: mirando no peito de quem acabou de
	chegar, a lente ficava inclinada uns 22 graus pra baixo, e com isso o TOPO
	DO TELAO caia fora do quadro. O telao existe pra dizer "comente seu nick";
	cortado pela metade, ele nao diz nada, e a live perde o unico convite que
	ela faz.

	Aqui a camera declara o que PRECISA estar no quadro (o topo do telao, a
	cabeca do avatar e os pes dele) e resolve a distancia e a inclinacao que
	fazem os tres caberem, com folga. Se nao houver distancia que resolva --
	acontece com um colosso -- ela desiste do telao e prioriza o avatar, que e'
	a escolha certa nesse impasse.

	O QUE "O TELAO" QUER DIZER AQUI

	A peca `Telao` e' so' a JANELA DO MEIO da parede de LED (y 18..32) -- a que
	carrega texto. Abaixo e acima ficam PainelInferior e PainelSuperior, e a
	camera NAO promete caber os dois: com a lente na altura do peito, o alto da
	parede nao esta' no quadro em nenhuma distancia razoavel, e o pe' dela fica
	atras das cabecas da galera. Ver o bloco TELAO do Config.luau.

	E O TELAO NAO MANDA MAIS NO PLANO. Ele empurra a lente pra tras ate'
	CAMERA.TELAO_RECUO_MAX e para ali; passando disso o solver desiste dele e
	entrega o plano de perto. Quem manda no quadro e' o boneco de quem chegou.

	═══════════════════════════════════════════════════════════════════════
	O ZOOM DE CHEGADA
	═══════════════════════════════════════════════════════════════════════

	Quem comenta ou manda presente ganha CAMERA.ZOOM_S segundos de close, com o
	boneco ocupando ~74% da altura do quadro e o nick legivel. Depois a camera
	volta sozinha pro plano aberto.

	Existe porque os dois pedidos do quadro brigam: o plano normal precisa da
	multidao e do telao, o close precisa de uma pessoa so'. Resolvido no TEMPO
	em vez de no espaco, os dois cabem.

	POR QUE ELA E' DO LADO DO CLIENTE

	A camera no Roblox e' propriedade do cliente. Mover do servidor exigiria
	replicar CFrame 60 vezes por segundo pra cada quadro -- e o resultado, no
	video, seria uma camera aos trancos. Aqui o servidor manda so' o EVENTO
	("agora o alvo e' aquele avatar") e o movimento e' calculado localmente.

	O ATRASO E' PROPOSITAL

	`SUAVIDADE` faz a camera chegar DEPOIS de quem ela persegue. Isso e' o que
	da' a sensacao de camera na mao de alguem em vez de trilho de trem. Colar no
	alvo instantaneamente parece um bug, mesmo estando "certo".
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Config"))
--[[ A conta de enquadramento mora num modulo puro pra poder ser TESTADA sem
	abrir o Studio. Ver roblox/src/ReplicatedStorage/Enquadramento.luau e a
	suite em roblox/testes/. ]]
local Enquadramento = require(ReplicatedStorage:WaitForChild("Enquadramento"))

local camera = workspace.CurrentCamera
local canal = ReplicatedStorage:WaitForChild("CameraLive") :: RemoteEvent

camera.CameraType = Enum.CameraType.Scriptable

-- ─────────────────────────── Estado ───────────────────────────

local modo = "seguir"
local alvo: Model? = nil
local cenaAte = 0
-- Ate' quando o ZOOM DE CHEGADA vale. Ver `destinoZoom`.
local zoomAte = 0
local centroAberto = Vector3.new(0, 0, 0)
-- Do fundo ate' a fileira da frente. O servidor manda junto com o centro.
local profundidadeAberta = 0
local abertaAte = 0
-- O angulo do giro da CENA. Guardado entre quadros pra ele continuar de onde
-- parou, em vez de saltar quando o modo troca.
local anguloCena = 0

--[[ Onde a camera QUER estar. O movimento de verdade e' a interpolacao entre a
	posicao atual e esta, quadro a quadro. ]]
local destino = CFrame.new(0, 20, 40)

-- ─────────────────── Os ajustes que vem do painel ───────────────────
--
-- Lidos a cada quadro, dos atributos do workspace. E' o que faz mexer no painel
-- valer na hora, sem reiniciar o Play -- e ler direto (em vez de guardar numa
-- variavel atualizada por evento) e' o que garante que nao existe uma copia
-- velha em lugar nenhum.

local function ajuste(nome: string, padrao: number, minimo: number, maximo: number): number
	local v = tonumber(workspace:GetAttribute(nome))
	return if v then math.clamp(v, minimo, maximo) else padrao
end

local function ehVertical(): boolean
	local v = workspace:GetAttribute("Vertical")
	if type(v) == "boolean" then
		return v
	end
	--[[ Sem ajuste do painel, DEDUZ pelo formato da janela.

		E' o padrao mais util: quem grava o Studio direto no OBS em modo retrato
		ganha o enquadramento certo sem saber que existe um ajuste. O painel
		continua podendo forcar, pra quem grava em janela deitada e recorta
		depois -- caso em que a janela mente sobre o formato final. ]]
	local tela = camera.ViewportSize
	return tela.Y > tela.X
end

local function recuoDoPainel(): number
	return ajuste("CameraRecuo", Config.CAMERA.RECUO, 10, 200)
end

--[[ Um liga/desliga que veio do painel. Sem ajuste nenhum, vale o Config.

	Separado do `ajuste` porque booleano nao passa por `tonumber`: um
	`GetAttribute` que devolve `false` viraria nil, e o desligado do painel
	seria lido como "nao configurado" -- ou seja, o botao nao desligaria nada.
	E' o mesmo motivo pelo qual o Principal espelha os sim/nao numa lista
	separada. ]]
local function ligado(nome: string, padrao: boolean): boolean
	local v = workspace:GetAttribute(nome)
	if type(v) == "boolean" then
		return v
	end
	return padrao
end

-- ─────────────────────── O TELAO no mundo ───────────────────────

--[[ Mede o telao de verdade, uma vez, e guarda.

	Medir a peca em vez de confiar so' no Config e' o que faz o enquadramento
	acompanhar o mapa: arrastou o telao no Studio, a camera passa a mirar onde
	ele esta' agora. Com numeros fixos, mexer no mapa quebraria o quadro sem
	nenhum aviso -- e o defeito apareceria como "o telao voltou a ficar
	cortado", varios dias depois, sem ninguem lembrar da mudanca.

	Uma vez so' porque o telao e' ancorado e nao se move durante a live; medir
	todo quadro seria uma travessia da arvore do Workspace 60 vezes por segundo
	pra sempre dar a mesma resposta. ]]
local telao = {
	z = Config.TELAO.Z,
	topo = Config.TELAO.TOPO,
	meiaLargura = Config.TELAO.MEIA_LARGURA,
}

local function medirTelao()
	local cenario = workspace:FindFirstChild("Cenario")
	local parede = cenario and cenario:FindFirstChild("ParedeDeLED")
	local peca = parede and parede:FindFirstChild("Telao")
	if peca and peca:IsA("BasePart") then
		telao.z = peca.Position.Z
		telao.topo = peca.Position.Y + peca.Size.Y / 2
		telao.meiaLargura = peca.Size.X / 2
	end
end

task.spawn(function()
	-- O Cenario chega junto com o lugar, mas o script pode subir antes de a
	-- arvore terminar de replicar. Uma tentativa por segundo, por alguns
	-- segundos: se nao achar, os valores do Config seguem valendo.
	for _ = 1, 10 do
		medirTelao()
		if telao.z ~= Config.TELAO.Z or workspace:FindFirstChild("Cenario") then
			return
		end
		task.wait(1)
	end
end)

-- ─────────────────────── O solver de enquadramento ───────────────────────

--[[ Quantas VEZES um boneco normal este avatar tem de altura.

	6 studs e' a altura de um R15 padrao com um chapeu pequeno: um avatar comum
	precisa dar 1 aqui, senao o enquadramento de quem so' comentou mudaria
	junto. ]]
local function tamanhoDe(modelo: Model): number
	local ok, tamanho = pcall(function()
		return modelo:GetExtentsSize().Y
	end)
	if not ok or not tamanho then
		return 1
	end
	return math.clamp(tamanho / 6, 1, 8)
end

--[[ Monta o pedido que o modulo de enquadramento resolve.

	Toda a conta esta' no Enquadramento.luau, que e' puro e testado. Aqui so'
	se junta o que vem de tres lugares diferentes: o alvo (do mundo), o telao
	(medido no mapa) e os ajustes (do painel). ]]
--[[ Onde termina o BALAO DO NOME deste avatar, em Y do mundo.

	O balao fica `ROTULO.ALTURA * tamanho` acima do CENTRO DA CABECA (e' um
	StudsOffsetWorldSpace, ver `ajustarRotulo` no Avatares.luau) e tem
	`2.2 * raiz(tamanho)` studs de altura. A cabeca de um R15 tem o centro a
	uns 78% da altura do boneco.

	ESTA CONTA E' O QUE FAZ O NICK APARECER. Sem ela a camera enquadra ate' o
	alto da cabeca e o nome fica acima da borda -- e quanto mais perto a lente
	chega, mais do nome fica de fora. ]]
local function topoDoBalao(pes: number, topo: number, tamanho: number): number
	local altura = topo - pes
	return pes + altura * 0.78 + Config.ROTULO.ALTURA * tamanho
		+ 1.1 * math.sqrt(tamanho)
end

local function enquadrar(alvoZ: number, alvoPes: number, alvoTopo: number,
	topoQuadro: number?, tetoTelao: number?, partida: number?,
	margem: number?, alturaBase: number?)
	: (number, number, number)
	local fov = if ehVertical()
		then ajuste("CameraFov", Config.CAMERA.FOV_VERTICAL, 30, 110)
		else ajuste("CameraFov", Config.CAMERA.FOV, 30, 110)

	local plano = Enquadramento.resolver({
		alvoZ = alvoZ,
		alvoPes = alvoPes,
		alvoTopo = alvoTopo,
		alvoTopoQuadro = topoQuadro,
		telaoZ = telao.z,
		telaoTopo = telao.topo,
		fov = fov,
		margem = margem or Config.CAMERA.MARGEM_GRAUS,
		--[[ O piso e' 0, e nao 4. Com 4, o Config.CAMERA.ALTURA = 1 (a altura
			do peito) era silenciosamente empurrado pra 4 aqui dentro e a lente
			subia pros ombros -- um ajuste do Config anulado por um limite de
			outro arquivo, sem erro e sem aviso. Negativo continua barrado: uma
			camera abaixo do palco filma o chao. ]]
		alturaBase = alturaBase
			or ajuste("CameraAltura", Config.CAMERA.ALTURA, 0, 90),
		--[[ A PARTIDA e' o piso da busca: `menorQueCabe` procura a menor
			distancia A PARTIR dela, e nunca aproxima mais que isso. Por isso o
			zoom precisa mandar a dele -- com a partida do plano normal, o
			solver responderia "ja' cabe" e devolveria a mesma distancia de
			sempre, e o zoom simplesmente nao aconteceria. ]]
		partida = partida or ajuste("CameraDistancia", Config.CAMERA.DISTANCIA,
			Config.CAMERA.DISTANCIA_MIN, Config.CAMERA.DISTANCIA_MAX),
		minimo = Config.CAMERA.DISTANCIA_MIN,
		maximo = Config.CAMERA.DISTANCIA_MAX,
		--[[ Ate' onde o TELAO pode empurrar a lente pra tras.

			Sem este teto, o telao mandava no plano inteiro: ele fica 74 studs
			atras da formacao, e caber o topo dele junto com o avatar exigia
			recuar ate' o boneco virar um bonequinho. A live inteira ficava
			longe por causa do fundo.

			Com ele, quem manda e' o AVATAR. Se o telao nao couber dentro deste
			limite, o solver desiste dele (o caminho `comTelao = false`, que ja'
			existia pro colosso) e entrega o plano de perto -- com o telao
			aparecendo cortado no fundo, que e' o preco certo a pagar. ]]
		tetoComTelao = tetoTelao,
	})
	return plano.distancia, plano.eixo, plano.altura
end

-- ─────────────────────────── Os modos ───────────────────────────

--[[ Monta o CFrame a partir do que o solver decidiu.

	O ponto de mira sai do ANGULO escolhido, e nao de um ponto do corpo do
	avatar. E' a diferenca inteira desta versao: mirar no peito de quem chegou
	deixava a lente inclinada uns 22 graus pra baixo, e era isso que cortava o
	topo do telao. ]]
local function montarPlano(x: number, alvoZ: number, alvoPes: number,
	alvoTopo: number, tamanho: number, tetoTelao: number?,
	partida: number?, margem: number?, alturaBase: number?): CFrame
	-- O quadro vai ate' o topo do BALAO, e nao ate' o alto da cabeca: e' o que
	-- garante que o nick de quem chegou esta' dentro do video.
	local topoQuadro = topoDoBalao(alvoPes, alvoTopo, tamanho)
	local d, eixo, yCam = enquadrar(alvoZ, alvoPes, alvoTopo, topoQuadro,
		tetoTelao, partida, margem, alturaBase)
	-- A camera fica do lado +Z, que e' o lado pra onde todos os avatares olham.
	local posicao = Vector3.new(x, yCam, alvoZ + d)
	local mira = posicao + Vector3.new(0, math.tan(math.rad(eixo)) * d, -d)
	return CFrame.new(posicao, mira)
end

--[[ ─────────────── O ZOOM DE CHEGADA ───────────────

	Quem comenta ou manda presente ganha alguns segundos de CLOSE: o boneco
	grande na tela, com o nick legivel, e depois a camera volta pro plano
	normal.

	POR QUE ISTO EXISTE

	Porque os dois pedidos do quadro brigam entre si. O plano normal precisa
	mostrar a MULTIDAO e o TELAO -- e' o que faz a proxima pessoa comentar. O
	close precisa mostrar UMA pessoa e o nome dela -- e' o que faz quem ja'
	comentou continuar assistindo. Nao existe uma distancia so' que entregue
	as duas coisas: a que mostra a multidao deixa a skin pequena, e a que
	mostra a skin corta a multidao.

	Resolver isso no TEMPO, e nao no espaco, entrega as duas: o close acontece
	no instante em que a pessoa chega (que e' o unico instante em que ela esta'
	olhando), e o resto do tempo a live respira aberta.

	O CLOSE NAO PEDE O TELAO. Ele enquadra so' o avatar e o balao do nome --
	por isso `tetoComTelao = 0`, que faz o solver desistir do fundo na hora em
	vez de recuar pra tentar caber os dois. ]]
local function destinoZoom(m: Model): CFrame?
	local ok, pivo = pcall(function()
		return m:GetPivot().Position
	end)
	if not ok or not pivo then
		return nil
	end
	local tamanho = tamanhoDe(m)
	local pes = pivo.Y - 3 * tamanho
	--[[ CORPO INTEIRO, E A LENTE NA HORIZONTAL.

		A primeira versao cortava na cintura pra chegar mais perto. Chegava --
		e saia olhando pra cima: com o quadro indo da cintura ao topo do balao,
		o MEIO do que precisa caber fica na altura da cabeca, e o eixo optico
		vai atras dele. Na tela, o boneco escorregava pro rodape e o miolo do
		quadro virava parede.

		Agora o quadro vai do PE' ao topo do balao, e as duas pontas ficam a
		mesma distancia da altura da lente (o peito, 4 studs num boneco normal;
		o balao termina em 8). Simetrico assim, o eixo sai reto sozinho -- sem
		mirar em ponto nenhum, sem caso especial -- e o peito fica no centro do
		quadro, que foi o pedido.

		O preco sao uns dois studs a mais de distancia, e a margem apertada do
		close (ZOOM_MARGEM_GRAUS) devolve quase todos. ]]
	local topo = pes + 6 * tamanho
	--[[ A LENTE EXATAMENTE NO MEIO DO QUE PRECISA CABER.

		"Reto" e' isto, escrito como conta em vez de como numero: com o pe' e o
		topo do balao a distancias iguais da lente, o eixo optico sai na
		horizontal por construcao, em qualquer escala de boneco.

		A CAMERA.ALTURA fixa do plano normal nao serve aqui. Ela vale 1 stud e
		nao cresce com o avatar, entao acertava a simetria so' no boneco de
		escala 1 -- no de escala 6 a lente ficava 6 studs abaixo do meio e o
		close voltava a olhar pra cima, que foi exatamente a reclamacao.

		O termo `- (topo - pes) * 0.5` desfaz a meia-altura que o proprio solver
		soma depois (ver `resolver` no Enquadramento.luau): o que sobra e' a
		altura da lente que ele precisa receber pra pousar no meio. ]]
	local topoQuadro = topoDoBalao(pes, topo, tamanho)
	local alturaBase = (topoQuadro - pes) / 2 - (topo - pes) * 0.5

	return montarPlano(pivo.X, pivo.Z, pes, topo, tamanho, 0,
		ajuste("CameraZoomDistancia", Config.CAMERA.ZOOM_DISTANCIA, 4, 40) * tamanho,
		Config.CAMERA.ZOOM_MARGEM_GRAUS, alturaBase)
end

--[[ O plano padrao: o alvo em primeiro plano e o telao atras dele. ]]
local function destinoSeguir(): CFrame
	if not alvo or not alvo.Parent then
		--[[ Sem alvo (comeco da live, ou o alvo foi limpo): enquadra a PRIMEIRA
			FILEIRA como se houvesse alguem la'.

			Antes isto era um plano geral fixo, e o comeco da live abria com um
			quadro diferente do resto -- a primeira impressao de quem entra era
			de outra transmissao. Passando pelo mesmo solver, o palco vazio ja'
			aparece com o telao no lugar em que ele vai ficar, e a chegada do
			primeiro avatar quase nao move a camera. ]]
		return montarPlano(0, 0, 0, 6, 1, Config.CAMERA.TELAO_RECUO_MAX)
	end

	local ok, pivo = pcall(function()
		return alvo:GetPivot().Position
	end)
	if not ok or not pivo then
		return destino
	end

	local tamanho = tamanhoDe(alvo)
	--[[ Os pes, e nao o pivo. O pivo de um R15 fica na cintura, e o solver
		precisa da base do boneco pra saber onde o quadro tem que terminar
		embaixo -- e do topo pra saber onde ele termina em cima. ]]
	local pes = pivo.Y - 3 * tamanho
	return montarPlano(pivo.X, pivo.Z, pes, pes + 6 * tamanho, tamanho,
		Config.CAMERA.TELAO_RECUO_MAX)
end

local function destinoCena(dt: number): CFrame
	if not alvo or not alvo.Parent then
		return destinoSeguir()
	end
	local ok, pivo = pcall(function()
		return alvo:GetPivot().Position
	end)
	if not ok or not pivo then
		return destino
	end
	local ponto = pivo + Vector3.new(0, 1.7 * tamanhoDe(alvo), 0)
	anguloCena += dt * Config.CAMERA.CENA_GIRO * math.pi * 2
	-- Afasta na medida do boneco: o CENA_DISTANCIA do Config e' a distancia de
	-- UM avatar normal, e quem e' quatro vezes maior precisa de quatro vezes
	-- mais espaco pra caber no mesmo quadro.
	local tamanho = tamanhoDe(alvo)
	local raio = Config.CAMERA.CENA_DISTANCIA * tamanho
	local posicao = ponto + Vector3.new(
		math.sin(anguloCena) * raio,
		Config.CAMERA.CENA_ALTURA * tamanho,
		math.cos(anguloCena) * raio)
	return CFrame.new(posicao, ponto)
end

--[[ O plano aberto do fim do ciclo: a formacao INTEIRA no quadro.

	O recuo do painel conta a partir da FILEIRA DA FRENTE, e nao do centro. Com
	dez fileiras, o centro fica na quinta -- recuar 34 studs dali punha a camera
	no meio da formacao, com metade dela nas costas da lente. Somar meia
	profundidade tira a camera pra fora antes de aplicar o recuo, e ai' o numero
	do painel volta a significar o que ele diz: distancia da plateia.

	A altura sobe junto pelo mesmo motivo: olhando de raspao, uma formacao funda
	esconde as fileiras de tras atras das da frente. ]]
local function destinoAberto(): CFrame
	local recuo = recuoDoPainel() + profundidadeAberta / 2
	local altura = math.max(Config.CAMERA.ALTURA_ABERTA, profundidadeAberta * 0.45)
	local posicao = centroAberto + Vector3.new(0, altura, recuo)
	return CFrame.new(posicao, centroAberto + Vector3.new(0, 2, 0))
end

-- ─────────────────────────── O laco ───────────────────────────

--[[ A lente propriamente dita.

	Escrita a cada quadro porque o painel pode mudar o FOV ao vivo e porque
	girar a janela (do modo deitado pro em pe') muda qual dos dois vale. Uma
	atribuicao por quadro num numero que quase nunca muda custa nada, e o
	`if` evita marcar a propriedade como suja a' toa. ]]
local function aplicarLente()
	local desejado = if ehVertical()
		then ajuste("CameraFov", Config.CAMERA.FOV_VERTICAL, 30, 110)
		else ajuste("CameraFov", Config.CAMERA.FOV, 30, 110)
	if math.abs(camera.FieldOfView - desejado) > 0.01 then
		camera.FieldOfView = desejado
	end
end

--[[ ─────────── QUEM A CAMERA ESTA' MOSTRANDO TEM NOME ───────────

	Marca o balao do alvo com um atributo, e o Rotulos.client.luau o acende
	sem passar por regra nenhuma -- nem rodizio de fileira, nem teto de
	quantidade, nem apagamento por distancia.

	POR QUE UM CANAL DIRETO, E NAO MAIS UMA HEURISTICA

	Porque "o nick nao aparece" ja' voltou tres vezes, cada uma por um motivo
	diferente: o rodizio apagava a fileira dele, o quadro cortava o balao pela
	borda de cima, o alcance nao acompanhava o recuo. Todas eram regras
	tentando ADIVINHAR quem a camera esta' mostrando -- e a camera SABE quem
	e'. Perguntar pra quem sabe e' mais curto que acertar a adivinhacao.

	O atributo e' escrito no CLIENTE e nao replica pra ninguem, que e'
	exatamente o que se quer: cada espectador acende o nome de quem a camera
	DELE esta' mostrando. E' a mesma razao de a camera viver no cliente.

	Reavaliado a cada quadro (e nao so' na troca de alvo) porque o balao chega
	DEPOIS do modelo: o avatar nasce, a camera ja' aponta pra ele, e a cabeca
	com o rotulo replica um instante mais tarde. Marcando so' na troca, quem
	chegasse durante esse instante ficaria sem nome ate' o proximo. Sao dois
	FindFirstChild por quadro. ]]
local balaoMarcado: BillboardGui? = nil

local function rotuloDe(m: Model?): BillboardGui?
	local cabeca = m and m:FindFirstChild("Head")
	local balao = cabeca and cabeca:FindFirstChild("Rotulo")
	return if balao and balao:IsA("BillboardGui") then balao else nil
end

local function marcarAlvo(m: Model?)
	local balao = rotuloDe(m)
	if balao == balaoMarcado then
		return
	end
	if balaoMarcado and balaoMarcado.Parent then
		balaoMarcado:SetAttribute("AlvoDaCamera", nil)
	end
	balaoMarcado = balao
	if balao then
		balao:SetAttribute("AlvoDaCamera", true)
	end
end

RunService.RenderStepped:Connect(function(dt)
	local tempo = workspace:GetServerTimeNow()

	if modo == "cena" and tempo >= cenaAte then
		modo = "seguir"
	end
	if modo == "aberta" and tempo >= abertaAte then
		modo = "seguir"
	end

	aplicarLente()

	-- Quem a camera esta' mostrando tem nome, sempre. Ver `marcarAlvo`.
	marcarAlvo(if modo == "aberta" then nil else alvo)

	--[[ O ZOOM manda enquanto durar, e so' no modo seguir: o plano aberto do
		fim de ciclo e a cinematica sao momentos com dono, e um close por cima
		deles seria a camera brigando consigo mesma. ]]
	local emZoom = modo == "seguir" and tempo < zoomAte and alvo ~= nil
		and alvo.Parent ~= nil

	if modo == "cena" then
		destino = destinoCena(dt)
	elseif modo == "aberta" then
		destino = destinoAberto()
	elseif emZoom then
		destino = destinoZoom(alvo :: Model) or destinoSeguir()
	else
		destino = destinoSeguir()
	end

	--[[ A interpolacao.

		O `1 - (1 - s)^(dt*60)` em vez de `s` puro nao e' firula: com `s` puro, a
		velocidade da camera dependeria do FPS de quem assiste -- mais macia num
		PC rapido, mais dura num lento. Assim ela se move igual em qualquer
		maquina, que e' o que importa quando o video e' o produto.

		A ENTRADA DO ZOOM USA OUTRA SUAVIDADE, e e' o pedido literal do dono:
		"tem que ser um zoom rapido". Com a suavidade normal (0.08) a camera
		levaria mais de um segundo pra chegar no close -- ou seja, ela ainda
		estaria viajando quando o tempo do close acabasse, e o efeito na tela
		seria um vai-e-vem molenga em vez de um zoom. Na VOLTA vale a suavidade
		normal: sair devagar do close devolve a multidao sem susto. ]]
	local suavidade = if emZoom then Config.CAMERA.ZOOM_SUAVIDADE
		else ajuste("CameraSuavidade", Config.CAMERA.SUAVIDADE, 0.02, 0.5)
	local fator = 1 - (1 - suavidade) ^ (dt * 60)
	camera.CFrame = camera.CFrame:Lerp(destino, math.clamp(fator, 0, 1))
end)

canal.OnClientEvent:Connect(function(ordem)
	if type(ordem) ~= "table" then
		return
	end
	local tempo = workspace:GetServerTimeNow()

	--[[ TROCOU DE ALVO? Comeca o zoom.

		Uma funcao so' pros dois caminhos (o "cena" convertido e o "seguir")
		porque os dois sao a mesma coisa do ponto de vista de quem assiste:
		alguem acabou de entrar na live. Quem mandou presente e quem so'
		comentou ganham o mesmo close -- o que separa os dois e' o tamanho do
		boneco e a aura, nao o direito de aparecer.

		SO' QUANDO O ALVO MUDA. Numa live movimentada o servidor manda "seguir"
		varias vezes seguidas pro mesmo avatar; reiniciando o zoom em cada uma,
		a camera ficaria presa no close sem nunca voltar pro plano aberto. ]]
	local function mirar(novo: Model?)
		if not novo or novo == alvo then
			return
		end
		alvo = novo
		if ligado("CameraZoomLigado", Config.CAMERA.ZOOM_LIGADO) then
			zoomAte = tempo + ajuste("CameraZoomS", Config.CAMERA.ZOOM_S, 0, 12)
		end
	end

	if ordem.modo == "cena" then
		--[[ Com a cinematica desligada, presente caro NAO tira a camera do
			normal: ela so' vira pra ele e fica parada, como faz com todo mundo.

			Convertido AQUI, e nao no servidor, de proposito: o servidor continua
			mandando "cena" e continua segurando os proximos spawns pelo tempo
			que a pessoa pagou. Quem decide como a camera se comporta e' o
			arquivo da camera -- entao ligar o giro de volta e' mexer em um
			lugar so', o Config, sem tocar na logica da live. ]]
		if ligado("CameraCenaLigada", Config.CAMERA.CENA_LIGADA) then
			modo = "cena"
			alvo = ordem.alvo
			cenaAte = tempo + (tonumber(ordem.duracao) or 3)
		else
			modo = "seguir"
			mirar(ordem.alvo)
		end
	elseif ordem.modo == "aberta" then
		modo = "aberta"
		centroAberto = ordem.centro or Vector3.new(0, 0, 0)
		profundidadeAberta = math.clamp(tonumber(ordem.profundidade) or 0, 0, 600)
		abertaAte = tempo + (tonumber(ordem.duracao) or Config.CAMERA.ABERTA_S)
	elseif ordem.modo == "seguir" then
		--[[ Uma CENA em andamento nao pode ser interrompida por um comentario
			comum que chegou logo atras.

			Sem esta guarda, o momento que a pessoa PAGOU pra ter duraria ate' o
			proximo "oi" no chat -- e numa live movimentada isso e' menos de um
			segundo. O presente caro viraria um piscar. ]]
		if modo == "cena" and tempo < cenaAte then
			return
		end
		modo = "seguir"
		mirar(ordem.alvo)
	end
end)

-- Sem personagem, o Roblox nao tem onde ancorar a interface padrao, e ela fica
-- ocupando canto de tela numa transmissao onde cada pixel e' conteudo.
local jogador = Players.LocalPlayer
if jogador then
	local gui = jogador:FindFirstChildOfClass("PlayerGui")
	if gui then
		pcall(function()
			game:GetService("StarterGui"):SetCoreGuiEnabled(
				Enum.CoreGuiType.All, false)
		end)
	end
end
