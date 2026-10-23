--!strict
--[[
	O APLICADOR DAS CENAS -- quem caminha pelo mapa e pinta.

	Este arquivo é o outro lado do Cenas.luau: aquele diz qual peça é qual
	papel, este pinta as peças com a cor que o papel ganhou na cena de agora.

	POR QUE A COR NÃO ESTÁ NO MAPA

	O mapa foi desenhado com UMA paleta, e essa paleta está gravada em
	ferramentas/gerar-cenario.py. Trocar a cor do set significava, até aqui,
	editar o gerador e remontar o arquivo do jogo -- ou seja, reiniciar a live
	no meio da transmissão, que é a hora em que a live está cara.

	Aqui a cor deixa de ser do MAPA e passa a ser um DADO que chega pelo
	`/ajustes`, junto com o resto. Trocar de cena custa um clique e vale em
	até 5 segundos, sem reiniciar nada.

	O QUE ESTE ARQUIVO NÃO FAZ

	Ele não troca o MATERIAL de nada, nem a posição, nem o tamanho. A paleta
	de cada cena foi desenhada respeitando o material de cada peça: uma peça
	que é Neon continua Neon, e continua sendo Neon porque a cor que ela
	recebe é a versão escura do acento. Mudar o material junto com a cor
	estragaria o set -- e o set é bom.
]]

local Cenas = require(ReplicatedStorage:WaitForChild("Cenas"))

local Cena = {}

-- As sete pastas do set. A lista é a mesma do gerador do cenário: se um dia
-- o mapa ganhar uma pasta nova, é aqui que ela entra.
local PASTAS = {
	"Pista", "Degraus", "ParedeDeLED", "Casca", "Portico", "Luzes", "Som",
}

--[[ UM TRIPLO DE 0 A 255 VIRA COLOR3.

	As cores chegam do servidor como trio de 0 a 255, porque é assim que o
	gerador do cenário também as escreve (e como elas aparecem no painel).
	O Roblox trabalha de 0 a 1. ]]
local function trio(v: any): Color3?
	if type(v) ~= "table" then
		return nil
	end
	return Color3.new(
		(tonumber(v[1]) or 0) / 255,
		(tonumber(v[2]) or 0) / 255,
		(tonumber(v[3]) or 0) / 255
	)
end

--[[ A COR DE UM PAPEL, JÁ COM O DEGRADE RESOLVIDO. ]]
local function corDoPapel(
	cores: { [string]: { number } },
	slot: string?,
	t: number?
): Color3?
	if slot == nil then
		return nil
	end
	return trio(Cenas.corDe(cores, slot, t))
end

--[[ PINTA O SET INTEIRO.

	Devolve (deuCerto, motivo, quantasPecas).

	O motivo existe porque esta função pode ser chamada antes do mapa chegar:
	o `Cenario` é uma pasta que o Rojo monta, e nos primeiros segundos do
	jogo ela pode ainda não estar no lugar. Devolver "ainda não chegou" é
	melhor do que pintar meia parede e fingir que deu certo. ]]
function Cena.aplicar(paleta: any): (boolean, string, number)
	if type(paleta) ~= "table" then
		return false, "a paleta veio vazia", 0
	end

	local cores = paleta.cores
	if type(cores) ~= "table" then
		return false, "a paleta veio sem cores", 0
	end

	local cenario = workspace:FindFirstChild("Cenario")
	if not cenario then
		return false, "o cenario ainda nao chegou", 0
	end

	local pintadas = 0

	for _, nomeDaPasta in PASTAS do
		local pasta = cenario:FindFirstChild(nomeDaPasta)
		if pasta then
			for _, item in ipairs(pasta:GetDescendants()) do
				if item:IsA("BasePart") then
					local slot, t = Cenas.slotDe(item.Name, item.Material.Name)
					local c = corDoPapel(cores, slot, t)
					if c then
						item.Color = c
						pintadas += 1
					end
				elseif item:IsA("GuiObject") then
					-- As faixas da tela do fundo são GUI, e GUI não tem
					-- `Color`: tem `BackgroundColor3`.
					local slot, t = Cenas.slotDeQuadro(item.Name)
					local c = corDoPapel(cores, slot, t)
					if c then
						item.BackgroundColor3 = c
						pintadas += 1
					end
				elseif item:IsA("SpotLight") then
					local pai = item.Parent
					local slot = "LUZ_QUENTE"
					if pai then
						slot = Cenas.slotDeLuz(pai.Name) or "LUZ_QUENTE"
					end
					local c = corDoPapel(cores, slot, nil)
					if c then
						item.Color = c
						pintadas += 1
					end
				elseif item:IsA("SurfaceLight") then
					-- A luz da face da tela do fundo.
					local c = corDoPapel(cores, "LUZ_QUENTE", nil)
					if c then
						item.Color = c
						pintadas += 1
					end
				end
			end
		end
	end

	Cena.aplicarLuz(paleta.luz)

	return true, "", pintadas
end

--[[ A LUZ DA CENA.

	O que a cena mexe aqui é o que o painel NÃO mexe: a cor do ar, o quanto
	ele pesa, o quanto ele embaça, a tonalidade da correção de cor e o
	brilho.

	A luz AMBIENTE não é dela: essa é do painel, no aba "Câmera e luz", e é
	de onde se regula o quanto o set está claro ou escuro. Se a cena
	também mexesse nela, as duas coisas brigariam, e quem ajustou o brilho
	na mão veria o painel sobrescrevendo a cena (ou o contrário) a cada 5
	segundos. ]]
function Cena.aplicarLuz(luz: any)
	if type(luz) ~= "table" then
		return
	end

	local Lighting = game:GetService("Lighting")

	local ar = Lighting:FindFirstChild("Ar")
	if ar and ar:IsA("Atmosphere") then
		local c = trio(luz.atmo)
		if c then
			ar.Color = c
		end
		if type(luz.decay) == "number" then
			ar.Decay = luz.decay
		end
		if type(luz.haze) == "number" then
			ar.Haze = luz.haze
		end
	end

	local br = Lighting:FindFirstChild("Brilho")
	if br and br:IsA("BloomEffect") and type(luz.bloom) == "number" then
		br.Intensity = luz.bloom
	end

	local corr = Lighting:FindFirstChild("Cores")
	if corr and corr:IsA("ColorCorrectionEffect") then
		local c = trio(luz.tint)
		if c then
			corr.TintColor = c
		end
		if type(luz.saturacao) == "number" then
			corr.Saturation = luz.saturacao
		end
		if type(luz.contraste) == "number" then
			corr.Contrast = luz.contraste
		end
	end
end

return Cena
