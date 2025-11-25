import pytest
from fastapi.testclient import TestClient
from main import app
from core.auth import create_access_token

client = TestClient(app)

def test_update_profile_telegram():
    # 1. Створюємо токен для тестового юзера (ID 1, якого ми вже знаємо)
    token = create_access_token(data={"sub": "1"})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Надсилаємо запит на оновлення телеграму
    new_telegram = "@updated_telegram_bot"
    response = client.put(
        "/auth/profile",
        json={"telegram": new_telegram},
        headers=headers
    )

    # 3. Перевіряємо відповідь
    assert response.status_code == 200
    data = response.json()
    assert data["telegram"] == new_telegram

    # 4. Перевіряємо, що інші поля не затерлися (наприклад, battletag)
    assert data["battletag"] == "ProGamer#1234"
    
    print("\n✅ Profile update test passed! Telegram updated successfully.")

if __name__ == "__main__":
    # Запускаємо тест вручну, якщо файл виконується як скрипт
    try:
        test_update_profile_telegram()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
