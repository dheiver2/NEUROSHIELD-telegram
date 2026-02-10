#!/usr/bin/env python3
"""
RTSP to Telegram Bot - Versão Simplificada
Execute: python run.py
"""
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa e executa o bot simplificado
from simple_bot import main
import asyncio

if __name__ == "__main__":
    try:
        print("🚀 Iniciando bot simplificado...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Sistema interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        sys.exit(1)
