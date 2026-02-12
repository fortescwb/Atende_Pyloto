# Atende Pyloto - Comandos úteis de desenvolvimento e deploy

**Manter atualizado** Em desenvolvimento ativo

Este repositório implementa um sistema de atendimento automatizado para WhatsApp usando IA conversacional (OpenAI GPT-5), com foco em qualificação de leads B2B para a Pyloto.

---

## Deploy

- Workflow diário
  Início do dia (min-instances=1):

cd "C:\Users\jamis\Repositórios\Atende_Pyloto"

gcloud builds submit --config cloudbuild.yaml --substitutions=_ENV=staging,_MIN_INSTANCES=1

Fim do dia (min-instances=0):

gcloud run services update atende-pyloto-staging \
  --region us-central1 \
  --min-instances 0
