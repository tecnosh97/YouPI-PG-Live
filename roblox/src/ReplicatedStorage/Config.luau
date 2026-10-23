--!strict
--[[
	Ajustes que o CLIENTE tambem precisa enxergar: camera, animacao, formacao.

	Nada de segredo aqui. Tudo em ReplicatedStorage e' replicado pra todos os
	jogadores e pode ser lido por qualquer um. A URL e a chave do servidor ficam
	em ServerScriptService/Segredos.luau, que nunca sai do servidor.
]]

return {
	--[[ ─────────────────────── A DANCA ───────────────────────

		Estes IDs sao animacoes GRATUITAS da propria Roblox. Elas funcionam
		sempre, em qualquer experiencia, sem voce precisar de permissao de
		ninguem -- e essa e' a razao de serem o padrao aqui.

		Se voce quiser usar um emote comprado do catalogo, ATENCAO a uma
		armadilha que custa horas: o ID do emote de catalogo (tipo 61) NAO
		funciona em Animation.AnimationId, que so' aceita tipo 24. Colar o ID do
		emote nao da' erro nenhum -- simplesmente nao toca nada, e voce fica
		procurando o problema no lugar errado. E' preciso extrair o ID da
		Animation que mora DENTRO do emote.

		E mais importante: um asset de TERCEIRO precisa da autorizacao do criador
		pra tocar na sua experiencia. Se um dia aparecer "Failed to load
		animation", e' permissao, nao o ID.

		Outras gratuitas da Roblox, caso queira variar:
		  507771019  Dance1A     507772104  Dance1C
		  507776043  Dance2A     507776879  Dance2C
		  507777268  Dance3A
	]]
	--[[ A DANCA PRINCIPAL: "Jamal Brazil Groove", da Setalcix Emote Creations.

		83796130837213 e' a ANIMATION (tipo 24). O emote de catalogo com o mesmo
		nome e' o 104131847054135, tipo 61, e ele NAO funciona aqui -- colar o
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
	ANIMACAO = 0, -- "Jamal Brazil Groove": chega cifrada pela licenca (vendo o preencher no ConfigServidor)

	--[[ A RESERVA. Animacao gratuita da propria Roblox: funciona sempre, em
		qualquer experiencia, sem depender da permissao de ninguem.

		Ela entra sozinha se a principal nao carregar. Sem isto, um asset de
		terceiro que perde a permissao no meio de uma live deixaria cem bonecos
		parados em pe', sem nenhuma mensagem explicando por que. ]]
	ANIMACAO_RESERVA = 507771019,

	--[[ ───────── UMA DANCA POR PRESENTE ─────────

		Quem chega por presente caro dança DIFERENTE de quem so' comentou. E'
		o que faz o presente ser visivel de longe: quem assiste percebe que
		aconteceu alguma coisa antes mesmo de ler o nome na tela.

		A chave da esquerda e' o que o painel manda no campo `danca` do efeito.
		"" (vazio) = usa a ANIMACAO principal, la' de cima.

		ESTAS CHAVES SAO UM CONTRATO COM O PYTHON. Uma dança so' chega aqui se o
		nome dela passar pela lista `DANCAS_VALIDAS` do ponte/regras.py -- ela
		existe justamente pra um nome errado no painel virar "dança padrao" em
		vez de virar um boneco parado em pe'. Criou uma dança nova aqui? Ponha o
		mesmo nome la' tambem, senao ela nunca sera' usada.

		As tres primeiras sao EMOTES COMPRADOS, com autorizacao dos criadores.
		A `festa` continua sendo uma gratuita da Roblox, de proposito: ela e' a
		unica que nao depende de permissao de terceiro, entao se um dia as
		outras pararem de carregar ainda sobra uma danca de verdade na live.

		O CAMPO `criador` NAO E' DECORACAO. A autorizacao de uso destas
		animacoes foi concedida com UMA contrapartida: creditar os autores na
		live. O nome fica ao lado do ID pra a obrigacao aparecer pra quem mexer
		na tabela, em vez de virar uma promessa que ninguem lembra.

		Pra trocar uma delas por outro emote comprado, lembre da armadilha: o
		ID do emote de CATALOGO (tipo 61) nao funciona aqui. So' o da Animation
		(tipo 24) que mora dentro dele. Pra extrair:

		    python ponte/extrair_animacao.py <id do emote>

		Se um dia uma delas parar de tocar com "Failed to load animation", e'
		PERMISSAO do asset e nao o ID: peca ao criador pra compartilhar com a
		experiencia pelo Creator Hub. No Studio em modo PLAY -- que e' como
		esta live roda -- o ID de terceiro funciona. ]]
	DANCAS = {
		-- emote 100548049120781 · animacao "Imported Animation Clip"
		rosquinha = 0, -- Moonwalk, de Blast Motion (o id chega pela licenca)
		-- emote 104142334418357 · animacao "Style4"
		oculos = 0, -- Gangnam Style (o id chega pela licenca)
		-- emote 73946479113094 · animacao "macaroni"
		galaxia = 0, -- Macarena, de Voxelates (o id chega pela licenca)
		festa = 507776879, -- R15Dance2C, gratuita da Roblox

		--[[ AS QUATRO DE BAIXO SAO GRATUITAS DA PROPRIA ROBLOX, e existem pra
			o painel ter de que ESCOLHER.

			O kit vinha com quatro dancas e tres delas eram de terceiro. Quem
			quisesse dar um passo diferente pra um presente novo tinha que sair
			procurando emote no catalogo, extrair o ID da Animation de dentro
			dele e torcer pela permissao -- ou seja, o painel oferecia uma lista
			de quatro e nao havia como aumentar a lista sem mexer em codigo.

			Estas quatro nao dependem da permissao de ninguem: funcionam em
			qualquer experiencia, hoje e daqui a um ano. Sao o piso da escolha,
			e e' por isso que elas tem nome de PASSO e nao nome de presente --
			qualquer presente pode usar qualquer uma. ]]
		disco = 507771019,     -- R15Dance1A
		solto = 507772104,     -- R15Dance1C
		passinho = 507776043,  -- R15Dance2A
		swing = 507777268,     -- R15Dance3A
	},

	--[[ A danca ESPECIAL: um presente configurado no painel faz a formacao
		INTEIRA trocar pra ela por alguns segundos, e depois ela volta sozinha.

		E' a MESMA da "festa" la' de cima, e de proposito: ela precisa ser
		diferente das tres dancas de presente, senao a formacao inteira trocaria
		pra danca do oculos bem no momento em que ela deveria fazer algo que
		nenhum presente sozinho faz -- e a troca geral, que e' o efeito mais caro
		da live, passaria despercebida. ]]
	ANIMACAO_ESPECIAL = 507776879,

	--[[ ───────────────────── A FORMACAO ─────────────────────

		A grade onde os avatares ficam em pe'. Estes sao os valores de fabrica;
		o painel manda os dele por cima, em tempo real.
	]]
	-- Quantos cabem antes de a formacao fechar o ciclo e recomecar do zero.
	MAX_AVATARES = 100,
	-- Quantos por fileira. A camera fica do lado +Z, entao cada fileira nova
	-- nasce mais PERTO de quem assiste.
	POR_FILA = 10,
	-- Distancia entre avatares vizinhos, em studs.
	ESPACO_X = 6,
	--[[ Distancia entre uma fileira e a proxima, PARA GENTE DE TAMANHO NORMAL.

		Maior que o ESPACO_X de proposito: com as fileiras muito juntas, quem
		esta' atras fica escondido por quem esta' na frente, e a formacao vira
		uma parede.

		Uma fileira com boneco grande abre mais que isto sozinha -- ela empurra a
		seguinte pelo tamanho do maior que tem. Ver `zDaFileira` no Formacao.luau:
		com este numero fixo pra todo mundo, um gigante invadia a fileira da
		frente com metade do corpo e a formacao virava um amontoado. ]]
	ESPACO_Z = 8,
	--[[ Quanto de LARGURA um avatar de escala 1.0 ocupa. E' o que decide quantos
		slots um avatar GRANDE precisa -- sem isso, um boneco de escala 4 nasceria
		em cima dos vizinhos.

		6 e nao 5: um R15 parado tem uns 4 studs de ombro a ombro, mas DANCANDO
		ele abre os bracos, e a conta apertada deixava o boneco de escala 3.2 (a
		galaxia) com tres slots quando o corpo dele pede quatro -- os bracos
		batiam nos vizinhos no meio da coreografia. ]]
	LARGURA_POR_ESCALA = 6,

	--[[ ───────────────────── O CRESCIMENTO ─────────────────────

		A promessa da live: "envie presentes e seu personagem cresce".

		ELA NAO ESTA' ESCRITA EM LUGAR NENHUM DO JOGO, e isso e' de proposito:
		o mapa nao tem uma letra (ver ferramentas/gerar-cenario.py). Quem faz a
		promessa e' a sua VOZ e o overlay do OBS; quem CUMPRE ela sao estes
		numeros aqui.

		Estes sao os valores de fabrica. O painel manda os dele por cima em
		tempo real (o Principal os espelha em atributos do workspace), entao
		mexer aqui so' muda o comportamento de quem nunca abriu o painel.
	]]
	CRESCIMENTO = {
		--[[ O que um presente faz na tela. "novo" | "crescer" | "ambos".

			  novo      cada presente poe um boneco NOVO na tela. <-- PADRAO
			  crescer   o presente engorda o boneco que a pessoa ja' tem.
			  ambos     as duas coisas.

			O padrao e' "novo" por uma razao de produto: presente tem que
			colocar ALGUMA COISA NOVA na tela. Um boneco que so' incha no meio
			da formacao e' um efeito que quem assiste pelo celular nao liga ao
			presente que acabou de passar no chat -- e quem pagou fica sem
			saber se funcionou.

			As tres opcoes sao legitimas e o painel troca entre elas ao vivo:
			"novo" mostra QUANTA gente participou, "crescer" premia QUEM
			gastou. Este valor so' vale enquanto o painel nunca foi aberto. ]]
		MODO = "novo",

		--[[ Ate' onde um avatar pode crescer somando presente sobre presente.

			6.0 nao e' um numero solto: e' o maior tamanho em que um boneco
			ainda CABE no enquadramento junto com a formacao. Acima disso a
			camera precisa recuar tanto pra ele caber que todo o resto da live
			vira um tapete de pontinhos no chao -- ou seja, o presente mais caro
			passaria a ESTRAGAR o quadro em vez de destacar quem pagou.

			Quem chega ao teto NAO para de receber efeito: o presente seguinte
			vira um avatar novo (ver `crescer` no Principal). ]]
		TAMANHO_MAX = 6.0,

		--[[ Quanto o crescimento demora, em segundos.

			Salto seco parece bug -- o boneco simplesmente e' outro no quadro
			seguinte, e quem esta' assistindo nao liga uma coisa a' outra. Longo
			demais termina depois de a camera ja' ter ido embora, e a pessoa nao
			ve' o que pagou. 0,6s e' o ponto em que da' pra VER acontecendo. ]]
		SUAVE_S = 0.6,
	},

	--[[ ───────────────────── A CAMERA ─────────────────────

		SEGUIR   o padrao, e o que roda a live quase inteira. Acompanha quem
		         acabou de chegar, com atraso, e RECUA quando o boneco e' grande
		         em vez de ficar em cima dele.
		ABERTA   fim do ciclo: recua e mostra a formacao inteira antes de limpar.
		CENA     DESLIGADA (ver CENA_LIGADA). Girava em volta de quem mandou
		         presente caro; enjoava e escondia a multidao.
	]]
	CAMERA = {
		--[[ ═══════════════ O ENQUADRAMENTO ═══════════════

			TUDO QUE DECIDE O QUADRO DA LIVE ESTA' NESTE BLOCO.

			E a camera NAO usa estes numeros crus: ela usa como PONTO DE PARTIDA
			e depois confere, quadro a quadro, se o telao e o avatar cabem os
			dois. Ver `enquadrar` no Camera.client.luau.

			Por que um solver em vez de numeros fixos: a distancia certa depende
			de tres coisas que mudam o tempo todo -- o tamanho do avatar (que
			agora CRESCE com presente, ate' 6x), a fileira em que ele esta' (a
			formacao anda 70 studs em direcao a' camera ao longo do ciclo) e o
			formato do video (9:16 corta muito mais que 16:9). Qualquer numero
			fixo esta' errado em duas das tres situacoes; foi assim que o topo do
			telao vivia cortado justamente na primeira fileira. ]]

		--[[ Altura da camera, CONTADA A PARTIR DO MEIO DO ALVO.

			A conta e' `pes + ALTURA + metade da altura do boneco` (ver
			`resolver` no Enquadramento.luau), entao 1 num boneco normal poe a
			lente a 4 studs do chao: A ALTURA DO PEITO dele.

			POR QUE NA ALTURA DO PEITO, E NAO ACIMA

			Era 19 (lente a 22 studs), depois 6.5 (lente a 9,5) -- e os dois
			ainda olhavam pra BAIXO. Camera acima da cabeca mostra a formacao
			como GRADE: da' pra contar as fileiras, e o boneco de quem acabou de
			comentar aparece de cima, que e' o angulo em que uma skin menos se
			reconhece (voce ve' o chapeu e o ombro, nao a roupa nem o rosto).

			No peito, a lente olha o boneco DE FRENTE. E' o enquadramento de
			quem esta' conversando com ele, e nao de quem esta' vigiando a
			plateia -- e e' o unico que mostra a skin inteira do jeito que a
			pessoa a montou.

			ELA ACOMPANHA O TAMANHO sozinha: a metade da altura do boneco entra
			na conta, entao um avatar de 36 studs e' filmado a 19 studs de
			altura -- o peito DELE. Nenhum caso especial no codigo.

			O preco disso esta' no fundo, e ele e' real: uma lente nessa altura
			nao alcanca o alto da parede. Por isso a FAIXA ACESA do fundo mora
			na parte de baixo dela -- ver o bloco TELAO aqui embaixo e o
			Cenario.model.json. ]]
		ALTURA = 1,

		--[[ Distancia de quem ela esta' seguindo -- o ponto de PARTIDA.

			Este numero e' o que decide se a live parece um close claustrofobico
			ou um palco. Perto demais, o avatar toma a tela inteira e nao da' pra
			ver que tem uma multidao atras -- e a multidao e' o argumento que faz
			a proxima pessoa comentar. Longe demais e os bonecos viram formigas.

			13 com a lente de 40 graus, na altura do peito, deixa um avatar
			normal ocupando mais da metade da altura do quadro, DE FRENTE. E' o
			plano em que a skin e o nick se leem sem esforco no celular de quem
			assiste -- que e' a coisa que esta live vende.

			Referencia pra ajustar:
			  10 = close no rosto
			  13 = padrao: corpo inteiro de frente, multidao atras
			  20 = grupo, duas ou tres fileiras
			  38 = o plano antigo, o palco inteiro ]]
		DISTANCIA = 13,

		--[[ Os limites dentro dos quais o solver pode se mexer.

			Ele SO' AFASTA a partir da DISTANCIA, nunca aproxima -- entao o
			MINIMO e' um piso de seguranca (se voce puser uma DISTANCIA absurda
			no painel) e o MAXIMO e' o que impede um colosso de empurrar a camera
			pro outro lado do mapa, transformando a live inteira num tapete de
			pontinhos. ]]
		DISTANCIA_MIN = 8,
		DISTANCIA_MAX = 120,

		--[[ ═══════════════ O ZOOM DE CHEGADA ═══════════════

			Quem comenta ou manda presente ganha alguns segundos de CLOSE: o
			boneco grande na tela, com o nick legivel, e depois a camera volta
			pro plano normal.

			POR QUE ELE EXISTE

			Os dois pedidos do quadro brigam entre si. O plano normal precisa
			mostrar a MULTIDAO e o TELAO -- e' o que faz a proxima pessoa
			comentar. O close precisa mostrar UMA pessoa e o nome dela -- e' o
			que faz quem ja' comentou continuar assistindo. Nao existe uma
			distancia so' que entregue as duas: a que mostra a multidao deixa a
			skin pequena, e a que mostra a skin corta a multidao.

			Resolvido no TEMPO, e nao no espaco, os dois cabem: o close acontece
			no instante em que a pessoa chega -- que e' o unico instante em que
			ela esta' olhando -- e o resto do tempo a live respira aberta. ]]
		ZOOM_LIGADO = true,

		--[[ Quantos segundos o close dura.

			2,2 e' tempo de LER um nick e reconhecer uma roupa, e pouco pra
			cansar. Mais curto vira susto; mais longo e a live vira uma
			sequencia de closes, sem multidao nenhuma -- que e' exatamente o
			defeito pelo qual a cinematica antiga (CENA_LIGADA) foi desligada. ]]
		ZOOM_S = 2.2,

		--[[ Onde o close COMECA a procurar distancia, por unidade de tamanho
			do boneco.

			E' o piso da busca, e nao a distancia final: o solver afasta a
			partir daqui ate' o boneco e o balao do nome caberem. Num avatar
			normal isso da' uns 12 studs, com o corpo ocupando ~70% da altura
			do quadro. Multiplicado pelo tamanho porque um boneco de escala 4
			precisa de quatro vezes mais espaco pro mesmo quadro. ]]
		ZOOM_DISTANCIA = 9,

		--[[ A folga do close, em graus -- menor que a do plano normal.

			O close nao tem telao pra acomodar nem multidao pra respeitar: e' um
			retrato. Apertar a margem de 4 pra 2 graus tira ~1,5 stud de
			distancia sem tirar nada do quadro, porque o que sobra na borda de
			um close e' ar, e nao cenario.

			ELE NAO PODE IR A ZERO: sem folga nenhuma, o balao do nome encosta
			na borda de cima e o pe' do boneco na de baixo, e qualquer tremida
			da interpolacao corta um dos dois. ]]
		ZOOM_MARGEM_GRAUS = 2,

		--[[ Suavidade da ENTRADA no close -- bem maior que a normal.

			O pedido foi literal: "tem que ser um zoom rapido". Com a suavidade
			de sempre (0.08) a camera levaria mais de um segundo pra chegar no
			close, ou seja, ainda estaria viajando quando o tempo dele acabasse
			-- e o que sai no video e' um vai-e-vem molenga, nao um zoom. Em
			0.22 ela fecha o movimento em ~0.25s.

			A VOLTA usa a suavidade normal, e de proposito: sair devagar do
			close devolve a multidao sem susto. ]]
		ZOOM_SUAVIDADE = 0.22,

		--[[ Ate' onde o TELAO pode empurrar a lente pra tras, em studs.

			Sem este teto, o telao mandava no plano inteiro: ele fica 74 studs
			atras da formacao, e caber o topo dele junto com o avatar exigia
			recuar ate' o boneco virar um bonequinho. A live ficava longe por
			causa do FUNDO.

			Com ele, quem manda e' o AVATAR. Se o telao nao couber dentro deste
			limite, o solver desiste dele -- o mesmo caminho que ja' existia pro
			colosso -- e entrega o plano de perto, com o telao aparecendo
			cortado. E' o preco certo: o boneco de quem chegou e' o assunto, o
			telao e' o cartaz atras dele. ]]
		TELAO_RECUO_MAX = 22,

		--[[ Abertura da lente, em graus (vertical).

			40 nos dois formatos. Antes eram 62 e 68 -- uma grande-angular, que
			e' a lente certa pra caber MUITA COISA e a errada pra mostrar UMA
			PESSOA: ela estica o que esta' perto da borda e achata o rosto de
			quem esta' no meio, e agora quem esta' no meio e' o assunto.

			Fechar a lente tambem e' o que permite chegar a 18 studs sem o
			quadro virar um olho-de-peixe. Os dois numeros andam juntos: uma
			lente aberta a 18 studs deformaria o boneco; uma lente fechada a 38
			mostraria so' um pedaco da formacao.

			OS DOIS FORMATOS IGUAIS, e antes nao eram. A vertical era mais
			aberta pra devolver largura no 9:16, onde a abertura horizontal sai
			da vertical pela proporcao da tela. Com 40 a largura util no 9:16 e'
			estreita mesmo -- e a resposta pra isso nao e' abrir a lente e
			entortar o boneco. E' o fundo nao depender de largura: ele nao tem
			texto pra ler, so' um degrade aceso que funciona em qualquer fatia
			que o 9:16 deixe aparecer. ]]
		FOV = 40,
		FOV_VERTICAL = 40,

		--[[ Folga, em graus, entre o que PRECISA aparecer e a borda do quadro.

			Sem ela o solver entrega um enquadramento tecnicamente correto e
			visualmente sufocado: o topo do telao encostado na borda de cima, os
			pes do avatar encostados na de baixo. 4 graus de cada lado e' o
			respiro que faz o quadro parecer composto em vez de espremido. ]]
		MARGEM_GRAUS = 4,

		--[[ Quanto do quadro o telao pode exigir pra si.

			Se o avatar cresceu muito, chega um ponto em que enquadrar os dois
			exige recuar tanto que os DOIS ficam pequenos. Passando disto, o
			solver desiste do topo do telao e prioriza o avatar -- ainda aparece
			bastante telao no fundo, mas o presente que a pessoa pagou continua
			grande na tela, que e' a escolha certa nesse impasse. ]]
		TELAO_ATE_GRAUS = 46,
		-- Suavidade do movimento, de 0 a 1. Quanto MENOR, mais macio -- e mais
		-- lento pra alcancar. 0.08 e' o ponto em que ela parece uma camera na
		-- mao de alguem, sem enjoar quem assiste.
		SUAVIDADE = 0.08,
		-- Distancia no plano ABERTO, no fim de cada ciclo. Precisa ser bem maior
		-- que a DISTANCIA, senao o "plano aberto" fica parecido demais com o de
		-- perto e o momento de mostrar a multidao inteira se perde.
		RECUO = 85,
		ALTURA_ABERTA = 48,
		-- Quanto o plano aberto dura antes de a formacao ser apagada.
		ABERTA_S = 3.0,
		--[[ A CINEMATICA DE GIRO -- DESLIGADA.

			Ligada, um presente caro fazia a camera CORTAR pro avatar e dar uma
			volta em torno dele. No papel e' o momento da pessoa; na tela o giro
			nao para de acontecer -- e numa live movimentada, com presente
			chegando a cada poucos segundos, a camera passava mais tempo rodando
			em volta de alguem do que mostrando a live. Fica tonto de assistir, e
			pior: cada giro joga fora a MULTIDAO do fundo, que e' o argumento que
			faz a proxima pessoa entrar.

			Desligada, quem pagou nao perde nada. A camera normal ja' vai atras
			de quem acabou de chegar, e o `segura` do presente continua valendo:
			ninguem nasce por cima dele. Ele fica em quadro o mesmo tempo -- so'
			que parado, com a formacao inteira atras.

			Pra ligar de volta: `true` aqui. O resto continua funcionando. ]]
		CENA_LIGADA = false,
		-- Velocidade do giro, em voltas por segundo (so' vale com CENA_LIGADA).
		-- Devagar de proposito: rapido demais embrulha o estomago de quem
		-- assiste, e o ponto da cena e' dar tempo de OLHAR a skin de quem pagou.
		CENA_GIRO = 0.12,
		--[[ A CENA e' o unico momento em que vale a pena chegar perto: e' o close
			de quem pagou. Mas nem tao perto -- a skin inteira, do chapeu ao
			sapato, precisa caber no quadro.

			ATENCAO: estes dois numeros valem pra um avatar de TAMANHO NORMAL. A
			camera multiplica os dois pela altura do boneco, senao um presente de
			escala 4 (o oculos) apareceria so' do peito pra cima -- e o colosso,
			so' a canela. Mexer aqui muda a cena de todo mundo junto. ]]
		CENA_DISTANCIA = 14,
		CENA_ALTURA = 6,
	},

	--[[ ───────────────────── O TELAO ─────────────────────

		Onde ele esta' no mundo. A camera usa isto pra garantir que ele CABE no
		quadro (ver `enquadrar` no Camera.client.luau).

		Estes numeros sao uma RESERVA: em tempo de execucao a camera mede a peca
		"Telao" de verdade dentro do Cenario e usa as medidas dela. E' a mesma
		ideia de sempre neste kit -- se um dia voce arrastar o telao no Studio,
		o enquadramento acompanha sozinho, em vez de continuar mirando no lugar
		onde ele estava.

		Se voce APAGAR o telao do mapa, estes valores entram e a camera
		continua enquadrando o fundo como se ele estivesse la'. E' de proposito:
		melhor um quadro um pouco alto demais do que uma camera que muda de
		comportamento sem ninguem entender por que.

		═══════════════════════════════════════════════════════════════════
		POR QUE O TOPO E' 32 E NAO 56 -- A PAREDE TEM TRES PECAS
		═══════════════════════════════════════════════════════════════════

		A parede do fundo continua com 52 studs de altura. O que mudou e' que
		ela virou TRES pecas empilhadas, e so' a do MEIO se chama `Telao`:

		  PainelInferior Y  4..18  pedra media, atras da galera a live inteira.
		  Telao          Y 18..32  o PAINEL ACESO. E' o que a camera promete
		                           caber -- e o que ilumina a nuca da formacao.
		  PainelSuperior Y 32..56  parede almofadada. Enfeite de plano aberto.

		A divisao existe porque a camera baixa (ver CAMERA.ALTURA) olha pra
		BAIXO, e o alto de uma parede de 56 studs simplesmente nao esta' no
		quadro dela -- em nenhuma distancia razoavel. Enquanto o `Telao` era a
		parede inteira, o solver obedecia: recuava ate' 40 studs pra caber um
		topo que ninguem precisava ler, e desfazia justamente o plano de perto
		que a lente veio buscar.

		A FAIXA DE BAIXO TAMBEM NAO SERVE, e por isso ela e' uma peca separada:
		com a lente na altura do peito, toda cabeca da galera fica acima da
		linha do horizonte e tapa o que estiver atras dela e mais baixo. Tudo
		abaixo de y=15 na parede esta', na pratica, atras de alguem.

		Sobra a janela do meio -- 14 studs de painel aceso, que a camera
		enquadra de perto e que iluminam a formacao por tras.

		═══════════════════════════════════════════════════════════════════
		ESTES NUMEROS SAO RESERVA, E JA' FICARAM PRA TRAS UMA VEZ
		═══════════════════════════════════════════════════════════════════

		Em tempo de execucao a camera MEDE a peca `Telao` de verdade e usa as
		medidas dela (ver `medirTelao`). Estes valores so' entram se o mapa nao
		carregar.

		Justamente por so' entrarem nesse caso, eles ficaram anos errados sem
		ninguem notar: diziam Y 4..21 enquanto o mapa ja' estava em Y 18..32.
		Um erro de 11 studs numa reserva que ninguem exercita e' invisivel ate'
		o dia em que ela e' a unica coisa que resta.

		Se voce mexer no telao, mexa AQUI JUNTO. O
		`ferramentas/gerar-cenario.py` recusa gravar um mapa que saia destes
		numeros, e o `roblox/testes/enquadramento.spec.luau` trava os mesmos. ]]
	TELAO = {
		Z = -74,
		TOPO = 32,
		BASE = 18,
		MEIA_LARGURA = 74,
	},

	--[[ ───────────────────── O ROTULO ─────────────────────

		O balao com o nome, em cima da cabeca de cada avatar. Duas linhas: o @ do
		TikTok em cima, o nick do Roblox embaixo -- e' o que deixa a pessoa se
		reconhecer na tela sem depender so' da skin.
	]]
	ROTULO = {
		--[[ Studs acima do CENTRO DA CABECA.

			Era 3.2, e o balao boiava longe do boneco. Nao era so' feio: cada
			stud de folga aqui e' um stud a mais que a camera precisa enquadrar
			pra o nick aparecer -- e, num close, isso empurra a lente pra tras
			ou joga o quadro pra cima do boneco. Foi o que fez o close sair
			"olhando pra cima" em vez de para o peito.

			2.2 poe o topo do balao a 8 studs do chao num boneco normal, que e'
			exatamente o dobro da altura da lente (4, a altura do peito). Essa
			simetria e' o que deixa o close RETO: com o que precisa caber
			distribuido igualmente acima e abaixo da lente, o eixo optico sai
			na horizontal sozinho, sem nenhum caso especial. ]]
		ALTURA = 2.2,
		--[[ Largura do balao, em studs.

			ELA PRECISA CABER NO ESPACO ENTRE VIZINHOS. Com a fileira da frente
			inteira nomeada, dez baloes ficam lado a lado a ESPACO_X (6 studs)
			um do outro -- e um balao de 9 studs invadia 3 studs do vizinho dos
			dois lados. Os nomes se encavalavam justamente na fileira que a live
			existe pra mostrar.

			5.5 deixa meio stud de ar entre um e outro. O texto nao fica menor
			por isso na pratica: o que limita o tamanho da fonte e' a ALTURA da
			linha, e ela nao mudou.

			Mexeu no ESPACO_X da formacao? Mexa aqui junto, ou os nomes voltam a
			se encostar. ]]
		LARGURA = 5.5,
		FUNDO = Color3.fromRGB(0, 0, 0),
		TRANSPARENCIA = 0.35,
		--[[ Nao existe COR_ARROBA aqui, e a falta e' de proposito: a linha do @
			usa sempre a COR DO PRESENTE. E' o sinal mais barato de "esta pessoa
			pagou", legivel de relance num celular assistindo a live -- uma cor
			fixa jogaria isso fora. Quem nao mandou presente cai no branco. ]]
		COR_NICK = Color3.fromRGB(255, 214, 64),

		--[[ ───────── QUANDO O ROTULO APARECE ─────────

			ESTES TRES NUMEROS EXISTEM POR UM MOTIVO SO': DE LONGE, NOME NENHUM
			SE LE'.

			O `DISTANCIA_MAX` era 80, e 80 e' MAIS que a formacao inteira. A
			camera de perto fica a uns 45 studs de quem ela esta' seguindo (ver
			CAMERA.DISTANCIA e CAMERA.ALTURA), entao 80 alcancava a pessoa
			seguida MAIS quatro fileiras atras dela: quarenta, cinquenta baloes
			pretos desenhados ao mesmo tempo, empilhados uns sobre os outros no
			video de um celular. Nao dava pra ler nenhum -- nem o de quem a
			camera estava seguindo, que e' o unico que importa -- e a multidao,
			que e' o argumento que faz a proxima pessoa comentar, sumia atras de
			uma parede de texto.

			Agora sao quatro regras, nesta ordem:

			  1. so' a FILEIRA DA FRENTE tem nome (ver SO_FILEIRA_DA_FRENTE);
			  2. passou do ALCANCE, o rotulo some;
			  3. dentro do alcance, ele APAGA aos poucos a partir do
			     DISTANCIA_SUAVE (some sem "piscar" na tela);
			  4. e nenhum nome pode cair EM CIMA de outro na tela, nem passar
			     de MAX_NA_TELA ao todo.

			Fora de todas elas fica QUEM A CAMERA ESTA' MOSTRANDO: esse acende
			sempre, marcado pelo proprio Camera.client.luau.

			Quem faz as contas e' o StarterPlayerScripts/Rotulos.client.luau,
			no cliente, quadro a quadro do lado de quem esta' vendo.

			PRA DESLIGAR TUDO ISTO e voltar ao comportamento antigo: ponha
			SO_FILEIRA_DA_FRENTE = false, SEM_SOBREPOR = false,
			DISTANCIA_MAX = 300 e MAX_NA_TELA = 400. ]]

		--[[ A que distancia o rotulo some de vez.

			ESTE NUMERO ANDA COLADO NA CAMERA.DISTANCIA, e por isso ele mudou
			junto com ela: era 68, calibrado pra uma lente que ficava a ~45
			studs de quem seguia. Com a lente a ~19 studs (ver CAMERA.DISTANCIA
			e CAMERA.ALTURA), 68 alcancaria seis fileiras -- sessenta baloes
			pretos empilhados no quadro de um celular, que e' exatamente a
			parede de texto que estes tres ajustes existem pra evitar.

			ESTE NUMERO E' PRA QUEM SO' COMENTOU, e foi ele que fez o nick de
			quem comenta nao aparecer enquanto o de quem mandou Rosa aparecia
			do lado. O alcance cresce com a raiz do tamanho (ver ESCALA_TETO),
			entao na MESMA distancia um boneco de escala 1 tinha 40 studs de
			alcance e o de escala 2 tinha 57: o pequeno apagava primeiro. Quem
			pagou ficava nomeado e quem comentou ficava anonimo ao lado dele --
			o oposto da promessa que a live faz no microfone.

			75 alcanca umas sete fileiras a partir da lente, que e' toda a parte
			da formacao que aparece grande o bastante pra um nome ser lido. Quem
			limita a poluicao nao e' este numero e sim o SO_FILEIRA_DA_FRENTE e o
			MAX_NA_TELA -- e os dois valem igual pra todo mundo, independente de
			tamanho.

			No PLANO ABERTO do fim do ciclo a camera vai pra ~130 studs, entao
			os rotulos da multidao somem sozinhos justamente no momento de
			mostrar QUANTA gente entrou. Um presente gigante ainda aparece
			nomeado la' -- e' UM balao, e e' o mais caro da live. ]]
		DISTANCIA_MAX = 75,

		--[[ Onde ele COMECA a apagar. Entre este numero e o DISTANCIA_MAX o
			rotulo vai ficando transparente.

			Sem esta faixa, o rotulo sumia de um quadro pro outro toda vez que a
			camera se mexia um pouco -- cem baloes piscando juntos, que na
			gravacao fica pior do que o excesso que este ajuste veio resolver. ]]
		DISTANCIA_SUAVE = 60,

		--[[ ───────── UM NOME NAO PODE CAIR EM CIMA DO OUTRO ─────────

			As regras acima decidem QUANTOS nomes aparecem. Esta decide se eles
			cabem no lugar onde caem.

			A conta que explica o embolamento: com a lente na altura do peito,
			todo balao esta' na mesma altura do MUNDO. Quanto mais longe, menor
			a elevacao -- entao o balao da fileira de tras DESCE na tela e vai
			pousar exatamente em cima da cabeca de quem esta' na frente. Nao e'
			azar de posicao, e' geometria: acontece toda vez.

			Ligado, o cliente mede o retangulo de cada balao na tela e da' o
			lugar a quem esta' MAIS PERTO da lente. Quem cairia por cima nao
			acende -- um nome a menos e' melhor que dois ilegiveis empilhados.

			`false` devolve o comportamento antigo (todos acendem, sobrepondo).
			Ver `retanguloDe` no Rotulos.client.luau. ]]
		SEM_SOBREPOR = true,

		--[[ Folga em PIXELS em volta de cada balao, na conta de sobreposicao.

			Zero deixaria dois nomes encostados um no outro -- tecnicamente sem
			sobrepor, e ilegiveis do mesmo jeito. 6 e' o respiro que faz o olho
			separar os dois. Numero maior = menos nomes na tela, mais espacados. ]]
		FOLGA_SOBREPOR = 6,

		--[[ Teto de rotulos na tela ao mesmo tempo, dos mais PERTOS pros mais
			longes.

			ELE PRECISA CABER A FILEIRA INTEIRA, senao ele corta justamente o que
			o SO_FILEIRA_DA_FRENTE veio garantir -- e corta calado, pelos mais
			distantes da fileira. 14 cobre os POR_FILA = 10 com folga pro colosso
			e pra quem a camera estiver seguindo de outra fileira.

			Aumentou o POR_FILA no painel? Aumente este junto. ]]
		MAX_NA_TELA = 14,

		--[[ ───────── SO' A FILEIRA DA FRENTE TEM NOME ─────────

			A fileira que esta' ENTRANDO aparece com todos os nicks; as de tras
			ficam sem nome, dancando na multidao. Quando uma fileira nova nasce,
			a anterior apaga.

			POR QUE NAO TODAS: com cem avatares, mostrar todos os nomes juntos e'
			uma parede de texto onde nenhum se le' -- e a multidao, que e' o
			argumento que faz a proxima pessoa comentar, some atras dos baloes.

			POR QUE NAO UM RODIZIO: foi o que existia antes. As fileiras se
			revezavam de 4 em 4 segundos pra todo mundo ter a vez, e na intencao
			era justo. Na tela era outra coisa: quem acabou de comentar -- que e'
			exatamente quem esta' olhando pra live naquele segundo -- tinha uma
			chance em dez de ver o proprio nome. A promessa da live e' "comente e
			apareca", e ela so' se cumpre no instante em que a pessoa comenta.

			`false` desliga e mostra o nome de todo mundo que estiver dentro do
			alcance -- que e' o comportamento antigo, e a parede de texto. ]]
		SO_FILEIRA_DA_FRENTE = true,

		--[[ Ate' que tamanho de boneco o alcance do rotulo cresce junto.

			ISTO NAO E' GOSTO: E' A MESMA LEI DO RECUO DA CAMERA.

			Quando chega um avatar grande, a camera se AFASTA dele -- e ela se
			afasta pela RAIZ do tamanho (ver `destinoSeguir` no
			Camera.client.luau, e o porque esta' explicado la'). Ou seja: quanto
			maior o boneco, mais longe da lente ele fica, mesmo sendo o alvo.

			Com alcance fixo pra todo mundo, o resultado era o pior possivel: o
			presente MAIS CARO da live -- o colosso, que empurra a camera pra
			mais de 130 studs -- era exatamente o unico que ficava SEM nome na
			tela. Quem pagou mais aparecia como um gigante anonimo.

			O alcance entao cresce pela raiz do tamanho, igualzinho ao recuo, e
			os dois se cancelam: cada avatar fica legivel na distancia em que a
			camera escolheu enquadra-lo, seja ele de escala 1 ou de escala 40.

			O TETO de 9 (raiz de 9 = 3 vezes o alcance) e' o que impede o
			colosso, que pode chegar a escala 40, de virar um outdoor visivel de
			qualquer canto do mapa. Na pratica:
			  escala  1  ->   75 studs   (quem so' comentou)
			  escala  4  ->  150 studs   (o oculos)
			  escala  6  ->  184 studs   (a galaxia)
			  escala 40  ->  225 studs   (colosso, no teto) ]]
		ESCALA_TETO = 9,
	},

	--[[ ───────────────────── O BRILHO ─────────────────────

		A aura de quem mandou presente. A cor vem do efeito (a mesma do nome),
		entao cada presente brilha de um jeito proprio sem precisar de outro
		campo. O numero e' so' a FORCA, de 1 a 5.

		Quem so' comentou nunca brilha, e isso e' regra e nao acaso: se todo
		mundo brilha, o brilho deixa de significar alguma coisa.

		E' UMA COISA SO': o CONTORNO no formato do corpo. Nada de luz no chao,
		nada de faisca, nada de halo -- essas camadas existiram e sairam. Luz de
		verdade nao respeita o corpo de ninguem: ela vaza pro chao, pinta os
		vizinhos e lava a cor da roupa da pessoa, que e' o que ela veio ver na
		tela. Com cem bonecos, cem luzes coloridas transformam a formacao numa
		mancha.

		O contorno acompanha a silhueta -- braco, cabelo, chapeu, acessorio --
		e para exatamente onde o boneco para. Ele cresce em FORCA, e nao em
		tamanho: quanto mais caro o presente, mais fechada a linha.
	]]
	BRILHO = {
		--[[ De que forca em diante o boneco ganha aura. 1 = todo presente tem.

			A escadinha de camadas antiga comecava no 2, e ai' a rosa (forca 1)
			nao ganhava nada. Com uma camada so', comecar no 2 deixaria o
			presente mais comum da live sem sinal nenhum de que foi pago. ]]
		CONTORNO_DESDE = 1,

		--[[ Quanto a LINHA fecha. Transparencia = BASE - POR_FORCA x forca,
			entao numero MENOR = linha mais forte. Forca 5 fecha em 0 (cheia). ]]
		LINHA_BASE = 0.45,
		LINHA_POR_FORCA = 0.09,

		--[[ Quanto de cor entra POR DENTRO do corpo. Quase nada, de proposito:
			preenchimento forte apaga a roupa da pessoa. Mesma conta da linha --
			menor = mais cor. ]]
		PREENCHIMENTO_BASE = 0.97,
		PREENCHIMENTO_POR_FORCA = 0.015,

		--[[ Teto de auras ao mesmo tempo. NAO E' AJUSTE DE GOSTO: o motor da
			Roblox desenha no maximo 31 Highlight por vez, e do 32 em diante ele
			simplesmente NAO desenha -- sem erro, sem aviso.

			Estourar o teto nao apaga a aura de quem chegou: o codigo tira a do
			presente MAIS FRACO que estiver na tela pra dar lugar ao mais forte.
			Assim a galaxia nunca fica sem aura porque vinte rosas chegaram
			antes -- que e' exatamente o que aconteceria com um teto simples. ]]
		MAX_CONTORNOS = 24,
	},
}
