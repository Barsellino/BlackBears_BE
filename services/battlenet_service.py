import httpx
from urllib.parse import urlencode
from typing import Optional
from core.config import settings
from schemas.auth import BattlenetUserInfo


class BattlenetService:
    def __init__(self):
        self.client_id = settings.battlenet_client_id
        self.client_secret = settings.battlenet_client_secret
        self.redirect_uri = settings.battlenet_redirect_uri
        self.auth_url = settings.battlenet_auth_url
        self.token_url = settings.battlenet_token_url
        self.user_info_url = settings.battlenet_user_info_url

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid",
        }
        if state:
            params["state"] = state
        
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            }
            
            print(f"Token request data: {data}")
            print(f"Token URL: {self.token_url}")
            
            response = await client.post(self.token_url, data=data)
            print(f"Token response status: {response.status_code}")
            print(f"Token response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            return None

    async def get_user_info(self, access_token: str) -> Optional[BattlenetUserInfo]:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(self.user_info_url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                return BattlenetUserInfo(
                    id=str(user_data.get("id")),
                    battletag=user_data.get("battletag", ""),
                    email=None  # Battle.net не надає email через OAuth
                )
            return None

    async def get_battlegrounds_rating(self, access_token: str, account_id: str) -> Optional[int]:
        """Get Hearthstone Battlegrounds rating (mock implementation)"""
        # Note: Real Hearthstone API requires additional setup and may not have current BG ratings
        # This is a mock implementation that returns a random rating for demo
        import random
        
        # In real implementation, you would call:
        # https://us.api.blizzard.com/hearthstone/account/{account_id}/collections
        # But this requires hs.collections scope and proper game data API setup
        
        # For now, return a mock rating between 4000-8000 MMR
        mock_rating = random.randint(4000, 8000)
        print(f"Mock Battlegrounds rating for {account_id}: {mock_rating}")
        return mock_rating


battlenet_service = BattlenetService()