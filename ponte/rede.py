"""O contexto TLS das consultas ao Roblox.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
No Windows, o Python NAO usa a mesma lista de certificados que o navegador.
Ele monta a dele a partir do que ja' esta' guardado na loja do sistema -- e o
Windows so' baixa um certificado raiz na PRIMEIRA vez que alguem precisa dele.
Num PC que nunca precisou, a lista chega a ter 24 certificados onde o pacote
completo tem mais de 120.

O resultado nao e' um erro de rede legivel. E' este:

    [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate

...e quem escreveu o codigo la' em cima capturou "erro de rede" e devolveu
"nick nao encontrado". A frase que chegava no painel era `O nick "fulano" nao
existe no Roblox` -- para TODO nick, inclusive o do proprio dono da live, numa
maquina em que a unica coisa errada era a lista de certificados. Da' pra passar
um dia conferindo a digitacao de um nick que sempre esteve certo.

A ESCADA, E POR QUE NESTA ORDEM
-------------------------------
  1. truststore  manda a verificacao pro proprio Windows, que sabe buscar o
                 certificado que falta na hora. E' o mais parecido com o que o
                 navegador faz. So' entra se estiver instalado.
  2. certifi     a lista completa da Mozilla, em arquivo. Vem junto com a
                 TikTokLive, entao na pratica esta' sempre ai'.
  3. o padrao    se nenhum dos dois existir. Pode falhar -- mas falhar aqui e'
                 melhor que subir sem TLS.

O QUE ESTE ARQUIVO NAO FAZ: desligar a verificacao. Um `CERT_NONE` faria o
sintoma sumir e trocaria um nick que nao resolve por uma conexao que qualquer
um no meio do caminho consegue ler. O problema e' a LISTA estar curta, e a
correcao e' completar a lista.
"""

import ssl

_contexto = None
_origem = "nao montado"


def contexto_ssl():
    """O contexto pras chamadas HTTPS. Montado uma vez e reaproveitado."""
    global _contexto, _origem
    if _contexto is not None:
        return _contexto

    # 1) A verificacao nativa do sistema.
    try:
        import truststore
        _contexto = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        _origem = "truststore (verificacao nativa do Windows)"
        return _contexto
    except Exception:
        pass

    # 2) A lista completa, em arquivo.
    try:
        import certifi
        _contexto = ssl.create_default_context(cafile=certifi.where())
        _origem = f"certifi ({certifi.where()})"
        return _contexto
    except Exception:
        pass

    # 3) O padrao do Python.
    _contexto = ssl.create_default_context()
    _origem = "padrao do Python (lista do Windows, pode estar incompleta)"
    return _contexto


def origem_dos_certificados():
    """De onde saiu a lista. So' pra diagnostico -- e' a linha que responde
    'por que aqui funciona e na maquina do cliente nao'."""
    contexto_ssl()
    return _origem


def quantos_certificados():
    """Quantos certificados raiz o contexto enxerga.

    Abaixo de ~50 e' quase certeza de lista curta do Windows, e e' o numero que
    explica o erro sem ninguem precisar entender de TLS.
    """
    try:
        return len(contexto_ssl().get_ca_certs())
    except Exception:
        return -1
