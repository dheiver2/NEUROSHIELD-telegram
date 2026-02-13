#!/usr/bin/env python3
"""
Bot Telegram ULTRA-SIMPLIFICADO para detecção de objetos
Versão minimalista: Conecta câmeras -> Detecta objetos -> Envia Telegram
Suporta estrutura hierárquica: Empresas -> Câmeras -> Chat IDs
"""
import os
import cv2
import asyncio
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ultralytics import YOLO
from dotenv import load_dotenv

# Configuração de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv("config/.env")

# ═══════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# NOVA ESTRUTURA: Tenta carregar de empresas.json, senão usa .env (compatibilidade)
CONFIG_EMPRESAS_PATH = "config/empresas.json"
USE_EMPRESAS_CONFIG = os.path.exists(CONFIG_EMPRESAS_PATH)
MODEL_PATH = os.getenv("DETECTION_MODEL", "models/yolo26n.pt")
CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
NMS_IOU_THRESHOLD = float(os.getenv("NMS_IOU_THRESHOLD", "0.65"))
DETECTION_SIZE = int(os.getenv("DETECTION_RESIZE", "640"))
SEND_COOLDOWN = int(os.getenv("SEND_COOLDOWN", "1"))
SEND_WIDTH = int(os.getenv("SEND_MAX_WIDTH", "960"))
SEND_TIMEOUT = int(os.getenv("SEND_TIMEOUT", "8"))
STARTUP_PING = os.getenv("TELEGRAM_STARTUP_PING", "0") == "1"
SEND_MIN_STREAK = int(os.getenv("SEND_MIN_STREAK", "1"))
SEND_MIN_MOVEMENT_SCORE = int(os.getenv("SEND_MIN_MOVEMENT_SCORE", "0"))
SEND_MIN_MOVED_OBJECTS = int(os.getenv("SEND_MIN_MOVED_OBJECTS", "1"))

# Tracking (multi-objeto)
TRACK_IOU_THRESHOLD = float(os.getenv("TRACK_IOU_THRESHOLD", "0.30"))
TRACK_MAX_MISSES = int(os.getenv("TRACK_MAX_MISSES", "5"))
TRACK_MIN_HITS = int(os.getenv("TRACK_MIN_HITS", "1"))

# Classes permitidas (pessoas + TODOS os meios de transporte)
ALLOWED_CLASSES = {
    'person',      # Pessoas
    'car',         # Carro
    'truck',       # Caminhão
    'bus',         # Ônibus
    'motorcycle',  # Moto
    'bicycle',     # Bicicleta
    'airplane',    # Avião
    'train',       # Trem
    'boat'         # Barco
}

# Sistema de priorização (todas no mesmo nível agora)
HIGH_PRIORITY_CLASSES = ALLOWED_CLASSES
MEDIUM_PRIORITY_CLASSES = set()  # Desabilitado
LOW_PRIORITY_CLASSES = set()     # Desabilitado

# Cooldown dinâmico por prioridade (segundos)
COOLDOWN_HIGH_PRIORITY = int(os.getenv("COOLDOWN_HIGH_PRIORITY", "2"))      # 2s para pessoas/veículos
COOLDOWN_MEDIUM_PRIORITY = int(os.getenv("COOLDOWN_MEDIUM_PRIORITY", "10"))  # 10s para animais
COOLDOWN_LOW_PRIORITY = int(os.getenv("COOLDOWN_LOW_PRIORITY", "30"))        # 30s para objetos

# Confiança mínima por prioridade
MIN_CONFIDENCE_HIGH = float(os.getenv("MIN_CONFIDENCE_HIGH", "0.30"))        # 30% para importantes
MIN_CONFIDENCE_MEDIUM = float(os.getenv("MIN_CONFIDENCE_MEDIUM", "0.50"))    # 50% para médios
MIN_CONFIDENCE_LOW = float(os.getenv("MIN_CONFIDENCE_LOW", "0.70"))          # 70% para comuns

# Movimento mínimo por prioridade (pixels)
MIN_MOVEMENT_HIGH = int(os.getenv("MIN_MOVEMENT_HIGH", "20"))                # 20px para importantes
MIN_MOVEMENT_MEDIUM = int(os.getenv("MIN_MOVEMENT_MEDIUM", "40"))            # 40px para médios
MIN_MOVEMENT_LOW = int(os.getenv("MIN_MOVEMENT_LOW", "80"))                  # 80px para comuns

# Sistema de detecção de mudança de cena (anti-repetição)
SCENE_HASH_THRESHOLD = int(os.getenv("SCENE_HASH_THRESHOLD", "15"))           # Diferença mínima de hash (0-100)
SCENE_CHANGE_THRESHOLD = float(os.getenv("SCENE_CHANGE_THRESHOLD", "0.25"))  # Mudança mínima na composição (0-1)
ENABLE_SCENE_DETECTION = os.getenv("ENABLE_SCENE_DETECTION", "1") == "1"      # Ativa detecção de cena

# Filtros avançados de detecção
MIN_DETECTION_AREA = int(os.getenv("MIN_DETECTION_AREA", "200"))              # Área mínima em pixels² (14x14)
MIN_ASPECT_RATIO = float(os.getenv("MIN_ASPECT_RATIO", "0.2"))                # Aspect ratio mínimo (largura/altura)
MAX_ASPECT_RATIO = float(os.getenv("MAX_ASPECT_RATIO", "5.0"))                # Aspect ratio máximo
TEMPORAL_SMOOTHING_FRAMES = int(os.getenv("TEMPORAL_SMOOTHING_FRAMES", "3"))  # Frames para suavização temporal

# Sistema de scoring inteligente
SCORING_CONFIDENCE_WEIGHT = float(os.getenv("SCORING_CONFIDENCE_WEIGHT", "0.3"))    # Peso da confiança
SCORING_MOVEMENT_WEIGHT = float(os.getenv("SCORING_MOVEMENT_WEIGHT", "0.3"))        # Peso do movimento
SCORING_NOVELTY_WEIGHT = float(os.getenv("SCORING_NOVELTY_WEIGHT", "0.2"))          # Peso da novidade
SCORING_PERSISTENCE_WEIGHT = float(os.getenv("SCORING_PERSISTENCE_WEIGHT", "0.2"))  # Peso da persistência
MIN_SEND_SCORE = float(os.getenv("MIN_SEND_SCORE", "50.0"))                         # Score mínimo para envio (0-100)

# Agregação temporal de frames
FRAME_AGGREGATION_WINDOW = float(os.getenv("FRAME_AGGREGATION_WINDOW", "2.0"))   # Janela de agregação em segundos
MAX_AGGREGATED_DETECTIONS = int(os.getenv("MAX_AGGREGATED_DETECTIONS", "5"))     # Máximo de detecções agregadas

# Detecção de eventos significativos
MULTI_OBJECT_THRESHOLD = int(os.getenv("MULTI_OBJECT_THRESHOLD", "3"))           # Número para evento multi-objeto
RAPID_MOVEMENT_THRESHOLD = int(os.getenv("RAPID_MOVEMENT_THRESHOLD", "150"))     # Pixels para movimento rápido
ENABLE_EVENT_DETECTION = os.getenv("ENABLE_EVENT_DETECTION", "1") == "1"         # Ativa detecção de eventos

# Função para carregar configuração de empresas
def load_empresas_config():
    """Carrega configuração hierárquica de empresas"""
    if not USE_EMPRESAS_CONFIG:
        # Modo compatibilidade: usa .env antigo
        logger.info("📋 Usando configuração legada (.env)")
        chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
        rtsp_urls = os.getenv("RTSP_URLS", "").split("|")
        camera_names = os.getenv("CAMERA_NAMES", "").split("|")
        
        # Parse chat IDs
        chat_ids = []
        for part in chat_ids_raw.split("|"):
            if ":" in part:
                chat_id, status = part.split(":", 1)
                if status.strip() == "1":
                    chat_ids.append(int(chat_id))
        
        # Ajusta nomes
        if not camera_names or len(camera_names) != len(rtsp_urls):
            camera_names = [f"Câmera {i+1}" for i in range(len(rtsp_urls))]
        
        # Retorna estrutura única de "empresa" para compatibilidade
        return [{
            'id': 'default',
            'nome': 'Sistema',
            'telegram_chat_ids': chat_ids,
            'cameras': [{
                'id': f'cam_{i}',
                'nome': nome,
                'rtsp_url': url,
                'ativa': True
            } for i, (url, nome) in enumerate(zip(rtsp_urls, camera_names)) if url.strip()]
        }]
    
    # Modo novo: carrega JSON de empresas
    logger.info(f"📋 Usando configuração hierárquica ({CONFIG_EMPRESAS_PATH})")
    try:
        with open(CONFIG_EMPRESAS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        empresas = data.get('empresas', [])
        
        # Converte chat_ids de string para int
        for empresa in empresas:
            empresa['telegram_chat_ids'] = [int(cid) for cid in empresa.get('telegram_chat_ids', [])]
        
        return empresas
    except Exception as e:
        logger.error(f"❌ Erro ao carregar {CONFIG_EMPRESAS_PATH}: {e}")
        return []

# Carrega configuração
EMPRESAS = load_empresas_config()

# Calcula totais para log
total_cameras = sum(len([c for c in emp['cameras'] if c.get('ativa', True)]) for emp in EMPRESAS)
total_chat_ids = sum(len(emp['telegram_chat_ids']) for emp in EMPRESAS)

logger.info(f"🚀 Configuração carregada: {len(EMPRESAS)} empresa(s), {total_cameras} câmera(s), {total_chat_ids} chat(s)")


# ═══════════════════════════════════════════════════════════
# SISTEMA DE ESTATÍSTICAS E RELATÓRIOS
# ═══════════════════════════════════════════════════════════
class DetectionStats:
    """Sistema de estatísticas de detecções para relatórios"""
    
    def __init__(self):
        self.reset_daily_stats()
    
    def reset_daily_stats(self):
        """Reseta estatísticas diárias"""
        self.today = datetime.now().date()
        self.total_detections = 0
        self.total_frames_sent = 0
        self.detections_by_class = Counter()  # {class_name: count}
        self.detections_by_hour = defaultdict(int)  # {hour: count}
        self.detections_by_camera = defaultdict(int)  # {camera_name: count}
        self.detections_by_priority = Counter()  # {priority: count}
        self.events_triggered = Counter()  # {event_type: count}
        self.frames_ignored = 0  # Frames ignorados por similaridade
        self.first_detection_time = None
        self.last_detection_time = None
        self.cameras_active = set()  # Câmeras que tiveram detecção
        self.last_detections = []  # Lista de últimas detecções
        self.class_counts = Counter()  # Alias para detections_by_class
        self.camera_detections = defaultdict(int)  # Alias para detections_by_camera
        self.detected_events = Counter()  # Alias para events_triggered
    
    def check_and_reset(self):
        """Verifica se mudou o dia e reseta se necessário"""
        current_date = datetime.now().date()
        if current_date != self.today:
            logger.info(f"📅 Novo dia detectado, resetando estatísticas")
            self.reset_daily_stats()
    
    def record_detection(self, camera_name, detections, events=None, frame_sent=True):
        """Registra uma detecção"""
        self.check_and_reset()
        
        now = datetime.now()
        
        if frame_sent:
            self.total_frames_sent += 1
            if self.first_detection_time is None:
                self.first_detection_time = now
            self.last_detection_time = now
        else:
            self.frames_ignored += 1
        
        # Registra por câmera
        self.cameras_active.add(camera_name)
        self.detections_by_camera[camera_name] += len(detections)
        
        # Registra por hora
        hour = now.hour
        self.detections_by_hour[hour] += len(detections)
        
        # Registra por classe e prioridade
        classes_list = []
        for det in detections:
            self.total_detections += 1
            self.detections_by_class[det['class']] += 1
            classes_list.append(det['class'])
            priority = det.get('priority', 'N/A')
            self.detections_by_priority[priority] += 1
        
        # Registra eventos
        if events:
            for event in events:
                event_type = event.split(':')[0].strip()
                self.events_triggered[event_type] += 1
        
        # Adiciona à lista de últimas detecções (mantém as 50 mais recentes)
        detection_record = {
            'timestamp': now.isoformat(),
            'camera': camera_name,
            'classes': classes_list,
            'count': len(detections),
            'score': detections[0].get('confidence', 0) if detections else 0,
            'events': events or [],
            'sent': frame_sent
        }
        self.last_detections.append(detection_record)
        if len(self.last_detections) > 50:
            self.last_detections.pop(0)
        
        # Atualiza aliases
        self.class_counts = self.detections_by_class
        self.camera_detections = self.detections_by_camera
        self.detected_events = self.events_triggered
    
    def generate_report(self, camera_filter=None):
        """Gera relatório formatado em texto"""
        self.check_and_reset()
        
        now = datetime.now()
        report = []
        
        # Cabeçalho
        report.append("📊 RELATÓRIO DIÁRIO DE DETECÇÕES")
        report.append("=" * 35)
        report.append(f"📅 Data: {now.strftime('%d/%m/%Y')}")
        report.append(f"⏰ Hora: {now.strftime('%H:%M:%S')}")
        report.append("")
        
        # Resumo geral
        report.append("📈 RESUMO GERAL")
        report.append("-" * 35)
        report.append(f"✅ Frames enviados: {self.total_frames_sent}")
        report.append(f"⏭️ Frames ignorados: {self.frames_ignored}")
        report.append(f"🎯 Total de detecções: {self.total_detections}")
        report.append(f"📹 Câmeras ativas: {len(self.cameras_active)}")
        
        if self.first_detection_time and self.last_detection_time:
            duration = self.last_detection_time - self.first_detection_time
            hours = duration.total_seconds() / 3600
            if hours > 0:
                rate = self.total_frames_sent / hours
                report.append(f"📊 Taxa: {rate:.1f} envios/hora")
        
        report.append("")
        
        # Top 5 classes
        if self.detections_by_class:
            report.append("🏆 TOP 5 DETECÇÕES POR CLASSE")
            report.append("-" * 35)
            for cls, count in self.detections_by_class.most_common(5):
                emoji = self._get_class_emoji(cls)
                percentage = (count / self.total_detections) * 100
                report.append(f"{emoji} {cls}: {count} ({percentage:.1f}%)")
            report.append("")
        
        # Detecções por prioridade
        if self.detections_by_priority:
            report.append("⚡ DETECÇÕES POR PRIORIDADE")
            report.append("-" * 35)
            for priority in ['HIGH', 'MEDIUM', 'LOW']:
                count = self.detections_by_priority.get(priority, 0)
                if count > 0:
                    percentage = (count / self.total_detections) * 100
                    report.append(f"{'🔴' if priority == 'HIGH' else '🟡' if priority == 'MEDIUM' else '🟢'} {priority}: {count} ({percentage:.1f}%)")
            report.append("")
        
        # Eventos significativos
        if self.events_triggered:
            report.append("🚨 EVENTOS SIGNIFICATIVOS")
            report.append("-" * 35)
            for event, count in self.events_triggered.most_common():
                report.append(f"• {event}: {count}x")
            report.append("")
        
        # Horários de pico
        if self.detections_by_hour:
            report.append("⏰ HORÁRIOS DE PICO")
            report.append("-" * 35)
            top_hours = sorted(self.detections_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
            for hour, count in top_hours:
                report.append(f"• {hour:02d}:00-{hour:02d}:59 → {count} detecções")
            report.append("")
        
        # Detecções por câmera
        if self.detections_by_camera:
            report.append("📹 DETECÇÕES POR CÂMERA")
            report.append("-" * 35)
            for camera, count in sorted(self.detections_by_camera.items(), key=lambda x: x[1], reverse=True):
                if camera_filter is None or camera == camera_filter:
                    report.append(f"• {camera}: {count}")
            report.append("")
        
        # Rodapé
        report.append("=" * 35)
        report.append("🤖 NEUROSHIELD-telegram v2.0")
        
        return "\n".join(report)
    
    def _get_class_emoji(self, class_name):
        """Retorna emoji para a classe"""
        emoji_map = {
            'person': '👤',
            'car': '🚗',
            'truck': '🚚',
            'bus': '🚌',
            'motorcycle': '🏍️',
            'bicycle': '🚲',
            'airplane': '✈️',
            'train': '🚂',
            'boat': '⛵',
            'dog': '🐕',
            'cat': '🐈',
        }
        return emoji_map.get(class_name, '📦')

# Instância global de estatísticas
stats = DetectionStats()


# ═══════════════════════════════════════════════════════════
# DETECTOR DE OBJETOS
# ═══════════════════════════════════════════════════════════
class SimpleDetector:
    def __init__(self):
        logger.info(f"📦 Carregando YOLO: {MODEL_PATH}")
        self.model = YOLO(MODEL_PATH)
        
        # Configurações otimizadas para detecção EXTREMA (motorcycle fix)
        self.model.overrides['conf'] = CONFIDENCE
        self.model.overrides['iou'] = NMS_IOU_THRESHOLD
        self.model.overrides['agnostic_nms'] = False  # NMS específico por classe
        self.model.overrides['max_det'] = 1000  # MÁXIMO de detecções
        
        logger.info("✅ YOLO carregado com configurações otimizadas")
        logger.info(f"   Dispositivo: {self.model.device}")
    
    def detect(self, frame):
        """Detecta objetos no frame com máxima precisão"""
        if frame is None:
            return []
        
        # FILTRO CRÍTICO: Só processa classes permitidas
        
        # Mantém frame original se DETECTION_SIZE=0, senão redimensiona mantendo aspect ratio
        detect_frame = frame
        scale_x = scale_y = 1.0
        
        if DETECTION_SIZE > 0:
            h, w = frame.shape[:2]
            if w > DETECTION_SIZE or h > DETECTION_SIZE:
                scale = min(DETECTION_SIZE / w, DETECTION_SIZE / h)
                new_w, new_h = int(w * scale), int(h * scale)
                detect_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                scale_x = w / new_w
                scale_y = h / new_h
        
        # Executa detecção com configurações otimizadas
        results = self.model(
            detect_frame,
            conf=CONFIDENCE,
            iou=NMS_IOU_THRESHOLD,
            verbose=False,
            half=False,  # Usa FP32 para máxima precisão
            augment=False  # Sem augmentation para velocidade
        )
        
        # Extrai detecções e ajusta coordenadas ao frame original
        detections = []
        if results and len(results) > 0:
            for box in results[0].boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = self.model.names[cls]
                
                # FILTRO 1: Ignora classes não permitidas
                if name not in ALLOWED_CLASSES:
                    continue
                
                # Coordenadas ajustadas para o frame original
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                
                # Calcula centro e área para tracking
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width = x2 - x1
                height = y2 - y1
                area = width * height
                
                # FILTRO 2: Área mínima (evita detecções muito pequenas/ruído)
                if area < MIN_DETECTION_AREA:
                    continue
                
                # FILTRO 3: Aspect ratio válido (evita detecções deformadas)
                aspect_ratio = width / max(height, 1)
                if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                    continue
                
                detections.append({
                    "class": name,
                    "confidence": conf,
                    "box": [x1, y1, x2, y2],
                    "center": (center_x, center_y),
                    "area": area,
                    "aspect_ratio": aspect_ratio,
                    "dimensions": (width, height)
                })
        
        return detections
    
    def draw_boxes(self, frame, detections):
        """Desenha caixas de detecção com alta qualidade"""
        if len(detections) == 0:
            return frame
        
        # Cria cópia para não alterar original
        output = frame.copy()
        
        # Mapa de cores por classe (Google Material Design)
        color_map = {
            'person': (33, 150, 243),      # Azul
            'car': (255, 152, 0),          # Laranja
            'truck': (255, 87, 34),        # Laranja escuro
            'bus': (255, 112, 67),         # Laranja avermelhado
            'motorcycle': (103, 58, 183),  # Roxo
            'bicycle': (66, 133, 244),     # Azul claro
            'dog': (76, 175, 80),          # Verde
            'cat': (129, 199, 132),        # Verde claro
        }
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det["box"])
            cls_name = det['class']
            conf = det['confidence']
            
            # Cor por classe ou verde padrão
            color = color_map.get(cls_name, (0, 255, 0))
            
            # Desenha retângulo com espessura proporcional ao frame
            thickness = max(2, int(frame.shape[1] / 400))
            cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)
            
            # Prepara label profissional
            label = f"{cls_name} {conf:.0%}"
            
            # Calcula tamanho do texto
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = max(0.5, frame.shape[1] / 1500)
            font_thickness = max(1, int(frame.shape[1] / 800))
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Desenha fundo do label
            padding = 5
            label_y1 = max(y1 - text_h - padding * 2, 0)
            label_y2 = y1
            label_x1 = x1
            label_x2 = x1 + text_w + padding * 2
            
            # Fundo semi-transparente
            overlay = output.copy()
            cv2.rectangle(overlay, (label_x1, label_y1), (label_x2, label_y2), color, -1)
            cv2.addWeighted(overlay, 0.7, output, 0.3, 0, output)
            
            # Desenha texto em branco com anti-aliasing
            text_y = label_y1 + text_h + padding
            cv2.putText(output, label, (x1 + padding, text_y),
                       font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        
        return output


# ═══════════════════════════════════════════════════════════
# BOT TELEGRAM
# ═══════════════════════════════════════════════════════════
class SimpleTelegramBot:
    def __init__(self):
        logger.info("💬 Inicializando bot Telegram")
        self.bot = Bot(token=BOT_TOKEN)
        logger.info(f"✅ Bot conectado")
    
    async def send_detection(self, frame, camera_name, detections, chat_ids, empresa_nome=None):
        """Envia frame com detecções para o Telegram
        
        Args:
            frame: Frame com detecções desenhadas
            camera_name: Nome da câmera
            detections: Lista de detecções
            chat_ids: Lista de chat IDs para enviar
            empresa_nome: Nome da empresa (opcional, para incluir no caption)
        """
        if not chat_ids:
            logger.warning("⚠️ Nenhum chat ID ativo para envio")
            return False
        
        # Redimensiona frame para envio
        if SEND_WIDTH > 0:
            h, w = frame.shape[:2]
            if w > SEND_WIDTH:
                scale = SEND_WIDTH / w
                frame = cv2.resize(frame, (SEND_WIDTH, int(h * scale)))
        
        # Converte frame para bytes
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        photo_bytes = buffer.tobytes()
        
        # Monta caption
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        obj_list = ", ".join([f"{d['class']} ({d['confidence']:.0%})" for d in detections])
        
        if empresa_nome:
            caption = f"🏢 {empresa_nome}\n🎯 {camera_name}\n⏰ {timestamp}\n🔍 {obj_list}"
        else:
            caption = f"🎯 {camera_name}\n⏰ {timestamp}\n🔍 {obj_list}"
        
        # Envia para todos os chats ativos
        success = False
        success_count = 0
        failed_ids = []
        for chat_id in chat_ids:
            try:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_bytes,
                    caption=caption,
                    read_timeout=SEND_TIMEOUT,
                    write_timeout=SEND_TIMEOUT
                )
                logger.info(f"✅ Enviado para chat {chat_id}: {camera_name}")
                success = True
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Erro ao enviar para chat {chat_id}: {e}")
                failed_ids.append(chat_id)

        if failed_ids:
            logger.warning(f"⚠️ Envio parcial: {success_count}/{len(chat_ids)} ok; falha em {failed_ids}")
        else:
            logger.info(f"📬 Envio OK: {success_count}/{len(chat_ids)} chats")
        
        return success

    async def send_startup_ping(self, chat_ids, empresa_nome=None):
        """Envia ping simples para validar todos os chat IDs
        
        Args:
            chat_ids: Lista de chat IDs para enviar
            empresa_nome: Nome da empresa (opcional)
        """
        if not chat_ids:
            return False

        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if empresa_nome:
            text = f"✅ Bot ativo - {empresa_nome}\n⏰ {timestamp}"
        else:
            text = f"✅ Bot ativo\n⏰ {timestamp}"

        success_count = 0
        failed_ids = []
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    read_timeout=SEND_TIMEOUT,
                    write_timeout=SEND_TIMEOUT
                )
                logger.info(f"✅ Ping enviado para chat {chat_id}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Erro ao enviar ping para chat {chat_id}: {e}")
                failed_ids.append(chat_id)

        if failed_ids:
            logger.warning(f"⚠️ Ping parcial: {success_count}/{len(chat_ids)} ok; falha em {failed_ids}")
        else:
            logger.info(f"📬 Ping OK: {success_count}/{len(chat_ids)} chats")

        return success_count > 0
    
    async def send_report(self, chat_ids, camera_filter=None, empresa_nome=None):
        """Envia relatório diário para os chat IDs
        
        Args:
            chat_ids: Lista de chat IDs para enviar
            camera_filter: Filtrar por câmera específica (opcional)
            empresa_nome: Nome da empresa (opcional)
        """
        if not chat_ids:
            logger.warning("⚠️ Nenhum chat ID ativo para envio de relatório")
            return False
        
        # Gera relatório
        report_text = stats.generate_report(camera_filter=camera_filter)
        
        success_count = 0
        failed_ids = []
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    read_timeout=SEND_TIMEOUT,
                    write_timeout=SEND_TIMEOUT,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Relatório enviado para chat {chat_id}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Erro ao enviar relatório para chat {chat_id}: {e}")
                failed_ids.append(chat_id)
        
        if failed_ids:
            logger.warning(f"⚠️ Envio de relatório parcial: {success_count}/{len(chat_ids)} ok; falha em {failed_ids}")
        else:
            logger.info(f"📬 Relatório enviado OK: {success_count}/{len(chat_ids)} chats")
        
        return success_count > 0


# ═══════════════════════════════════════════════════════════
# MONITOR DE CÂMERA
# ═══════════════════════════════════════════════════════════
class CameraMonitor:
    def __init__(self, camera_id, rtsp_url, camera_name, detector, telegram_bot, chat_ids, empresa_nome=None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
        self.detector = detector
        self.telegram_bot = telegram_bot
        self.chat_ids = chat_ids
        self.empresa_nome = empresa_nome
        self.last_send_time = 0
        self.running = False
        
        # Tracking multi-objeto
        self.tracks = {}  # {track_id: {class, box, center, hits, misses}}
        self.next_track_id = 1
        self.track_iou_threshold = TRACK_IOU_THRESHOLD
        self.track_max_misses = TRACK_MAX_MISSES
        self.track_min_hits = TRACK_MIN_HITS
        self.movement_threshold = 30  # Pixels mínimos de movimento
        self.movement_streak = 0
        
        # Sistema de detecção de mudança de cena
        self.last_scene_signature = None  # Assinatura da última cena enviada
        self.last_frame_hash = None  # Hash do último frame enviado
        self.scene_comparison_enabled = ENABLE_SCENE_DETECTION
        
        # Suavização temporal (histórico de detecções)
        self.detection_history = []  # Lista de detecções dos últimos N frames
        
        # Agregação temporal
        self.aggregation_buffer = []  # Buffer de {time, detections, frame}
        
        # Análise de histograma para anti-repetição
        self.last_histogram = None  # Histograma do último frame enviado
        
        # Detecção de eventos
        self.event_history = []  # Histórico de eventos detectados
    
    def _get_priority_config(self, class_name):
        """Retorna configuração de prioridade para a classe"""
        if class_name in HIGH_PRIORITY_CLASSES:
            return 'HIGH', COOLDOWN_HIGH_PRIORITY, MIN_CONFIDENCE_HIGH, MIN_MOVEMENT_HIGH
        elif class_name in MEDIUM_PRIORITY_CLASSES:
            return 'MEDIUM', COOLDOWN_MEDIUM_PRIORITY, MIN_CONFIDENCE_MEDIUM, MIN_MOVEMENT_MEDIUM
        else:
            return 'LOW', COOLDOWN_LOW_PRIORITY, MIN_CONFIDENCE_LOW, MIN_MOVEMENT_LOW
    
    def _filter_by_importance(self, detections, current_time):
        """Filtra detecções por importância, confiança e cooldown"""
        important_detections = []
        
        for det in detections:
            cls_name = det['class']
            confidence = det['confidence']
            priority, cooldown, min_conf, min_movement = self._get_priority_config(cls_name)
            
            # Filtro 1: Confiança mínima por prioridade
            if confidence < min_conf:
                continue
            
            # DEBOUNCE REMOVIDO para permitir múltiplos objetos na mesma cena
            # Filtro 2: Movimento significativo será o debounce natural
            
            # Passou em todos os filtros
            det['priority'] = priority
            det['min_movement'] = min_movement
            important_detections.append(det)
        
        return important_detections
    
    def _calculate_frame_hash(self, frame):
        """Calcula hash perceptual simplificado do frame"""
        try:
            # Reduz para 16x16 em escala de cinza e calcula média por célula
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
            # Normaliza para 0-100 e retorna como tupla para comparação
            normalized = (resized / 255.0 * 100).astype(int)
            return normalized.tobytes()
        except Exception as e:
            logger.warning(f"Erro ao calcular hash: {e}")
            return None
    
    def _calculate_scene_signature(self, detections):
        """Calcula assinatura única da cena baseada em classes e posições"""
        if not detections:
            return None
        
        # Cria assinatura: classes ordenadas + grid de posições
        signature = {
            'classes': {},  # {class_name: count}
            'positions': set()  # Grid positions (x_grid, y_grid, class)
        }
        
        for det in detections:
            cls_name = det['class']
            # Conta ocorrências de cada classe
            signature['classes'][cls_name] = signature['classes'].get(cls_name, 0) + 1
            
            # Divide frame em grid 10x10 e registra posição aproximada
            x, y = det['center']
            x_grid = min(9, int(x / 100))  # Grid 0-9
            y_grid = min(9, int(y / 100))
            signature['positions'].add((x_grid, y_grid, cls_name))
        
        return signature
    
    def _calculate_histogram(self, frame):
        """Calcula histograma de cor do frame para comparação avançada"""
        try:
            # Calcula histograma HSV (melhor que RGB para comparação)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # Histograma de Hue e Saturation (ignora Value para robustez a iluminação)
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            # Normaliza
            hist_h = cv2.normalize(hist_h, hist_h).flatten()
            hist_s = cv2.normalize(hist_s, hist_s).flatten()
            return {'h': hist_h, 's': hist_s}
        except Exception as e:
            logger.warning(f"Erro ao calcular histograma: {e}")
            return None
    
    def _compare_histograms(self, hist1, hist2):
        """Compara dois histogramas e retorna similaridade (0-1, 1=idêntico)"""
        if not hist1 or not hist2:
            return 0.0
        try:
            # Correlação entre histogramas (método de Bhattacharyya)
            similarity_h = cv2.compareHist(hist1['h'], hist2['h'], cv2.HISTCMP_BHATTACHARYYA)
            similarity_s = cv2.compareHist(hist1['s'], hist2['s'], cv2.HISTCMP_BHATTACHARYYA)
            # Bhattacharyya retorna 0 para idênticos, 1 para completamente diferentes
            # Invertemos para 1=idêntico, 0=diferente
            avg_similarity = 1 - ((similarity_h + similarity_s) / 2)
            return max(0.0, min(1.0, avg_similarity))
        except Exception as e:
            logger.warning(f"Erro ao comparar histogramas: {e}")
            return 0.0
    
    def _apply_temporal_smoothing(self, detections):
        """Aplica suavização temporal às detecções para reduzir intermitências"""
        # Adiciona detecções atuais ao histórico
        self.detection_history.append(detections)
        
        # Mantém apenas os últimos N frames
        if len(self.detection_history) > TEMPORAL_SMOOTHING_FRAMES:
            self.detection_history.pop(0)
        
        # Se não temos histórico suficiente, retorna detecções atuais
        if len(self.detection_history) < TEMPORAL_SMOOTHING_FRAMES:
            return detections
        
        # Conta quantas vezes cada classe aparece no histórico
        class_counts = {}
        for frame_dets in self.detection_history:
            for det in frame_dets:
                cls = det['class']
                class_counts[cls] = class_counts.get(cls, 0) + 1
        
        # Filtra detecções que aparecem em pelo menos 2/3 dos frames
        threshold = TEMPORAL_SMOOTHING_FRAMES * 0.66
        smoothed = [d for d in detections if class_counts.get(d['class'], 0) >= threshold]
        
        return smoothed
    
    def _calculate_detection_score(self, detections, movement_score, current_time):
        """Calcula score ponderado para decidir se deve enviar (0-100)"""
        if not detections:
            return 0.0
        
        # 1. Score de confiança (média das confianças)
        avg_confidence = sum(d['confidence'] for d in detections) / len(detections)
        confidence_score = avg_confidence * 100
        
        # 2. Score de movimento (já calculado)
        movement_score_norm = min(100, movement_score)
        
        # 3. Score de novidade (quantos objetos são novos)
        new_count = sum(1 for d in detections if d.get('track_is_new', False))
        novelty_score = min(100, (new_count / max(len(detections), 1)) * 100)
        
        # 4. Score de persistência (quantos objetos têm hits altos)
        persistent_count = 0
        for det in detections:
            track = self.tracks.get(det.get('track_id'))
            if track and track['hits'] >= self.track_min_hits * 2:
                persistent_count += 1
        persistence_score = min(100, (persistent_count / max(len(detections), 1)) * 100)
        
        # Score final ponderado
        final_score = (
            confidence_score * SCORING_CONFIDENCE_WEIGHT +
            movement_score_norm * SCORING_MOVEMENT_WEIGHT +
            novelty_score * SCORING_NOVELTY_WEIGHT +
            persistence_score * SCORING_PERSISTENCE_WEIGHT
        )
        
        return final_score
    
    def _detect_significant_events(self, detections, movement_score):
        """Detecta eventos significativos que justificam envio imediato"""
        if not ENABLE_EVENT_DETECTION or not detections:
            return None
        
        events = []
        
        # Evento 1: Múltiplos objetos detectados simultaneamente
        if len(detections) >= MULTI_OBJECT_THRESHOLD:
            events.append(f"MULTI_OBJECT: {len(detections)} objetos")
        
        # Evento 2: Movimento rápido detectado
        max_movement = max((d.get('movement_distance', 0) for d in detections), default=0)
        if max_movement >= RAPID_MOVEMENT_THRESHOLD:
            events.append(f"RAPID_MOVEMENT: {max_movement}px")
        
        # Evento 3: Múltiplos objetos novos
        new_count = sum(1 for d in detections if d.get('track_is_new', False))
        if new_count >= 2:
            events.append(f"NEW_OBJECTS: {new_count} novos")
        
        # Evento 4: Mix de classes diferentes
        unique_classes = len(set(d['class'] for d in detections))
        if unique_classes >= 3:
            events.append(f"DIVERSE_CLASSES: {unique_classes} tipos")
        
        return events if events else None
    
    def _is_scene_different(self, current_signature, current_hash, current_histogram=None):
        """Verifica se a cena mudou significativamente (versão melhorada)"""
        if not self.scene_comparison_enabled:
            return True  # Se desabilitado, sempre considera diferente
        
        # Primeira cena sempre é diferente
        if self.last_scene_signature is None or self.last_frame_hash is None:
            return True
        
        # NOVO: Comparação de histograma (mais robusta que hash)
        if current_histogram and self.last_histogram:
            hist_similarity = self._compare_histograms(current_histogram, self.last_histogram)
            # Se histogramas são muito similares (>85%), provavelmente é a mesma cena
            if hist_similarity > 0.85:
                logger.debug(f"⏭️ Histograma muito similar: {hist_similarity:.1%}")
                return False
            # Se muito diferentes (<40%), definitivamente mudou
            if hist_similarity < 0.40:
                logger.debug(f"🔄 Histograma muito diferente: {hist_similarity:.1%}")
                return True
        
        # Verifica mudança no hash do frame (visual geral)
        if current_hash and self.last_frame_hash:
            try:
                # Calcula diferença percentual entre hashes
                hash1 = bytes(self.last_frame_hash)
                hash2 = bytes(current_hash)
                diff_count = sum(a != b for a, b in zip(hash1, hash2))
                diff_percent = (diff_count / len(hash1)) * 100
                
                if diff_percent >= SCENE_HASH_THRESHOLD:
                    logger.debug(f"🔄 Mudança visual detectada: {diff_percent:.1f}% diferente")
                    return True
            except Exception as e:
                logger.warning(f"Erro ao comparar hash: {e}")
        
        # Verifica mudança na composição da cena
        if current_signature and self.last_scene_signature:
            # Compara classes presentes
            curr_classes = set(current_signature['classes'].keys())
            last_classes = set(self.last_scene_signature['classes'].keys())
            
            # Nova classe ou classe sumiu?
            if curr_classes != last_classes:
                new_classes = curr_classes - last_classes
                gone_classes = last_classes - curr_classes
                if new_classes:
                    logger.debug(f"🆕 Nova(s) classe(s): {new_classes}")
                if gone_classes:
                    logger.debug(f"❌ Classe(s) sumiu: {gone_classes}")
                return True
            
            # Mudança significativa na quantidade?
            for cls_name in curr_classes:
                curr_count = current_signature['classes'].get(cls_name, 0)
                last_count = self.last_scene_signature['classes'].get(cls_name, 0)
                if abs(curr_count - last_count) > 0:  # Qualquer mudança na contagem
                    logger.debug(f"📊 Mudança na quantidade: {cls_name} {last_count}→{curr_count}")
                    return True
            
            # Mudança significativa nas posições?
            curr_positions = current_signature['positions']
            last_positions = self.last_scene_signature['positions']
            
            # Calcula similaridade de Jaccard
            intersection = len(curr_positions & last_positions)
            union = len(curr_positions | last_positions)
            
            if union > 0:
                similarity = intersection / union
                change = 1 - similarity
                
                if change >= SCENE_CHANGE_THRESHOLD:
                    logger.debug(f"📍 Mudança de posição: {change:.1%} diferente")
                    return True
        
        # Cena é muito similar, não enviar
        logger.debug(f"⏭️ Cena similar ignorada")
        return False
    
    @staticmethod
    def _iou(box_a, box_b):
        """Calcula IoU entre duas caixas"""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union

    def _update_tracks(self, detections, current_time):
        """Atualiza tracks usando IoU e retorna detecções enriquecidas"""
        if not detections:
            # Envelhece tracks existentes
            for track in self.tracks.values():
                track['misses'] += 1
            # Remove tracks expirados
            self.tracks = {tid: t for tid, t in self.tracks.items() if t['misses'] <= self.track_max_misses}
            return

        matches = []
        for track_id, track in self.tracks.items():
            for idx, det in enumerate(detections):
                if det['class'] != track['class']:
                    continue
                iou = self._iou(track['box'], det['box'])
                if iou >= self.track_iou_threshold:
                    matches.append((iou, track_id, idx))

        matches.sort(key=lambda x: x[0], reverse=True)
        matched_tracks = set()
        matched_dets = set()

        for iou, track_id, det_idx in matches:
            if track_id in matched_tracks or det_idx in matched_dets:
                continue

            matched_tracks.add(track_id)
            matched_dets.add(det_idx)

            track = self.tracks[track_id]
            det = detections[det_idx]

            prev_center = track['center']
            det['track_id'] = track_id
            det['movement_distance'] = int(((det['center'][0] - prev_center[0]) ** 2 +
                                            (det['center'][1] - prev_center[1]) ** 2) ** 0.5)

            track['box'] = det['box']
            track['center'] = det['center']
            track['last_seen'] = current_time
            track['hits'] += 1
            track['misses'] = 0

        # Tracks não casados: incrementa misses
        for track_id, track in list(self.tracks.items()):
            if track_id not in matched_tracks:
                track['misses'] += 1
                if track['misses'] > self.track_max_misses:
                    del self.tracks[track_id]

        # Deteções não casadas: cria novos tracks
        for idx, det in enumerate(detections):
            if idx in matched_dets:
                continue
            track_id = self.next_track_id
            self.next_track_id += 1
            det['track_id'] = track_id
            det['movement_distance'] = 0
            self.tracks[track_id] = {
                'id': track_id,
                'class': det['class'],
                'box': det['box'],
                'center': det['center'],
                'last_seen': current_time,
                'hits': 1,
                'misses': 0
            }

    def _calculate_movement(self, current_detections, current_time):
        """Calcula se houve movimento significativo dos objetos"""
        if not current_detections:
            return False, 0, []

        self._update_tracks(current_detections, current_time)

        moved_detections = []
        max_dist = 0
        any_new = False

        for det in current_detections:
            track = self.tracks.get(det.get('track_id'))
            if not track:
                continue
            min_movement = det.get('min_movement', self.movement_threshold)
            is_new = track['hits'] <= self.track_min_hits

            if is_new:
                det['track_is_new'] = True
                moved_detections.append(det)
                any_new = True
                continue

            if det.get('movement_distance', 0) > min_movement:
                moved_detections.append(det)
                if det['movement_distance'] > max_dist:
                    max_dist = det['movement_distance']

        if not moved_detections:
            return False, 0, []

        if any_new:
            movement_score = 100
        else:
            movement_score = min(100, int((max_dist / self.movement_threshold) * 100)) if max_dist > 0 else 0

        return True, movement_score, moved_detections
    
    async def start(self):
        """Inicia monitoramento da câmera"""
        self.running = True
        logger.info(f"📹 Iniciando monitoramento: {self.camera_name}")
        
        while self.running:
            cap = None
            try:
                # Conecta à câmera
                logger.info(f"🔌 Conectando: {self.camera_name}")
                cap = cv2.VideoCapture(self.rtsp_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not cap.isOpened():
                    logger.error(f"❌ Falha ao conectar: {self.camera_name}")
                    await asyncio.sleep(10)
                    continue
                
                logger.info(f"✅ Conectado: {self.camera_name}")
                
                # Loop de captura
                while self.running:
                    ret, frame = cap.read()
                    
                    if not ret or frame is None:
                        logger.warning(f"⚠️ Falha ao ler frame: {self.camera_name}")
                        await asyncio.sleep(1)
                        break
                    
                    # Detecta objetos
                    detections = await asyncio.to_thread(self.detector.detect, frame)
                    
                    # Aplica filtros de importância e processamento avançado
                    if detections:
                        current_time = asyncio.get_event_loop().time()
                        
                        # Filtro 1: Importância (prioridade + confiança + cooldown)
                        important_detections = self._filter_by_importance(detections, current_time)
                        
                        if important_detections:
                            # Aplica suavização temporal para reduzir falsos positivos
                            smoothed_detections = self._apply_temporal_smoothing(important_detections)
                            
                            if smoothed_detections:
                                # Filtro 2: Movimento significativo
                                has_movement, movement_score, moved_detections = self._calculate_movement(
                                    smoothed_detections, current_time
                                )
                                
                                if has_movement and moved_detections:
                                    # Calcula score inteligente
                                    detection_score = self._calculate_detection_score(
                                        moved_detections, movement_score, current_time
                                    )
                                    
                                    # Detecta eventos significativos
                                    significant_events = self._detect_significant_events(
                                        moved_detections, movement_score
                                    )
                                    
                                    # Força envio se houver evento significativo
                                    force_send = significant_events is not None
                                    
                                    # Qualifica para envio por score ou evento
                                    qualifies_by_score = detection_score >= MIN_SEND_SCORE
                                    qualifies = force_send or qualifies_by_score
                                    
                                    if qualifies:
                                        self.movement_streak += 1
                                    else:
                                        self.movement_streak = 0
                                    
                                    # Verifica streak mínimo
                                    if self.movement_streak >= SEND_MIN_STREAK:
                                        # Cooldown global mínimo
                                        if current_time - self.last_send_time >= SEND_COOLDOWN:
                                            # Calcula análises da cena
                                            current_hash = self._calculate_frame_hash(frame)
                                            current_histogram = self._calculate_histogram(frame)
                                            current_signature = self._calculate_scene_signature(smoothed_detections)
                                            
                                            # Verifica se a cena mudou (com análise de histograma)
                                            if self._is_scene_different(current_signature, current_hash, current_histogram):
                                                # Desenha caixas
                                                frame_with_boxes = self.detector.draw_boxes(
                                                    frame.copy(), smoothed_detections
                                                )
                                                
                                                # Log detalhado
                                                obj_info = []
                                                for d in smoothed_detections:
                                                    priority = d.get('priority', 'N/A')
                                                    conf = d['confidence']
                                                    dist = d.get('movement_distance', 0)
                                                    track_id = d.get('track_id')
                                                    if d.get('track_is_new'):
                                                        dist_label = "NEW"
                                                    else:
                                                        dist_label = f"{dist}px"
                                                    obj_info.append(
                                                        f"{d['class']}#{track_id}({priority},{conf:.0%},{dist_label})"
                                                    )
                                                
                                                obj_list = ", ".join(obj_info)
                                                
                                                # Log com informações de score e eventos
                                                log_parts = [f"🎯 Detecção (score:{detection_score:.1f})"]
                                                if significant_events:
                                                    log_parts.append(f"[EVENTOS: {', '.join(significant_events)}]")
                                                log_parts.append(f"{obj_list} - {self.camera_name}")
                                                logger.info(" ".join(log_parts))
                                                
                                                # Registra nas estatísticas
                                                stats.record_detection(
                                                    self.camera_name,
                                                    smoothed_detections,
                                                    events=significant_events,
                                                    frame_sent=True
                                                )
                                                
                                                # Envia para Telegram
                                                await self.telegram_bot.send_detection(
                                                    frame_with_boxes, self.camera_name, smoothed_detections,
                                                    self.chat_ids, self.empresa_nome
                                                )
                                                
                                                # Atualiza estados
                                                self.last_send_time = current_time
                                                self.last_scene_signature = current_signature
                                                self.last_frame_hash = current_hash
                                                self.last_histogram = current_histogram
                                                self.movement_streak = 0
                                            else:
                                                # Registra nas estatísticas (frame ignorado por similaridade)
                                                stats.record_detection(
                                                    self.camera_name,
                                                    smoothed_detections,
                                                    events=None,
                                                    frame_sent=False
                                                )
                                                logger.debug(f"⏭️ Cena repetida ignorada - {self.camera_name}")
                                else:
                                    self.movement_streak = 0
                    else:
                        # Nenhum objeto detectado - reseta tracking e histórico
                        self.tracks = {}
                        self.movement_streak = 0
                        self.detection_history = []
                    
                    # Pequeno delay para não sobrecarregar
                    await asyncio.sleep(0.1)
            
            except Exception as e:
                logger.error(f"❌ Erro em {self.camera_name}: {e}")
            
            finally:
                if cap:
                    cap.release()
                    logger.info(f"🔌 Desconectado: {self.camera_name}")
                
                if self.running:
                    logger.info(f"🔄 Reconectando em 10s: {self.camera_name}")
                    await asyncio.sleep(10)
    
    async def stop(self):
        """Para monitoramento"""
        self.running = False


# ═══════════════════════════════════════════════════════════
# HANDLERS DE COMANDOS TELEGRAM
# ═══════════════════════════════════════════════════════════

# Mapa global para rastrear que chat belongs to which empresa
chat_to_empresa = {}  # {chat_id: empresa_data}

async def cmd_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /relatorio"""
    chat_id = update.effective_chat.id
    
    # Encontra a empresa deste chat
    empresa_data = None
    for empresa in EMPRESAS:
        if chat_id in empresa['telegram_chat_ids']:
            empresa_data = empresa
            break
    
    if not empresa_data:
        await update.message.reply_text(
            "❌ Chat não configurado no sistema.\n"
            "Por favor, verifique a configuração em config/empresas.json"
        )
        return
    
    # Gera e envia relatório
    logger.info(f"📊 Relatório solicitado por {chat_id} ({empresa_data['nome']})")
    
    telegram_bot = SimpleTelegramBot()
    await telegram_bot.send_report(
        [chat_id],
        camera_filter=None,
        empresa_nome=empresa_data['nome']
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /status"""
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
    
    # Constrói status
    status_text = "✅ STATUS DO SISTEMA\n"
    status_text += "=" * 30 + "\n"
    status_text += f"🏢 Empresa: {empresa_data['nome']}\n"
    status_text += f"📹 Câmeras ativas: {len([c for c in empresa_data['cameras'] if c.get('ativa', True)])}\n"
    status_text += f"💬 Chats notificados: {len(empresa_data['telegram_chat_ids'])}\n"
    status_text += f"📊 Total detecções hoje: {stats.total_detections}\n"
    status_text += f"📬 Frames enviados: {stats.total_frames_sent}\n"
    status_text += f"📹 Câmeras com detecção: {len(stats.cameras_active)}\n"
    status_text += "=" * 30
    
    await update.message.reply_text(status_text)

async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /help ou /ajuda"""
    ajuda_text = """🤖 NEUROSHIELD-telegram v2.0

📋 COMANDOS DISPONÍVEIS:

/relatorio - 📊 Relatório detalhado do dia
  Mostra: total de detecções, top classes,
  timeline por hora, eventos significativos

/status - ✅ Status geral do sistema
  Mostra: câmeras ativas, detecções totais,
  estatísticas gerais

/resumo - 📈 Resumo ultra-rápido
  Mostra: números principais só

/cameras - 📹 Lista de câmeras e status
  Mostra: todas as câmeras e seu status

/status_cameras - ℹ️ Detalhes de cada câmera
  Mostra: tempo de conexão, fps, últimas detecções

/top_eventos - 🚨 Top 5 eventos do dia
  Mostra: eventos mais significativos

/historico - 📚 Últimas 10 detecções
  Mostra: detecções mais recentes com timestamps

/ajuda - 📖 Este menu de ajuda

───────────────────────────────
🎯 DETECÇÕES AUTOMÁTICAS:
• Pessoas, veículos, animais
• Eventos significativos
• Mudanças de cena

🔔 NOTIFICAÇÕES:
• Automáticas e inteligentes
• Com confiança de detecção
• Score de relevância

Dúvidas? Contate o administrador!
"""
    await update.message.reply_text(ajuda_text)

async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /resumo - relatório ultra-rápido"""
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
    
    # Resumo rápido com números principais
    resumo_text = "📈 RESUMO RÁPIDO\n"
    resumo_text += "=" * 30 + "\n"
    resumo_text += f"📊 Detecções: {stats.total_detections}\n"
    resumo_text += f"📬 Frames enviados: {stats.total_frames_sent}\n"
    resumo_text += f"👤 Pessoas: {stats.class_counts.get('person', 0)}\n"
    resumo_text += f"🚗 Veículos: {stats.class_counts.get('car', 0) + stats.class_counts.get('truck', 0) + stats.class_counts.get('bus', 0)}\n"
    resumo_text += f"📹 Câmeras ativas: {len([c for c in empresa_data['cameras'] if c.get('ativa', True)])}\n"
    
    if stats.detected_events:
        resumo_text += f"🚨 Eventos: {len(stats.detected_events)}\n"
    
    resumo_text += "=" * 30
    
    await update.message.reply_text(resumo_text)

async def cmd_cameras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /cameras - lista de câmeras"""
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
    
    # Lista de câmeras
    cameras_text = f"📹 CÂMERAS DE {empresa_data['nome'].upper()}\n"
    cameras_text += "=" * 40 + "\n"
    
    for i, camera in enumerate(empresa_data['cameras'], 1):
        status = "✅ ATIVA" if camera.get('ativa', True) else "❌ INATIVA"
        cameras_text += f"{i}. {camera['nome']}\n"
        cameras_text += f"   Status: {status}\n"
        cameras_text += f"   Detecções: {stats.camera_detections.get(camera['nome'], 0)}\n"
        cameras_text += "\n"
    
    cameras_text += "=" * 40
    
    await update.message.reply_text(cameras_text)

async def cmd_status_cameras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /status_cameras - detalhes de cada câmera"""
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
    
    status_text = "📹 STATUS DAS CÂMERAS\n"
    status_text += "=" * 40 + "\n"
    
    for camera in empresa_data['cameras']:
        nome = camera['nome']
        ativa = "✅" if camera.get('ativa', True) else "❌"
        deteccoes = stats.camera_detections.get(nome, 0)
        
        status_text += f"{ativa} {nome}\n"
        status_text += f"   Detecções hoje: {deteccoes}\n"
        
        # Últimas detecções desta câmera
        ultimas = [d for d in stats.last_detections[-5:] if d.get('camera') == nome]
        if ultimas:
            ultima = ultimas[-1]
            tempo_atras = (datetime.now() - datetime.fromisoformat(ultima['timestamp'])).seconds
            status_text += f"   Última detecção: há {tempo_atras}s\n"
            status_text += f"   Classes: {', '.join(ultima.get('classes', []))}\n"
        else:
            status_text += f"   Última detecção: nenhuma\n"
        
        status_text += "\n"
    
    status_text += "=" * 40
    
    await update.message.reply_text(status_text)

async def cmd_top_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /top_eventos - top 5 eventos do dia"""
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
    
    eventos_text = "🚨 TOP 5 EVENTOS DO DIA\n"
    eventos_text += "=" * 40 + "\n"
    
    if not stats.detected_events:
        eventos_text += "Nenhum evento significativo detectado\n"
    else:
        # Ordena eventos por importância (múltiplos objetos primeiro, depois outros)
        ordernado = sorted(
            stats.detected_events.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for i, (tipo_evento, count) in enumerate(ordernado, 1):
            emoji_map = {
                'MULTI_OBJECT': '👥',
                'RAPID_MOVEMENT': '💨',
                'NEW_OBJECTS': '✨',
                'DIVERSE_CLASSES': '🎯'
            }
            emoji = emoji_map.get(tipo_evento, '🔔')
            eventos_text += f"{i}. {emoji} {tipo_evento}: {count}x\n"
    
    eventos_text += "=" * 40
    
    await update.message.reply_text(eventos_text)

async def cmd_historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /historico - últimas 10 detecções"""
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
    
    historico_text = "📚 HISTÓRICO - ÚLTIMAS DETECÇÕES\n"
    historico_text += "=" * 40 + "\n"
    
    if not stats.last_detections:
        historico_text += "Nenhuma detecção registrada\n"
    else:
        for i, det in enumerate(stats.last_detections[-10:], 1):
            tempo = datetime.fromisoformat(det['timestamp']).strftime("%H:%M:%S")
            camera = det.get('camera', 'desconhecida')
            classes = ', '.join(det.get('classes', []))
            score = det.get('score', 0)
            
            historico_text += f"{i}. {tempo} | {camera}\n"
            historico_text += f"   Classes: {classes}\n"
            historico_text += f"   Score: {score:.1f}\n"
    
    historico_text += "=" * 40
    
    await update.message.reply_text(historico_text)

async def setup_telegram_handlers(application: Application):
    """Configura handlers de comandos telegram"""
    # Relatórios e Análise
    application.add_handler(CommandHandler("relatorio", cmd_relatorio))
    application.add_handler(CommandHandler("resumo", cmd_resumo))
    application.add_handler(CommandHandler("top_eventos", cmd_top_eventos))
    application.add_handler(CommandHandler("historico", cmd_historico))
    
    # Status e Monitoramento
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("cameras", cmd_cameras))
    application.add_handler(CommandHandler("status_cameras", cmd_status_cameras))
    
    # Ajuda
    application.add_handler(CommandHandler("help", cmd_ajuda))
    application.add_handler(CommandHandler("ajuda", cmd_ajuda))
    
    logger.info("✅ Handlers de comandos registrados (9 comandos disponíveis)")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
async def main():
    logger.info("="*60)
    logger.info("🤖 TELEGRAM BOT - DETECÇÃO DE OBJETOS (ESTRUTURA HIERÁRQUICA)")
    logger.info("="*60)
    
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN não configurado!")
        return
    
    if not EMPRESAS:
        logger.error("❌ Nenhuma empresa configurada!")
        return
    
    # Inicializa componentes
    detector = SimpleDetector()
    telegram_bot = SimpleTelegramBot()

    # Envia ping de startup se configurado
    if STARTUP_PING:
        for empresa in EMPRESAS:
            if empresa['telegram_chat_ids']:
                await telegram_bot.send_startup_ping(
                    empresa['telegram_chat_ids'],
                    empresa['nome']
                )
    
    # Cria monitores para cada câmera de cada empresa
    monitors = []
    camera_counter = 0
    
    for empresa in EMPRESAS:
        empresa_nome = empresa['nome']
        chat_ids = empresa['telegram_chat_ids']
        
        if not chat_ids:
            logger.warning(f"⚠️ Empresa '{empresa_nome}' sem chat IDs configurados, pulando...")
            continue
        
        for camera in empresa['cameras']:
            if not camera.get('ativa', True):
                logger.info(f"⏭️  Câmera '{camera['nome']}' ({empresa_nome}) está desativada")
                continue
            
            rtsp_url = camera['rtsp_url']
            camera_name = camera['nome']
            
            if rtsp_url.strip():
                monitor = CameraMonitor(
                    camera_counter,
                    rtsp_url,
                    camera_name,
                    detector,
                    telegram_bot,
                    chat_ids,
                    empresa_nome
                )
                monitors.append(monitor)
                camera_counter += 1
                logger.info(f"📹 Configurado: {camera_name} ({empresa_nome}) → {len(chat_ids)} chat(s)")
    
    logger.info(f"🎬 Iniciando {len(monitors)} monitores de câmera")
    
    # Inicia aplicação Telegram para handlers de comandos
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        await setup_telegram_handlers(app)
        
        # Inicia o polling do telegram em background
        async with app:
            await app.initialize()
            await app.start()
            
            # Inicia  monitores de câmera
            monitor_tasks = [monitor.start() for monitor in monitors]
            
            try:
                # Executa ambas: polls telegram e monitores de câmera
                await asyncio.gather(
                    app.updater.start_polling(),
                    *monitor_tasks,
                    return_exceptions=True
                )
            except KeyboardInterrupt:
                logger.info("\n⏹️ Parando sistema...")
                for monitor in monitors:
                    await monitor.stop()
                await app.updater.stop()
            finally:
                await app.stop()
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar handlers: {e}")
        # Mesmo com erro nos handlers, inicia os monitores
        tasks = [monitor.start() for monitor in monitors]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("\n⏹️ Parando sistema...")
            for monitor in monitors:
                await monitor.stop()
    
    logger.info("✅ Sistema finalizado")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
