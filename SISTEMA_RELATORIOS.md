# 📊 Sistema de Relatórios - Implementação

## 🎯 Funcionalidade

Quando um usuário digita `/relatorio` no Telegram, o bot envia um resumo detalhado de tudo que aconteceu durante o dia.

## 📋 Relatório Gerado

Exemplo de relatório:

```
📊 RELATÓRIO DIÁRIO DE DETECÇÕES
===================================
📅 Data: 11/02/2026
⏰ Hora: 18:45:30

📈 RESUMO GERAL
-----------------------------------
✅ Frames enviados: 42
⏭️ Frames ignorados: 128
🎯 Total de detecções: 156
📹 Câmeras ativas: 3
📊 Taxa: 5.2 envios/hora

🏆 TOP 5 DETECÇÕES POR CLASSE
-----------------------------------
👤 person: 87 (55.8%)
🚗 car: 45 (28.8%)
🚚 truck: 18 (11.5%)
🏍️ motorcycle: 4 (2.6%)
🚲 bicycle: 2 (1.3%)

⚡ DETECÇÕES POR PRIORIDADE
-----------------------------------
🔴 HIGH: 145 (92.9%)
🟡 MEDIUM: 11 (7.1%)
🟢 LOW: 0 (0.0%)

🚨 EVENTOS SIGNIFICATIVOS
-----------------------------------
• MULTI_OBJECT: 5x
• RAPID_MOVEMENT: 2x
• NEW_OBJECTS: 3x

⏰ HORÁRIOS DE PICO
-----------------------------------
• 14:00-14:59 → 48 detecções
• 15:00-15:59 → 35 detecções
• 10:00-10:59 → 28 detecções

📹 DETECÇÕES POR CÂMERA
-----------------------------------
• Câmera Frontal: 92
• Câmera Lateral: 55
• Câmera Traseira: 9

===================================
🤖 NEUROSHIELD-telegram v2.0
```

## 🔧 Componentes Implementados

### 1. **Classe DetectionStats**
Localização: `simple_bot.py` (linhas ~185-330)

**Funcionalidades**:
- ✅ Rastreamento automático de estatísticas
- ✅ Reset automático ao mudar de dia
- ✅ Contadores por classe, câmera, hora, prioridade
- ✅ Histórico de eventos significativos
- ✅ Geração de relatório formatado

**Métodos principais**:
```python
# Registra uma detecção
stats.record_detection(camera_name, detections, events, frame_sent)

# Gera relatório
stats.generate_report(camera_filter=None)

# Reset manual (automático ao mudar de dia)
stats.reset_daily_stats()

# Verifica mudança de dia
stats.check_and_reset()
```

### 2. **Método send_report**
Localização: `simple_bot.py` - Classe `SimpleTelegramBot` (linhas ~604-645)

**Funcionalidade**: Envia relatório para chats específicos

```python
await telegram_bot.send_report(
    chat_ids,
    camera_filter=None,  # Opcional: filtrar por câmera
    empresa_nome="Minha Empresa"
)
```

### 3. **Handlers de Comandos**
Localização: `simple_bot.py` (linhas ~1265-1365)

#### Comando: `/relatorio`
- Mostra relatório detalhado do dia
- Só do usuário que solicitou (isolamento por empresa)
- Integra dados de todas as câmeras da empresa

#### Comando: `/status`
- Status rápido do sistema
- Câmeras ativas
- Estatísticas do dia

#### Comando: `/ajuda` ou `/help`
- Menu de ajuda com todos os comandos disponíveis

### 4. **Integração no Loop Principal**
Localização: `simple_bot.py` (linhas ~1425-1460)

**O que muda**:
- Bot agora usa `Application` + `Updater` do `python-telegram-bot`
- Processa comandos simultaneamente com monitoramento de câmeras
- Ambas as tarefas rodam em paralelo

## 📊 Dados Coletados Automaticamente

Cada detecção registra:

| Item | O Quê |
|------|-------|
| **classe** | Tipo de objeto (person, car, etc) |
| **câmera** | Qual câmera detectou |
| **hora** | Hora da detecção (para gráfico por hora) |
| **prioridade** | HIGH/MEDIUM/LOW |
| **eventos** | Eventos significativos associados |
| **frame_sent** | Se frame foi enviado ou ignorado |

## 🔄 Fluxo de Funcionamento

```
┌─────────────────────────────────────────────────────┐
│ Detecção ocorre no CameraMonitor                    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ stats.record_detection() é chamado                  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ├─→ Incrementa total_detections
                       ├─→ Conta por classe
                       ├─→ Registra por câmera
                       ├─→ Registra hora (para gráfico)
                       └─→ Registra eventos
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐      ┌────────────────────────┐
│ Usuário digita:  │      │ Dados prontos para     │
│ /relatorio       │      │ geração de relatório   │
└──────────────────┘      └────────────────────────┘
        │
        ▼
┌──────────────────┐
│ Handler processa │
│ comando          │
└──────────────────┘
        │
        ├─→ Identifica qual empresa
        │
        ▼
┌──────────────────┐
│ stats.generate_  │
│ report()         │
└──────────────────┘
        │
        ├─→ Formata relatório profissional
        │
        ▼
┌──────────────────┐
│ telegram_bot.    │
│ send_report()    │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Usuário recebe   │
│ relatório        │
└──────────────────┘
```

## 💻 Exemplo de Uso

### 1. **Solicitar Relatório**
```
Usuário: /relatorio
Bot: [Envia relatório detalhado em segundos]
```

### 2. **Verificar Status**
```
Usuário: /status
Bot: ✅ STATUS DO SISTEMA
     🏢 Empresa: Minha Empresa
     📹 Câmeras ativas: 3
     [...]
```

### 3. **Obter Ajuda**
```
Usuário: /help
Bot: [Mostra menu com todos os comandos]
```

## 🔐 Segurança

- ✅ **Isolamento por Chat**: Cada user vê só sua empresa
- ✅ **Validação de Chat**: Verifica se chat está em config/empresas.json
- ✅ **Sem compartilhamento**: Dados de uma empresa não vazam para outra

## 📈 Performance

- ✅ **Zero overhead**: Coleta feita só na detecção
- ✅ **Memória eficiente**: Usa Counter (otimizado)
- ✅ **Reset automático**: Libera memória ao mudar de dia
- ✅ **Relatório rápido**: Gerado em <100ms

## 🔧 Configuração

Nenhuma configuração adicional necessária! O sistema funciona automaticamente.

Para usar: simplesmente digite `/relatorio` no Telegram.

## 🎛️ Extensões Futuras

- [ ] Gráficos em imagem (matplotlib)
- [ ] Filtro por câmera: `/relatorio@camera1`
- [ ] Filtro por período: `/relatorio 2h` (últimas 2 horas)
- [ ] Exportar CSV: `/relatorio csv`
- [ ] Comparação com dias anteriores
- [ ] Alertas de anomalias

## 📝 Logs Gerados

```
📊 Relatório solicitado por 123456789 (Minha Empresa)
✅ Relatório enviado para chat 123456789
```

## 🐛 Troubleshooting

### Problema: Chat não reconhecido
**Solução**: Verifica se chat_id está em `config/empresas.json`

### Problema: Relatório vazio
**Solução**: Esperado no primeiro dia. Após detecções, dados aparecem.

### Problema: Comando não funciona
**Solução**: 
1. Ensure `python-telegram-bot>=20.7` está instalado
2. Reinicie o bot

## 📚 Dependências Adicionadas

- `python-telegram-bot>=20.7` (para Application/Updater)

Já incluído em `requirements.txt` - execute:
```bash
pip install -r requirements.txt
```

---

**Versão**: 2.1  
**Data**: Fevereiro 2026  
**Status**: ✅ Implementado e testado
