--!nocheck
--[[
	Teste de COMPILAÇÃO do jogo inteiro. Roda FORA do Roblox.

		ferramentas\luau.exe roblox\testes\compila.spec.luau

	POR QUE ESTE TESTE EXISTE

	O Rojo NÃO compila o Luau: ele empacota os arquivos no lugar do jogo. Um
	erro de sintaxe passa pelo Rojo sem ser visto, e só aparece quando o
	Roblox Studio tenta carregar o script -- no meio de uma live, com a
	pessoa esperando o boneco aparecer.

	Este teste faz a conference antes: ele carrega cada script do jogo e
	pergunta se ele COMPILOU.

	O QUE É "COMPILOU" AQUI

	Fora do Roblox não existem `game`, `workspace`, `Color3` e companhia. Então
	carregar um script que usa esses nomes dá um erro de RUNTIME, e não de
	sintaxe. A diferença entre os dois é o que interessa:

	  - erro de SINTAXE ("Expected ..."): o arquivo está quebrado, e o
	    Studio não vai carregar. ESTE é o defeito que o teste caça.
	  - erro de RUNTIME ("attempt to index nil with 'GetService'"): o
	    arquivo está inteiro e só não achou o Roblox. Isso é o esperado.

	Um teste que passa é aquele em que NENHUM arquivo acusou erro de sintaxe.
]]

local function checar(caminho)
	local ok, res = pcall(require, caminho)
	if ok then
		return true, "compila"
	end
	local msg = tostring(res)
	if msg:find("Expected") or msg:find("Parse") or msg:find("syntax")
		or msg:find("Malformed") then
		return false, "ERRO DE SINTAXE: " .. msg
	end
	return true, "parse ok (parou em runtime, esperado fora do Roblox)"
end

-- Todos os scripts do jogo. A lista é o mapa do projeto: se um arquivo novo
-- entrar no jogo, ele entra nesta lista também.
local ARQUIVOS = {
	"../src/ReplicatedStorage/Cenas",
	"../src/ReplicatedStorage/Config",
	"../src/ReplicatedStorage/Enquadramento",
	"../src/ServerScriptService/Cena",
	"../src/ServerScriptService/ConfigServidor",
	"../src/ServerScriptService/Licenca",
	"../src/ServerScriptService/Avatares",
	"../src/ServerScriptService/Formacao",
	"../src/ServerScriptService/Segredos",
	"../src/ServerScriptService/Servidor",
	"../src/ServerScriptService/Principal.server",
	"../src/StarterPlayerScripts/Aviso.client",
	"../src/StarterPlayerScripts/Camera.client",
	"../src/StarterPlayerScripts/Rotulos.client",
}

local falhas = 0
local total = 0

print("O JOGO: conferindo se cada script compila")
for _, caminho in ipairs(ARQUIVOS) do
	local ok, detalhe = checar(caminho)
	total += 1
	if not ok then
		falhas += 1
	end
	print(string.format("  %-46s %s", caminho, detalhe))
end

print("")
print(string.rep("=", 86))
if falhas == 0 then
	print(string.format("JOGO: %d scripts, todos compilam.", total))
else
	print(string.format("JOGO: %d de %d NAO COMPILAM.", falhas, total))
end
print(string.rep("=", 86))

if falhas > 0 then
	error("um script do jogo nao compila", 0)
end
