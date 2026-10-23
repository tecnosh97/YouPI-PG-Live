--!strict
--[[
	A LICENÇA, vista de dentro do jogo.

	ESTE MÓDULO É O PORTÃO DO LADO DO JOGO. Sem licença, o jogo não
	nasce boneco nenhum.

	POR QUE O JOGO PRECISA CONFERIR SOZINHO

	O servidor local e a ponte já conferem. Mas o jogo é um processo
	separado, e é o ÚNICO que roda no lugar que importa no modo publicado:
	nos servidores da Roblox, onde o comprador não pode mexer em nada.

	Se o jogo não conferisse, bastaria alguém abrir o .rbxlx, tirar a
	conferência e publicar — e o produto inteiro rodaria de graça, para
	qualquer um, sem passar pelo servidor de chaves. Com a conferência
	DENTRO do jogo, quem publica precisa de uma chave válida.

	OS DOIS MODOS

	  local   o jogo roda no Studio, na máquina do comprador. Ele pergunta
	          ao SERVIDOR LOCAL, que já conferiu a licença com o servidor
	          de chaves. É o modo de conveniência.

	  remoto  o jogo está PUBLICADO na Roblox. Ele pergunta direto ao
	          SERVIDOR DE CHAVES, por HTTPS. É o modo protegido: o
	          comprador nunca vê estes scripts, nunca vê a chave e nunca
	          vê o pacote.

	O COMO A LICENÇA VOLTA

	O jogo pede a licença, e recebe junto o PACOTE PROTEGIDO: os IDs das
	animações de terceiro e as paletas das cenas. Na build de venda, esses
	numbers não estão no arquivo do jogo -- estão no servidor de chaves.

	E por isso que este módulo PREENCHE o ConfigServidor: o jogo lê as
	animações DEPOIS desta conferência, e não antes.
]]

local HttpService = game:GetService("HttpService")
local Segredos = require(script.Parent:WaitForChild("Segredos"))
local ConfigServidor = require(script.Parent:WaitForChild("ConfigServidor"))

local Licenca = {}

-- O estado, lido por todo mundo que precisa saber.
Licenca.ok = false
Licenca.motivo = "a licenca ainda nao foi conferida"
Licenca.paletas = {}
Licenca.endpoint = ""
Licenca.modo = Segredos.LICENCA_MODO

local conferido = false

--[[ A PALETA DE UMA CENA.

	O jogo pinta a cena que o painel escolheu, e a cor de cada peça vem
	aqui. Na build de venda, as paletas NÃO estão no arquivo do jogo: vêm
	no pacote da licença.

	Se a cena não tiver paleta (licença sem o pacote, ou cena nova que o
	vendedor ainda não exportou), devolve nil -- e quem chama decide o que
	fazer com isso. ]]
function Licenca.paletaCena(id: string): any?
	local tema = Licenca.paletas[id]
	if type(tema) == "table" then
		return tema
	end
	return nil
end

--[[ O ESCAPE DE URL.
	O HttpService nao tem um, e a chave pode ter caractere que precise
	escapado. ]]
local function urllibEncode(texto: string): string
	return (string.gsub(texto, "[^%w%-%_%.~]", function(c)
		return string.format("%%%02X", string.byte(c))
	end))
end

--[[ A CONFERENCIA.

	Duas formas, conforme o modo. Em ambas a resposta traz o pacote. ]]
local function conferir(): (boolean, string)
	local modo = Licenca.modo
	local url
	local cabecalhos = {}
	local corpo = nil

	if modo == "remoto" then
		-- No modo publicado, o jogo fala direto com o servidor de chaves.
		-- A chave esta' no Segredos, que nunca e' replicado.
		url = Segredos.LICENCA_URL .. "/robo?chave=" ..
			urllibEncode(Segredos.LICENCA_CHAVE)
		cabecalhos = {}
	else
		-- No modo local, o servidor local ja conferiu: ele pergunta por
		-- este endereco e traz o que o jogo precisa.
		url = Segredos.URL .. "/licenca?pacote=1"
		cabecalhos = { ["X-Chave"] = Segredos.CHAVE }
	end

	local ok, resposta = pcall(function()
		return HttpService:RequestAsync({
			Url = url,
			Method = "GET",
			Headers = cabecalhos,
		})
	end)

	if not ok then
		return false, "nao consegui falar com o servidor de licencas: " .. tostring(resposta)
	end
	if not resposta.Success then
		return false, "o servidor de licencas respondeu " .. tostring(resposta.StatusCode)
	end

	local dados
	local leu = pcall(function()
		dados = HttpService:JSONDecode(resposta.Body)
	end)
	if not leu or type(dados) ~= "table" then
		return false, "o servidor de licencas respondeu algo que nao e' uma resposta"
	end

	if not dados.ok then
		return false, tostring(dados.erro or "licenca invalida.")
	end

	local pacote = dados.pacote or dados.protegido
	if type(pacote) == "table" then
		-- Os IDs das animacoes de terceiro.
		ConfigServidor.preencher(pacote)
		-- As paletas das cenas.
		local cenas = pacote.cenas
		if type(cenas) == "table" then
			Licenca.paletas = cenas
		end
	end

	Licenca.endpoint = tostring(dados.endpoint or "")
	return true, "licenca valida"
end

--[[ O ESCAPE DE URL.
	O HttpService nao tem um, e a chave pode ter caractere que precise
	escapado. ]]
local function urllibEncode(texto: string): string
	return (string.gsub(texto, "[^%w%-%_%.~]", function(c)
		return string.format("%%%02X", string.byte(c))
	end))
end

--[[ A CONFERENCIA, ESPERANDO.

	O jogo precisa do pacote ANTES de montar as animações -- e o pacote só
	chega depois de uma ida à internet. Por isso esta função ESPERA, em vez
	de devolver "ainda não sei" e sair correndo.

	A espera é de 20 segundos no máximo: passou disso, ou o servidor de
	chaves está fora do ar, ou a chave está errada -- e nos dois casos o
	jogo não vai dançar dos passos de terceiro. ]]
function Licenca.aguardar(limiteSegundos: number?): boolean
	if conferido then
		return Licenca.ok
	end
	conferido = true

	local ate = os.clock() + (limiteSegundos or 20)
	local pronto = false
	local motivo = "a licenca nao foi conferida"
	task.spawn(function()
		local ok, m = conferir()
		pronto = true
		if ok then
			Licenca.ok = true
			Licenca.motivo = m
		else
			Licenca.ok = false
			Licenca.motivo = m
			motivo = m
		end
	end)

	while not pronto and os.clock() < ate do
		task.wait(0.2)
	end

	if not pronto then
		Licenca.ok = false
		Licenca.motivo = "o servidor de licencas nao respondeu a tempo."
		motivo = Licenca.motivo
	end

	if Licenca.ok then
		print("[licenca] valida. Modo: " .. tostring(Licenca.modo))
	else
		warn("[licenca] INVALIDA: " .. tostring(motivo))
	end
	return Licenca.ok
end

--[[ A CONFERENCIA DE TEMPOS EM TEMPOS.

	Uma licença pode CAIR no meio da live: o vendedor revoga, o prazo
	acaba. Conferir só na subida deixaria a live inteira funcionando de
	 graça depois disso. ]]
function Licenca.laco(intervalo: number?)
	while true do
		task.wait(intervalo or 120)
		local ok, motivo = conferir()
		if ok ~= Licenca.ok then
			Licenca.ok = ok
			Licenca.motivo = motivo
			if ok then
				print("[licenca] a licenca voltou a valer.")
			else
				warn("[licenca] a licenca CAIU: " .. tostring(motivo))
			end
		end
	end
end

return Licenca
