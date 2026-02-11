# ⚡ Guia Rápido - Comandos Telegram

## 📊 Usar o Sistema de Relatórios

Basta digitar no chat do Telegram com o bot:

### Comando: `/relatorio`

**O que faz**: Envia relatório completo do dia

**Quando usar**: Fazer auditoria, revisar eventos do dia

**Resultado**:
```
📊 RELATÓRIO DIÁRIO DE DETECÇÕES
📅 Data: 11/02/2026
⏰ Hora: 18:45:30

📈 RESUMO GERAL:
✅ Frames enviados: 42
⏭️ Frames ignorados: 128
🎯 Total de detecções: 156
📹 Câmeras ativas: 3

[+ TOP 5 CLASSES, EVENTOS, HORÁRIOS DE PICO, etc]
```

---

### Comando: `/status`

**O que faz**: Status rápido do sistema

**Quando usar**: Verificação rápida

**Resultado**:
```
✅ STATUS DO SISTEMA
🏢 Empresa: Minha Empresa
📹 Câmeras ativas: 3
💬 Chats notificados: 2
📊 Total detecções hoje: 156
[...]
```

---

### Comando: `/ajuda` ou `/help`

**O que faz**: Mostra menu de ajuda

**Quando usar**: Lembrar os comandos disponíveis

**Resultado**:
```
🤖 NEUROSHIELD-telegram v2.0

📋 COMANDOS DISPONÍVEIS:

/relatorio - 📊 Relatório detalhado do dia
/status - ✅ Status do sistema
/ajuda - 📖 Este menu de ajuda
[...]
```

---

## 🎯 Casos de Uso Comuns

### Cenário 1: Revisar Dia de Trabalho
```
1. Digite: /relatorio
2. Recebe resumo com:
   - Total de pessoas detectadas
   - Veículos por hora
   - Eventos importantes
3. Identifica eventos anormais
```

### Cenário 2: Verificar se Sistema Está Funcionando
```
1. Digite: /status
2. Veja que câmeras estão ativas
3. Confirme que houve detecções
```

### Cenário 3: Analisar Picos de Movimento
```
1. Digite: /relatorio
2. Vere seção "HORÁRIOS DE PICO"
3. Identifique quando foi mais movimento
```

---

## 📚 O Que o Relatório Mostra

| Seção | Informação |
|-------|-----------|
| **RESUMO GERAL** | Total frames/detecções/câmeras |
| **TOP 5 CLASSES** | Quais objetos mais detectados |
| **POR PRIORIDADE** | HIGH/MEDIUM/LOW split |
| **EVENTOS** | Quantas vezes cada evento ocorreu |
| **HORÁRIOS DE PICO** | Qual hora teve mais detecções |
| **POR CÂMERA** | Atividade de cada câmera |

---

## 🔒 Segurança

✅ Cada chat só vê sua própria empresa  
✅ Dados isolados entre empresas  
✅ Sem compartilhamento de informações  

Se adicionar um chat novo em `config/empresas.json`, ele passa automaticamente a receber comandos.

---

## ⏰ Reset Automático

O relatório reseta automaticamente todo dia às 00:00

- Dados de hoje começam do zero
- Histórico não é perdido (fica em memória até próximo boot)
- Se desligar e religar o bot, perde historio do dia

**Dica**: Para preservar dados históricos, resquest relatório antes de desligar.

---

## 🐛 Problemas?

### "Chat não configurado no sistema"
→ Seu chat_id não está em `config/empresas.json`  
→ Peça ao admin para adicionar

### "Comando não reconhecido"
→ Certificar que digitou `/relatorio` (com barra)  
→ Bot precisa estar rodando

### Relatório vazio
→ Normal no primeiro dia. Aguarde detecções.

---

## 💡 Dicas Profissionais

1. **Crie um grupo Telegram**: Adicione o bot em um grupo com sua equipe para compartilhar relatórios

2. **Automatize**: Use screenshots do relatório em relatórios diários

3. **Compare**: Tome nota dos números para comparar com outros dias

4. **Identifique Padrões**: Veja horários de pico para ajustar patrulhas

---

## 📞 Suporte

- **Comandos não funcionam**: Reinicie o bot
- **Chat não reconhecido**: Contate admin
- **Números estranhos**: Tente /status para confirmar

Versão: 2.1 - Fevereiro 2026
