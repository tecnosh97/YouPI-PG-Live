import datetime
import sys
import os

# Data de expiração (exemplo: 31/10/2026)
DATA_EXPIRACAO = datetime.date(2026, 10, 31)
HOJE = datetime.date.today()

if HOJE > DATA_EXPIRACAO:
    print("\n" + "="*50)
    print("AVISO: O período de avaliação deste software terminou.")
    print(f"Data de expiração: {DATA_EXPIRACAO.strftime('%d/%m/%Y')}")
    print(f"Data atual: {HOJE.strftime('%d/%m/%Y')}")
    print("\nPara continuar usando, adquira uma licença válida em:")
    print("https://seusite.com/licenca")
    print("="*50 + "\n")
    
    # Opção 1: Apenas impedir a execução do live (recomendado)
    sys.exit(1)  # Sai com erro, não executa o live
    
    # Opção 2: Permitir modo de teste limitado (mais amigável)
    # Descomente as linhas abaixo se quiser permitir uso em modo teste
    # print("Iniciando em MODO TESTE (funcionalidades limitadas)...")
    # os.system("start "" 4-MODO-TESTE.bat")  # Ou outro batch de teste
    # sys.exit(0)
else:
    # Data válida - permite a execução normal
    print(f"Licença válida até {DATA_EXPIRACAO.strftime('%d/%m/%Y')}")
    # Aqui você chamaria seu batch original de inicialização
    os.system("start "" 2-COMECAR-LIVE-TIKTOK.bat")
