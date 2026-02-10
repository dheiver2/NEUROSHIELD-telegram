# 📋 Configuração Hierárquica - Empresas, Câmeras e IDs

## 🎯 Visão Geral

O bot agora suporta uma estrutura **hierárquica** organizada por empresas:

```
Empresas
  ├── Empresa 1
  │   ├── Chat IDs do Telegram
  │   └── Câmeras
  │       ├── Câmera 1
  │       ├── Câmera 2
  │       └── ...
  └── Empresa 2
      ├── Chat IDs do Telegram
      └── Câmeras
          ├── Câmera 3
          ├── Câmera 4
          └── ...
```

## 📂 Arquivo de Configuração

O arquivo `config/empresas.json` define toda a estrutura:

```json
{
  "empresas": [
    {
      "id": "empresa_1",
      "nome": "Empresa Principal",
      "telegram_chat_ids": [
        "5871339278",
        "6452106412"
      ],
      "cameras": [
        {
          "id": "cam_1",
          "nome": "Recepção Principal",
          "rtsp_url": "rtsp://usuario:senha@ip:porta/path",
          "ativa": true
        },
        {
          "id": "cam_2",
          "nome": "Estacionamento",
          "rtsp_url": "rtsp://usuario:senha@ip:porta/path",
          "ativa": true
        }
      ]
    },
    {
      "id": "empresa_2",
      "nome": "Filial Norte",
      "telegram_chat_ids": [
        "9876543210"
      ],
      "cameras": [
        {
          "id": "cam_3",
          "nome": "Entrada Filial",
          "rtsp_url": "rtsp://usuario:senha@ip:porta/path",
          "ativa": true
        }
      ]
    }
  ]
}
```

## 🔑 Campos Explicados

### Empresa
- **id**: Identificador único da empresa (alfanumérico, sem espaços)
- **nome**: Nome amigável da empresa (aparece nas notificações)
- **telegram_chat_ids**: Lista de IDs do Telegram que receberão alertas desta empresa
- **cameras**: Lista de câmeras desta empresa

### Câmera
- **id**: Identificador único da câmera (alfanumérico, sem espaços)
- **nome**: Nome amigável da câmera (aparece nas notificações)
- **rtsp_url**: URL RTSP completa da câmera
- **ativa**: `true` (monitorar) ou `false` (desativar temporariamente)

## 🎨 Vantagens da Nova Estrutura

### ✅ Isolamento por Empresa
Cada empresa recebe apenas notificações de suas próprias câmeras:
- Empresa A não vê alertas das câmeras da Empresa B
- Cada empresa pode ter múltiplos IDs do Telegram
- IDs podem ser compartilhados entre empresas (para gestores)

### ✅ Facilidade de Gerenciamento
```json
// Adicionar nova empresa
{
  "id": "empresa_nova",
  "nome": "Nova Unidade",
  "telegram_chat_ids": ["123456789"],
  "cameras": [...]
}

// Desativar câmera temporariamente
{
  "ativa": false  // Câmera não será monitorada
}

// Adicionar novo chat ID
"telegram_chat_ids": ["111", "222", "333"]
```

### ✅ Notificações Personalizadas
As mensagens incluem informações da empresa:
```
🏢 Empresa Principal
🎯 Câmera Recepção
⏰ 10/02/2026 14:30:00
🔍 person (85%), car (75%)
```

## 🔧 Como Usar

### 1️⃣ Editar Configuração
Edite o arquivo `config/empresas.json`:

```json
{
  "empresas": [
    {
      "id": "minha_empresa",
      "nome": "Minha Empresa LTDA",
      "telegram_chat_ids": [
        "SEU_CHAT_ID_AQUI"
      ],
      "cameras": [
        {
          "id": "cam_1",
          "nome": "Câmera Principal",
          "rtsp_url": "rtsp://usuario:senha@192.168.1.100:554/stream",
          "ativa": true
        }
      ]
    }
  ]
}
```

### 2️⃣ Executar o Bot
```bash
python simple_bot.py
```

O bot detectará automaticamente o arquivo `config/empresas.json` e usará a estrutura hierárquica.

### 3️⃣ Ver Logs
O bot mostrará:
```
📋 Usando configuração hierárquica (config/empresas.json)
🚀 Configuração carregada: 2 empresa(s), 5 câmera(s), 8 chat(s)
📹 Configurado: Câmera Principal (Minha Empresa LTDA) → 2 chat(s)
```

## 🔄 Compatibilidade

**O bot ainda suporta o modo antigo (.env)** caso o arquivo `config/empresas.json` não exista:
- Usa `TELEGRAM_CHAT_IDS`, `RTSP_URLS` e `CAMERA_NAMES` do `.env`
- Cria estrutura única de "empresa padrão"
- Sem impacto para quem não quiser migrar

## 📝 Exemplos Práticos

### Cenário 1: Empresa Única com Múltiplas Câmeras
```json
{
  "empresas": [
    {
      "id": "empresa_principal",
      "nome": "Security Corp",
      "telegram_chat_ids": ["5871339278", "6452106412"],
      "cameras": [
        {"id": "cam_1", "nome": "Entrada", "rtsp_url": "rtsp://...", "ativa": true},
        {"id": "cam_2", "nome": "Garagem", "rtsp_url": "rtsp://...", "ativa": true},
        {"id": "cam_3", "nome": "Fundos", "rtsp_url": "rtsp://...", "ativa": true}
      ]
    }
  ]
}
```

### Cenário 2: Múltiplas Filiais
```json
{
  "empresas": [
    {
      "id": "filial_sp",
      "nome": "Filial São Paulo",
      "telegram_chat_ids": ["111111111"],
      "cameras": [
        {"id": "sp_cam1", "nome": "SP - Recepção", "rtsp_url": "rtsp://...", "ativa": true}
      ]
    },
    {
      "id": "filial_rj",
      "nome": "Filial Rio de Janeiro",
      "telegram_chat_ids": ["222222222"],
      "cameras": [
        {"id": "rj_cam1", "nome": "RJ - Recepção", "rtsp_url": "rtsp://...", "ativa": true}
      ]
    }
  ]
}
```

### Cenário 3: Gestor Recebe Tudo, Operadores Por Empresa
```json
{
  "empresas": [
    {
      "id": "loja_1",
      "nome": "Loja Shopping",
      "telegram_chat_ids": ["999999999", "111111111"],  // Gestor + Operador Loja 1
      "cameras": [...]
    },
    {
      "id": "loja_2",
      "nome": "Loja Centro",
      "telegram_chat_ids": ["999999999", "222222222"],  // Gestor + Operador Loja 2
      "cameras": [...]
    }
  ]
}
```

## 🛠️ Manutenção

### Adicionar Câmera
Adicione no array `cameras` da empresa correspondente:
```json
{
  "id": "cam_nova",
  "nome": "Nova Câmera",
  "rtsp_url": "rtsp://...",
  "ativa": true
}
```

### Desativar Câmera (Manutenção)
```json
{
  "ativa": false  // Temporariamente desligada
}
```

### Adicionar Chat ID
Adicione no array `telegram_chat_ids`:
```json
"telegram_chat_ids": ["5871339278", "6452106412", "8566048157"]
```

### Remover Empresa
Delete todo o objeto da empresa do array `empresas`.

## ⚙️ O Arquivo `.env` Continua Importante

O arquivo `.env` ainda controla todas as configurações de detecção:
- `CONFIDENCE_THRESHOLD`: Confiança mínima
- `DETECTION_RESIZE`: Resolução de detecção
- `COOLDOWN_HIGH_PRIORITY`: Tempo entre alertas
- Etc.

**Apenas a estrutura de empresas/câmeras/IDs mudou para JSON.**

## 🆘 Solução de Problemas

### Bot não encontra câmeras
- Verifique se `config/empresas.json` existe
- Verifique se o JSON está válido (use jsonlint.com)
- Veja os logs: `📋 Usando configuração...`

### IDs não recebem notificações
- Confirme que o chat ID está correto
- Verifique se está na empresa certa
- Veja os logs de envio: `✅ Enviado para chat...`

### Voltar para modo antigo (.env)
- Delete ou renomeie `config/empresas.json`
- O bot voltará automaticamente para o `.env`

---

**Estrutura criada em:** 10/02/2026  
**Compatível com:** Bot versão 2.0+
