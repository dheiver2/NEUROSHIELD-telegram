#!/usr/bin/env python3
"""
Adicional: Novo comando /fila para monitorar fila de envio
Insira este código nos handlers de comando em simple_bot.py
"""

# Adicione esta função com os outros handlers (cmd_status, cmd_cameras, etc):

async def cmd_fila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /fila - mostra status da fila de envio"""
    chat_id = update.effective_chat.id
    
    # Encontra a empresa deste chat
    empresa_data = None
    for empresa in EMPRESAS:
        if chat_id in empresa['telegram_chat_ids']:
            empresa_data = empresa
            break
    
    if not empresa_data:
        await update.message.reply_text("❌ Chat não configurado")
        return
    
    # Pega referência do bot
    telegram_bot = globals().get('telegram_bot_instance')
    if not telegram_bot:
        await update.message.reply_text("❌ Bot não inicializado")
        return
    
    # Gera relatório da fila
    fila_text = telegram_bot.fila.gerar_relatorio()
    
    # Envia relatório
    await update.message.reply_text(f"```\n{fila_text}\n```", parse_mode='Markdown')


# Adicione na função setup_telegram_handlers():
# Não esqueça de adicionar esta linha:
# application.add_handler(CommandHandler("fila", cmd_fila))
