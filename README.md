# 🤖 Telegram Bot - Detecção de Objetos

Sistema simplificado para detecção de objetos em câmeras RTSP com notificação via Telegram.

## ✨ Características

✅ **Ultra-Simples**: Um único arquivo Python de 300 linhas  
✅ **3 Funcionalidades Essenciais**: Conecta câmeras → Detecta objetos → Envia Telegram  
✅ **Multi-Camera**: Suporta múltiplas câmeras RTSP simultaneamente  
✅ **Multi-Chat**: Envia notificações para múltiplos chats do Telegram  
✅ **YOLO**: Detecção precisa com modelo otimizado  

## 📋 Requisitos

- Python 3.8+
- Câmeras RTSP acessíveis
- Token do Telegram Bot

## 🚀 Instalação Rápida

```bash
# 1. Clone ou baixe o repositório
cd telegram-bot

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure o arquivo .env
# Edite: config/.env

# 4. Execute o bot
python run.py
```

## ⚙️ Configuração

Edite o arquivo `config/.env`:

```env
# ═══════════════════════════════════════════════════════════
# Telegram Bot Configuration
# ═══════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_IDS=123456789:1|987654321:1

# ═══════════════════════════════════════════════════════════
# Camera Configuration
# ═══════════════════════════════════════════════════════════
RTSP_URLS=rtsp://usuario:senha@ip:porta/cam1|rtsp://usuario:senha@ip:porta/cam2
CAMERA_NAMES=Camera 1|Camera 2

# ═══════════════════════════════════════════════════════════
# Detection Settings
# ═══════════════════════════════════════════════════════════
DETECTION_MODEL=models/yolo26n.pt
CONFIDENCE_THRESHOLD=0.35
DETECTION_RESIZE=480

# ═══════════════════════════════════════════════════════════
# Notification Settings
# ═══════════════════════════════════════════════════════════
SEND_COOLDOWN=1
SEND_MAX_WIDTH=960
SEND_TIMEOUT=8

# ═══════════════════════════════════════════════════════════
# Advanced (Optional)
# ═══════════════════════════════════════════════════════════
LOG_LEVEL=INFO
```

### 📝 Explicação das Variáveis

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Token do seu bot Telegram | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_IDS` | IDs dos chats (formato: `id:1\|id:0`) | `5871339278:1\|6452106412:1` |
| `RTSP_URLS` | URLs das câmeras (separadas por `\|`) | `rtsp://user:pass@ip:port/stream` |
| `CAMERA_NAMES` | Nomes das câmeras (separados por `\|`) | `Entrada\|Garagem` |
| `DETECTION_MODEL` | Caminho do modelo YOLO | `models/yolo26n.pt` |
| `CONFIDENCE_THRESHOLD` | Confiança mínima (0-1) | `0.35` |
| `DETECTION_RESIZE` | Largura para detecção (0=original) | `480` |
| `SEND_COOLDOWN` | Segundos entre envios | `1` |
| `SEND_MAX_WIDTH` | Largura máxima do frame enviado | `960` |
| `SEND_TIMEOUT` | Timeout do envio (segundos) | `8` |

## 📖 Como Obter o Token do Telegram

1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Copie o token fornecido
4. Para obter o Chat ID:
   - Envie uma mensagem para seu bot
   - Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
   - Procure por `"chat":{"id":123456789}`

## 📁 Estrutura do Projeto

```
telegram-bot/
├── simple_bot.py              # ⭐ Bot simplificado (TUDO AQUI)
├── run.py                     # Script de execução
├── requirements.txt           # Dependências Python
├── config/
│   ├── .env                  # ⚙️ Configurações
│   └── coco8.yaml            # Classes YOLO
├── models/
│   └── yolo26n.pt           # 🧠 Modelo YOLO
├── README.md                 # Esta documentação
├── README_SIMPLE.md          # Documentação detalhada
└── COMPARATIVO_SIMPLIFICACAO.md  # Comparação com versão anterior
```

## 🎯 Como Funciona

```
┌──────────────┐
│ Câmera RTSP  │
└──────┬───────┘
       │ captura frame
       ▼
┌──────────────┐
│ YOLO Detect  │ ← Detecta pessoas, carros, etc.
└──────┬───────┘
       │ objetos encontrados?
       ▼
┌──────────────┐
│  Telegram    │ ➤ 📱 Notificação com foto
└──────────────┘
```

### Fluxo Detalhado

1. **Conexão**: Conecta às câmeras via `cv2.VideoCapture()`
2. **Captura**: Lê frames continuamente
3. **Detecção**: Processa com YOLO (modelo otimizado)
4. **Filtro**: Aplica confiança mínima (`CONFIDENCE_THRESHOLD`)
5. **Cooldown**: Verifica tempo desde último envio (`SEND_COOLDOWN`)
6. **Desenho**: Adiciona caixas e labels nos objetos detectados
7. **Envio**: Envia foto para todos os chats ativos no Telegram

## 💻 Exemplo de Uso

```bash
# Executar com logs detalhados
python run.py

# Saída esperada:
🚀 Configuração carregada: 2 câmeras, 2 chats ativos
📦 Carregando YOLO: models/yolo26n.pt
✅ YOLO carregado com sucesso
💬 Inicializando bot Telegram
✅ Bot conectado: 2 chat(s) ativo(s)
🎬 Iniciando 2 monitores de câmera
📹 Iniciando monitoramento: Camera 1
🔌 Conectando: Camera 1
✅ Conectado: Camera 1
✅ Enviado para chat 123456789: Camera 1
```

## 🔧 Troubleshooting

### ❌ Câmera não conecta

```bash
# Teste a URL RTSP manualmente
ffplay "rtsp://usuario:senha@ip:porta/stream"
```

**Soluções:**
- Verifique usuário/senha
- Teste se a câmera está acessível na rede
- Confirme a porta RTSP (geralmente 554 ou 7070)

### ❌ Detecções não aparecem

**Soluções:**
- Reduza `CONFIDENCE_THRESHOLD` (ex: 0.25)
- Verifique se o modelo existe: `models/yolo26n.pt`
- Aumente o `LOG_LEVEL=DEBUG` para ver mais informações

### ❌ Telegram não envia

**Soluções:**
- Verifique o `TELEGRAM_BOT_TOKEN`
- Confirme que os `TELEGRAM_CHAT_IDS` têm `:1` no final (habilitado)
- Teste o bot manualmente enviando `/start`
- Aumente `SEND_TIMEOUT` se houver timeout

### ❌ Erro de dependências

```bash
# Reinstale todas as dependências
pip install --upgrade -r requirements.txt

# Ou instale manualmente
pip install opencv-python ultralytics python-telegram-bot python-dotenv pillow
```

## 📊 Performance

| Configuração | FPS | Latência | CPU |
|--------------|-----|----------|-----|
| `DETECTION_RESIZE=480` | ~15 FPS | ~200ms | Médio ✅ |
| `DETECTION_RESIZE=640` | ~10 FPS | ~300ms | Alto ⚠️ |
| `DETECTION_RESIZE=320` | ~25 FPS | ~150ms | Baixo ⚡ |

**Recomendação**: Use `480` para melhor balanço precisão/velocidade.

## 🎨 Objetos Detectados

O modelo YOLO detecta 80 classes, incluindo:

- 👤 **Pessoas**: person
- 🚗 **Veículos**: car, truck, bus, motorcycle, bicycle
- 🐕 **Animais**: dog, cat, bird, horse
- 📦 **Objetos**: backpack, bottle, cup, chair, table, laptop
- E muito mais...

## 🔒 Segurança

⚠️ **IMPORTANTE**: O arquivo `.env` contém informações sensíveis!

```bash
# Nunca commite o .env
echo "config/.env" >> .gitignore

# Use variáveis de ambiente em produção
export TELEGRAM_BOT_TOKEN="seu_token"
export TELEGRAM_CHAT_IDS="chat_ids"
```

## 🆚 Comparação com Versão Anterior

| Métrica | Versão Antiga | Versão Nova | Melhoria |
|---------|---------------|-------------|----------|
| **Arquivos** | 10 arquivos | 1 arquivo | 90% ⬇️ |
| **Código** | 3000 linhas | 300 linhas | 90% ⬇️ |
| **Configuração** | 60+ variáveis | 10 variáveis | 83% ⬇️ |
| **Complexidade** | Alta | Baixa | ✅ |

Veja detalhes em [COMPARATIVO_SIMPLIFICACAO.md](COMPARATIVO_SIMPLIFICACAO.md)

## 📚 Documentação Adicional

- [README_SIMPLE.md](README_SIMPLE.md) - Guia detalhado
- [COMPARATIVO_SIMPLIFICACAO.md](COMPARATIVO_SIMPLIFICACAO.md) - Comparação técnica

## 🤝 Contribuindo

Este projeto foi simplificado ao máximo. Contribuições são bem-vindas, mas devem manter a filosofia de **simplicidade**:

- ✅ Melhorias de performance
- ✅ Correções de bugs
- ✅ Documentação
- ❌ Adicionar complexidade desnecessária
- ❌ Múltiplos arquivos
- ❌ Over-engineering

## 📜 Licença

MIT License

## 👨‍💻 Autor

Sistema simplificado em 10/02/2026

---

**✨ "Simplicidade é a sofisticação máxima" - Leonardo da Vinci**

## 🆘 Suporte

Se encontrar problemas:

1. Verifique a seção [Troubleshooting](#-troubleshooting)
2. Ative `LOG_LEVEL=DEBUG` no `.env`
3. Verifique os logs no console
4. Teste cada componente separadamente (câmera, YOLO, Telegram)

---

Feito com ❤️ e muito ☕
