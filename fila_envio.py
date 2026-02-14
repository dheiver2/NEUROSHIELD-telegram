#!/usr/bin/env python3
"""
Sistema de fila inteligente para envio de detecções
Gerencia cadência profissional com 64 câmeras
"""
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PrioridadeEnvio(Enum):
    """Níveis de prioridade de envio"""
    CRITICA = 3      # Eventos críticos (roubo, intrusão anômala)
    ALTA = 2         # Múltiplos objetos, movimento rápido
    NORMAL = 1       # Detecção padrão
    BAIXA = 0        # Confirmação/histórico

class ConfiguracaoFila:
    """Configurações da fila de envio"""
    def __init__(self):
        # Limite de envios simultâneos (evita sobrecarregar Telegram)
        self.max_envios_simultaneos = 3
        
        # Limite total de envios por minuto (rate limiting)
        self.max_envios_por_minuto = 50
        
        # Delay mínimo entre envios da mesma câmera (segundos)
        self.delay_entre_cameras = {
            PrioridadeEnvio.CRITICA: 1,    # 1s para críticas
            PrioridadeEnvio.ALTA: 3,       # 3s para alta prioridade
            PrioridadeEnvio.NORMAL: 5,     # 5s para normal
            PrioridadeEnvio.BAIXA: 10      # 10s para baixa
        }
        
        # Delay mínimo entre envios para o mesmo chat (segundos)
        self.delay_entre_chats = 0.5      # 500ms entre msgs no mesmo chat
        
        # Timeout para envio (segundos)
        self.timeout_envio = 8
        
        # Retry automático em caso de erro
        self.max_tentativas = 2
        self.delay_retry = 2              # 2 segundos entre tentativas

class ItemFila:
    """Item da fila de envio"""
    def __init__(self, camera_id: str, camera_nome: str, empresa_nome: str,
                 chat_ids: List[int], frame_bytes: bytes, caption: str,
                 prioridade: PrioridadeEnvio = PrioridadeEnvio.NORMAL,
                 deteccoes: List[Dict] = None, timestamp: Optional[float] = None):
        self.camera_id = camera_id
        self.camera_nome = camera_nome
        self.empresa_nome = empresa_nome
        self.chat_ids = chat_ids
        self.frame_bytes = frame_bytes
        self.caption = caption
        self.prioridade = prioridade
        self.deteccoes = deteccoes or []
        self.timestamp = timestamp or datetime.now().timestamp()
        self.tentativa = 0
        self.criado_em = datetime.now()
    
    def __lt__(self, outro):
        """Comparação para ordenação na fila (prioridade + tempo)"""
        if self.prioridade.value != outro.prioridade.value:
            return self.prioridade.value > outro.prioridade.value
        return self.timestamp < outro.timestamp

class FilaEnvioInteligente:
    """
    Gerencia fila de envios com:
    - Priorização automática
    - Rate limiting
    - Distribuição de carga
    - Retry automático
    - Estatísticas em tempo real
    """
    
    def __init__(self, bot, config: ConfiguracaoFila = None):
        self.bot = bot
        self.config = config or ConfiguracaoFila()
        
        # Fila de prioridades
        self.fila = []
        self.lock_fila = asyncio.Lock()
        
        # Rastreamento de envios
        self.ultimo_envio_camera = {}        # {camera_id: timestamp}
        self.ultimo_envio_chat = {}          # {chat_id: timestamp}
        self.envios_no_minuto = []           # Lista de timestamps dos últimos 60s
        
        # Estatísticas
        self.total_enviados = 0
        self.total_erros = 0
        self.envios_por_camera = defaultdict(int)
        self.envios_por_prioridade = defaultdict(int)
        self.erros_por_camera = defaultdict(int)
        
        # Status
        self.ativo = False
        self.processando = False
    
    async def adicionar(self, item: ItemFila) -> None:
        """Adiciona item à fila de forma thread-safe"""
        async with self.lock_fila:
            self.fila.append(item)
            self.fila.sort()  # Ordena por prioridade
            
            logger.debug(
                f"📥 Item adicionado à fila: {item.camera_nome} "
                f"(prioridade: {item.prioridade.name}, tamanho fila: {len(self.fila)})"
            )
    
    async def _wait_rate_limit(self) -> None:
        """Aguarda se está no limite de rate limiting"""
        agora = datetime.now().timestamp()
        
        # Remove envios antigos (> 60 segundos)
        self.envios_no_minuto = [
            t for t in self.envios_no_minuto 
            if agora - t < 60
        ]
        
        # Verifica se atingiu limite
        if len(self.envios_no_minuto) >= self.config.max_envios_por_minuto:
            proxima_disponibilidade = self.envios_no_minuto[0] + 60 - agora
            if proxima_disponibilidade > 0:
                logger.warning(
                    f"⏸️ Rate limit atingido! Aguardando {proxima_disponibilidade:.1f}s "
                    f"({len(self.envios_no_minuto)}/{self.config.max_envios_por_minuto})"
                )
                await asyncio.sleep(proxima_disponibilidade + 0.5)
    
    async def _wait_camera(self, camera_id: str, prioridade: PrioridadeEnvio) -> None:
        """Aguarda delay mínimo antes de enviar pela mesma câmera"""
        ultimo = self.ultimo_envio_camera.get(camera_id, 0)
        delay_necessario = self.config.delay_entre_cameras[prioridade]
        tempo_passado = datetime.now().timestamp() - ultimo
        
        if tempo_passado < delay_necessario:
            espera = delay_necessario - tempo_passado
            logger.debug(f"⏳ Aguardando {espera:.1f}s para câmera {camera_id}")
            await asyncio.sleep(espera)
    
    async def _wait_chat(self, chat_id: int) -> None:
        """Aguarda delay mínimo antes de enviar para o mesmo chat"""
        ultimo = self.ultimo_envio_chat.get(chat_id, 0)
        tempo_passado = datetime.now().timestamp() - ultimo
        
        if tempo_passado < self.config.delay_entre_chats:
            espera = self.config.delay_entre_chats - tempo_passado
            await asyncio.sleep(espera)
    
    async def _enviar_item(self, item: ItemFila) -> bool:
        """Envia um item da fila"""
        try:
            # Verifica rate limiting global
            await self._wait_rate_limit()
            
            # Aguarda delay da câmera
            await self._wait_camera(item.camera_id, item.prioridade)
            
            # Tenta enviar para cada chat
            sucesso_total = False
            erros = []
            
            for chat_id in item.chat_ids:
                try:
                    # Aguarda delay do chat
                    await self._wait_chat(chat_id)
                    
                    # Envia foto
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=item.frame_bytes,
                        caption=item.caption,
                        read_timeout=self.config.timeout_envio,
                        write_timeout=self.config.timeout_envio
                    )
                    
                    # Registra sucesso
                    self.ultimo_envio_chat[chat_id] = datetime.now().timestamp()
                    sucesso_total = True
                    
                    logger.info(
                        f"✅ Enviado: {item.camera_nome} → chat {chat_id} "
                        f"(fila: {len(self.fila)} itens)"
                    )
                
                except Exception as e:
                    erros.append((chat_id, str(e)))
                    logger.error(f"❌ Erro ao enviar para chat {chat_id}: {e}")
            
            # Registra último envio da câmera
            if sucesso_total:
                self.ultimo_envio_camera[item.camera_id] = datetime.now().timestamp()
                self.envios_no_minuto.append(datetime.now().timestamp())
            
            return sucesso_total, erros
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout ao enviar: {item.camera_nome}")
            return False, [(None, "Timeout")]
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar: {e}")
            return False, [(None, str(e))]
    
    async def processar_fila(self) -> None:
        """Processa fila de envios continuamente"""
        self.ativo = True
        logger.info("🚀 Fila de envio iniciada")
        
        while self.ativo:
            try:
                if not self.fila:
                    await asyncio.sleep(0.5)
                    continue
                
                # Se já está processando muitos itens, aguarda um pouco
                if self.processando:
                    await asyncio.sleep(0.1)
                    continue
                
                async with self.lock_fila:
                    if not self.fila:
                        continue
                    
                    # Pega próximo item (já ordenado por prioridade)
                    item = self.fila.pop(0)
                
                self.processando = True
                
                try:
                    # Tenta enviar com retry
                    for tentativa in range(self.config.max_tentativas):
                        item.tentativa = tentativa + 1
                        
                        sucesso, erros = await self._enviar_item(item)
                        
                        if sucesso:
                            self.total_enviados += 1
                            self.envios_por_camera[item.camera_id] += 1
                            self.envios_por_prioridade[item.prioridade.name] += 1
                            break
                        
                        elif tentativa < self.config.max_tentativas - 1:
                            logger.warning(
                                f"🔄 Retry {tentativa + 1}/{self.config.max_tentativas} "
                                f"para {item.camera_nome}"
                            )
                            await asyncio.sleep(self.config.delay_retry)
                        else:
                            self.total_erros += 1
                            self.erros_por_camera[item.camera_id] += 1
                            logger.error(
                                f"❌ Falha permanente: {item.camera_nome} "
                                f"(tentativas esgotadas)"
                            )
                
                finally:
                    self.processando = False
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Erro na fila de envio: {e}")
                await asyncio.sleep(1)
        
        logger.info("⏹️ Fila de envio parada")
    
    async def parar(self) -> None:
        """Para o processamento da fila"""
        self.ativo = False
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas da fila"""
        return {
            'total_enviados': self.total_enviados,
            'total_erros': self.total_erros,
            'itens_na_fila': len(self.fila),
            'envios_por_camera': dict(self.envios_por_camera),
            'envios_por_prioridade': dict(self.envios_por_prioridade),
            'erros_por_camera': dict(self.erros_por_camera),
            'taxa_sucesso': (
                self.total_enviados / (self.total_enviados + self.total_erros) * 100
                if (self.total_enviados + self.total_erros) > 0
                else 0
            )
        }
    
    def gerar_relatorio(self) -> str:
        """Gera relatório formatado das estatísticas"""
        stats = self.obter_estatisticas()
        
        relatorio = []
        relatorio.append("📊 ESTATÍSTICAS DA FILA DE ENVIO")
        relatorio.append("=" * 45)
        relatorio.append(f"✅ Enviados: {stats['total_enviados']}")
        relatorio.append(f"❌ Erros: {stats['total_erros']}")
        relatorio.append(f"⏳ Na fila: {stats['itens_na_fila']}")
        relatorio.append(f"📈 Taxa sucesso: {stats['taxa_sucesso']:.1f}%")
        
        if stats['envios_por_prioridade']:
            relatorio.append("")
            relatorio.append("por Prioridade:")
            for prio, count in sorted(stats['envios_por_prioridade'].items()):
                relatorio.append(f"  {prio}: {count}")
        
        if stats['envios_por_camera']:
            relatorio.append("")
            relatorio.append("Top 5 Câmeras:")
            top_cameras = sorted(
                stats['envios_por_camera'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for cam_id, count in top_cameras:
                relatorio.append(f"  {cam_id}: {count}")
        
        return "\n".join(relatorio)
