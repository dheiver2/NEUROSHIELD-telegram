#!/usr/bin/env python3
"""
Script para diagnosticar problemas de câmera
"""
import os
import cv2
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv("config/.env")

print("=" * 70)
print("📹 DIAGNÓSTICO DE CÂMERAS")
print("=" * 70)

# ═══════════════════════════════════════════════════════════
# 1. Carrega configuração de empresas
# ═══════════════════════════════════════════════════════════
CONFIG_EMPRESAS_PATH = "config/empresas.json"
print("\n1️⃣ CARREGANDO CONFIGURAÇÃO")
print("-" * 70)

try:
    with open(CONFIG_EMPRESAS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    empresas = data.get('empresas', [])
    print(f"✅ Configuração carregada: {len(empresas)} empresa(s)")
except Exception as e:
    print(f"❌ Erro ao carregar: {e}")
    exit(1)

# ═══════════════════════════════════════════════════════════
# 2. Testa cada câmera
# ═══════════════════════════════════════════════════════════
print("\n2️⃣ TESTANDO CÂMERAS")
print("-" * 70)

total_cameras = 0
working_cameras = 0
error_camera_list = []

for empresa in empresas:
    print(f"\n🏢 {empresa['nome']}")
    cameras = empresa.get('cameras', [])
    
    for camera in cameras:
        if not camera.get('ativa', True):
            continue
        
        total_cameras += 1
        camera_id = camera['id']
        camera_name = camera['nome']
        rtsp_url = camera['rtsp_url']
        
        print(f"\n   📹 {camera_name}")
        print(f"      URL: {rtsp_url[:50]}...")
        
        try:
            print(f"      🔌 Conectando...", end=" ", flush=True)
            
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Tenta ler um frame (timeout após 5 segundos)
            ret = False
            frame = None
            attempts = 0
            max_attempts = 50  # ~5 segundos com 100ms delay
            
            while attempts < max_attempts and not ret:
                ret, frame = cap.read()
                if ret:
                    break
                attempts += 1
                cv2.waitKey(100)  # 100ms por tentativa
            
            if not cap.isOpened():
                print(f"❌ FALHA NA ABERTURA")
                print(f"      Status: Câmera não respondeu")
                error_camera_list.append((camera_name, "Não respondeu à conexão"))
                cap.release()
                continue
            
            if not ret or frame is None:
                print(f"❌ SEM FRAMES")
                print(f"      Status: Conectada mas não retorna frames")
                error_camera_list.append((camera_name, "Conectada mas sem frames"))
                cap.release()
                continue
            
            # Camera está funcionando
            h, w, c = frame.shape
            print(f"✅ OK")
            print(f"      Resolução: {w}x{h}")
            print(f"      Status: Conectada e capturando")
            working_cameras += 1
            
            cap.release()
        
        except Exception as e:
            print(f"❌ ERRO: {str(e)[:50]}")
            error_camera_list.append((camera_name, str(e)))

# ═══════════════════════════════════════════════════════════
# 3. Resumo
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("📊 RESUMO")
print("=" * 70)
print(f"Total de câmeras testadas: {total_cameras}")
print(f"✅ Câmeras funcionando: {working_cameras}")
print(f"❌ Câmeras com erro: {len(error_camera_list)}")

if error_camera_list:
    print("\nCâmeras com erro:")
    for cam_name, error in error_camera_list:
        print(f"  • {cam_name}")
        print(f"    Erro: {error}")

print("\n" + "=" * 70)

if working_cameras == 0:
    print("❌ NENHUMA CÂMERA FUNCIONANDO!")
    print("\nPossíveis causas:")
    print("  1. URLs RTSP incorretas")
    print("  2. Câmeras offline ou inacessíveis")
    print("  3. Credenciais inválidas")
    print("  4. Problema de rede/firewall")
    print("  5. Câmeras precisam ser inicializadas")
elif working_cameras < total_cameras:
    print(f"⚠️ APENAS {working_cameras}/{total_cameras} CÂMERAS FUNCIONANDO")
    print("   Verifique os erros acima para as câmeras que falharam")
else:
    print(f"✅ TODAS AS {working_cameras} CÂMERAS ESTÃO FUNCIONANDO!")
    print("   O problema está em outro lugar:")
    print("   - Verifique se não há detecções ocorrendo")
    print("   - Verifique o score de detecção (MIN_SEND_SCORE)")
    print("   - Check logs do simple_bot.py")

print("=" * 70)
