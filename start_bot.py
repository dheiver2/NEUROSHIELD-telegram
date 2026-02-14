#!/usr/bin/env python3
"""
Script para iniciar o bot Telegram com logging detalhado
Mostra o que está acontecendo em tempo real
"""
import os
import sys
import asyncio
import logging
from simple_bot import main

# Configuração detalhada de logging para no console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🤖 INICIANDO BOT TELEGRAM - DETECÇÃO DE OBJETOS")
    print("=" * 70)
    print("\n📋 Verificação pré-inicialização:")
    print("-" * 70)
    
    # Verifica telegram token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        print(f"✅ Telegram Bot Token: Configurado")
    else:
        print(f"❌ Telegram Bot Token: NÃO ENCONTRADO")
        sys.exit(1)
    
    # Verifica arquivo de empresas
    if os.path.exists("config/empresas.json"):
        print(f"✅ Arquivo empresas.json: Encontrado")
    else:
        print(f"❌ Arquivo empresas.json: NÃO ENCONTRADO")
        sys.exit(1)
    
    # Verifica modelo YOLO
    if os.path.exists("models/yolo26n.pt"):
        print(f"✅ Modelo YOLO: Encontrado")
    else:
        print(f"❌ Modelo YOLO: NÃO ENCONTRADO")
        sys.exit(1)
    
    print("-" * 70)
    print("\n🚀 Iniciando aplicação...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Bot interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
