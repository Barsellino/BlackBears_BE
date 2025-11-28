# WebSocket API Documentation

## Підключення

```
ws://host/ws?token=JWT_TOKEN
```

**Універсальне підключення:** Один WebSocket підключення на користувача. Автоматично отримує сповіщення про всі турніри, де користувач є учасником.

## Авторизація

- **Токен обов'язковий** в query параметрі `token`
- При невалідному токені або помилці авторизації відправляється повідомлення про помилку перед закриттям
- Код закриття: `1008` (Policy Violation)

## Формат повідомлень

### 1. Connected (при підключенні)

```json
{
  "type": "connected",
  "user_id": 1,
  "user_battletag": "Player#1234",
  "tournaments_count": 3,
  "tournaments": [
    {
      "id": 29,
      "name": "Summer Cup",
      "status": "ACTIVE",
      "current_round": 2,
      "total_rounds": 5
    },
    {
      "id": 30,
      "name": "Winter Championship",
      "status": "REGISTRATION",
      "current_round": 0,
      "total_rounds": 3
    }
  ],
  "message": "Connected successfully. You will receive notifications for all your tournaments.",
  "timestamp": "2025-01-01T12:00:00Z",
  "heartbeat_interval": 30
}
```

### 2. Tournament Started

```json
{
  "type": "tournament_started",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "current_round": 1,
  "priority": "high",
  "requires_action": true,
  "sound": "tournament_start",
  "title": "🏆 Tournament Started!",
  "message": "Tournament 'Summer Cup' has started! Check your round and add the lobby maker as a friend in-game.",
  "action_text": "Add lobby maker as friend",
  "icon": "🏆"
}
```

### 3. Round Started

```json
{
  "type": "round_started",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "round_number": 2,
  "is_final": false,
  "round_name": "Round 2",
  "priority": "high",
  "requires_action": true,
  "sound": "round_start",
  "title": "⚔️ Round 2 Started!",
  "message": "Round 2 of tournament 'Summer Cup' has started! Check your game and add the lobby maker as a friend.",
  "action_text": "Add lobby maker as friend",
  "icon": "⚔️"
}
```

### 4. Finals Started

```json
{
  "type": "finals_started",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "current_round": 4,
  "finalists_count": 8,
  "priority": "high",
  "requires_action": true,
  "sound": "finals_start",
  "title": "🏆 Finals Started!",
  "message": "Finals of tournament 'Summer Cup' have started! Top 8 players are competing. Check your game and add the lobby maker as a friend.",
  "action_text": "Add lobby maker as friend",
  "icon": "🏆"
}
```

### 5. Tournament Finished

```json
{
  "type": "tournament_finished",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "priority": "medium",
  "requires_action": false,
  "sound": "tournament_finished",
  "title": "✅ Tournament Finished",
  "message": "Tournament 'Summer Cup' has finished. Check the results!",
  "icon": "✅"
}
```

### 6. Error

```json
{
  "type": "error",
  "error_type": "authentication_error" | "authorization_error" | "not_found" | "validation_error",
  "message": "Error description",
  "code": 1008,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

**Типи помилок:**
- `authentication_error` - невалідний токен, користувач не знайдений
- `authorization_error` - користувач неактивний, немає доступу
- `not_found` - турнір не знайдений
- `validation_error` - помилка валідації

### 7. Ping/Pong (heartbeat)

**Сервер → Клієнт (ping):**
```json
{
  "type": "ping",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

**Клієнт → Сервер (ping):**
```
ping
```
або
```json
{
  "type": "ping"
}
```

**Сервер → Клієнт (pong):**
```json
{
  "type": "pong",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Heartbeat та перепідключення

- **Інтервал heartbeat:** 30 секунд
- **Таймаут:** 60 секунд без відповіді
- **Автоматичний ping:** Сервер відправляє ping кожні 5 секунд якщо немає активності
- **Перепідключення:** Клієнт повинен реалізувати автоматичне перепідключення при розриві з'єднання

## Приклад використання (JavaScript)

```javascript
class TournamentWebSocket {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    const url = `ws://localhost:8000/ws?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.stopHeartbeat();
      
      // Автоматичне перепідключення
      if (event.code !== 1008 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }

  handleMessage(data) {
    switch(data.type) {
      case 'connected':
        console.log('Connected successfully!', data);
        console.log(`You are participating in ${data.tournaments_count} tournaments`);
        break;
      case 'tournament_started':
        console.log('Tournament started!');
        // Оновити UI
        break;
      case 'round_started':
        console.log('Round started:', data.round_name);
        // Оновити UI
        break;
      case 'finals_started':
        console.log('Finals started!');
        // Оновити UI
        break;
      case 'tournament_finished':
        console.log('Tournament finished!');
        // Оновити UI
        break;
      case 'ping':
        // Відповісти на ping
        this.ws.send(JSON.stringify({ type: 'pong' }));
        break;
      case 'pong':
        // Heartbeat отримано
        break;
      case 'error':
        console.error('WebSocket error:', data);
        // Обробити помилку
        break;
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000); // 30 секунд
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Використання
const ws = new TournamentWebSocket('your-jwt-token');
ws.connect();
```

## Примітки

1. **Універсальне підключення:** Один WebSocket підключення на користувача. Отримує сповіщення про всі турніри, де користувач є учасником
2. **Автоматичне перепідключення:** Рекомендується реалізувати на фронтенді з експоненційною затримкою
3. **Heartbeat:** Клієнт повинен відповідати на ping або відправляти власний ping кожні 30 секунд
4. **Обробка помилок:** Завжди перевіряйте `type: "error"` перед обробкою інших повідомлень
5. **Таймаути:** При відсутності активності більше 60 секунд з'єднання може бути розірвано
6. **Фільтрація повідомлень:** Повідомлення відправляються тільки учасникам турніру (автоматично фільтрується на бекенді)

