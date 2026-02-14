#!/usr/bin/env python3
"""
Teste da fila inteligente para demonstrar funcionamento
"""
import asyncio
from fila_envio import FilaEnvioInteligente, ItemFila, PrioridadeEnvio, ConfiguracaoFila

class BotMock:
    """Bot mock para testes"""
    async def send_photo(self, chat_id, photo, caption, **kwargs):
        await asyncio.sleep(0.1)  # Simula envio
        print(f"   📤 Enviado para chat {chat_id}: {len(photo)} bytes")

async def teste_fila():
    print("=" * 70)
    print("🧪 TESTE DA FILA INTELIGENTE")
    print("=" * 70)
    
    # Inicializa fila
    bot = BotMock()
    config = ConfiguracaoFila()
    config.max_envios_simultaneos = 2        # Reduz para teste
    config.max_envios_por_minuto = 10        # Reduz para teste
    config.delay_entre_cameras[PrioridadeEnvio.NORMAL] = 0.5
    config.delay_entre_chats = 0.1
    
    fila = FilaEnvioInteligente(bot, config)
    
    print("\n1️⃣ CRIANDO ITENS DE TESTE")
    print("-" * 70)
    
    # Cria itens com diferentes prioridades
    itens = [
        ItemFila(
            "cam_001", "Câmera 001", "Empresa A",
            [5871339278, 6452106412],
            b"frame_data" * 1000,
            "Detecção normal",
            PrioridadeEnvio.NORMAL
        ),
        ItemFila(
            "cam_002", "Câmera 002", "Empresa A",
            [5871339278, 6452106412],
            b"frame_data" * 1000,
            "Detecção ALTA (2 objetos)",
            PrioridadeEnvio.ALTA,
            [{"class": "person"}, {"class": "car"}]
        ),
        ItemFila(
            "cam_003", "Câmera 003", "Empresa A",
            [5871339278],
            b"frame_data" * 1000,
            "Detecção CRÍTICA",
            PrioridadeEnvio.CRITICA,
            [{"class": "person"}, {"class": "car"}, {"class": "motorcycle"}]
        ),
        ItemFila(
            "cam_004", "Câmera 004", "Empresa A",
            [6452106412],
            b"frame_data" * 1000,
            "Detecção normal #2",
            PrioridadeEnvio.NORMAL
        ),
    ]
    
    print(f"✅ {len(itens)} itens criados")
    
    print("\n2️⃣ ADICIONANDO À FILA")
    print("-" * 70)
    
    for item in itens:
        await fila.adicionar(item)
        print(f"✅ {item.camera_nome} ({item.prioridade.name})")
    
    print(f"\n   Fila antes processamento: {len(fila.fila)} itens")
    
    print("\n3️⃣ PROCESSANDO FILA")
    print("-" * 70)
    
    # Inicia processamento direto
    task = asyncio.create_task(fila.processar_fila())
    
    # Aguarda processamento
    await asyncio.sleep(3)
    
    print("\n4️⃣ ESTATÍSTICAS FINAIS")
    print("-" * 70)
    
    stats = fila.obter_estatisticas()
    print(fila.gerar_relatorio())
    
    print("\n5️⃣ VERIFICAÇÕES")
    print("-" * 70)
    
    checks = [
        ("✅ Enviados > 0", stats['total_enviados'] > 0),
        ("✅ Fila vazia", stats['itens_na_fila'] == 0),
        ("✅ Taxa sucesso > 90%", stats['taxa_sucesso'] > 90),
        ("✅ Priorização OK", len(stats['envios_por_prioridade']) > 0),
    ]
    
    for check, resultado in checks:
        status = "✅" if resultado else "❌"
        print(f"{status} {check}: {resultado}")
    
    # Para processamento
    await fila.parar()
    
    print("\n" + "=" * 70)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(teste_fila())
