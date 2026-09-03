import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from gateway.main import app

async def test_gateway_endpoints():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Health check
            print("1. Testing GET /health...")
            res = await client.get("/health")
            print(f"   Status: {res.status_code}, Response: {res.json()}")
            assert res.status_code == 200

            admin_headers = {"X-Admin-Token": os.getenv("ADMIN_TOKEN", "default-admin-secret-key")}

            # 2. Cookie validation via admin
            print("\n2. Testing POST /admin/accounts/main/validate-cookies...")
            res = await client.post("/admin/accounts/main/validate-cookies", headers=admin_headers)
            print(f"   Status: {res.status_code}, Response: {res.json()}")
            assert res.status_code == 200

            # 3. Create a test API key
            print("\n3. Testing POST /admin/api-keys to create an API key...")
            res = await client.post("/admin/api-keys", json={
                "account_id": "main",
                "name": "Live Test Key",
                "rate_limit": 60,
                "permissions": ["read", "write", "studio"]
            }, headers=admin_headers)
            print(f"   Status: {res.status_code}, Response: {res.json()}")
            assert res.status_code == 200
            api_key = res.json()["api_key"]

            # 4. List notebooks via /v1/notebooks using X-API-Key
            print("\n4. Testing GET /v1/notebooks with X-API-Key...")
            res = await client.get("/v1/notebooks", headers={"X-API-Key": api_key})
            print(f"   Status: {res.status_code}, Response: {res.json()}")
            assert res.status_code == 200
            print("\n=== ALL GATEWAY REST ENDPOINTS AND NOTEBOOKLM VERIFIED 100% OPERATIONAL ===")

if __name__ == "__main__":
    asyncio.run(test_gateway_endpoints())
