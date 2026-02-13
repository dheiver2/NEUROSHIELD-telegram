# 🛡️ NEUROSHIELD-telegram

**Sistema Inteligente de Monitoramento com IA** - Detecção automática de pessoas e veículos em câmeras RTSP com notificações via Telegram.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Visão Geral

NEUROSHIELD-telegram é um sistema de segurança inteligente que monitora câmeras em tempo real, detecta pessoas e veículos usando IA, e envia alertas instantâneos para o Telegram com foto e informações precisas.

**Arquitetura Hierárquica**: Empresas → Câmeras → Chat IDs

### 📊 Configuração Atual
- **64 Câmeras PACSAFE** configuradas
- **Layout 8x8** (matriz de 8 linhas × 8 colunas)
- **2 Servidores RTSP** (portas 1800 e 1801)
- **Servidor**: 45.187.84.213

## ✨ Características

### 🚀 **Núcleo**
✅ Detecção com **YOLOv8** (state-of-the-art)  
✅ Multi-câmera RTSP simultâneas  
✅ Multi-empresa com isolamento de notificações  
✅ Tracking multi-objeto em tempo real  
✅ Sistema anti-repetição inteligente  

### 🎯 **Detecção Focada**
- 👤 **person** (pessoas)
- 🚗 **car** (carros)
- 🚚 **truck** (caminhões)
- 🚌 **bus** (ônibus)
- 🏍️ **motorcycle** (motos)
- 🚲 **bicycle** (bicicletas)
- ✈️ **airplane** (aviões)
- 🚂 **train** (trens)
- ⛵ **boat** (barcos)

### 🧠 **Inteligência**
- Movimento mínimo configurável
- Cooldown dinâmico por classe
- Detecção de mudança de cena
- Tracking com ID único por objeto
- Confiança ajustável

## 📋 Requisitos

- **Python**: 3.8+
- **Hardware**: PC, servidor ou Raspberry Pi 4 (4GB+)
- **Câmeras**: Streams RTSP acessíveis
- **Telegram**: Bot token + Chat IDs

## 🚀 Instalação Rápida

### 1️⃣ Clone o Repositório
```bash
git clone https://github.com/dheiver2/NEUROSHIELD-telegram.git
cd NEUROSHIELD-telegram
```

### 2️⃣ Instale Dependências
```bash
pip install -r requirements.txt
```

### 3️⃣ Configure Empresas e Câmeras
Edite `config/empresas.json`:

```json
{
  "empresas": [
    {
      "id": "minha_empresa",
      "nome": "Minha Empresa",
      "telegram_chat_ids": ["SEU_CHAT_ID"],
      "cameras": [
        {
          "id": "cam_1",
          "nome": "Câmera Principal",
          "rtsp_url": "rtsp://usuario:senha@ip:porta/stream",
          "ativa": true
        }
      ]
    }
  ]
}
```

**🎯 Configuração Atual**: O sistema já vem com 64 câmeras PACSAFE configuradas. Consulte [config/PACSAFE_CAMERAS.md](config/PACSAFE_CAMERAS.md) para detalhes completos.

### 4️⃣ Configure Telegram
Edite `config/.env`:

```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
DETECTION_RESIZE=480
CONFIDENCE_THRESHOLD=0.35
```

### 5️⃣ Execute o Bot
```bash
python simple_bot.py
```

## 📖 Como Obter Credenciais do Telegram

### Token do Bot
1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Copie o token fornecido

### Chat ID
1. Envie uma mensagem para seu bot
2. Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
3. Procure por `"chat":{"id":123456789}`

## 📁 Estrutura do Projeto

```
NEUROSHIELD-telegram/
├── simple_bot.py                 # 🧠 Core do sistema
├── run.py                        # 🚀 Launcher
├── requirements.txt              # 📦 Dependências
├── config/
│   ├── empresas.json            # 🏢 Empresas/Câmeras/IDs
│   ├── PACSAFE_CAMERAS.md       # 📋 Documentação 64 câmeras
│   ├── .env                     # ⚙️ Configurações técnicas
│   ├── .env.raspberry           # 🥧 Config otimizada RPi4
│   └── coco8.yaml               # 📋 Classes YOLO
├── models/
│   └── yolo26n.pt              # 🎯 Modelo YOLOv8 Nano
└── docs/
    ├── README.md
    └── ESTRUTURA_HIERARQUICA.md # 📚 Guia de estrutura
```

## 🎯 Como Funciona

```mermaid
graph LR
    A[Câmeras RTSP] --> B[YOLOv8 Detection]
    B --> C{Objeto<br/>Detectado?}
    C -->|Sim| D[Tracking MultiObj]
    D --> E{Movimento<br/>Significativo?}
    E -->|Sim| F{Cena<br/>Mudou?}
    F -->|Sim| G[Telegram Alert]
    F -->|Não| H[Ignora Duplicata]
    E -->|Não| H
    C -->|Não| H
```

### Fluxo Inteligente

1. **Captura**: Conecta múltiplas câmeras RTSP
2. **Detecção**: YOLOv8 processa frames (pessoas/veículos)
3. **Tracking**: Atribui ID único a cada objeto
4. **Filtros**:
   - ✅ Confiança mínima
   - ✅ Movimento significativo
   - ✅ Mudança de cena (anti-repetição)
   - ✅ Cooldown dinâmico
5. **Notificação**: Envia foto + dados para Telegram da empresa

## 💻 Exemplos de Uso

### Desktop/Servidor (Windows/Linux)
```bash
python simple_bot.py
```

### Raspberry Pi 4
```bash
# Copiar config otimizada
cp config/.env.raspberry config/.env

# Rodar com prioridade baixa (não travar sistema)
nice -n 10 python3 simple_bot.py
```

### Docker (futuro)
```bash
docker build -t neuroshield .
docker run -d --restart=always neuroshield
```

## 📊 Performance & Hardware

| Hardware | Câmeras | FPS/Cam | Latência | Status |
|----------|---------|---------|----------|--------|
| **PC i5 8GB** | 5 | 15-20 | <200ms | ✅ Recomendado |
| **RPi 4 8GB** | 3-5 | 4-8 | <500ms | ✅ Funciona |
| **RPi 4 4GB** | 2-3 | 4-6 | <500ms | ⚠️ Limitado |
| **RPi 3** | 1 | 2-3 | >1s | ❌ Não recomendado |

### Otimizações por Plataforma

**PC/Servidor** (config/.env):
```env
DETECTION_RESIZE=1920  # Alta resolução
CONFIDENCE_THRESHOLD=0.15  # Muito sensível
```

**Raspberry Pi 4** (config/.env.raspberry):
```env
DETECTION_RESIZE=416  # Otimizado ARM
CONFIDENCE_THRESHOLD=0.20
TRACK_MAX_MISSES=10  # Mais tolerante
```

## 🔧 Configurações Avançadas

### Ajuste de Sensibilidade

```env
# Muito sensível (mais alertas)
CONFIDENCE_THRESHOLD=0.15
MIN_CONFIDENCE_HIGH=0.15
COOLDOWN_HIGH_PRIORITY=1

# Balanceado (recomendado)
CONFIDENCE_THRESHOLD=0.35
MIN_CONFIDENCE_HIGH=0.40
COOLDOWN_HIGH_PRIORITY=2

# Conservador (poucos alertas)
CONFIDENCE_THRESHOLD=0.50
MIN_CONFIDENCE_HIGH=0.60
COOLDOWN_HIGH_PRIORITY=5
```

### Sistema Anti-Repetição

```env
# Ativar/Desativar
ENABLE_SCENE_DETECTION=1  # 1=ativo, 0=desligado

# Sensibilidade visual
SCENE_HASH_THRESHOLD=15  # 0-100 (menor=mais sensível)

# Sensibilidade de composição
SCENE_CHANGE_THRESHOLD=0.25  # 0-1 (menor=mais sensível)
```

## 🏢 Gerenciamento Multi-Empresa

### Adicionar Nova Empresa

```json
{
  "empresas": [
    {
      "id": "empresa_nova",
      "nome": "Nova Filial",
      "telegram_chat_ids": ["999888777"],
      "cameras": [
        {
          "id": "cam_x",
          "nome": "Câmera X",
          "rtsp_url": "rtsp://...",
          "ativa": true
        }
      ]
    }
  ]
}
```

### Desativar Câmera Temporariamente

```json
{
  "ativa": false  // Não será monitorada
}
```

### Compartilhar ID Entre Empresas

```json
// Gestor recebe alertas de todas
{
  "id": "empresa_a",
  "telegram_chat_ids": ["111", "999"]  // 999=gestor
},
{
  "id": "empresa_b",
  "telegram_chat_ids": ["222", "999"]  // 999=gestor
}
```

Veja [ESTRUTURA_HIERARQUICA.md](ESTRUTURA_HIERARQUICA.md) para detalhes.

## 🔒 Segurança

### Proteção de Credenciais

```bash
# Nunca commite .env
echo "config/.env" >> .gitignore

# Use permissões restritas (Linux)
chmod 600 config/.env
chmod 600 config/empresas.json
```

### URLs RTSP Seguras

```json
// ✅ Bom: credenciais no JSON (controlado)
"rtsp_url": "rtsp://usuario:senha@192.168.1.100:554/stream"

// ⚠️ Melhor: usar VPN para acesso às câmeras
// 🔒 Ideal: autenticação por certificado (se câmera suportar)
```

## 🐛 Troubleshooting

### Erro: Câmera não conecta

```bash
# Testar URL RTSP
ffplay "rtsp://usuario:senha@ip:porta/stream"

# Verificar rede
ping 192.168.1.100
```

**Soluções:**
- Verifique credenciais (usuário/senha)
- Confirme porta (554, 7070, 7081...)
- Teste subtype (0, 1, main, sub)

### Erro: Sem detecções

```env
# Reduzir confiança mínima
CONFIDENCE_THRESHOLD=0.15

# Ajustar resolução
DETECTION_RESIZE=640  # Maior = mais preciso
```

### Erro: Bot não envia

```bash
# Verificar token
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Verificar chat IDs
python -c "import json; print(json.load(open('config/empresas.json'))['empresas'])"
```

### Erro: Alto consumo de CPU

```env
# Reduzir resolução
DETECTION_RESIZE=320

# Aumentar cooldown
SEND_COOLDOWN=3
COOLDOWN_HIGH_PRIORITY=5

# Reduzir câmeras simultâneas
# (remova câmeras menos críticas do empresas.json)
```

## 📈 Roadmap

- [ ] Interface Web para gerenciamento
- [ ] Suporte a gravação de vídeo
- [ ] Análise de comportamento (loitering)
- [ ] Reconhecimento facial
- [ ] API REST para integração
- [ ] Dashboard de estatísticas
- [ ] Suporte a GPU (CUDA)
- [ ] Docker containerization
- [ ] Kubernetes deployment

## 📚 Documentação Adicional

- [ESTRUTURA_HIERARQUICA.md](ESTRUTURA_HIERARQUICA.md) - Guia completo da estrutura de empresas
- [config/.env.raspberry](config/.env.raspberry) - Configuração otimizada para Raspberry Pi 4

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📜 Licença

MIT License - sinta-se livre para usar em projetos pessoais e comerciais.

## 👨‍💻 Autor

**Dheiver Santos**
- GitHub: [@dheiver2](https://github.com/dheiver2)
- Projeto: [NEUROSHIELD-telegram](https://github.com/dheiver2/NEUROSHIELD-telegram)

## 🙏 Agradecimentos

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Framework de detecção
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - API do Telegram
- [OpenCV](https://opencv.org/) - Processamento de imagens

## 🆘 Suporte

Se encontrar problemas:

1. Verifique a seção [🐛 Troubleshooting](#-troubleshooting)
2. Ative `LOG_LEVEL=DEBUG` no `.env`
3. Verifique os logs no console
4. Teste componentes separadamente (câmera → YOLO → Telegram)
5. Abra uma [issue](https://github.com/dheiver2/NEUROSHIELD-telegram/issues)

---

⭐ **Se este projeto foi útil, deixe uma estrela no GitHub!**

📧 **Dúvidas ou sugestões?** Abra uma [issue](https://github.com/dheiver2/NEUROSHIELD-telegram/issues)

**✨ "Simplicidade é a sofisticação máxima" - Leonardo da Vinci**

---

Feito com ❤️ e ☕ por Dheiver Santos © 2026
