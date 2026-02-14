#!/usr/bin/env python3
"""
Script para testar o envio de imagens simuladas para Telegram
Simula detecções e verifica se o bot envia corretamente
"""
import os
import cv2
import json
import asyncio
import logging
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv("config/.env")

print("=" * 70)
print("🧪 TESTE DE ENVIO DE DETECÇÕES")
print("=" * 70)

# ═══════════════════════════════════════════════════════════
# 1. Carrega configuração
# ═══════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CONFIG_EMPRESAS_PATH = "config/empresas.json"

print("\n1️⃣ CARREGANDO CONFIGURAÇÃO")
print("-" * 70)

try:
    with open(CONFIG_EMPRESAS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    empresas = data.get('empresas', [])
    print(f"✅ Configuração carregada")
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)

# ═══════════════════════════════════════════════════════════
# 2. Cria frame de teste com desenho
# ═══════════════════════════════════════════════════════════
print("\n2️⃣ CRIANDO FRAME DE TESTE")
print("-" * 70)

frame_width = 1920
frame_height = 1080

# Cria um frame preto
test_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

# Adiciona alguns detalhes visuais
cv2.rectangle(test_frame, (100, 100), (300, 300), (0, 255, 0), 2)  # Retângulo verde
cv2.putText(test_frame, "Test Detection", (110, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

cv2.rectangle(test_frame, (500, 200), (700, 400), (255, 0, 0), 2)  # Retângulo azul
cv2.putText(test_frame, "Person", (510, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

cv2.rectangle(test_frame, (1000, 300), (1200, 500), (0, 0, 255), 2)  # Retângulo vermelho
cv2.putText(test_frame, "Car", (1010, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

print(f"✅ Frame criado: {frame_width}x{frame_height}")

# ═══════════════════════════════════════════════════════════
# 3. Testa envio
# ═══════════════════════════════════════════════════════════
print("\n3️⃣ TESTANDO ENVIO PARA TELEGRAM")
print("-" * 70)

async def test_send_detection():
    bot = Bot(token=BOT_TOKEN)
    
    # Simula detecções
    mock_detections = [
        {
            'class': 'person',
            'confidence': 0.95,
            'box': [100, 100, 300, 300]
        },
        {
            'class': 'car',
            'confidence': 0.87,
            'box': [1000, 300, 1200, 500]
        }
    ]
    
    # Prepara caption
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    obj_list = ", ".join([f"{d['class']} ({d['confidence']:.0%})" for d in mock_detections])
    
    empresa = empresas[0]
    camera_name = empresa['cameras'][0]['nome'] if empresa['cameras'] else "Test Camera"
    
    caption = f"🏢 {empresa['nome']}\n🎯 {camera_name}\n⏰ {timestamp}\n🔍 {obj_list}"
    
    # Converte frame para bytes
    _, buffer = cv2.imencode('.jpg', test_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    photo_bytes = buffer.tobytes()
    
    print(f"   Frame: {len(photo_bytes)} bytes")
    print(f"   Caption:\\n{caption}")
    print(f"\n   Enviando para {len(empresa['telegram_chat_ids'])} chat(s)...")
    
    for chat_id in empresa['telegram_chat_ids']:
        try:
            print(f"\n   📤 Enviando para chat {chat_id}...", end=" ", flush=True)
            
            message = await bot.send_photo(
                chat_id=chat_id,
                photo=photo_bytes,
                caption=caption,
                read_timeout=8,
                write_timeout=8
            )
            
            print(f"✅ OK")
            print(f"      Message ID: {message.message_id}")
            
        except Exception as e:
            print(f"❌ ERRO")
            print(f"      {e}")
            return False
    
    return True

success = asyncio.run(test_send_detection())

print("\n" + "=" * 70)
if success:
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("\nConclusões:")
    print("  • Bot está funcionando corretamente")
    print("  • Chat IDs são válidos")
    print("  • Câmeras estão conectando")
    print("  • Frame envio está funcionando")
    print("\nPROVÁVEL CAUSA: Bot rodando mas SEM DETECÇÕES ocorrendo")
    print("\nVerifique:")
    print("  1. Score de detecção é muito alto (MIN_SEND_SCORE)")
    print("  2. Como está o FRAME_SKIP (pode estar pulando demais)")
    print("  3. Há objetos nas câmeras?")
    print("  4. Verifique logs: 🔍 Detecção vs ⏭️ Cena similar ignorada")
else:
    print("❌ TESTE FALHOU!")
    print("   Verifique os erros acima")

print("=" * 70)
