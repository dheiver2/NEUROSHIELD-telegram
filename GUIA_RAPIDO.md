# 🚀 Guia Rápido - Melhorias de Detecção

## ⚡ Início Rápido

### 1. Configuração Básica (Perfil Balanceado)

Adicione ao seu `config/.env`:

```bash
# Sistema de scoring inteligente
MIN_SEND_SCORE=50.0

# Filtros avançados
MIN_DETECTION_AREA=400
TEMPORAL_SMOOTHING_FRAMES=3

# Eventos significativos
ENABLE_EVENT_DETECTION=1
MULTI_OBJECT_THRESHOLD=3

# Anti-repetição melhorado
ENABLE_SCENE_DETECTION=1
SCENE_HASH_THRESHOLD=15
```

### 2. Execute o Bot

```bash
python simple_bot.py
```

### 3. Observe os Novos Logs

```
🎯 Detecção (score:87.5) [EVENTOS: MULTI_OBJECT: 4 objetos] 
   person#1(HIGH,92%,NEW), car#2(HIGH,88%,45px), truck#3(HIGH,85%,NEW)
```

**Interpretação**:
- `score:87.5` - Score de qualidade (0-100)
- `EVENTOS` - Eventos significativos detectados
- `person#1` - Classe e ID do track
- `HIGH` - Prioridade
- `92%` - Confiança
- `NEW` ou `45px` - Novo objeto ou distância movida

---

## 🎛️ Ajuste Fino

### Problema: Muitos envios duplicados

**Solução**:
```bash
SCENE_HASH_THRESHOLD=10           # Mais sensível a mudanças
MIN_SEND_SCORE=60.0               # Score mais alto
TEMPORAL_SMOOTHING_FRAMES=5       # Mais suavização
```

### Problema: Perdendo detecções importantes

**Solução**:
```bash
MIN_DETECTION_AREA=200            # Detecta objetos menores
MIN_SEND_SCORE=40.0               # Score mais permissivo
TEMPORAL_SMOOTHING_FRAMES=2       # Menos suavização
```

### Problema: Muitos falsos positivos

**Solução**:
```bash
MIN_DETECTION_AREA=600            # Só objetos maiores
MIN_SEND_SCORE=65.0               # Score mais rigoroso
TEMPORAL_SMOOTHING_FRAMES=5       # Mais suavização
MIN_ASPECT_RATIO=0.3              # Geometria mais restrita
```

---

## 📊 Perfis Prontos

### Alta Sensibilidade (Segurança Máxima)

```bash
MIN_DETECTION_AREA=200
MIN_SEND_SCORE=30.0
TEMPORAL_SMOOTHING_FRAMES=2
SCENE_HASH_THRESHOLD=10
MULTI_OBJECT_THRESHOLD=2
```

### Balanceado (Recomendado)

```bash
MIN_DETECTION_AREA=400
MIN_SEND_SCORE=50.0
TEMPORAL_SMOOTHING_FRAMES=3
SCENE_HASH_THRESHOLD=15
MULTI_OBJECT_THRESHOLD=3
```

### Alta Precisão (Menos Notificações)

```bash
MIN_DETECTION_AREA=800
MIN_SEND_SCORE=70.0
TEMPORAL_SMOOTHING_FRAMES=5
SCENE_HASH_THRESHOLD=20
MULTI_OBJECT_THRESHOLD=4
```

---

## 🔍 Entendendo o Sistema de Scoring

### Como Funciona

O score (0-100) combina 4 fatores:

1. **Confiança** (30%): Quão certo o YOLO está
2. **Movimento** (30%): Quanto o objeto se moveu
3. **Novidade** (20%): É um objeto novo na cena?
4. **Persistência** (20%): Objeto está há vários frames?

### Exemplo Prático

```
Cenário: 2 pessoas detectadas
- Pessoa 1: 85% confiança, 120px movimento, nova
- Pessoa 2: 90% confiança, 30px movimento, 10 frames ativa

Cálculo:
- Confiança: (85+90)/2 = 87.5 → 87.5 * 0.3 = 26.25
- Movimento: max(120,30) → 100 * 0.3 = 30.00
- Novidade: 1 de 2 nova → 50 * 0.2 = 10.00
- Persistência: 1 de 2 persistente → 50 * 0.2 = 10.00

Score Final: 26.25 + 30 + 10 + 10 = 76.25 ✅ APROVADO
```

---

## 🚨 Eventos Significativos

### O que são?

Situações especiais que **forçam envio imediato**, ignorando score mínimo:

| Evento | Quando | Exemplo |
|--------|--------|---------|
| `MULTI_OBJECT` | ≥3 objetos | 4 pessoas entrando juntas |
| `RAPID_MOVEMENT` | Movimento ≥150px | Carro passando rápido |
| `NEW_OBJECTS` | ≥2 novos | 3 pessoas chegando |
| `DIVERSE_CLASSES` | ≥3 tipos | Pessoa + carro + moto |

### Como Desativar

```bash
ENABLE_EVENT_DETECTION=0
```

---

## 🛡️ Sistema Anti-Repetição

### Como Funciona

Três camadas de verificação:

1. **Histograma de Cor** (novo!)
   - Compara distribuição de cores HSV
   - > 85% similar → Não envia
   
2. **Hash Perceptual**
   - Compara aparência visual geral
   - < 15% diferente → Não envia
   
3. **Assinatura de Cena**
   - Compara posições dos objetos
   - < 25% mudança → Não envia

### Debug

Para ver detalhes, habilite logs DEBUG:

```bash
LOG_LEVEL=DEBUG
```

Verá logs como:
```
⏭️ Histograma muito similar: 92.3%
🔄 Mudança visual detectada: 22.5% diferente
📍 Mudança de posição: 35% diferente
```

---

## 📈 Monitoramento

### Logs Importantes

```
✅ - Enviado com sucesso
⏭️ - Ignorado (cena similar)
🎯 - Detecção aprovada
🆕 - Nova classe detectada
🚨 - Evento significativo
```

### Métricas para Acompanhar

1. **Taxa de envio**: Quantos frames/minuto?
2. **Score médio**: Qual o score típico?
3. **Eventos**: Quantos eventos/hora?
4. **Repetições**: Quantos ignorados por similaridade?

---

## ⚙️ Configuração Avançada

### Ajustar Pesos do Scoring

Se você quer priorizar movimento sobre confiança:

```bash
SCORING_CONFIDENCE_WEIGHT=0.2    # Menos peso
SCORING_MOVEMENT_WEIGHT=0.4      # Mais peso
SCORING_NOVELTY_WEIGHT=0.2
SCORING_PERSISTENCE_WEIGHT=0.2
```

### Personalizar Eventos

```bash
# Evento multi-objeto mais restritivo
MULTI_OBJECT_THRESHOLD=5

# Movimento extremamente rápido
RAPID_MOVEMENT_THRESHOLD=200
```

---

## 🐛 Troubleshooting

### Bot não envia nada

1. Verifique `MIN_SEND_SCORE` - pode estar muito alto
2. Verifique `MIN_DETECTION_AREA` - pode estar muito grande
3. Ative `LOG_LEVEL=DEBUG` para ver detalhes

### Enviando cenas muito similares

1. Aumente `SCENE_HASH_THRESHOLD` (ex: 20)
2. Verifique se `ENABLE_SCENE_DETECTION=1`
3. Aumente `MIN_SEND_SCORE` (ex: 60)

### Perdendo objetos pequenos

1. Reduza `MIN_DETECTION_AREA` (ex: 200)
2. Ajuste `MIN_ASPECT_RATIO` se objetos finos

### Muitos falsos positivos

1. Aumente `TEMPORAL_SMOOTHING_FRAMES` (ex: 5)
2. Aumente `MIN_DETECTION_AREA` (ex: 600)
3. Aumente `MIN_SEND_SCORE` (ex: 65)

---

## 📚 Mais Informações

- **Documentação completa**: [`MELHORIAS_DETECCAO.md`](MELHORIAS_DETECCAO.md)
- **Resumo técnico**: [`RESUMO_MELHORIAS.md`](RESUMO_MELHORIAS.md)
- **Configuração**: [`config/.env.example`](config/.env.example)

---

## 💡 Dicas Finais

1. **Comece com o perfil balanceado** e ajuste aos poucos
2. **Monitore os logs** por algumas horas antes de ajustar
3. **Use DEBUG** temporariamente para entender o comportamento
4. **Teste um perfil por vez** para ver o impacto
5. **Documente suas configurações** que funcionam bem

---

**Versão**: 2.0  
**Atualizado**: Fevereiro 2026
