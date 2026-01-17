#!/bin/bash
# Test 1Password integration

echo "🔐 Testing 1Password Integration..."
echo ""

# Test 1: Read secrets
echo "1. Testing secret retrieval:"
LOCAL_PASS=$(op read "op://Bicameral/Local Redis/password" 2>&1)
if [ $? -eq 0 ]; then
    echo "   ✅ Local Redis password retrieved (${#LOCAL_PASS} chars)"
else
    echo "   ❌ Failed to retrieve Local Redis password"
    exit 1
fi

VPS_PASS=$(op read "op://Bicameral/VPS Redis/password" 2>&1)
if [ $? -eq 0 ]; then
    echo "   ✅ VPS Redis password retrieved (${#VPS_PASS} chars)"
else
    echo "   ❌ Failed to retrieve VPS Redis password"
    exit 1
fi

GATEWAY_TOKEN=$(op read "op://Bicameral/Gateway/token" 2>&1)
if [ $? -eq 0 ]; then
    echo "   ✅ Gateway token retrieved (${#GATEWAY_TOKEN} chars)"
else
    echo "   ❌ Failed to retrieve Gateway token"
    exit 1
fi

echo ""
echo "2. Testing environment injection:"
op inject -i config/.env.example > /tmp/bicameral-test.env 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Environment file injection successful"
    source /tmp/bicameral-test.env
    echo "   ✅ LOCAL_REDIS_PASSWORD: ${#LOCAL_REDIS_PASSWORD} chars"
    echo "   ✅ REDIS_PASSWORD: ${#REDIS_PASSWORD} chars"
    echo "   ✅ GATEWAY_TOKEN: ${#GATEWAY_TOKEN} chars"
    rm /tmp/bicameral-test.env
else
    echo "   ❌ Failed to inject environment file"
    exit 1
fi

echo ""
echo "✅ All 1Password integration tests passed!"
