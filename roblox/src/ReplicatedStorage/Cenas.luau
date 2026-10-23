--!strict
--[[
	AS CENAS -- o kit de temas do cenário, trocados ao vivo.

	MODULO PURO: so' numeros e nomes entram, so' numeros e nomes saem. Nenhuma
	Instance, nenhum serviço da Roblox, nenhum estado global.

	POR QUE ELE E' SEPARADO DO APLICADOR

	O nome de cada peça do set é o que decide a cor dela. Um nome escrito
	errado -- um `LenteRefletor` que virou `LenteRefletorEsq`, um `Degrau` que
	sobrou sem o número -- não dá erro nenhum: a peça simplesmente fica com a
	cor do mapa, e o resultado é um set com uma parede da cor errada que
	ninguém sabe explicar.

	Por isso a conta de "qual peça é qual papel" mora AQUI, num arquivo que
	roda FORA do Roblox, e tem uma suite de casos em
	roblox/testes/cenas.spec.luau que confere cada nome do mapa contra o papel
	que ele tem que receber.

	O QUE E' UM PAPEL

	Uma peça do set não tem uma cor: tem um PAPEL. "Isto é a parede", "isto é
	o acento quente", "isto é o tile que acende". A paleta de cada cena é uma
	tabela de PAPEL -> cor, e por isso uma cena nova não redesenha o mapa: ela
	só diz que "a parede" passa a ser verde, e todas as paredes ficam verdes de
	uma vez.

	O APLICADOR (ServerScriptService/Cena.luau) é quem caminha pelo mapa e
	pinta. Este arquivo só diz quem é quem.
]]

local Cenas = {}

--[[ UMA REGRA: o PADRÃO que casa com o nome, e o PAPEL que a peça recebe.
	O Luau não tem tipo de tupla, então a regra é uma tabela indexada: [1] é o
	padrão e [2] é o papel. ]]
type Regra = { [number]: string }

--[[ OS PAPEIS DO SET, e a ordem em que eles aparecem no painel.
	The order goes from the floor up: what the camera sees first is first. ]]
local SLOTS: { string } = {
	"SALAO", "PALCO", "REJUNTE",
	"PISTA_A", "PISTA_B", "PISTA_ACESA",
	"DEGRAU_A", "DEGRAU_B",
	"PAREDE", "PAREDE_ESC",
	"ESTRUTURA", "ESTRUTURA_ESC", "MADEIRA",
	"NEON_A", "NEON_B", "NEON_A_VIVO", "NEON_B_VIVO",
	"LENTE_QUENTE", "LENTE_FRIA",
	"TELA", "PAINEL_ALTO",
	"LUZ_QUENTE", "LUZ_FRIA",
}

--[[ AS REGRAS: nome da peça -> papel.

	O formato e' propositalmente simples: uma linha, um padrao, um papel. E' o
	que permite a suite de testes (e o teste de Python) lerem esta tabela e
	conferirem que TODA peça do mapa tem um papel -- sem ninguem precisar saber
	Luau pra fazer isso.

	A ORDEM IMPORTA: a primeira regra que casa e' a que vale. Por isso os
	nomes genericos ficam no fim. ]]
local REGRAS: { Regra } = {
	-- ─────────────────────────── A PISTA ───────────────────────────
	{"^PisoDoSalao$", "SALAO"},
	{"^Palco$", "PALCO"},
	{"^Rejunte$", "REJUNTE"},
	{"^Tile%d+_%d+$", "PISTA"},
	{"^FioPistaFrente$", "NEON_A"},
	{"^FioPistaEsq$", "NEON_A"},
	{"^FioPistaFundo$", "NEON_B"},
	{"^FioPistaDir$", "NEON_B"},
	{"^BordaPalco", "MADEIRA"},

	-- ─────────────────────────── OS DEGRAUS ───────────────────────────
	{"^DegrauEsq%d+$", "DEGRAU"},
	{"^DegrauDir%d+$", "DEGRAU"},
	{"^NarizDegrauEsq%d+$", "NEON_A"},
	{"^NarizDegrauDir%d+$", "NEON_B"},

	-- ─────────────────────── A PAREDE DE LED ───────────────────────
	{"^PainelInferior$", "PAREDE_ESC"},
	{"^Telao$", "TELA"},
	{"^PainelSuperior$", "PAREDE"},
	{"^AlmofadaAlta%d+$", "PAREDE_ESC"},
	{"^FioAlmofadaBase%d+$", "MADEIRA"},
	{"^FioAlmofadaTopo%d+$", "MADEIRA"},
	{"^Cornija$", "MADEIRA"},
	{"^FrisoDivisor0$", "NEON_A"},
	{"^FrisoDivisor1$", "NEON_B"},
	{"^MolduraTopo$", "MADEIRA"},
	{"^MolduraEsq$", "MADEIRA"},
	{"^MolduraDir$", "MADEIRA"},
	{"^MolduraBase$", "ESTRUTURA"},
	{"^AlaEsq$", "PAREDE_ESC"},
	{"^AlaDir$", "PAREDE_ESC"},
	{"^RipaAlaEsq%d+$", "ESTRUTURA"},
	{"^RipaAlaDir%d+$", "ESTRUTURA"},
	{"^AcentoLateralEsq$", "NEON_A"},
	{"^AcentoLateralDir$", "NEON_B"},

	-- ─────────────────────────── A CASCA ───────────────────────────
	{"^ParedeAlta$", "PAREDE_ESC"},
	{"^ParedeLateralEsq$", "PAREDE_ESC"},
	{"^ParedeLateralDir$", "PAREDE_ESC"},
	{"^PilastraLateralEsq%d+$", "PAREDE"},
	{"^PilastraLateralDir%d+$", "PAREDE"},
	{"^Forro$", "PAREDE_ESC"},
	{"^ParedeFrente$", "PAREDE_ESC"},

	-- ─────────────────────────── O PORTICO ───────────────────────────
	{"^ColunaPorticoEsq$", "PAREDE"},
	{"^ColunaPorticoDir$", "PAREDE"},
	{"^CaneluraPorticoEsq%d+$", "ESTRUTURA"},
	{"^CaneluraPorticoDir%d+$", "ESTRUTURA"},
	{"^FioPorticoEsq$", "NEON_A"},
	{"^FioPorticoDir$", "NEON_B"},
	{"^CapitelPorticoEsq$", "MADEIRA"},
	{"^CapitelPorticoDir$", "MADEIRA"},
	{"^VigaPortico$", "PAREDE"},
	{"^FioVigaPortico$", "MADEIRA"},

	-- ─────────────────────────── AS LUZES ───────────────────────────
	{"^TorreEsqFrente$", "ESTRUTURA"},
	{"^TorreEsqFundo$", "ESTRUTURA"},
	{"^TorreDirFrente$", "ESTRUTURA"},
	{"^TorreDirFundo$", "ESTRUTURA"},
	{"^VigaFundo$", "ESTRUTURA"},
	{"^VigaFrente$", "ESTRUTURA"},
	{"^VigaEsq$", "ESTRUTURA"},
	{"^VigaDir$", "ESTRUTURA"},
	{"^SoftboxFrente%d+$", "ESTRUTURA"},
	{"^SoftboxFundo%d+$", "ESTRUTURA"},
	{"^LuzFrente%d+$", "LENTE_QUENTE"},
	{"^LuzFundo%d+$", "LENTE_FRIA"},
	{"^RefletorEsq%d+$", "ESTRUTURA"},
	{"^RefletorDir%d+$", "ESTRUTURA"},
	{"^LenteRefletorEsq%d+$", "NEON_A"},
	{"^LenteRefletorDir%d+$", "NEON_B"},
	{"^HasteDoGlobo$", "ESTRUTURA"},
	{"^GloboEspelhado$", "PAREDE"},

	-- ─────────────────────────── O SOM ───────────────────────────
	{"^ColunaEsq%d+$", "PAREDE"},
	{"^ColunaDir%d+$", "PAREDE"},
	{"^FioColunaEsq%d+$", "NEON_A"},
	{"^FioColunaDir%d+$", "NEON_B"},
	{"^RemateColunaEsq%d+$", "MADEIRA"},
	{"^RemateColunaDir%d+$", "MADEIRA"},
	{"^CaixaBaseEsq$", "ESTRUTURA_ESC"},
	{"^CaixaBaseDir$", "ESTRUTURA_ESC"},
	{"^CaixaSomEsq%d+$", "ESTRUTURA"},
	{"^CaixaSomDir%d+$", "ESTRUTURA"},
	{"^ConeSomEsq%d+$", "ESTRUTURA_ESC"},
	{"^ConeSomDir%d+$", "ESTRUTURA_ESC"},
	{"^FrisoCaixaEsq$", "NEON_A"},
	{"^FrisoCaixaDir$", "NEON_B"},
}

--[[ AS FAIXAS DA TELA, que sao QUADROS e nao peças.
	The screen gradient is made of twelve stacked Frames, not of parts. ]]
local REGRAS_QUADRO: { Regra } = {
	{"^Fundo$", "PAINEL_ALTO"},
	{"^Faixa%d+$", "FAIXA"},
	{"^FioDoTopo$", "NEON_B"},
	{"^FioDaBase$", "NEON_A"},
}

Cenas.SLOTS = SLOTS
Cenas.REGRAS = REGRAS
Cenas.REGRAS_QUADRO = REGRAS_QUADRO

--[[ O PAPEL DE UMA PEÇA.

	`material` vem como TEXTO ("Neon", "Metal", "Concrete"...), e nao como
	Enum.Material, porque este módulo não conhece a Roblox. Quem chama passa
	o nome.

	O material entra por um motivo só: os ACENTOS DO SET existem em duas
	versões, uma de metal e outra que acende. A de metal é a cor clara; a que
	acende tem que ser escura, porque em Neon uma cor clara acende como BRANCO
	(e o branco no meio do quadro é um clarão, não um acento). Separar as duas
	pelo material é o que impede a cena de virar um borrão de luz. ]]
function Cenas.slotDe(nome: string, material: string?): (string?, number?)
	for _, regra in Cenas.REGRAS do
		local casa = string.match(nome, regra[1])
		if casa then
			local slot = regra[2]

			-- A pista tem tres papeis, e o nome sozinho nao diz qual.
			if slot == "PISTA" then
				local i, j = string.match(nome, "^Tile(%d+)_(%d+)$")
				if material == "Neon" then
					return "PISTA_ACESA", nil
				end
				local a = tonumber(i) or 0
				local b = tonumber(j) or 0
				if (a + b) % 2 == 0 then
					return "PISTA_A", nil
				end
				return "PISTA_B", nil
			end

			-- O acento que acende tem a propria cor.
			if slot == "NEON_A" and material == "Neon" then
				return "NEON_A_VIVO", nil
			end
			if slot == "NEON_B" and material == "Neon" then
				return "NEON_B_VIVO", nil
			end

			return slot, Cenas.parametro(nome)
		end
	end
	return nil, nil
end

--[[ O PAPEL DE UM QUADRO DA TELA. ]]
function Cenas.slotDeQuadro(nome: string): (string?, number?)
	for _, regra in Cenas.REGRAS_QUADRO do
		if string.match(nome, regra[1]) then
			return regra[2], Cenas.parametro(nome)
		end
	end
	return nil, nil
end

--[[ ONDE A PEÇA ESTÁ NO DEGRADE.

	Os degraus e as faixas da tela não têm uma cor só: são um degrade. O que
	se guarda em cada uma é a POSIÇÃO dentro dele -- de 0 (o começo) a 1 (o
	fim) -- e a cor final é misturada na hora.

	Os números 4 e 11 são o número de degraus menos um e o número de faixas
	menos um. ]]
function Cenas.parametro(nome: string): number?
	local degrau = string.match(nome, "^Degrau%a+(%d+)$")
	if degrau then
		return (tonumber(degrau) or 0) / 4
	end
	local faixa = string.match(nome, "^Faixa(%d+)$")
	if faixa then
		return (tonumber(faixa) or 0) / 11
	end
	return nil
end

--[[ A COR DE UM PAPEL, já com o degrade resolvido.

	`cores` é a tabela de cores da cena: {"SALAO": {r, g, b}, ...}, com os
	canais de 0 a 255. ]]
function Cenas.corDe(
	cores: { [string]: { number } },
	slot: string,
	t: number?
): { number }?
	if slot == "DEGRAU" then
		local a = cores["DEGRAU_A"]
		local b = cores["DEGRAU_B"]
		if not a or not b then
			return nil
		end
		return Cenas.misturar(a, b, t or 0)
	end
	if slot == "FAIXA" then
		local a = cores["PAINEL_ALTO"]
		local b = cores["TELA"]
		if not a or not b then
			return nil
		end
		return Cenas.misturar(a, b, t or 0)
	end
	return cores[slot]
end

--[[ MISTURA DUAS CORES.

	`a` e `b` são trios de 0 a 255; `t` vai de 0 (tudo `a`) a 1 (tudo `b`). ]]
function Cenas.misturar(a: { number }, b: { number }, t: number): { number }
	local n = math.clamp(t, 0, 1)
	return {
		a[1] + (b[1] - a[1]) * n,
		a[2] + (b[2] - a[2]) * n,
		a[3] + (b[3] - a[3]) * n,
	}
end

--[[ A COR DE UMA LUZ.

	Os focos (SpotLight) e a luz da face da tela (SurfaceLight) se chamam
	IGUALMENTE "Foco" e "LuzDaFace". O que os diferencia é o pai: um foco
	embaixo de uma luz de frente é quente, embaixo de uma luz de fundo é frio.

	O jogo passa o nome do pai. ]]
function Cenas.slotDeLuz(nomeDoPai: string): string?
	if string.match(nomeDoPai, "^LuzFundo") then
		return "LUZ_FRIA"
	end
	if string.match(nomeDoPai, "^LuzFrente") then
		return "LUZ_QUENTE"
	end
	-- O refletor de canto ilumina com luz quente.
	return "LUZ_QUENTE"
end

return Cenas
