--!strict
--[[
	Os ajustes que SÓ O SERVIDOR precisa: as animações.

	POR QUE ESTE ARQUIVO EXISTE, E POR QUE ELE NÃO ESTÁ NO Config.luau

	O Config.luau mora em ReplicatedStorage, e ReplicatedStorage é
	replicado para TODOS os jogadores. Qualquer pessoa que entre na sua
	experiência pode abrir o Explorer e ler o que está lá dentro.

	Os IDs das animações de terceiro (os que o kit comprou ou negociou)
	não podem estar lá: eles são a parte do produto que dá trabalho para
	conseguir, e a parte que o comprador não pode revender. Quem lê o
	Explorer da experiência publicada tira esses IDs de graça.

	Então eles vivem AQUI, em ServerScriptService, que nunca é replicado.

	NA BUILD DE VENDA, ESTES VALORES VÊM VAZIOS.

	O que está no arquivo do jogo entregue ao comprador é a estrutura
	só. Os números chegam com a LICENÇA, conferida pelo servidor de
	chaves -- e é o servidor de chaves que decide se o jogo funciona.

	Quem abre o .rbxlx no Studio vê o esqueleto. Quem tenta rodar sem
	licença não tem os números, e o jogo não dança.

	O `preencher` é quem recebe esses números, e quem decide, na
	build do vendedor, que eles já estão aqui.
]]

local ConfigServidor = {}

-- O ESPELHO: a tabela que o AVATARES de fato le e' a do modulo Config
-- (ReplicatedStorage). A licenca chega aqui (servidor, nunca replicado)
-- e este modulo empurra os ids para o espelho — sem ele, a licenca nao
-- mudaria o que os bonecos dançam. A build publica carrega zeros; so
-- preencher() escreve de verdade.
local Config = require(game:GetService("ReplicatedStorage"):WaitForChild("Config"))

--[[ ESTA É A BUILD DE VENDA. Os IDs de terceiro estão zerados:
--	eles chegam com a LICENÇA (o manifesto no GitHub), e o
--	servidor de chaves é quem os entrega. A reserva gratuita da
--	Roblox continua aqui, para que a formação dance mesmo sem
--	licença -- no passo padrão. ]]

--[[ A DANCA PRINCIPAL: "Jamal Brazil Groove", da Setalcix Emote Creations.

	83796130837213 e' a ANIMATION (tipo 24). O emote de catalogo com o mesmo
	nome e' o 104131334418357, tipo 61, e ele NAO funciona aqui -- colar o
	numero do emote nao da' erro nenhum, simplesmente nao toca nada, e voce
	perde horas procurando o problema no lugar errado.

	ATENCAO -- LEIA ANTES DE VENDER: este asset e' de TERCEIRO. Para tocar
	numa experiencia, o criador precisa compartilha-lo com ela pelo Creator
	Hub. No Studio em modo PLAY, que e' como esta live roda, o ID de terceiro
	costuma funcionar sem isso. Mas se um dia voce PUBLICAR o jogo, ou se a
	Setalcix mudar a permissao, ele para de tocar -- e ai' entra a reserva
	abaixo, sozinha, sem derrubar a live.

	Se este virar o carro-chefe do seu produto, vale falar com a Setalcix e
	pedir a autorizacao no seu nome. ]]
ConfigServidor.ANIMACAO = 0

--[[ A RESERVA. Animacao gratuita da propria Roblox: funciona sempre, em
	qualquer experiencia, sem depender da permissao de ninguem.

	Ela entra sozinha se a principal nao carregar. Sem isto, um asset de
	terceiro que perde a permissao no meio de uma live deixaria cem bonecos
	parados em pe', sem nenhuma mensagem explicando por que.

	Esta uma NAO e' protegida: e' um asset publico da Roblox, e esconder o
	ID de um asset publico nao protege nada. ]]
ConfigServidor.ANIMACAO_RESERVA = 507771019

--[[ A danca ESPECIAL: um presente configurado no painel faz a formacao
	INTEIRA trocar pra ela por alguns segundos, e depois ela volta sozinha.

	E' a MESMA da "festa" la' de baixo, e de proposito: ela precisa ser
	diferente das tres dancas de presente, senao a formacao inteira trocaria
	pra danca do oculos bem no momento em que ela deveria fazer algo que
	nenhum presente sozinho faz -- e a troca geral, que e' o efeito mais caro
	da live, passaria despercebida. ]]
ConfigServidor.ANIMACAO_ESPECIAL = 507776879

--[[ ───────── UMA DANCA POR PRESENTE ─────────

	Montado a partir de uma linha no Config, e nao escrito a mao, pra
	adicionar uma danca nova ser UMA linha -- e nao uma linha aqui mais
	outra no Config que alguem vai esquecer.

	As quatro de baixo (festa, disco, solto, passinho, swing) sao GRATUITAS
	DA PROPRIA ROBLOX, e existem pra o painel ter de que ESCOLHER. O kit
	vinha com quatro dancas e tres delas eram de terceiro. Quem quisesse
	dar um passo diferente pra um presente novo tinha que sair procurando
	emote no catalogo, extrair o ID da Animation de dentro dele e torcer
	pela permissao -- ou seja, o painel oferecia uma lista de quatro e nao
	havia como aumentar a lista sem mexer em codigo.

	Estas quatro nao dependem da permissao de ninguem: funcionam em
	qualquer experiencia, hoje e daqui a um ano. Sao o piso da escolha, e
	e' por isso que elas tem nome de PASSO e nao nome de presente -- qualquer
	presente pode usar qualquer uma. ]]

-- Os tres IDs de TERCEIRO. Estes sao os protegidos: na build de venda,
-- chegam com a licenca.
ConfigServidor.DANCAS = {
	-- emote 100548049120781 -> animacao "Imported Animation Clip"
	rosquinha = 0, -- Moonwalk, de Blast Motion
	-- emote 104142334418357 -> animacao "Style4"
	oculos = 0, -- Gangnam Style, de Our new group!
	-- emote 73946479113094 -> animacao "macaroni"
	galaxia = 0, -- Macarena, de Voxelates

	-- As gratuitas da propria Roblox.
	festa = 507776879, -- R15Dance2C
	disco = 507771019, -- R15Dance1A
	solto = 507772104, -- R15Dance1C
	passinho = 507776043, -- R15Dance2A
	swing = 507777268, -- R15Dance3A
}

--[[ O PREENCHER: é por aqui que a licença entrega o que falta.

	Na build do VENDEDOR, os valores já estão no arquivo e isto não faz
	nada. Na build de VENDA, os valores chegam vazios e são preenchidos
	com o que a licença autorizou.

	Os IDs de terceiro são os que interessam: os gratuitos da Roblox
	ficam, porque esconder o ID de um asset público não protege nada. ]]
function ConfigServidor.preencher(pacote: any)
	if type(pacote) ~= "table" then
		return false
	end

	local dancas = pacote.dancas
	if type(dancas) == "table" then
		for nome, id in pairs(dancas) do
			if type(nome) == "string" and type(id) == "number" and id > 0 then
				ConfigServidor.DANCAS[nome] = id
				Config.DANCAS[nome] = id -- o espelho que o AVATARES le
			end
		end
	end

	local animacao = pacote.animacao
	if type(animacao) == "number" and animacao > 0 then
		ConfigServidor.ANIMACAO = animacao
		Config.ANIMACAO = animacao -- o espelho que o AVATARES le
	end

	return true
end

--[[ TEM ALGUMA DANCA? (para o jogo saber se pode começar)

	Sem os IDs de terceiro, a formação ainda dança -- na reserva gratuita
	da Roblox. Então isto é mais um aviso do que um portão: quem tira a
	licença não fica com um jogo quebrado, e sim com um jogo sem os
	passos de presente. ]]
function ConfigServidor.temDancasDeTerceiro(): boolean
	return (ConfigServidor.DANCAS.rosquinha or 0) > 0
		or (ConfigServidor.DANCAS.oculos or 0) > 0
		or (ConfigServidor.DANCAS.galaxia or 0) > 0
end

return ConfigServidor
