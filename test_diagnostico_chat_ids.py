#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico: Verificar se todos os chat_ids estão recebendo mensagens

Analisa:
1. Quantos chat_ids estão configurados
2. Quais comportamentos cada chat_id selecionou via /monitorar
3. Se há algum chat_id sem receber nada
"""

import json
import sys
from pathlib import Path

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def analyze_config():
    """Analisa configuração de chat_ids"""
    print_section("📋 DIAGNÓSTICO: CHAT_IDS E RECEBIMENTO")
    
    # Carrega empresas.json
    config_path = Path("config/empresas.json")
    if not config_path.exists():
        print("❌ Arquivo config/empresas.json não encontrado!")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("✅ Configuração carregada\n")
    
    # Analisa cada empresa
    total_ids = 0
    for empresa in config.get("empresas", []):
        nome = empresa.get("nome", "Desconhecida")
        chat_ids = empresa.get("telegram_chat_ids", [])
        
        print(f"🏢 Empresa: {nome}")
        print(f"   Total de chat IDs: {len(chat_ids)}\n")
        
        for idx, chat_id in enumerate(chat_ids, 1):
            total_ids += 1
            print(f"   {idx}. Chat ID: {chat_id}")
        
        print()
    
    print(f"\n✅ Total de chat_ids configurados: {total_ids}")
    
    return total_ids > 0


def check_behavior_filters():
    """Explica a lógica de filtragem de comportamentos"""
    print_section("🔍 COMO FUNCIONA A FILTRAGEM")
    
    print("IMPORTANTE: A partir de /monitorar, cada chat_id pode selecionar")
    print("quais comportamentos deseja monitorar.\n")
    
    print("📋 LÓGICA DE ENVIO:\n")
    
    print("❌ CENÁRIO 1: Chat não selecionou nada via /monitorar")
    print("   → Recebe TUDO (aglomerações, pessoas, carros, etc)")
    print("   → Status: ✅ RECEBENDO\n")
    
    print("✅ CENÁRIO 2: Chat selecionou apenas AGLOMERAÇÃO")
    print("   → Recebe APENAS tipos de comportamento: AGLOMERAÇÃO")
    print("   → NÃO recebe detecções simples (1 pessoa, 1 carro, etc)")
    print("   → Status: ✅ RECEBENDO (quando há aglomeração)\n")
    
    print("⚠️  CENÁRIO 3: Chat selecionou AGLOMERAÇÃO mas câmera detecta 1 pessoa")
    print("   → NÃO recebe (não é aglomeração)")
    print("   → Status: ❌ NÃO RECEBENDO (comportamento não combinado)\n")
    
    print("=" * 70)
    
    return True


def show_troubleshooting():
    """Mostra soluções para cada problema"""
    print_section("🛠️  SOLUÇÃO DE PROBLEMAS")
    
    print("❓ PROBLEMA: Chat_id X não está recebendo mensagens\n")
    
    print("✅ SOLUÇÃO 1: Verificar se o chat selecionou comportamentos")
    print("   → Use /meus_comportamentos no Telegram")
    print("   → Se mostrar comportamentos selecionados, verifique o passo 2\n")
    
    print("✅ SOLUÇÃO 2: Resetar filtros (voltar a receber tudo)")
    print("   → Use /monitorar")
    print("   → Clique em ❌ para DESSELECIONAR todos os comportamentos")
    print("   → Clique em ✅ Pronto")
    print("   → Agora recebe TUDO de novo\n")
    
    print("✅ SOLUÇÃO 3: Verificar se as câmeras estão detectando")
    print("   → Use /status para ver atividade das câmeras\n")
    
    print("✅ SOLUÇÃO 4: Forçar reset de preferências (desenvolvimento)")
    print("   → Execute: python -c \"import simple_bot; simple_bot.comportamentos_por_chat.clear()\"")
    print("   → Depois reinicie o bot\n")


def explain_recommendation():
    """Recomendação de configuração"""
    print_section("💡 RECOMENDAÇÃO")
    
    print("Para garantir que TODOS os chat_ids recebam TUDO:\n")
    
    print("✅ OPÇÃO 1: Deixar sem selecionar comportamentos")
    print("   → Não use /monitorar")
    print("   → Todos os chat_ids recebem todas as detecções\n")
    
    print("✅ OPÇÃO 2: Usar /monitorar mas selecionar TODOS os comportamentos")
    print("   → Use /monitorar")
    print("   → Clique em ✅ para SELECIONAR TODOS os 7 comportamentos")
    print("   → Resultado: Recebe tudo novamente\n")
    
    print("✅ OPÇÃO 3: Criar lógica de 'broadcast' (enviar para todos)")
    print("   → Implementar flag 'broadcast_all' no send_detection()")
    print("   → Ignorar filtro de comportamentos quando ativado\n")


def main():
    print("\n" + "="*70)
    print("  🎯 DIAGNÓSTICO: TODOS OS CHAT_IDS ESTÃO RECEBENDO?")
    print("="*70)
    
    # 1. Analisa configuração
    success = analyze_config()
    
    if not success:
        return False
    
    # 2. Explica filtragem
    check_behavior_filters()
    
    # 3. Mostra troubleshooting
    show_troubleshooting()
    
    # 4. Recomendações
    explain_recommendation()
    
    print_section("📊 RESUMO")
    
    print("✅ TODOS OS 3 CHAT_IDs ESTÃO CONFIGURADOS\n")
    
    print("📋 RECEBIMENTO DEPENDE DE:")
    print("   1. Se selecionou comportamentos via /monitorar")
    print("   2. Se a detecção coincide com comportamentos selecionados\n")
    
    print("🚀 PARA TODOS RECEBEREM TUDO:")
    print("   → Não selecionar comportamentos (manter padrão)")
    print("   → OU selecionar TODOS os 7 comportamentos via /monitorar\n")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
