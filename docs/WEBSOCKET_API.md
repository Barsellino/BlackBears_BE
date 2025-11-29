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

### 3a. Next Round Created (з force_reload)

Відправляється після створення нового раунду через `POST /tournaments/{id}/next-round` або `POST /tournaments/{id}/start-finals`. 

**Важливо:** Повідомлення відправляється **всім підключеним користувачам** (не тільки учасникам турніру) для оновлення UI. Фронтенд має перевірити, чи користувач є учасником турніру, і якщо так - показати пушап/сповіщення.

**Фронтенд повинен перезавантажити таб/сторінку** для відображення нового раунду.

```json
{
  "type": "next_round_created",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "round_number": 3,
  "is_final": false,
  "round_name": "Round 3",
  "force_reload": true,
  "show_notification": false,  // ← НОВЕ ПОЛЕ: завжди false, фронтенд сам вирішить чи показувати пушап
  "priority": "high",
  "requires_action": true,
  "sound": "round_start",
  "title": "⚔️ Round 3 Created!",
  "message": "Round 3 of tournament 'Summer Cup' has been created. The page will reload to show the new round.",
  "action_text": "Add lobby maker as friend",
  "icon": "⚔️",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Для фіналів:**
```json
{
  "type": "next_round_created",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "round_number": 6,
  "is_final": true,
  "round_name": "Final 1",
  "force_reload": true,
  "show_notification": false,  // ← НОВЕ ПОЛЕ: завжди false, фронтенд сам вирішить чи показувати пушап
  "priority": "high",
  "requires_action": true,
  "sound": "round_start",
  "title": "🏆 Final 1 Created!",
  "message": "Final 1 of tournament 'Summer Cup' has been created. The page will reload to show the new round.",
  "action_text": "Add lobby maker as friend",
  "icon": "🏆",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Обробка на фронтенді:**
1. Отримати повідомлення `next_round_created`
2. Перевірити, чи користувач є учасником турніру (`tournament_id`)
3. Якщо так - показати пушап/сповіщення з `title` та `message`
4. Якщо ні - тільки оновити UI (перезавантажити таб якщо `force_reload: true`)

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

### 5. Tournament Finished (з force_reload)

Відправляється після завершення турніру через `POST /tournaments/{id}/finish`. **Фронтенд повинен перезавантажити таб/сторінку** для відображення фінальних результатів.

```json
{
  "type": "tournament_finished",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "force_reload": true,
  "priority": "high",
  "requires_action": false,
  "sound": "tournament_finished",
  "title": "✅ Tournament Finished",
  "message": "Tournament 'Summer Cup' has finished. The page will reload to show the final results.",
  "icon": "✅",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

### 6. Game Result Updated

Відправляється при встановленні, зміні або очищенні позиції учасника в грі.

```json
{
  "type": "game_result_updated",
  "tournament_id": 39,
  "game_id": 123,
  "round_number": 2,
  "is_final": false,
  "updated_participant": {
    "id": 456,                    // ID GameParticipant (не participant_id з tournament_participants!)
    "participant_id": 789,        // ID з tournament_participants
    "user_id": 101,               // ID користувача
    "battletag": "Player#1234",   // Для відображення
    "position": [1, 2],           // Масив позицій (або null якщо очищено)
    "calculated_points": 8.2,     // Розраховані очки (або null)
    "is_lobby_maker": false
  },
  "game_status": "active",        // 'pending' | 'active' | 'completed'
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Приклад з очищеною позицією:**
```json
{
  "type": "game_result_updated",
  "tournament_id": 39,
  "game_id": 123,
  "round_number": 2,
  "is_final": false,
  "updated_participant": {
    "id": 456,
    "participant_id": 789,
    "user_id": 101,
    "battletag": "Player#1234",
    "position": null,             // Очищено
    "calculated_points": null,
    "is_lobby_maker": false
  },
  "game_status": "active",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

### 7. Game Completed

Відправляється при завершенні гри (всі позиції встановлені, гра переходить у статус completed).

```json
{
  "type": "game_completed",
  "tournament_id": 39,
  "game_id": 123,
  "round_number": 2,
  "is_final": false,
  "timestamp": "2025-11-28T10:30:00Z"
}
```

### 8. Position Updated (Leaderboard)

Відправляється при оновленні загальних очок учасника в турнірі (після збереження результатів гри).

```json
{
  "type": "position_updated",
  "tournament_id": 39,
  "participant_id": 789,          // ID з tournament_participants
  "user_id": 101,                 // ID користувача
  "total_score": 24.5,            // Новий загальний рахунок
  "final_position": null,         // Фінальна позиція (якщо є)
  "timestamp": "2025-11-28T10:30:00Z"
}
```

### 9. Lobby Maker Assigned

Відправляється при призначенні лоббі мейкера для гри (після успішного збереження в БД).

```json
{
  "type": "lobby_maker_assigned",
  "tournament_id": 39,
  "game_id": 123,
  "round_number": 2,
  "lobby_maker_id": 101,              // ID користувача (user_id)
  "lobby_maker_participant_id": 456,  // ID з game_participants (для оновлення is_lobby_maker)
  "lobby_maker_battletag": "Player#1234",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Обробка на фронтенді:**
- Оновити `game.lobby_maker_id`
- Оновити `participant.is_lobby_maker` для participant з `lobby_maker_participant_id`
- Показати бейдж "LM" біля імені participant

### 10. Lobby Maker Removed

Відправляється при видаленні лоббі мейкера з гри (після успішного видалення в БД).

```json
{
  "type": "lobby_maker_removed",
  "tournament_id": 39,
  "game_id": 123,
  "round_number": 2,
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Обробка на фронтенді:**
- Оновити `game.lobby_maker_id` на `null`
- Оновити `participant.is_lobby_maker` на `false` для всіх participant в грі
- Прибрати бейдж "LM" біля імені participant

### 11. Error

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

### 12. Ping/Pong (heartbeat)

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
      case 'next_round_created':
        console.log('Next round created:', data.round_name);
        // Перезавантажити таб/сторінку якщо force_reload === true
        if (data.force_reload) {
          window.location.reload(); // або router.navigate() для SPA
        }
        break;
      case 'finals_started':
        console.log('Finals started!');
        // Оновити UI
        break;
      case 'tournament_finished':
        console.log('Tournament finished!');
        // Перезавантажити таб/сторінку якщо force_reload === true
        if (data.force_reload) {
          window.location.reload(); // або router.navigate() для SPA
        }
        break;
      case 'game_result_updated':
        console.log('Game result updated:', data);
        // Оновити конкретний рядок у таблиці гри
        // data.updated_participant.id - ID з game_participants
        // data.updated_participant.participant_id - ID з tournament_participants
        break;
      case 'game_completed':
        console.log('Game completed:', data.game_id);
        // Оновити статус гри на "completed"
        break;
      case 'position_updated':
        console.log('Position updated:', data);
        // Оновити лідерборд (загальні очки)
        // data.participant_id - ID з tournament_participants
        break;
      case 'lobby_maker_assigned':
        console.log('Lobby maker assigned:', data);
        // Оновити game.lobby_maker_id та participant.is_lobby_maker
        // data.lobby_maker_participant_id - ID з game_participants
        // Показати бейдж "LM"
        break;
      case 'lobby_maker_removed':
        console.log('Lobby maker removed:', data);
        // Оновити game.lobby_maker_id на null
        // Прибрати бейдж "LM" для всіх participant в грі
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

## Послідовність подій при оновленні результатів

**Приклад:** Користувач встановлює позицію [1, 2] для participant_id=789 у game_id=123:

1. **game_result_updated** - оновлення позиції в грі:
```json
{
  "type": "game_result_updated",
  "tournament_id": 39,
  "game_id": 123,
  "updated_participant": {
    "id": 456,
    "participant_id": 789,
    "position": [1, 2],
    "calculated_points": 8.2
  }
}
```

2. **position_updated** - оновлення загальних очок (після перерахунку):
```json
{
  "type": "position_updated",
  "tournament_id": 39,
  "participant_id": 789,
  "total_score": 24.5
}
```

3. **game_completed** - якщо всі позиції встановлені:
```json
{
  "type": "game_completed",
  "tournament_id": 39,
  "game_id": 123
}
```

## Примітки

1. **Універсальне підключення:** Один WebSocket підключення на користувача. Отримує сповіщення про всі турніри, де користувач є учасником
2. **Автоматичне перепідключення:** Рекомендується реалізувати на фронтенді з експоненційною затримкою
3. **Heartbeat:** Клієнт повинен відповідати на ping або відправляти власний ping кожні 30 секунд
4. **Обробка помилок:** Завжди перевіряйте `type: "error"` перед обробкою інших повідомлень
5. **Таймаути:** При відсутності активності більше 60 секунд з'єднання може бути розірвано
6. **Фільтрація повідомлень:** 
   - Повідомлення про старт турніру/раунду (`tournament_started`, `round_started`, `finals_started`, `tournament_finished`) відправляються тільки учасникам турніру
   - **`next_round_created`** відправляється **всім підключеним користувачам** (для оновлення UI), але пушап/сповіщення має показуватися тільки учасникам (фронтенд перевіряє участь)
   - Оновлення результатів гри (`game_result_updated`, `game_completed`, `position_updated`) відправляються **всім підключеним користувачам**, незалежно від участі в турнірі
   - Оновлення лоббі мейкера (`lobby_maker_assigned`, `lobby_maker_removed`) відправляються **всім підключеним користувачам**, незалежно від участі в турнірі
7. **Перезавантаження табів:**
   - Повідомлення `next_round_created` та `tournament_finished` містять поле `force_reload: true`
   - Фронтенд повинен перезавантажити таб/сторінку при отриманні таких повідомлень для відображення нових даних
7. **Реалтайм оновлення:** Повідомлення `game_result_updated`, `game_completed`, `position_updated` відправляються синхронно зі збереженням в БД, дозволяючи оновлювати UI без перезавантаження
8. **Ідентифікація:** 
   - `id` в `updated_participant` - це ID з `game_participants` (для оновлення конкретного рядка в таблиці гри)
   - `participant_id` - це ID з `tournament_participants` (для оновлення лідерборду)

