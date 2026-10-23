--!strict
--[[
	O aviso na TELA quando a live nao esta' recebendo nada.

	POR QUE ISTO EXISTE

	O relato numero 1 de quem comprou o kit e' sempre a mesma frase: "apertei
	Play e nao acontece nada". E "nada" tem causas diferentes, com solucoes
	diferentes:

	  - a janela preta do servidor fechou (ou nem chegou a abrir);
	  - as requisicoes HTTP estao desligadas no Studio;
	  - esta' tudo certo e ninguem comentou um nick do Roblox ainda.

	Ate' aqui as tres se pareciam com exatamente a mesma coisa: um palco vazio.
	A resposta existia -- no Output do Studio, na janela preta da ponte, no
	diagnostico do painel -- mas em tres lugares que quem esta' de olho na tela
	do jogo nao esta' olhando.

	Entao a resposta vem pra ONDE A PESSOA ESTA' OLHANDO.

	QUANDO ELE APARECE, E QUANDO NAO APARECE

	So' quando o jogo passou varios segundos sem conseguir falar com o servidor
	-- ou seja, quando a live ja' esta' quebrada e nao ha' nada pra atrapalhar.
	Ele some sozinho no instante em que o servidor responde. Numa live que
	funciona, este arquivo nunca desenha nada.

	Fica no CANTO, e nao no meio, pelo mesmo motivo: se acontecer de aparecer
	com a transmissao no ar, ele avisa sem tapar a live.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local canal = ReplicatedStorage:WaitForChild("AvisoLive") :: RemoteEvent

-- A anotacao existe pro modo estrito: em StarterPlayerScripts o LocalPlayer
-- sempre existe, mas o tipo declarado pela Roblox e' `Player?`.
local jogador = Players.LocalPlayer :: Player
local paiDaGui = jogador:WaitForChild("PlayerGui")

local tela = Instance.new("ScreenGui")
tela.Name = "AvisoDaLive"
tela.ResetOnSpawn = false
-- Sem personagem, o jogador nunca "renasce", mas a inset da barra superior
-- continua existindo: sem isto o aviso nasce empurrado alguns pixels pra baixo
-- e desalinha do canto.
tela.IgnoreGuiInset = true
tela.DisplayOrder = 50
tela.Enabled = false
tela.Parent = paiDaGui

local caixa = Instance.new("Frame")
caixa.Name = "Caixa"
caixa.Size = UDim2.new(0, 520, 0, 132)
caixa.Position = UDim2.new(0.5, -260, 0, 24)
caixa.BackgroundColor3 = Color3.fromRGB(12, 12, 18)
caixa.BackgroundTransparency = 0.12
caixa.BorderSizePixel = 0
caixa.Parent = tela

local canto = Instance.new("UICorner")
canto.CornerRadius = UDim.new(0, 14)
canto.Parent = caixa

local linha = Instance.new("UIStroke")
linha.Color = Color3.fromRGB(255, 45, 111)
linha.Thickness = 2
linha.Transparency = 0.15
linha.Parent = caixa

local titulo = Instance.new("TextLabel")
titulo.Name = "Titulo"
titulo.BackgroundTransparency = 1
titulo.Size = UDim2.new(1, -32, 0, 34)
titulo.Position = UDim2.new(0, 16, 0, 14)
titulo.Font = Enum.Font.GothamBold
titulo.TextSize = 22
titulo.TextColor3 = Color3.fromRGB(255, 214, 64)
titulo.TextXAlignment = Enum.TextXAlignment.Left
titulo.Text = ""
titulo.Parent = caixa

local texto = Instance.new("TextLabel")
texto.Name = "Texto"
texto.BackgroundTransparency = 1
texto.Size = UDim2.new(1, -32, 0, 66)
texto.Position = UDim2.new(0, 16, 0, 50)
texto.Font = Enum.Font.Gotham
texto.TextSize = 16
texto.TextColor3 = Color3.fromRGB(235, 235, 245)
texto.TextXAlignment = Enum.TextXAlignment.Left
texto.TextYAlignment = Enum.TextYAlignment.Top
texto.TextWrapped = true
texto.Text = ""
texto.Parent = caixa

--[[ O servidor manda (titulo, texto) pra mostrar e (nil, nil) pra esconder.

	Esconder pelo `Enabled` em vez de destruir e recriar: a mesma live pode
	perder e recuperar o servidor varias vezes (a janela preta fechada e aberta
	de novo, por exemplo), e recriar a GUI a cada vez custaria uma piscada na
	transmissao. ]]
canal.OnClientEvent:Connect(function(qual: any, detalhe: any)
	if type(qual) ~= "string" or qual == "" then
		tela.Enabled = false
		return
	end
	titulo.Text = qual
	texto.Text = tostring(detalhe or "")
	tela.Enabled = true
end)
