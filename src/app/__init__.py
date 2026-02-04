"""App — coração do sistema: orquestração, casos de uso e infraestrutura.

Subpastas:
- bootstrap/: composition root (factories, inicialização, wiring)
- coordinators/: fluxos end-to-end (inbound → pipeline → outbound)
- use_cases/: casos de uso (inputs/outputs, sem IO direto)
- services/: serviços de aplicação
- infra/: implementações concretas de IO
- protocols/: contratos/interfaces
- sessions/: modelos e componentes de sessão
- policies/: políticas (rate limit, abuse, dedupe)
- observability/: logs estruturados, tracing, métricas
- constants/: constantes da aplicação

Padrão: app executa; api adapta; ai decide; fsm governa; utils apoia.
"""
