--!strict
--[[
	Onde cada avatar fica em pe'.

	A regra e' uma grade preenchida em ORDEM DE CHEGADA, e nunca fora dela:

	  - os avatares entram um por um, lado a lado, na fileira atual;
	  - quando a fileira enche, a proxima nasce NA FRENTE da anterior;
	  - quando a grade inteira enche, o ciclo acaba: a camera abre pra mostrar
	    tudo, a formacao e' apagada, e recomeca do zero.

	A camera fica do lado +Z de cada avatar, entao "na frente" e' +Z: cada
	fileira nova tem Z maior e fica mais perto de quem assiste.

	═══════════════════════════════════════════════════════════════════
	POR QUE ISTO E' UM LAYOUT QUE SE RECALCULA, E NAO UM CURSOR QUE SO' ANDA
	═══════════════════════════════════════════════════════════════════

	A versao anterior reservava slots com um cursor que so' avancava, e a
	posicao de cada avatar era decidida UMA vez, no nascimento. Isso funcionava
	enquanto o tamanho de um boneco nunca mudava depois de ele nascer.

	So' que agora o presente FAZ O AVATAR CRESCER (e' a promessa do telao), e um
	boneco que cresce ocupa mais largura e mais profundidade do que ocupava
	quando nasceu. Com posicoes congeladas, o resultado era garantido e feio: o
	avatar de quem mandou a galaxia inflava POR CIMA dos dois vizinhos, com
	bracos atravessando corpos, e empurrava metade do corpo pra dentro da
	fileira da frente. Ou seja, exatamente o presente mais caro da live e' o que
	quebraria a formacao.

	Aqui a formacao guarda a LISTA de quem esta' nela, e as posicoes sao
	derivadas dessa lista sempre que alguem entra ou muda de tamanho. Cresceu?
	Todo mundo se reacomoda em volta, e ninguem se atravessa.

	A ORDEM DA LISTA NUNCA MUDA, e e' isso que preserva a propriedade que fazia
	o cursor valer a pena: quem chegou por ultimo continua sendo o ultimo da
	lista, ou seja, na fileira mais perto da camera. Recalcular reacomoda; nao
	reordena.

	Modulo sem estado global e sem efeito colateral: da' pra raciocinar sobre
	ele inteiro sem abrir o Studio, e e' por isso que ele tem teste proprio.
]]

local Config = require(game:GetService("ReplicatedStorage"):WaitForChild("Config"))

local Formacao = {}
Formacao.__index = Formacao

--[[ Um lugar ocupado na grade.

	`escala` e' o tamanho ATUAL (ele muda quando a pessoa recebe presente).
	`fileira`, `coluna` e `cframe` sao derivados -- o `recalcular` os reescreve
	inteiros toda vez, e ninguem deve escrever neles de fora. ]]
export type Ocupante = {
	escala: number,
	vivo: boolean,
	fileira: number,
	coluna: number,
	slots: number,
	cframe: CFrame,
}

export type Formacao = typeof(setmetatable(
	{} :: {
		ocupantes: { Ocupante },
		--[[ Quantos por fileira NESTE ciclo.

			Fica na instancia, e nao lido do painel a cada chamada, porque o
			painel pode mudar isto no meio da live: com a regua mudando embaixo
			de gente ja' plantada, a formacao inteira saltaria de lugar no meio
			da transmissao. O valor novo so' entra no `limpar`, ou seja, no
			ciclo seguinte -- e o Principal fecha o ciclo na hora justamente pra
			a mudanca nao demorar cem avatares pra aparecer. ]]
		porFila: number,
		-- Quantos slots a grade inteira esta' usando agora. Derivado.
		usados: number,
		-- Z de cada fileira, em studs. Derivado.
		zDaFileira: { [number]: number },
	},
	Formacao
))

--[[ Quantos por fileira o painel pede agora. O Principal espelha o valor num
	atributo do workspace; sem atributo, vale o padrao do Config. ]]
local function porFilaDoPainel(): number
	local v = tonumber(workspace:GetAttribute("PorFila"))
	if not v then
		return Config.POR_FILA
	end
	return math.clamp(math.floor(v), 2, 20)
end

local function totalDoPainel(): number
	local v = tonumber(workspace:GetAttribute("TotalAvatares"))
	if not v then
		return Config.MAX_AVATARES
	end
	return math.clamp(math.floor(v), 4, 400)
end

--[[ Quantos slots um avatar dessa escala precisa.

	Sem isto um boneco de escala 4 nasceria em cima dos vizinhos: ele ocuparia
	um slot de largura normal e o corpo invadiria os dois lados. ]]
function Formacao.slotsPara(escala: number, porFila: number?): number
	local largura = Config.LARGURA_POR_ESCALA * math.max(escala, 0.1)
	local n = math.ceil(largura / Config.ESPACO_X)
	-- Nunca mais que uma fileira inteira, senao nada caberia nunca.
	return math.clamp(n, 1, porFila or Config.POR_FILA)
end

--[[ A coluna de um slot, ja' com a serpentina aplicada.

	As fileiras impares sao invertidas de proposito. Numa disposicao normal, o
	ultimo slot de uma fileira e o primeiro da seguinte ficam em pontas opostas,
	e a camera atravessaria a formacao inteira toda vez que uma fileira enchesse
	-- um solavanco lateral a cada dez avatares. Com a serpentina, o fim de uma
	fileira encosta no comeco da outra e a camera so' anda um passo. ]]
local function colunaVisual(fileira: number, coluna: number, porFila: number): number
	if fileira % 2 == 1 then
		return porFila - 1 - coluna
	end
	return coluna
end

function Formacao.novo(): Formacao
	return setmetatable({
		ocupantes = {},
		porFila = porFilaDoPainel(),
		usados = 0,
		zDaFileira = {},
	}, Formacao)
end

--[[ Refaz TODAS as posicoes a partir da lista de ocupantes.

	Tres passadas, e a separacao entre elas nao e' estilo -- cada uma depende do
	resultado inteiro da anterior:

	  1. distribui em fileiras e colunas, e descobre o MAIOR de cada fileira;
	  2. com o maior de cada fileira em maos, calcula o Z de cada uma;
	  3. so' entao monta o CFrame de cada ocupante.

	A passada 2 nao pode acontecer junto da 1 pelo motivo classico da grade:
	o vao entre a fileira F e a F+1 depende do maior boneco da F, e o maior
	boneco da F so' e' conhecido quando a fileira F terminou de ser preenchida.
	Misturar as duas foi o que, na versao antiga, deixava um gigante que chegava
	por ultimo invadindo quem ja' estava plantado na frente dele. ]]
function Formacao.recalcular(self: Formacao)
	local porFila = self.porFila
	local fileira, coluna = 0, 0
	local maiorDaFileira: { [number]: number } = {}

	-- 1) fileira e coluna de cada um, na ordem de chegada.
	for _, oc in ipairs(self.ocupantes) do
		local slots = Formacao.slotsPara(oc.escala, porFila)
		-- Os slots precisam caber na MESMA fileira: um avatar nao pode ficar
		-- metade numa e metade na outra. Se nao couber no que resta desta, pula
		-- pro comeco da proxima -- deixando um buraco no fim, que e' o preco de
		-- manter o avatar inteiro.
		if coluna + slots > porFila then
			fileira += 1
			coluna = 0
		end
		oc.fileira = fileira
		oc.coluna = coluna
		oc.slots = slots
		coluna += slots

		local tamanho = math.max(oc.escala, 1)
		if tamanho > (maiorDaFileira[fileira] or 0) then
			maiorDaFileira[fileira] = tamanho
		end
	end

	--[[ 2) O Z de cada fileira.

		Cada fileira empurra a seguinte pelo tamanho do MAIOR boneco que ela
		tem. Fileira so' de gente normal fica a ESPACO_Z; uma fileira com um
		oculos de escala 4 abre bem mais, e ninguem se atravessa.

		A MEDIA e nao a escala crua: o vao entre duas fileiras precisa caber
		meio corpo de cada lado, entao ele acompanha a media dos dois tamanhos.
		Multiplicar direto (8 x 4 = 32 studs) daria o dobro do necessario, e a
		formacao ficaria com um vazio enorme atras de cada presente grande --
		espalhada demais pra caber no plano aberto, e sem a sensacao de plateia
		cheia que faz a live funcionar. ]]
	table.clear(self.zDaFileira)
	local z = 0
	self.zDaFileira[0] = 0
	for f = 1, fileira do
		local grande = math.max(maiorDaFileira[f - 1] or 1, 1)
		z += Config.ESPACO_Z * (grande + 1) / 2
		self.zDaFileira[f] = z
	end

	--[[ 3) O CFrame.

		Centraliza no CONJUNTO de slots: um avatar de 2 slots fica no meio dos
		dois, e nao encostado no primeiro.

		Girado 180 graus. No Roblox o "para frente" de um CFrame e' o -Z, entao
		um CFrame.new(pos) puro deixaria todo mundo olhando pra -Z -- e a camera
		fica do lado +Z, entao o close pegaria a nuca de cada um. ]]
	for _, oc in ipairs(self.ocupantes) do
		local primeira = colunaVisual(oc.fileira, oc.coluna, porFila)
		local ultima = colunaVisual(oc.fileira, oc.coluna + oc.slots - 1, porFila)
		local meio = (primeira + ultima) / 2
		-- Centraliza a fileira no eixo X: as colunas vao de -(N-1)/2 a
		-- +(N-1)/2 vezes o espacamento, e nao de 0 a N-1. Sem isso, a formacao
		-- inteira cresceria so' pra direita e sairia do quadro.
		local x = (meio - (porFila - 1) / 2) * Config.ESPACO_X
		oc.cframe = CFrame.new(Vector3.new(x, 0, self.zDaFileira[oc.fileira] or 0))
			* CFrame.Angles(0, math.pi, 0)
	end

	self.usados = fileira * porFila + coluna
end

--[[ Poe mais um na formacao. Devolve o INDICE dele, ou nil se a grade encheu.

	O nil e' o sinal de "ciclo completo", e e' ele que dispara o plano aberto e
	a limpeza la' no Principal.

	Desfaz a entrada quando nao cabe, em vez de deixar o ocupante na lista e
	devolver nil: um ocupante fantasma na lista faria a proxima chamada do
	`recalcular` contar espaco pra um boneco que nao existe, e a formacao
	ficaria com um buraco permanente que so' sumiria no fim do ciclo. ]]
function Formacao.entrar(self: Formacao, escala: number): number?
	local oc: Ocupante = {
		escala = math.max(escala or 1, 0.1),
		vivo = true,
		fileira = 0,
		coluna = 0,
		slots = 1,
		cframe = CFrame.identity,
	}
	table.insert(self.ocupantes, oc)
	self:recalcular()

	if self.usados > totalDoPainel() then
		table.remove(self.ocupantes)
		self:recalcular()
		return nil
	end
	return #self.ocupantes
end

--[[ Este avatar cresceu: reacomoda a formacao em volta dele.

	Devolve `false` quando o tamanho novo nao cabe na grade -- e ai' o tamanho
	antigo e' restaurado, em vez de ficar um estado meio aplicado. Quem chama
	decide o que fazer (hoje: aplica o crescimento assim mesmo, e deixa o ciclo
	fechar; ver `Principal.crescer`). ]]
function Formacao.mudarEscala(self: Formacao, indice: number, escala: number): boolean
	local oc = self.ocupantes[indice]
	if not oc then
		return false
	end
	local antes = oc.escala
	oc.escala = math.max(escala or 1, 0.1)
	self:recalcular()

	if self.usados > totalDoPainel() then
		oc.escala = antes
		self:recalcular()
		return false
	end
	return true
end

function Formacao.posicaoDe(self: Formacao, indice: number): CFrame?
	local oc = self.ocupantes[indice]
	return if oc then oc.cframe else nil
end

function Formacao.escalaDe(self: Formacao, indice: number): number
	local oc = self.ocupantes[indice]
	return if oc then oc.escala else 1
end

--[[ Em que fileira este ocupante caiu no ultimo `recalcular`.

	O cliente usa isto pra achar a FILEIRA DA FRENTE (a ultima, entao
	contagem - 1), que e' a unica que aparece nomeada. Vem do
	estado derivado de proposito: ninguem guarda "a fileira" em lugar nenhum,
	ela e' recalculada junto com as posicoes -- e assim nao ha' como ela ficar
	dessincronizada de onde o boneco esta' de fato. ]]
function Formacao.fileiraDe(self: Formacao, indice: number): number
	local oc = self.ocupantes[indice]
	return if oc then oc.fileira else 0
end

--[[ Quantas fileiras a formacao tem agora (0 quando esta' vazia). ]]
function Formacao.fileiras(self: Formacao): number
	if #self.ocupantes == 0 then
		return 0
	end
	return self.ocupantes[#self.ocupantes].fileira + 1
end

--[[ Onde o COLOSSO fica: ATRAS da ultima fileira possivel.

	A grade cresce em +Z (fileira nova = mais perto da camera), entao "atras de
	todo mundo" e' o Z mais NEGATIVO -- antes ate' da primeira fileira. Fica um
	pouco alem pra ele nao encostar em quem esta' no fundo, mesmo sendo enorme.

	`quantos` e' quantos colossos JA' nasceram neste ciclo, e ele existe porque
	o colosso nao entra na grade (de proposito -- um gigante consumindo meia
	fileira fecharia o ciclo cedo demais). Sem esse numero, dois colossos
	seguidos nasciam exatamente no mesmo ponto e viravam um borrao de bracos e
	pernas atravessados. Aqui o primeiro fica no meio, e os seguintes se
	revezam nos lados.

	O ciclo de TRES nao e' arbitrario: acima de tres gigantes na mesma tela, os
	das pontas ja' saem do quadro da camera aberta, entao o quarto volta pro
	meio -- onde pelo menos aparece. ]]
function Formacao.posicaoColosso(quantos: number?): CFrame
	local vez = math.floor(quantos or 0) % 3
	local lado = if vez == 1 then -1 elseif vez == 2 then 1 else 0
	return CFrame.new(Vector3.new(lado * Config.ESPACO_X * 6, 0, -Config.ESPACO_Z * 3.5))
		* CFrame.Angles(0, math.pi, 0)
end

--[[ Do fundo ate' a ultima fileira, em studs.

	A camera do plano aberto PRECISA deste numero. Antes ela recuava um valor
	fixo a partir do centro, e isso ja' era apertado com a grade uniforme: com
	dez fileiras a 8 studs, a fileira da frente ficava praticamente em cima da
	lente. Como uma fileira com gigante abre mais espaco que uma normal, a
	profundidade varia de uma live pra outra -- de 72 studs numa live so' de
	comentarios a 180 numa cheia de presente grande -- e um recuo fixo deixaria
	metade da formacao ATRAS da camera no fim do ciclo, que e' justamente o
	momento de mostrar que a live esta' cheia. ]]
function Formacao.profundidade(self: Formacao): number
	local ultima = 0
	for _, oc in ipairs(self.ocupantes) do
		if oc.fileira > ultima then
			ultima = oc.fileira
		end
	end
	return self.zDaFileira[ultima] or 0
end

--[[ O centro da formacao no chao, pro plano aberto do fim do ciclo.

	Meio caminho ate' a ultima fileira, medido pelo Z de verdade dela -- e nao
	por `fileiras * ESPACO_Z`. Com um gigante no meio, as fileiras nao estao
	mais igualmente espacadas, e a conta antiga apontaria o plano aberto pra um
	ponto onde nao tem ninguem. ]]
function Formacao.centro(self: Formacao): Vector3
	return Vector3.new(0, 0, self:profundidade() / 2)
end

function Formacao.quantos(self: Formacao): number
	return #self.ocupantes
end

function Formacao.slotsUsados(self: Formacao): number
	return self.usados
end

function Formacao.cheia(self: Formacao): boolean
	return self.usados >= totalDoPainel()
end

--[[ Recomeca o ciclo.

	E' AQUI que uma mudanca de "por fileira" feita no painel entra em vigor: com
	a grade vazia, ninguem foi plantado pela regua antiga. ]]
function Formacao.limpar(self: Formacao)
	table.clear(self.ocupantes)
	table.clear(self.zDaFileira)
	self.usados = 0
	self.porFila = porFilaDoPainel()
end

return Formacao
