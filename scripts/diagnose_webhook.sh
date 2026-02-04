#!/bin/bash
# Diagnóstico de Webhook WhatsApp
# Execute: bash scripts/diagnose_webhook.sh

set -e

echo "=========================================="
echo "  Diagnóstico de Webhook WhatsApp"
echo "=========================================="
echo ""

# Configurações
SERVICE_URL="https://atende-pyloto-staging-691572891105.us-central1.run.app"
WEBHOOK_PATH="/webhook/whatsapp/"
VERIFY_TOKEN="Pyloto_da_cadeia_ALIMENTAR"

echo "1. Testando Health Check..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${SERVICE_URL}/health")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | tail -1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -1)

if [ "$HEALTH_STATUS" = "200" ]; then
    echo "   ✅ Health Check OK: $HEALTH_BODY"
else
    echo "   ❌ Health Check FAILED: HTTP $HEALTH_STATUS"
    exit 1
fi
echo ""

echo "2. Testando Webhook Verification (GET)..."
VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" "${SERVICE_URL}${WEBHOOK_PATH}?hub.mode=subscribe&hub.verify_token=${VERIFY_TOKEN}&hub.challenge=test_challenge_123")
VERIFY_STATUS=$(echo "$VERIFY_RESPONSE" | tail -1)
VERIFY_BODY=$(echo "$VERIFY_RESPONSE" | head -1)

if [ "$VERIFY_STATUS" = "200" ] && [ "$VERIFY_BODY" = "test_challenge_123" ]; then
    echo "   ✅ Webhook Verification OK: $VERIFY_BODY"
else
    echo "   ❌ Webhook Verification FAILED: HTTP $VERIFY_STATUS, Body: $VERIFY_BODY"
fi
echo ""

echo "3. Testando Webhook POST (sem assinatura - deve rejeitar)..."
POST_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${SERVICE_URL}${WEBHOOK_PATH}" \
    -H "Content-Type: application/json" \
    -d '{"object":"whatsapp_business_account","entry":[]}')
POST_STATUS=$(echo "$POST_RESPONSE" | tail -1)

if [ "$POST_STATUS" = "401" ]; then
    echo "   ✅ Webhook POST corretamente rejeita sem assinatura (HTTP 401)"
else
    echo "   ⚠️ Webhook POST retornou HTTP $POST_STATUS (esperado 401)"
fi
echo ""

echo "=========================================="
echo "  Checklist do Meta Developer Portal"
echo "=========================================="
echo ""
echo "Verifique no https://developers.facebook.com:"
echo ""
echo "1. [ ] App Mode: LIVE (não Development)"
echo "       - Se estiver em Development, apenas números de teste recebem webhooks"
echo ""
echo "2. [ ] Webhook URL configurada:"
echo "       - URL: ${SERVICE_URL}${WEBHOOK_PATH}"
echo "       - Verify Token: ${VERIFY_TOKEN}"
echo ""
echo "3. [ ] Campos de webhook subscritos:"
echo "       - [ ] messages"
echo "       - [ ] message_reactions (opcional)"
echo "       - [ ] message_template_status_update (opcional)"
echo ""
echo "4. [ ] Número de telefone vinculado ao App"
echo "       - Phone Number ID: Deve corresponder ao configurado no Secret Manager"
echo ""
echo "5. [ ] Permissões do App:"
echo "       - [ ] whatsapp_business_messaging"
echo "       - [ ] whatsapp_business_management"
echo ""
echo "6. [ ] Se em modo Development:"
echo "       - [ ] Seu número de telefone está adicionado como 'Test User'"
echo "       - Adicione em: App Dashboard > Roles > Test Users"
echo ""
echo "=========================================="
echo "  Logs Recentes (últimos 5 minutos)"
echo "=========================================="
echo ""
echo "Execute para ver logs em tempo real:"
echo "  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=atende-pyloto-staging' --project=atende-pyloto --limit=20 --format='value(timestamp,severity,textPayload)' --freshness=5m"
echo ""
