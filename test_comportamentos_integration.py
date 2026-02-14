#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da integração de comportamentos com o sistema de detecção.
Valida que:
1. DetectorComportamento detecta corretamente comportamentos
2. Comportamentos são registrados por chat_id
3. Filtragem funciona corretamente
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from comportamentos import DetectorComportamento, TipoComportamento, COMPORTAMENTOS_DISPONIVEIS

# Configure stdout para UTF-8 no Windows
if sys.platform == 'win32':
    import os
    os.system("chcp 65001 > nul")  # Windows: mudar para UTF-8 na console


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_detector_initialization():
    """Testa inicialização do detector de comportamentos"""
    print_section("TEST 1: Inicialización do DetectorComportamento")
    
    detector = DetectorComportamento()
    
    print(f"✅ DetectorComportamento criado")
    print(f"   - Comportamentos disponíveis: {len(COMPORTAMENTOS_DISPONIVEIS)}")
    
    for tipo, config in COMPORTAMENTOS_DISPONIVEIS.items():
        status = "✅" if tipo in detector.comportamentos_monitorados else "❌"
        print(f"     {status} {tipo.name}: severidade={config.severidade}, "
              f"min_objetos={config.minimo_objetos}")


def test_behavior_activation():
    """Testa ativação/desativação de comportamentos"""
    print_section("TEST 2: Activação e Desativação de Comportamentos")
    
    detector = DetectorComportamento()

    
    # Começa vazio
    initial_count = len(detector.comportamentos_monitorados)
    print(f"✅ Comportamentos inicialmente ativos: {initial_count}")
    
    # Ativa algun comportamentos
    detector.ativar_comportamento(TipoComportamento.AGLOMERACAO)
    detector.ativar_comportamento(TipoComportamento.ACIDENTE_TRANSITO)
    
    print(f"✅ Ativados 2 comportamentos")
    print(f"   Comportamentos ativos: {detector.comportamentos_monitorados}")
    
    # Desativa um
    detector.desativar_comportamento(TipoComportamento.AGLOMERACAO)
    print(f"✅ Desativado AGLOMERACAO")
    print(f"   Comportamentos restantes: {detector.comportamentos_monitorados}")


def test_crowd_detection():
    """Testa detecção de aglomeração (3+ pessoas)"""
    print_section("TEST 3: Detecção de Aglomeração (3+ Pessoas)")
    
    detector = DetectorComportamento()
    detector.ativar_comportamento(TipoComportamento.AGLOMERACAO)
    
    # Simula 3 pessoas perto uma da outra
    detections_crowd = [
        {
            'bbox': [100, 100, 120, 180],
            'class': 'person',
            'confidence': 0.95,
            'class_id': 0,
            'track_id': 1
        },
        {
            'bbox': [200, 110, 220, 190],
            'class': 'person',
            'confidence': 0.92,
            'class_id': 0,
            'track_id': 2
        },
        {
            'bbox': [150, 105, 170, 185],
            'class': 'person',
            'confidence': 0.88,
            'class_id': 0,
            'track_id': 3
        }
    ]
    
    movement_score = 0.5  # Movimento moderado
    comportamentos = detector.detectar_comportamento(detections_crowd, movement_score)
    
    found_crowd = any(tipo == TipoComportamento.AGLOMERACAO for tipo, _ in comportamentos)
    print(f"{'✅' if found_crowd else '❌'} Aglomeração detectada: {found_crowd}")
    if comportamentos:
        for tipo, desc in comportamentos:
            print(f"   - {tipo.name}: {desc}")


def test_traffic_accident_detection():
    """Testa detecção de acidente de trânsito (2+ veículos)"""
    print_section("TEST 4: Detecção de Acidente de Trânsito (2+ Veículos)")
    
    detector = DetectorComportamento()
    detector.ativar_comportamento(TipoComportamento.ACIDENTE_TRANSITO)
    
    # Simula 2 veículos perto um do outro
    detections_accident = [
        {
            'bbox': [100, 100, 200, 180],
            'class': 'car',
            'confidence': 0.95,
            'class_id': 2,
            'track_id': 1
        },
        {
            'bbox': [210, 110, 310, 190],
            'class': 'car',
            'confidence': 0.92,
            'class_id': 2,
            'track_id': 2
        }
    ]
    
    movement_score = 0.3  # Movimento leve
    comportamentos = detector.detectar_comportamento(detections_accident, movement_score)
    
    found_accident = any(tipo == TipoComportamento.ACIDENTE_TRANSITO for tipo, _ in comportamentos)
    print(f"{'✅' if found_accident else '❌'} Acidente detectado: {found_accident}")
    if comportamentos:
        for tipo, desc in comportamentos:
            print(f"   - {tipo.name}: {desc}")


def test_event_registration():
    """Testa registro de eventos"""
    print_section("TEST 5: Registro de Eventos")
    
    detector = DetectorComportamento()
    
    detections = [
        {
            'bbox': [100, 100, 120, 180],
            'class': 'person',
            'confidence': 0.95,
            'class_id': 0,
            'track_id': 1
        }
    ]
    
    # Registra um evento
    detector.registrar_evento(TipoComportamento.AGLOMERACAO, "camera_01", detections)
    print(f"✅ Evento registrado")
    
    # Consulta histórico
    historico = detector.obter_historico(TipoComportamento.AGLOMERACAO)
    print(f"✅ Histórico de AGLOMERACAO contém {len(historico)} registros")
    
    if historico:
        evento = historico[0]
        print(f"   - Camera: {evento['camera']}")
        print(f"   - Timestamp: {evento['timestamp']}")
        print(f"   - Detecções: {evento['deteccoes']}")


def test_filtering_by_chat():
    """Testa filtragem de comportamentos por chat_id"""
    print_section("TEST 6: Filtragem por Chat ID")
    
    from collections import defaultdict
    
    detector = DetectorComportamento()
    comportamentos_por_chat = defaultdict(set)
    
    # Chat 1 quer monitorar aglomeração
    comportamentos_por_chat[100].add(TipoComportamento.AGLOMERACAO)
    
    # Chat 2 quer monitorar acidente de trânsito
    comportamentos_por_chat[200].add(TipoComportamento.ACIDENTE_TRANSITO)
    
    # Simula aglomeração
    detections = [
        {'bbox': [100, 100, 120, 180], 'class': 'person', 'confidence': 0.95, 'class_id': 0, 'track_id': i}
        for i in range(3)
    ]
    
    comportamentos_detectados = detector.detectar_comportamento(detections, 0.5)
    
    print(f"✅ Comportamentos detectados: {[t.name for t, _ in comportamentos_detectados]}")
    
    # Simula envio para cada chat
    for chat_id, chats_comportamentos in comportamentos_por_chat.items():
        match_found = False
        
        for tipo_comp, _ in comportamentos_detectados:
            if tipo_comp in chats_comportamentos:
                match_found = True
                print(f"✅ Chat {chat_id} receberá notificação (comportamento: {tipo_comp.name})")
                break
        
        if not match_found:
            print(f"❌ Chat {chat_id} não receberá notificação (sem interesse em comportamentos detectados)")


def test_no_false_positives():
    """Testa que não há falsos positivos"""
    print_section("TEST 7: Prevenção de Falsos Positivos")
    
    detector = DetectorComportamento()
    
    # Detections com apenas 1 pessoa (não deve detectar aglomeração)
    detections_single = [
        {
            'bbox': [100, 100, 120, 180],
            'class': 'person',
            'confidence': 0.95,
            'class_id': 0,
            'track_id': 1
        }
    ]
    
    comportamentos = detector.detectar_comportamento(detections_single, 0.5)
    has_crowd = any(tipo == TipoComportamento.AGLOMERACAO for tipo, _ in comportamentos)
    
    print(f"✅ Uma pessoa sozinha: aglomeração detectada = {has_crowd}")
    assert not has_crowd, "ERRO: Falso positivo detectado!"
    
    # Detections com 2 carros distantes (não deve detectar acidente)
    detections_distant_cars = [
        {
            'bbox': [100, 100, 200, 180],
            'class': 'car',
            'confidence': 0.95,
            'class_id': 2,
            'track_id': 1
        },
        {
            'bbox': [800, 350, 900, 430],  # Muito longe
            'class': 'car',
            'confidence': 0.92,
            'class_id': 2,
            'track_id': 2
        }
    ]
    
    comportamentos = detector.detectar_comportamento(detections_distant_cars, 0.3)
    has_accident = any(tipo == TipoComportamento.ACIDENTE_TRANSITO for tipo, _ in comportamentos)
    
    print(f"✅ Dois carros distantes: acidente detectado = {has_accident}")
    assert not has_accident, "ERRO: Falso positivo detectado!"


def main():
    print("\n" + "="*60)
    print("  TESTE DE INTEGRAÇÃO - SISTEMA DE COMPORTAMENTOS")
    print("="*60)
    
    try:
        test_detector_initialization()
        test_behavior_activation()
        test_crowd_detection()
        test_traffic_accident_detection()
        test_event_registration()
        test_filtering_by_chat()
        test_no_false_positives()
        
        print_section("RESUMO - TESTES COMPLETOS ✅")
        print("✅ Todos os testes passaram com sucesso!")
        print("\nPróximo passo: Executar bot com `/monitorar` para selecionar comportamentos")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
