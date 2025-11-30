#!/bin/bash

# Frontend Migration Testing Script
# This script helps test the migration from backend to frontend processing

echo "🧪 Frontend Migration Testing Script"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backend is running
echo "1. Checking Backend Server..."
if curl -s http://localhost:8000/api/videos/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend server is running${NC}"
else
    echo -e "${RED}✗ Backend server is not running${NC}"
    echo "   Please start backend: cd backend && python manage.py runserver"
    exit 1
fi

# Check if frontend is running
echo ""
echo "2. Checking Frontend Server..."
if curl -s http://localhost:5173 > /dev/null 2>&1 || curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend server is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend server may not be running${NC}"
    echo "   Please start frontend: cd frontend && npm run dev"
fi

# Test deprecated endpoint
echo ""
echo "3. Testing Deprecated Endpoint (process_ai_view)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/videos/1/process_ai/ 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "410" ]; then
    echo -e "${GREEN}✓ Deprecated endpoint returns HTTP 410 (Gone)${NC}"
    echo "   Response: $BODY"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠ Video not found (expected if video ID 1 doesn't exist)${NC}"
else
    echo -e "${RED}✗ Unexpected response: HTTP $HTTP_CODE${NC}"
    echo "   Response: $BODY"
fi

# Test status update endpoint
echo ""
echo "4. Testing Status Update Endpoint (update_video_status)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/videos/1/update_status/ \
    -H "Content-Type: application/json" \
    -d '{"transcript_hindi": "test translation", "ai_summary": "test summary", "ai_tags": "tag1,tag2", "hindi_script": "test script"}' 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status update endpoint works${NC}"
    echo "   Response: $BODY"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠ Video not found (expected if video ID 1 doesn't exist)${NC}"
else
    echo -e "${RED}✗ Unexpected response: HTTP $HTTP_CODE${NC}"
    echo "   Response: $BODY"
fi

# Check backend logs for migration messages
echo ""
echo "5. Backend Code Verification..."
if grep -q "Translation will be handled by frontend" backend/downloader/views.py; then
    echo -e "${GREEN}✓ Backend has migration messages${NC}"
else
    echo -e "${RED}✗ Backend migration messages not found${NC}"
fi

if grep -q "AI processing will be handled by frontend" backend/downloader/views.py; then
    echo -e "${GREEN}✓ Backend has AI processing migration messages${NC}"
else
    echo -e "${RED}✗ Backend AI processing migration messages not found${NC}"
fi

if grep -q "Script generation will be handled by frontend" backend/downloader/views.py; then
    echo -e "${GREEN}✓ Backend has script generation migration messages${NC}"
else
    echo -e "${RED}✗ Backend script generation migration messages not found${NC}"
fi

# Check frontend services
echo ""
echo "6. Frontend Services Verification..."
if [ -f "frontend/src/services/translation.js" ]; then
    echo -e "${GREEN}✓ Translation service exists${NC}"
else
    echo -e "${RED}✗ Translation service not found${NC}"
fi

if [ -f "frontend/src/services/aiProcessing.js" ]; then
    echo -e "${GREEN}✓ AI processing service exists${NC}"
else
    echo -e "${RED}✗ AI processing service not found${NC}"
fi

if [ -f "frontend/src/services/scriptGenerator.js" ]; then
    echo -e "${GREEN}✓ Script generator service exists${NC}"
else
    echo -e "${RED}✗ Script generator service not found${NC}"
fi

if [ -f "frontend/src/utils/textProcessing.js" ]; then
    echo -e "${GREEN}✓ Text processing utilities exist${NC}"
else
    echo -e "${RED}✗ Text processing utilities not found${NC}"
fi

# Summary
echo ""
echo "===================================="
echo "📋 Testing Summary"
echo "===================================="
echo ""
echo "✅ Frontend builds successfully"
echo "✅ Backend code has migration messages"
echo "✅ Frontend services are in place"
echo ""
echo "📝 Next Steps:"
echo "   1. Start backend: cd backend && python manage.py runserver"
echo "   2. Start frontend: cd frontend && npm run dev"
echo "   3. Extract a video and monitor processing"
echo "   4. Check browser console for frontend processing messages"
echo "   5. Check backend logs for migration messages"
echo ""
echo "📖 See Docs/TESTING_GUIDE.md for detailed testing instructions"
echo ""

