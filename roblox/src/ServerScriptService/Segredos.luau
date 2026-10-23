--!strict
--[[
	Endereco e chave do servidor da live.

	Este modulo vive em ServerScriptService e NUNCA e' replicado pros clientes.
	E' por isso que ele existe separado do Config.luau: se a chave estivesse em
	ReplicatedStorage, qualquer pessoa que entrasse na sua experiencia
	conseguiria le-la e ficar consultando (ou poluindo) o seu servidor.
]]

return {
	--[[ O servidor roda na SUA maquina, sem nuvem e sem cota.

		Isto so' funciona com o jogo rodando no Studio em modo PLAY -- nesse
		modo o servidor do jogo roda no seu PC e alcanca o 127.0.0.1. O jogo
		PUBLICADO roda na nuvem da Roblox e nao alcanca a sua maquina; com ele,
		nada aparece, e nao ha' configuracao que resolva.
	]]
	URL = "http://localhost:8000",

	--[[ A chave de LEITURA. Nunca ponha a de escrita aqui.

		Se esta vazar, o pior que fazem e' ler a fila. Com a de escrita,
		injetariam avatares falsos na sua live. Rodando local nada disso e'
		alcancavel de fora do seu PC, mas o par continua separado pra que a
		troca pra nuvem, um dia, seja so' mudar estas duas linhas.
	]]
	CHAVE = "leitura-local",

	--[[ Intervalo entre consultas ao servidor.

		1s = 60 requisicoes por minuto, bem abaixo do teto de 500/min por
		servidor do HttpService.

		NAO baixe de 0,5s: estourar o teto nao da' erro, faz as requisicoes
		TRAVAREM por cerca de 30 segundos -- e ai' a live inteira congela, sem
		nenhuma mensagem dizendo por que.
	]]
	INTERVALO = 1.0,
}
