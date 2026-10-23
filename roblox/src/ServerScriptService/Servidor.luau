--!strict
--[[
	Conversa com o servidor da live.

	POR QUE O JOGO PERGUNTA EM VEZ DE RECEBER

	O Roblox nao fala WebSocket, e o HttpService so' faz requisicao de SAIDA.
	Nao existe nenhum jeito de o jogo ser AVISADO de que alguem comentou -- ele
	tem que perguntar.

	Dai' o cursor: cada resposta diz ate' onde o jogo ja' leu, e a pergunta
	seguinte continua dali. Sem isso, ou o jogo receberia tudo de novo a cada
	segundo, ou perderia o que chegou entre duas perguntas.
]]

local HttpService = game:GetService("HttpService")
local Segredos = require(script.Parent:WaitForChild("Segredos"))

local Servidor = {}

export type Spawn = {
	tiktok_id: string,
	nickname: string,
	nick_roblox: string,
	roblox_id: number,

	-- Quem tem numero maior fura a fila e entra na frente.
	prio: number,
	-- Multiplicador de tamanho com que o avatar NASCE.
	escala: number,
	--[[ Quanto SOMAR no avatar que esta pessoa ja' tem na tela.
		0 = este evento nao faz crescer.

		Escala e crescimento sao coisas diferentes e o jogo usa uma OU a outra,
		nunca as duas: quem ja' tem boneco cresce, quem nao tem nasce. Ver
		`Principal.aplicar`. ]]
	crescimento: number,
	-- Segundos na tela antes de sumir.
	vida: number,
	-- Segundos em que NINGUEM mais nasce depois deste avatar. Como a camera
	-- acompanha quem acabou de chegar, isto vira o tempo de tela dele.
	segura: number,
	-- Segundos de CINEMATICA (0 = nenhuma). So' presente caro tem.
	cena: number,
	-- Segundos varrendo a formacao e derrubando todo mundo (0 = nao faz).
	furacao: number,
	-- Cor do nome e do brilho, em hexadecimal ("FF2D6F").
	cor: string,
	-- Forca da aura, de 0 a 5. 0 = sem aura.
	brilho: number,
	-- A danca SO' DESTE avatar ("rosquinha", "oculos", "galaxia"...). "" = a
	-- danca padrao, a mesma de quem so' comentou. O nome tem que bater com uma
	-- chave de Config.DANCAS; nome desconhecido cai na padrao em vez de deixar o
	-- boneco parado.
	danca: string,
	-- Segundos em que a formacao INTEIRA troca pra danca especial e volta.
	danca_geral: number,
	-- Escala do COLOSSO: um gigante atras da formacao, fora da grade. 0 = normal.
	colosso: number,

	-- O nome do presente que trouxe esta pessoa ("" = comentario ou curtida).
	presente: string,
	-- O ID numerico do presente no TikTok ("" = nao veio).
	presente_id: string,
	moedas: number,
	-- comentario | curtida | seguiu | compartilhou | presente
	tipo: string,
	-- Quantas curtidas CRUAS este evento representa (a ponte junta N por avatar).
	curtidas: number,
	-- A posicao dentro de um combo. 0 = o primeiro, ou um presente avulso.
	combo: number,
}

--[[ COMO FOI A ULTIMA CONVERSA COM O SERVIDOR.

	Guardado aqui porque o `pedir` engole os erros de proposito (com o servidor
	instavel, um warn por falha repetiria 60x por minuto e afogaria o Output).
	So' que engolir tudo produzia o pior sintoma do kit: a tela vazia com o chat
	andando, sem uma linha em lugar nenhum dizendo de que lado estava o
	problema.

	Agora o motivo fica gravado, e o Principal usa ele pra por um aviso na TELA
	-- que e' onde quem comprou esta' olhando. ]]
local ultimoOk = false
local ultimoMotivo = "ainda nao tentei falar com o servidor"

--[[ (deu certo?, por que nao). O motivo e' texto cru da Roblox: quem traduz
	pra portugues e' o Principal, que e' quem mostra. ]]
function Servidor.estado(): (boolean, string)
	return ultimoOk, ultimoMotivo
end

local function pedir(caminho: string): any?
	local ok, resposta = pcall(function()
		return HttpService:RequestAsync({
			Url = Segredos.URL .. caminho,
			Method = "GET",
			Headers = { ["X-Chave"] = Segredos.CHAVE },
		})
	end)

	if not ok then
		-- Erro de rede, ou HttpService desligado. Silencioso de proposito: com
		-- o servidor instavel isto repetiria 60x por minuto e afogaria o Output
		-- justamente quando voce precisa ler alguma outra coisa nele.
		ultimoOk, ultimoMotivo = false, tostring(resposta)
		return nil
	end
	if not resposta.Success then
		if resposta.StatusCode == 401 then
			warn("[servidor] chave recusada -- confira CHAVE em Segredos.luau")
		end
		ultimoOk = false
		ultimoMotivo = string.format("o servidor respondeu %d", resposta.StatusCode)
		return nil
	end
	ultimoOk, ultimoMotivo = true, ""

	local okJson, dados = pcall(function()
		return HttpService:JSONDecode(resposta.Body)
	end)
	return if okJson then dados else nil
end

--[[ "Estou entrando agora, me diga so' onde a fila esta'."

	Sem isto, um servidor de jogo que sobe no meio da live receberia o historico
	inteiro de uma vez e spawnaria uma multidao de fantasmas no primeiro segundo
	-- gente que comentou ha' dez minutos e ja' foi embora.
]]
function Servidor.ancorar(): number?
	local dados = pedir("/eventos")
	if type(dados) == "table" and type(dados.seq) == "number" then
		return dados.seq
	end
	return nil
end

--[[ Devolve (novoCursor, spawns).

	Em falha devolve o cursor ANTIGO e uma lista vazia: a proxima volta do laco
	tenta de novo do mesmo ponto, e ninguem se perde. ]]
function Servidor.puxar(cursor: number): (number, { Spawn })
	local dados = pedir("/eventos?desde=" .. tostring(cursor))
	if type(dados) ~= "table" or type(dados.seq) ~= "number" then
		return cursor, {}
	end

	local spawns: { Spawn } = {}
	for _, ev in ipairs(dados.lista or {}) do
		-- Um evento torto nao pode derrubar a live: valida, monta o que da', e
		-- ignora o resto em silencio.
		if type(ev) == "table" and type(ev.roblox_id) == "number" and ev.roblox_id > 0 then
			table.insert(spawns, {
				tiktok_id = tostring(ev.tiktok_id or ""),
				nickname = tostring(ev.nickname or "?"),
				nick_roblox = tostring(ev.nick_roblox or ""),
				roblox_id = ev.roblox_id,

				prio = tonumber(ev.prio) or 0,
				--[[ Teto 6, o MESMO do ESCALA_MAX do ponte/regras.py e do
					`Avatares.escalaDe`. Ja' foi 4 aqui, e os tres discordando
					custavam o presente mais caro da live: o painel mostrava 6, o
					arquivo gravava 6, e o boneco nascia 4. ]]
				escala = math.clamp(tonumber(ev.escala) or 1, 0.5, 6),
				-- Teto de 3 por evento, igual ao CRESCIMENTO_MAX do
				-- ponte/regras.py. Nao e' o teto do AVATAR (esse e' o
				-- tamanho_max, que vem do painel): e' o teto do SALTO, pra um
				-- evento torto nao fazer um boneco pular de tamanho num quadro
				-- so' e atravessar meia formacao antes de a camera reagir.
				crescimento = math.clamp(tonumber(ev.crescimento) or 0, 0, 3),
				vida = math.clamp(tonumber(ev.vida) or 45, 5, 900),
				-- Teto de 25s: um `segura` grande demais -- por bug ou por
				-- evento forjado -- congelaria os spawns, e a live inteira
				-- pararia sem nenhum sinal do que aconteceu.
				segura = math.clamp(tonumber(ev.segura) or 0.4, 0, 25),
				cena = math.clamp(tonumber(ev.cena) or 0, 0, 25),
				-- Teto de 20s pelo mesmo motivo: uma varredura sem fim deixaria
				-- a formacao presa pro resto da transmissao.
				furacao = math.clamp(tonumber(ev.furacao) or 0, 0, 20),
				cor = tostring(ev.cor or "FFFFFF"),
				brilho = math.clamp(tonumber(ev.brilho) or 0, 0, 5),
				-- Cortado em 20 caracteres: o nome vira ATRIBUTO do modelo, e
				-- um evento torto com um texto gigante ficaria replicado pra
				-- todos os clientes, cem vezes por ciclo, sem servir pra nada.
				danca = string.sub(tostring(ev.danca or ""), 1, 20),
				danca_geral = math.clamp(tonumber(ev.danca_geral) or 0, 0, 120),
				colosso = math.clamp(tonumber(ev.colosso) or 0, 0, 40),

				presente = tostring(ev.presente or ""),
				presente_id = string.sub(tostring(ev.presente_id or ""), 1, 20),
				moedas = tonumber(ev.moedas) or 0,
				-- "comentario" como padrao: um evento de uma ponte antiga (sem
				-- o campo) continua valendo como participacao, em vez de cair
				-- num tipo desconhecido e sumir dos placares.
				tipo = tostring(ev.tipo or "comentario"),
				-- Teto alto mas existente: um evento forjado com um numero
				-- absurdo tomaria o placar de curtidas pra sempre.
				curtidas = math.clamp(tonumber(ev.curtidas) or 0, 0, 100000),
				combo = math.clamp(tonumber(ev.combo) or 0, 0, 300),
			})
		end
	end
	return dados.seq, spawns
end

export type LinhaDePlacar = { nick: string, id: number, pontos: number }

--[[ Publica os TRES placares (top 10 cada) -- e' o que alimenta o overlay do
	OBS. Silencioso em falha, e de proposito: placar atrasado e' muito melhor
	que Output afogado no meio da live.

	Os tres numa requisicao so', e nao uma cada: sao tres leituras da MESMA live
	que mudam ao mesmo tempo, e manda-las separadas triplicaria o trafego pra
	mostrar exatamente a mesma coisa. ]]
function Servidor.publicarPlacar(moedas: { LinhaDePlacar }, curtidas: { LinhaDePlacar },
	presenca: { LinhaDePlacar })
	pcall(function()
		HttpService:RequestAsync({
			Url = Segredos.URL .. "/placar",
			Method = "POST",
			Headers = {
				["X-Chave"] = Segredos.CHAVE,
				["content-type"] = "application/json",
			},
			Body = HttpService:JSONEncode({
				moedas = moedas,
				curtidas = curtidas,
				presenca = presenca,
			}),
		})
	end)
end

--[[ Avisa em QUEM a camera acabou de parar.

	E' isto que faz a voz narrar: da' pra tocar uma fala gravada so' pra quem
	mandou presente, outra pra quem so' comentou -- e ate' uma so' da rosquinha,
	porque o nome do presente vai junto.

	Silencioso em falha, e chamado de dentro de um task.spawn: uma fala perdida
	nao vale segurar o laco da live. ]]
function Servidor.avisarCamera(tipo: string, nick: string, presente: string)
	pcall(function()
		HttpService:RequestAsync({
			Url = Segredos.URL .. "/camera",
			Method = "POST",
			Headers = {
				["X-Chave"] = Segredos.CHAVE,
				["content-type"] = "application/json",
			},
			Body = HttpService:JSONEncode({ tipo = tipo, nick = nick, presente = presente }),
		})
	end)
end

--[[ Manda pro painel o TAMANHO de cada avatar que esta' na tela.

	POR QUE O JOGO PRECISA CONTAR ISTO

	A ponte sabe quem mandou presente; so' o jogo sabe de que tamanho o boneco
	ficou. Sem este envio, a coluna "tamanho atual" do painel seria uma
	previsao -- e previsao erra sempre que um avatar nao carregou, quando o
	ciclo limpou a formacao, ou quando o teto de tamanho cortou o crescimento.
	Mostrar 5.4 pra um boneco que na verdade esta' em 2.0 e' pior do que nao
	mostrar nada, porque e' com esse numero que voce vai calibrar o painel. ]]
function Servidor.publicarTamanhos(tamanhos: { [string]: any })
	pcall(function()
		HttpService:RequestAsync({
			Url = Segredos.URL .. "/jogadores",
			Method = "POST",
			Headers = {
				["X-Chave"] = Segredos.CHAVE,
				["content-type"] = "application/json",
			},
			Body = HttpService:JSONEncode({ tamanhos = tamanhos }),
		})
	end)
end

--[[ O ciclo limpou a formacao: zera os tamanhos no painel de uma vez.

	Separado do `publicarTamanhos` porque nao da' pra dizer "ninguem tem
	avatar" mandando uma tabela vazia -- o servidor nao teria como distinguir
	isso de "nao tenho novidade", e o painel ficaria mostrando os tamanhos do
	ciclo anterior pra sempre. ]]
function Servidor.limparTamanhos()
	pcall(function()
		HttpService:RequestAsync({
			Url = Segredos.URL .. "/jogadores",
			Method = "POST",
			Headers = {
				["X-Chave"] = Segredos.CHAVE,
				["content-type"] = "application/json",
			},
			Body = HttpService:JSONEncode({ limpar_tamanhos = true }),
		})
	end)
end

--[[ Uma linha no diario do painel, vinda de DENTRO do jogo.

	O Output do Studio ja' recebe tudo por `print`/`warn`. Mas ele fica atras
	da janela do jogo durante a transmissao, e o que acontece no Roblox (o
	avatar que nao carregou, o ciclo que fechou) e' justamente o que nao
	aparece em lugar nenhum do painel. Com isto, o painel conta a historia
	inteira num lugar so'. ]]
function Servidor.contar(nivel: string, texto: string)
	pcall(function()
		HttpService:RequestAsync({
			Url = Segredos.URL .. "/logs",
			Method = "POST",
			Headers = {
				["X-Chave"] = Segredos.CHAVE,
				["content-type"] = "application/json",
			},
			Body = HttpService:JSONEncode({
				linhas = { { nivel = nivel, origem = "jogo", texto = texto } },
			}),
		})
	end)
end

--[[ Os ajustes do PAINEL. O jogo consulta de tempos em tempos e aplica sem
	reiniciar -- e' o que faz o "salvei e ja' valeu" ser verdade tambem DENTRO
	do Roblox, e nao so' na ponte. ]]
function Servidor.lerAjustes(): any?
	return pedir("/ajustes")
end

function Servidor.configurado(): boolean
	return Segredos.URL ~= "" and Segredos.CHAVE ~= ""
end

return Servidor
