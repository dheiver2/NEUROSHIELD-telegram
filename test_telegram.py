#!/usr/bin/env python3
"""
Script de teste para diagnosticar problemas de envio para Telegram
"""
import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from telegram import Bot

# Carrega variáveis de ambiente
load_dotenv("config/.env")

print("=" * 60)
print("🔍 DIAGNÓSTICO DE TELEGRAM BOT")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 1. Verifica BOT_TOKEN
# ═══════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print("\n1️⃣ VERIFICANDO BOT_TOKEN")
print("-" * 60)
if BOT_TOKEN:
    print(f"✅ BOT_TOKEN encontrado: {BOT_TOKEN[:20]}...{BOT_TOKEN[-10:]}")
else:
    print("❌ BOT_TOKEN NÃO CONFIGURADO!")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# 2. Verifica arquivo de empresas
# ═══════════════════════════════════════════════════════════
print("\n2️⃣ VERIFICANDO ARQUIVO empresas.json")
print("-" * 60)
CONFIG_EMPRESAS_PATH = "config/empresas.json"
if os.path.exists(CONFIG_EMPRESAS_PATH):
    print(f"✅ Arquivo encontrado: {CONFIG_EMPRESAS_PATH}")
    try:
        with open(CONFIG_EMPRESAS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        empresas = data.get('empresas', [])
        print(f"✅ JSON válido! {len(empresas)} empresa(s) configurada(s)")
        
        total_cameras = 0
        total_chat_ids = 0
        for emp in empresas:
            total_cameras += len(emp.get('cameras', []))
            chat_ids = emp.get('telegram_chat_ids', [])
            total_chat_ids += len(chat_ids)
            print(f"\n   🏢 {emp['nome']}")
            print(f"      • Câmeras: {len(emp.get('cameras', []))}")
            print(f"      • Chat IDs: {total_chat_ids}")
            if chat_ids:
                print(f"        IDs: {chat_ids}")
            else:
                print(f"        ❌ NENHUM CHAT ID CONFIGURADO!")
        
        print(f"\n   TOTAL: {total_cameras} câmeras, {total_chat_ids} chat IDs")
        
        if total_chat_ids == 0:
            print("\n❌ PROBLEMA ENCONTRADO: Nenhum chat ID configurado!")
            print("   Verifique o arquivo: config/empresas.json")
            print("   Este é provavelmente o motivo por que nada está sendo enviado.")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        sys.exit(1)
else:
    print(f"❌ Arquivo NÃO encontrado: {CONFIG_EMPRESAS_PATH}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# 3. Testa conexão com Telegram
# ═══════════════════════════════════════════════════════════
print("\n3️⃣ TESTANDO CONEXÃO COM TELEGRAM")
print("-" * 60)

async def test_telegram():
    try:
        print("🔌 Conectando ao Telegram...")
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ Conectado com sucesso!")
        print(f"   Bot username: @{me.username}")
        print(f"   Bot ID: {me.id}")
        print(f"   Bot name: {me.first_name}")
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False

success = asyncio.run(test_telegram())

if not success:
    print("\n❌ Problema: Não foi possível conectar ao Telegram!")
    print("   Verifique:")
    print("   1. Se o token está correto em config/.env")
    print("   2. Se há conexão com a internet")
    print("   3. Se o token não foi revogado/expirado")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# 4. Testa envio para chat IDs
# ═══════════════════════════════════════════════════════════
print("\n4️⃣ TESTANDO ENVIO PARA CHAT IDs")
print("-" * 60)

async def test_send():
    bot = Bot(token=BOT_TOKEN)
    
    # Pega os chat IDs
    chat_ids = []
    for emp in empresas:
        chat_ids.extend(emp.get('telegram_chat_ids', []))
    
    print(f"   Testando envio para {len(chat_ids)} chat ID(s)...")
    
    for chat_id in chat_ids:
        try:
            print(f"\n   📝 Enviando para chat {chat_id}...")
            
            message = await bot.send_message(
                chat_id=chat_id,
                text="🧪 TESTE - Bot está funcionando!",
                read_timeout=8,
                write_timeout=8
            )
            
            print(f"   ✅ Mensagem enviada com sucesso!")
            print(f"      Message ID: {message.message_id}")
            
        except Exception as e:
            print(f"   ❌ ERRO ao enviar: {e}")
            print(f"      Verifique se o chat_id {chat_id} é válido")
            return False
    
    return True

success = asyncio.run(test_send())

print("\n" + "=" * 60)
if success:
    print("✅ TODOS OS TESTES PASSARAM!")
    print("   O bot está pronto para usar.")
    print("   Verifique se as câmeras estão conectando corretamente.")
else:
    print("❌ ALGUNS TESTES FALHARAM")
    print("   Verifique os erros acima.")
print("=" * 60)
