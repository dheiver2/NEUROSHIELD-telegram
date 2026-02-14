#!/usr/bin/env python3
"""
Sistema de Detectores de Comportamento para análise de câmeras da cidade
Detecta padrões como aglomerações, acidentes, atropelamentos, etc
"""
import logging
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TipoComportamento(Enum):
    """Tipos de comportamentos detectáveis na cidade"""
    AGLOMERACAO = "aglomeracao"           # 3+ pessoas próximas
    ACIDENTE_TRANSITO = "acidente"        # Múltiplos veículos + parados
    ATROPELAMENTO = "atropelamento"       # Pessoa + veículo próximos
    CRIME_POTENCIAL = "crime"             # Comportamento suspeito (múltiplos obj rápido)
    CONGESTIONAMENTO = "congestionamento" # 5+ veículos em área
    ASSALTO = "assalto"                   # Pessoas rápido perto de comércio
    MANIFESTACAO = "manifestacao"          # Aglomeração grande + movimento
    INCENDIO = "incendio"                 # (Futuro - entrada manual)
    DESABAMENTO = "desabamento"           # (Futuro - entrada manual)
    ENCHENTE = "enchente"                 # (Futuro - entrada manual)

@dataclass
class ConfiguracaoComportamento:
    """Configuração de um comportamento"""
    tipo: TipoComportamento
    nome: str
    descricao: str
    emoji: str
    minimo_objetos: int
    minimo_velocidade: int  # pixels por frame
    distancia_maxima: int   # pixels entre objetos
    classes_esperadas: Set[str]
    severidade: int  # 1-5 (5=crítico)
    ativo: bool = True

# Definição de todos os comportamentos disponíveis
COMPORTAMENTOS_DISPONIVEIS = {
    TipoComportamento.AGLOMERACAO: ConfiguracaoComportamento(
        tipo=TipoComportamento.AGLOMERACAO,
        nome="Aglomeração",
        descricao="Detecção de 3+ pessoas próximas",
        emoji="👥",
        minimo_objetos=3,
        minimo_velocidade=0,
        distancia_maxima=200,
        classes_esperadas={'person'},
        severidade=2
    ),
    TipoComportamento.ACIDENTE_TRANSITO: ConfiguracaoComportamento(
        tipo=TipoComportamento.ACIDENTE_TRANSITO,
        nome="Acidente de Trânsito",
        descricao="Detecção de 2+ veículos parados ou colidindo",
        emoji="🚗💥",
        minimo_objetos=2,
        minimo_velocidade=0,
        distancia_maxima=150,
        classes_esperadas={'car', 'truck', 'bus', 'motorcycle'},
        severidade=4
    ),
    TipoComportamento.ATROPELAMENTO: ConfiguracaoComportamento(
        tipo=TipoComportamento.ATROPELAMENTO,
        nome="Possível Atropelamento",
        descricao="Detecção de pessoa e veículo muito próximos com movimento",
        emoji="⚠️🚗",
        minimo_objetos=2,
        minimo_velocidade=30,
        distancia_maxima=100,
        classes_esperadas={'person', 'car', 'truck', 'bus', 'motorcycle'},
        severidade=5
    ),
    TipoComportamento.CRIME_POTENCIAL: ConfiguracaoComportamento(
        tipo=TipoComportamento.CRIME_POTENCIAL,
        nome="Atividade Suspeita",
        descricao="Detecção de múltiplos objetos com movimento rápido",
        emoji="🚨",
        minimo_objetos=2,
        minimo_velocidade=50,
        distancia_maxima=300,
        classes_esperadas={'person', 'car', 'truck'},
        severidade=4
    ),
    TipoComportamento.CONGESTIONAMENTO: ConfiguracaoComportamento(
        tipo=TipoComportamento.CONGESTIONAMENTO,
        nome="Congestionamento",
        descricao="Detecção de 5+ veículos acumulados",
        emoji="🚦",
        minimo_objetos=5,
        minimo_velocidade=0,
        distancia_maxima=400,
        classes_esperadas={'car', 'truck', 'bus', 'motorcycle'},
        severidade=2
    ),
    TipoComportamento.ASSALTO: ConfiguracaoComportamento(
        tipo=TipoComportamento.ASSALTO,
        nome="Potencial Assalto",
        descricao="Múltiplas pessoas com movimento rápido perto de ponto comercial",
        emoji="💰🚨",
        minimo_objetos=2,
        minimo_velocidade=40,
        distancia_maxima=150,
        classes_esperadas={'person'},
        severidade=5
    ),
    TipoComportamento.MANIFESTACAO: ConfiguracaoComportamento(
        tipo=TipoComportamento.MANIFESTACAO,
        nome="Aglomeração Grande",
        descricao="Detecção de 8+ pessoas em movimento",
        emoji="🗣️",
        minimo_objetos=8,
        minimo_velocidade=10,
        distancia_maxima=500,
        classes_esperadas={'person'},
        severidade=3
    ),
}

class DetectorComportamento:
    """Detector de comportamentos em tempo real"""
    
    def __init__(self):
        self.comportamentos_monitorados = set()
        self.historico_eventos = []  # Últimos 100 eventos
    
    def ativar_comportamento(self, tipo: TipoComportamento) -> bool:
        """Ativa monitoramento de um comportamento"""
        if tipo not in COMPORTAMENTOS_DISPONIVEIS:
            return False
        
        self.comportamentos_monitorados.add(tipo)
        logger.info(f"✅ Monitoramento ativado: {COMPORTAMENTOS_DISPONIVEIS[tipo].nome}")
        return True
    
    def desativar_comportamento(self, tipo: TipoComportamento) -> bool:
        """Desativa monitoramento de um comportamento"""
        if tipo in self.comportamentos_monitorados:
            self.comportamentos_monitorados.discard(tipo)
            logger.info(f"❌ Monitoramento desativado: {COMPORTAMENTOS_DISPONIVEIS[tipo].nome}")
            return True
        return False
    
    def listar_comportamentos(self) -> Dict:
        """Lista todos os comportamentos com status"""
        resultado = {}
        for tipo, config in COMPORTAMENTOS_DISPONIVEIS.items():
            resultado[tipo.value] = {
                'nome': config.nome,
                'emoji': config.emoji,
                'descricao': config.descricao,
                'severidade': config.severidade,
                'ativo': tipo in self.comportamentos_monitorados
            }
        return resultado
    
    def detectar_comportamento(self, detections: List[Dict], 
                              movimento_score: int = 0) -> List[Tuple[TipoComportamento, str]]:
        """
        Detecta comportamentos baseado em detecções
        
        Args:
            detections: Lista de detecções formato {'class': ..., 'confidence': ..., ...}
            movimento_score: Score de movimento (0-100)
        
        Returns:
            List de (TipoComportamento, descrição) detectados
        """
        if not self.comportamentos_monitorados or not detections:
            return []
        
        comportamentos_detectados = []
        
        # Agrupa detecções por classe
        por_classe = {}
        for det in detections:
            cls = det.get('class', 'unknown')
            if cls not in por_classe:
                por_classe[cls] = []
            por_classe[cls].append(det)
        
        # Verifica cada comportamento monitorado
        for tipo in self.comportamentos_monitorados:
            config = COMPORTAMENTOS_DISPONIVEIS[tipo]
            
            # Filtra detecções relevantes para este comportamento
            dets_relevantes = []
            for cls in config.classes_esperadas:
                dets_relevantes.extend(por_classe.get(cls, []))
            
            if len(dets_relevantes) >= config.minimo_objetos:
                # Verifica movimento
                if movimento_score >= config.minimo_velocidade:
                    # Calcula distância média entre objetos
                    distancia_media = self._calcular_distancia_media(dets_relevantes)
                    
                    if distancia_media <= config.distancia_maxima:
                        comportamentos_detectados.append((
                            tipo,
                            f"{config.emoji} {config.nome}: "
                            f"{len(dets_relevantes)} objetos detectados"
                        ))
        
        return comportamentos_detectados
    
    @staticmethod
    def _calcular_distancia_media(detections: List[Dict]) -> float:
        """Calcula distância média entre detecções"""
        if len(detections) < 2:
            return 0
        
        total_distancia = 0
        pares = 0
        
        for i, det1 in enumerate(detections[:-1]):
            x1, y1 = det1.get('center', (0, 0))
            
            for det2 in detections[i+1:]:
                x2, y2 = det2.get('center', (0, 0))
                
                # Distância euclidiana
                dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                total_distancia += dist
                pares += 1
        
        return total_distancia / pares if pares > 0 else 0
    
    def registrar_evento(self, comportamento: TipoComportamento, 
                        camera_nome: str, detections: List[Dict]):
        """Registra um evento de comportamento detectado"""
        from datetime import datetime
        
        config = COMPORTAMENTOS_DISPONIVEIS[comportamento]
        evento = {
            'timestamp': datetime.now().isoformat(),
            'tipo': comportamento.value,
            'camera': camera_nome,
            'deteccoes': len(detections),
            'severidade': config.severidade,
            'descricao': f"{config.emoji} {config.nome}"
        }
        
        self.historico_eventos.append(evento)
        
        # Mantém apenas últimos 100 eventos
        if len(self.historico_eventos) > 100:
            self.historico_eventos.pop(0)
    
    def obter_historico(self, comportamento: TipoComportamento = None,
                       limite: int = 10) -> List[Dict]:
        """Retorna histórico de eventos"""
        if comportamento:
            eventos = [e for e in self.historico_eventos 
                      if e['tipo'] == comportamento.value]
        else:
            eventos = self.historico_eventos
        
        return eventos[-limite:]
    
    def obter_relatorio(self) -> str:
        """Gera relatório de comportamentos monitorados"""
        linhas = []
        linhas.append("📊 RELATÓRIO DE COMPORTAMENTOS")
        linhas.append("=" * 50)
        
        if not self.comportamentos_monitorados:
            linhas.append("❌ Nenhum comportamento sendo monitorado")
        else:
            linhas.append(f"✅ {len(self.comportamentos_monitorados)} comportamento(s) ativo(s):\n")
            
            for tipo in sorted(self.comportamentos_monitorados, 
                             key=lambda x: COMPORTAMENTOS_DISPONIVEIS[x].severidade, 
                             reverse=True):
                config = COMPORTAMENTOS_DISPONIVEIS[tipo]
                eventos_tipo = [e for e in self.historico_eventos 
                               if e['tipo'] == tipo.value]
                
                linhas.append(f"{config.emoji} {config.nome}")
                linhas.append(f"   Severidade: {'🔴' * config.severidade}")
                linhas.append(f"   Eventos hoje: {len(eventos_tipo)}")
                linhas.append("")
        
        linhas.append("=" * 50)
        return "\n".join(linhas)
