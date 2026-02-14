#!/usr/bin/env python3
"""
Script para testar detecção YOLO em um frame real de câmera
Ajuda a diagnosticar se o problema é falta de detecção
"""
import cv2
import json
import logging
from ultralytics import YOLO
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("🔍 TESTE DE DETECÇÃO YOLO")
print("=" * 70)

# Carrega configurações
load_dotenv("config/.env")

MODEL_PATH = os.getenv("DETECTION_MODEL", "models/yolo26n.pt")
CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))

print(f"\n1️⃣ CARREGANDO MODELO")
print("-" * 70)
print(f"Modelo: {MODEL_PATH}")
print(f"Confiança: {CONFIDENCE:.0%}")

try:
    model = YOLO(MODEL_PATH)
    print(f"✅ Modelo carregado: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Erro ao carregar modelo: {e}")
    exit(1)

# Carrega configuração de câmeras
print(f"\n2️⃣ CARREGANDO CÂMERAS")
print("-" * 70)

try:
    with open("config/empresas.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cameras = []
    for empresa in data.get('empresas', []):
        for camera in empresa.get('cameras', []):
            if camera.get('ativa', True):
                cameras.append(camera)
    
    print(f"✅ {len(cameras)} câmeras ativas encontradas")
except Exception as e:
    print(f"❌ Erro ao carregar câmeras: {e}")
    exit(1)

# Testa detecção em câmeras
print(f"\n3️⃣ TESTANDO DETECÇÃO EM 3 CÂMERAS")
print("-" * 70)

test_count = 0
for camera in cameras[:3]:
    test_count += 1
    cam_name = camera['nome']
    rtsp_url = camera['rtsp_url']
    
    print(f"\n   Câmera #{test_count}: {cam_name}")
    print(f"   URL: {rtsp_url[:50]}...")
    
    try:
        print(f"   🔌 Conectando...", end=" ", flush=True)
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Lê um frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"❌ Sem frame")
            cap.release()
            continue
        
        print(f"✅ Frame capturado")
        h, w = frame.shape[:2]
        print(f"   Resolução: {w}x{h}")
        
        # Executa detecção
        print(f"   🔍 Detectando objetos...", end=" ", flush=True)
        results = model(frame, conf=CONFIDENCE, verbose=False)
        
        if results and len(results) > 0:
            boxes = results[0].boxes
            if len(boxes) > 0:
                print(f"✅ OK")
                print(f"   Detectados: {len(boxes)} objeto(s)")
                
                for i, box in enumerate(boxes[:5]):  # Mostra até 5
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = model.names[cls]
                    print(f"      {i+1}. {name} ({conf:.0%})")
                
                if len(boxes) > 5:
                    print(f"      ... e mais {len(boxes) - 5}")
            else:
                print(f"❌ Sem detecções")
        else:
            print(f"❌ Sem resultados")
        
        cap.release()
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)[:50]}")

print("\n" + "=" * 70)
print("✅ TESTE CONCLUÍDO")
print("=" * 70)

print("""
INTERPRETAÇÃO DO RESULTADO:

✅ Se viu detecções:
   - YOLO está funcionando!
   - Verifique se as câmeras têm objetos sempre
   - Abra o bot para começar a enviar detecções

❌ Se NÃO viu detecções:
   - Câmeras podem estar vazias (sem movimento/objetos)
   - Tente reduzir CONFIDENCE_THRESHOLD em config/.env
   - Experimental com valor: 0.10 ou 0.15

⚠️ Se houve erro de conexão:
   - Câmera pode estar offline ou inacessível
   - Verifique URL RTSP
   - Verifique credenciais
   - Teste manualmente com ffmpeg
""")
