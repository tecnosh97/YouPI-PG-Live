--!nocheck
--[[
	Teste das CENAS -- as regras que dizem qual peça do set é qual papel.

		Roda FORA do Roblox:

			ferramentas\luau.exe roblox\testes\cenas.spec.luau

	POR QUE ESTE TESTE EXISTE

	Uma regra errada aqui não dá erro nenhum. A peça simplesmente fica com a
	cor do mapa, e o resultado é um set com uma parede da cor errada e uma
	faixa acesa que não acende -- e ninguém sabe explicar, porque no Output do
	Studio não aparece nada.

	Por isso este arquivo confere, peça por peça, que o NOME que o gerador do
	cenário grava no mapa cai na regra certa. A lista de nomes aqui é a mesma
	que está em ferramentas/gerar-cenario.py, e o teste de Python
	(servidor/testes_cenas.py) confere a outra ponta da corrente: que a cor de
	fábrica de cada papel é a cor que a peça tem no mapa.

	O que este teste NÃO faz é conferir a paleta: ela mora no servidor
	(servidor/cenas.py) e chega pelo /ajustes. O que ele confere é a decisão
	"isto é a parede, isto é o acento quente" -- a parte que, se errar, deixa
	o set torto sem dar nenhum aviso.
]]

local Cenas = require("../src/ReplicatedStorage/Cenas")

-- ─────────────────────────── O RELÓGIO ───────────────────────────

local falhas = 0
local total = 0

local function afirmar(condicao: boolean, mensagem: string)
	total += 1
	if not condicao then
		falhas += 1
		print("  FALHOU: " .. mensagem)
	end
end

local function iguais(a, b): boolean
	if type(a) ~= type(b) then
		return false
	end
	if type(a) ~= "table" then
		return a == b
	end
	for k, v in pairs(a) do
		if not iguais(v, b[k]) then
			return false
		end
	end
	for k in pairs(b) do
		if a[k] == nil then
			return false
		end
	end
	return true
end

-- ─────────────────────── AS PEÇAS DO SET ───────────────────────
--
-- A lista completa: todo nome que o gerador do cenário grava no mapa, com o
-- material que ele usa, e o papel que a peça tem que receber.
--
-- O nome da coluna do meio é a ESPERADA, e ela é o que este teste afirma.

local PECAS = {
	-- a pista
	{"PisoDoSalao", "SmoothPlastic", "SALAO"},
	{"Palco", "SmoothPlastic", "PALCO"},
	{"Rejunte", "Slate", "REJUNTE"},
	{"Tile0_0", "Marble", "PISTA_A"},
	{"Tile0_1", "Marble", "PISTA_B"},
	{"Tile1_1", "Marble", "PISTA_A"},
	{"Tile9_15", "Marble", "PISTA_A"},
	{"Tile0_1", "Neon", "PISTA_ACESA"},
	{"Tile9_13", "Neon", "PISTA_ACESA"},
	{"FioPistaFrente", "Neon", "NEON_A_VIVO"},
	{"FioPistaEsq", "Neon", "NEON_A_VIVO"},
	{"FioPistaFundo", "Neon", "NEON_B_VIVO"},
	{"FioPistaDir", "Neon", "NEON_B_VIVO"},
	{"BordaPalcoFrente", "Metal", "MADEIRA"},
	{"BordaPalcoEsq", "Metal", "MADEIRA"},
	{"BordaPalcoDir", "Metal", "MADEIRA"},

	-- os degraus
	{"DegrauEsq0", "Concrete", "DEGRAU"},
	{"DegrauEsq4", "Concrete", "DEGRAU"},
	{"DegrauDir0", "Concrete", "DEGRAU"},
	{"NarizDegrauEsq0", "Metal", "NEON_A"},
	{"NarizDegrauDir4", "Metal", "NEON_B"},

	-- a parede de LED
	{"PainelInferior", "Concrete", "PAREDE_ESC"},
	{"Telao", "SmoothPlastic", "TELA"},
	{"PainelSuperior", "Concrete", "PAREDE"},
	{"AlmofadaAlta0", "Concrete", "PAREDE_ESC"},
	{"FioAlmofadaBase0", "Metal", "MADEIRA"},
	{"FioAlmofadaTopo6", "Metal", "MADEIRA"},
	{"Cornija", "Metal", "MADEIRA"},
	{"FrisoDivisor0", "Neon", "NEON_A_VIVO"},
	{"FrisoDivisor1", "Neon", "NEON_B_VIVO"},
	{"MolduraTopo", "Metal", "MADEIRA"},
	{"MolduraEsq", "Metal", "MADEIRA"},
	{"MolduraDir", "Metal", "MADEIRA"},
	{"MolduraBase", "Concrete", "ESTRUTURA"},
	{"AlaEsq", "Concrete", "PAREDE_ESC"},
	{"AlaDir", "Concrete", "PAREDE_ESC"},
	{"RipaAlaEsq0", "Metal", "ESTRUTURA"},
	{"RipaAlaDir4", "Metal", "ESTRUTURA"},
	{"AcentoLateralEsq", "Metal", "NEON_A"},
	{"AcentoLateralDir", "Metal", "NEON_B"},

	-- a casca
	{"ParedeAlta", "Concrete", "PAREDE_ESC"},
	{"ParedeLateralEsq", "Concrete", "PAREDE_ESC"},
	{"ParedeLateralDir", "Concrete", "PAREDE_ESC"},
	{"PilastraLateralEsq0", "Concrete", "PAREDE"},
	{"PilastraLateralDir10", "Concrete", "PAREDE"},
	{"Forro", "Concrete", "PAREDE_ESC"},
	{"ParedeFrente", "Concrete", "PAREDE_ESC"},

	-- o portico
	{"ColunaPorticoEsq", "Concrete", "PAREDE"},
	{"ColunaPorticoDir", "Concrete", "PAREDE"},
	{"CaneluraPorticoEsq0", "Metal", "ESTRUTURA"},
	{"CaneluraPorticoDir3", "Metal", "ESTRUTURA"},
	{"FioPorticoEsq", "Metal", "NEON_A"},
	{"FioPorticoDir", "Metal", "NEON_B"},
	{"CapitelPorticoEsq", "Metal", "MADEIRA"},
	{"CapitelPorticoDir", "Metal", "MADEIRA"},
	{"VigaPortico", "Concrete", "PAREDE"},
	{"FioVigaPortico", "Metal", "MADEIRA"},

	-- as luzes
	{"TorreEsqFrente", "Metal", "ESTRUTURA"},
	{"TorreEsqFundo", "Metal", "ESTRUTURA"},
	{"TorreDirFrente", "Metal", "ESTRUTURA"},
	{"TorreDirFundo", "Metal", "ESTRUTURA"},
	{"VigaFundo", "Metal", "ESTRUTURA"},
	{"VigaFrente", "Metal", "ESTRUTURA"},
	{"VigaEsq", "Metal", "ESTRUTURA"},
	{"VigaDir", "Metal", "ESTRUTURA"},
	{"SoftboxFrente0", "SmoothPlastic", "ESTRUTURA"},
	{"SoftboxFundo4", "SmoothPlastic", "ESTRUTURA"},
	{"LuzFrente0", "Neon", "LENTE_QUENTE"},
	{"LuzFundo0", "Neon", "LENTE_FRIA"},
	{"RefletorEsq0", "SmoothPlastic", "ESTRUTURA"},
	{"RefletorDir5", "SmoothPlastic", "ESTRUTURA"},
	{"LenteRefletorEsq0", "Neon", "NEON_A_VIVO"},
	{"LenteRefletorDir5", "Neon", "NEON_B_VIVO"},
	{"HasteDoGlobo", "Metal", "ESTRUTURA"},
	{"GloboEspelhado", "Metal", "PAREDE"},

	-- o som
	{"ColunaEsq0", "Concrete", "PAREDE"},
	{"ColunaDir3", "Concrete", "PAREDE"},
	{"FioColunaEsq0", "Metal", "NEON_A"},
	{"FioColunaDir3", "Metal", "NEON_B"},
	{"RemateColunaEsq0", "Metal", "MADEIRA"},
	{"RemateColunaDir3", "Metal", "MADEIRA"},
	{"CaixaBaseEsq", "Metal", "ESTRUTURA_ESC"},
	{"CaixaBaseDir", "Metal", "ESTRUTURA_ESC"},
	{"CaixaSomEsq0", "Metal", "ESTRUTURA"},
	{"CaixaSomDir2", "Metal", "ESTRUTURA"},
	{"ConeSomEsq0", "Fabric", "ESTRUTURA_ESC"},
	{"ConeSomDir2", "Fabric", "ESTRUTURA_ESC"},
	{"FrisoCaixaEsq", "Metal", "NEON_A"},
	{"FrisoCaixaDir", "Metal", "NEON_B"},
}

print("AS CENAS: conferindo as regras do set")

for _, caso in ipairs(PECAS) do
	local nome, material, esperado = caso[1], caso[2], caso[3]
	local slot = Cenas.slotDe(nome, material)
	afirmar(slot == esperado, string.format(
		"'%s' (%s) caiu em '%s', e o papel certo e' '%s'",
		nome, material, tostring(slot), esperado))
end

--[[ A PISTA E' O UNICO LUGAR COM TRES PAPEIS, E O NOME NAO DIZ QUAL.

	O xadrez da pista alterna dois tomsex quase iguais, e uma das fileiras
	acende. A regra que decide é a paridade da soma dos dois números do nome
	-- mais o material, que separa o tile que acende. ]]
print("  a pista (o xadrez e o tile que acende)")
for i = 0, 9 do
	for j = 0, 15 do
		local nome = string.format("Tile%d_%d", i, j)
		local aceso = (j % 4 == 1) and (i == 0 or i == 9)
		local material = aceso and "Neon" or "Marble"
		local esperado
		if aceso then
			esperado = "PISTA_ACESA"
		elseif (i + j) % 2 == 0 then
			esperado = "PISTA_A"
		else
			esperado = "PISTA_B"
		end
		local slot = Cenas.slotDe(nome, material)
		afirmar(slot == esperado, string.format(
			"'%s' (%s) caiu em '%s', e o papel certo e' '%s'",
			nome, material, tostring(slot), esperado))
	end
end

--[[ O ACENTO QUE ACENDE TEM A COR DELE.

	Uma peça Neon desenha a própria cor no brilho máximo, sem cair com a
	distância. Numa cor clara, isso acende como BRANCO -- e o branco no meio
	do quadro é um clarão, não um acento. Por isso o acento que acende tem
	papel próprio, mais escuro. ]]
print("  o acento que acende (Neon) tem papel proprio")
afirmar(Cenas.slotDe("FioPorticoEsq", "Metal") == "NEON_A",
	"o acento de metal tem que ser o NEON_A")
afirmar(Cenas.slotDe("FioPorticoEsq", "Neon") == "NEON_A_VIVO",
	"o acento que acende tem que ser o NEON_A_VIVO")
afirmar(Cenas.slotDe("FioPorticoDir", "Neon") == "NEON_B_VIVO",
	"o acento frio que acende tem que ser o NEON_B_VIVO")

--[[ OS DEGRAUS E AS FAIXAS DA TELA SAO DEGRADES.

	O que se guarda em cada um é a POSIÇÃO dentro do degrade, de 0 a 1. ]]
print("  os degrades (degraus e a tela do fundo)")
afirmar(Cenas.parametro("DegrauEsq0") == 0, "o primeiro degrau e' o comeco do degrade")
afirmar(Cenas.parametro("DegrauEsq4") == 1, "o ultimo degrau e' o fim do degrade")
afirmar(Cenas.parametro("DegrauDir2") == 0.5, "o degrau do meio fica no meio do degrade")
afirmar(Cenas.parametro("Faixa0") == 0, "a primeira faixa e' o comeco do degrade")
afirmar(Cenas.parametro("Faixa11") == 1, "a ultima faixa e' o fim do degrade")

--[[ A TELA DO FUNDO E' FEITA DE QUADROS, E QUADRO NAO TEM `Color`. ]]
print("  a tela do fundo (os quadros)")
afirmar(Cenas.slotDeQuadro("Fundo") == "PAINEL_ALTO", "o fundo da tela e' o topo do degrade")
afirmar(Cenas.slotDeQuadro("Faixa0") == "FAIXA", "as faixas sao degrade")
afirmar(Cenas.slotDeQuadro("Faixa11") == "FAIXA", "as faixas sao degrade")
afirmar(Cenas.slotDeQuadro("FioDoTopo") == "NEON_B", "o fio de cima e' o acento frio")
afirmar(Cenas.slotDeQuadro("FioDaBase") == "NEON_A", "o fio da base e' o acento quente")

--[[ OS FOCOS SE CHAMAM TODOS IGUAL, E O QUE OS DIFERENCIA E' O PAI. ]]
print("  as luzes (o foco e' coldado pelo pai)")
afirmar(Cenas.slotDeLuz("LuzFrente0") == "LUZ_QUENTE", "a luz da frente e' quente")
afirmar(Cenas.slotDeLuz("LuzFundo0") == "LUZ_FRIA", "a luz do fundo e' fria")
afirmar(Cenas.slotDeLuz("RefletorEsq3") == "LUZ_QUENTE", "o refletor de canto e' quente")

--[[ A MISTURA DO DEGRADE. ]]
print("  a mistura das cores")
local cores = {
	DEGRAU_A = {0, 0, 0},
	DEGRAU_B = {100, 200, 255},
	PAINEL_ALTO = {10, 20, 30},
	TELA = {110, 120, 130},
}
afirmar(iguais(Cenas.corDe(cores, "DEGRAU", 0), {0, 0, 0}),
	"no comeco do degrade, a cor e' a do comeco")
afirmar(iguais(Cenas.corDe(cores, "DEGRAU", 1), {100, 200, 255}),
	"no fim do degrade, a cor e' a do fim")
afirmar(iguais(Cenas.corDe(cores, "DEGRAU", 0.5), {50, 100, 127.5}),
	"no meio do degrade, a cor e' a mistura")
afirmar(iguais(Cenas.corDe(cores, "FAIXA", 0), {10, 20, 30}),
	"a tela comeca no topo do degrade")
afirmar(iguais(Cenas.corDe(cores, "FAIXA", 1), {110, 120, 130}),
	"a tela termina na base do degrade")
afirmar(Cenas.corDe(cores, "PISTA_A", nil) == nil,
	"um papel que nao existe na paleta devolve nada")

--[[ UM NOME QUE NAO EXISTE NAO PODE VIRAR PAPEL. ]]
print("  um nome que nao existe no set")
afirmar(Cenas.slotDe("PalcoDoMeio", "SmoothPlastic") == nil,
	"uma peca que nao esta' no set nao pode ter papel")
afirmar(Cenas.slotDeQuadro("FotoDoPerfil") == nil,
	"um quadro que nao esta' no set nao pode ter papel")

-- ─────────────────────────── O RESUMO ───────────────────────────

print("")
print(string.rep("=", 86))
if falhas == 0 then
	print(string.format("CENAS: %d verificacoes, todas passaram.", total))
else
	print(string.format("CENAS: %d de %d FALHARAM.", falhas, total))
end
print(string.rep("=", 86))

if falhas > 0 then
	error("teste das cenas falhou", 0)
end
