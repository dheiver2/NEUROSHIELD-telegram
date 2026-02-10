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
from datetime import datetime
from telegram import Bot
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
CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
NMS_IOU_THRESHOLD = float(os.getenv("NMS_IOU_THRESHOLD", "0.65"))
DETECTION_SIZE = int(os.getenv("DETECTION_RESIZE", "480"))
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
MIN_CONFIDENCE_HIGH = float(os.getenv("MIN_CONFIDENCE_HIGH", "0.40"))        # 40% para importantes
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
                area = (x2 - x1) * (y2 - y1)
                
                detections.append({
                    "class": name,
                    "confidence": conf,
                    "box": [x1, y1, x2, y2],
                    "center": (center_x, center_y),
                    "area": area
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
    
    def _is_scene_different(self, current_signature, current_hash):
        """Verifica se a cena mudou significativamente"""
        if not self.scene_comparison_enabled:
            return True  # Se desabilitado, sempre considera diferente
        
        # Primeira cena sempre é diferente
        if self.last_scene_signature is None or self.last_frame_hash is None:
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
                    
                    # Aplica filtros de importância
                    if detections:
                        current_time = asyncio.get_event_loop().time()
                        
                        # Filtro 1: Importância (prioridade + confiança + cooldown + debounce)
                        important_detections = self._filter_by_importance(detections, current_time)
                        
                        if important_detections:
                            # Filtro 2: Movimento significativo
                            has_movement, movement_score, moved_detections = self._calculate_movement(important_detections, current_time)
                            
                            if has_movement and moved_detections:
                                qualifies = (
                                    movement_score >= SEND_MIN_MOVEMENT_SCORE and
                                    len(moved_detections) >= SEND_MIN_MOVED_OBJECTS
                                )
                                if qualifies:
                                    self.movement_streak += 1
                                else:
                                    self.movement_streak = 0

                                if self.movement_streak >= SEND_MIN_STREAK:
                                    # Cooldown global mínimo
                                    if current_time - self.last_send_time >= SEND_COOLDOWN:
                                        # Calcula hash e assinatura da cena atual
                                        current_hash = self._calculate_frame_hash(frame)
                                        current_signature = self._calculate_scene_signature(important_detections)
                                        
                                        # Verifica se a cena mudou significativamente
                                        if self._is_scene_different(current_signature, current_hash):
                                            # Desenha caixas de todos os objetos importantes do frame
                                            frame_with_boxes = self.detector.draw_boxes(frame.copy(), important_detections)
                                            
                                            # Log detalhado
                                            obj_info = []
                                            for d in important_detections:
                                                priority = d.get('priority', 'N/A')
                                                conf = d['confidence']
                                                dist = d.get('movement_distance', 0)
                                                track_id = d.get('track_id')
                                                if d.get('track_is_new'):
                                                    dist_label = "NEW"
                                                else:
                                                    dist_label = f"{dist}px"
                                                obj_info.append(f"{d['class']}#{track_id}({priority},{conf:.0%},{dist_label})")
                                            
                                            obj_list = ", ".join(obj_info)
                                            logger.info(f"🎯 Mudança detectada ({movement_score}%): {obj_list} - {self.camera_name}")
                                            
                                            # Envia para Telegram
                                            await self.telegram_bot.send_detection(
                                                frame_with_boxes, self.camera_name, important_detections,
                                                self.chat_ids, self.empresa_nome
                                            )
                                            
                                            # Atualiza timestamps (SEM cooldown individual por classe)
                                            self.last_send_time = current_time
                                            self.last_scene_signature = current_signature
                                            self.last_frame_hash = current_hash
                                            self.movement_streak = 0
                                        else:
                                            logger.debug(f"⏭️ Cena repetida ignorada - {self.camera_name}")
                            else:
                                self.movement_streak = 0
                    else:
                        # Nenhum objeto detectado - reseta tracking
                        self.tracks = {}
                        self.movement_streak = 0
                    
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
    
    # Inicia todos os monitores
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
