# Пояснення змін на бекенді: WebSocket повідомлення для перезавантаження табів

## Що було зроблено

Додано функціонал автоматичного перезавантаження табів на фронтенді через WebSocket повідомлення з полем `force_reload: true` при створенні нового раунду або завершенні турніру.

## Зміни в коді

### 1. Нова функція `notify_next_round_created()` 

**Файл:** `services/notification_service.py`

**Що робить:**
- Відправляє WebSocket повідомлення всім учасникам турніру після створення нового раунду
- Містить поле `force_reload: true` для вказівки фронтенду про необхідність перезавантаження
- Працює для звичайних раундів та фіналів

**Ключові особливості:**
```python
message = {
    "type": "next_round_created",
    "tournament_id": tournament_id,
    "round_number": round_number,
    "is_final": is_final,
    "round_name": round_name,
    "force_reload": True,  # ← Ключове поле!
    "priority": "high",
    "requires_action": True,
    "sound": "round_start",
    "title": f"{icon} {round_display} Created!",
    "message": f"{round_display} of tournament '{tournament.name}' has been created. The page will reload to show the new round.",
    "action_text": "Add lobby maker as friend",
    "icon": icon,
    "timestamp": datetime.utcnow().isoformat() + "Z"
}
```

### 2. Оновлена функція `notify_tournament_finished()`

**Файл:** `services/notification_service.py`

**Що змінилося:**
- Додано поле `force_reload: true`
- Змінено `priority` з `"medium"` на `"high"`
- Додано `timestamp`

**До:**
```python
message = {
    "type": "tournament_finished",
    "priority": "medium",  # ← Було
    # force_reload відсутнє
}
```

**Після:**
```python
message = {
    "type": "tournament_finished",
    "force_reload": True,  # ← Додано
    "priority": "high",     # ← Змінено
    "timestamp": datetime.utcnow().isoformat() + "Z"  # ← Додано
}
```

### 3. Оновлені ендпоінти в `tournaments.py`

#### 3.1. `create_next_round_endpoint`

**Що змінилося:**
- Замінено виклик `notify_round_started` на `notify_next_round_created`
- Використовується правильна асинхронна відправка через `send_websocket_notification_async()`

**До:**
```python
from services.notification_service import notify_round_started
import asyncio
asyncio.create_task(notify_round_started(...))  # ← Може не працювати в синхронному контексті
```

**Після:**
```python
from services.notification_service import notify_next_round_created
from services.games_service import send_websocket_notification_async
send_websocket_notification_async(
    notify_next_round_created,
    tournament_id=tournament_id,
    round_number=next_round.round_number,
    is_final=is_final,
    final_round_number=final_round_number,
    db=None
)  # ← Правильна асинхронна відправка через threading
```

#### 3.2. `start_finals_endpoint`

**Що змінилося:**
- Додано виклик `notify_next_round_created` для перезавантаження табу
- Залишено `notify_finals_started` для сповіщення фіналістів
- Використовується правильна асинхронна відправка

**Після:**
```python
# Відправляємо повідомлення про створення раунду (з force_reload)
send_websocket_notification_async(
    notify_next_round_created,
    tournament_id=tournament_id,
    round_number=first_final_round_number,
    is_final=True,
    final_round_number=1,
    db=None
)

# Також відправляємо сповіщення фіналістам
send_websocket_notification_async(
    notify_finals_started,
    tournament_id=tournament_id,
    current_round=first_final_round_number,
    finalists_count=len(top_participants),
    db=None
)
```

#### 3.3. `finish_tournament_endpoint`

**Що змінилося:**
- Замінено `asyncio.create_task()` на `send_websocket_notification_async()`
- Тепер використовується правильна асинхронна відправка

**До:**
```python
import asyncio
asyncio.create_task(notify_tournament_finished(tournament_id))  # ← Може не працювати
```

**Після:**
```python
from services.games_service import send_websocket_notification_async
send_websocket_notification_async(
    notify_tournament_finished,
    tournament_id=tournament_id,
    db=None
)  # ← Правильна асинхронна відправка
```

### 4. Використання `send_websocket_notification_async()`

**Файл:** `services/games_service.py`

**Що це:**
- Helper-функція для асинхронного виклику WebSocket повідомлень з синхронного контексту
- Використовує `threading.Thread` та `asyncio.run()` для правильного виконання асинхронного коду

**Чому це важливо:**
- `asyncio.create_task()` не працює, якщо викликається з синхронного контексту (наприклад, з FastAPI endpoint)
- `threading.Thread` + `asyncio.run()` створює новий event loop в окремому потоці
- Це дозволяє виконувати асинхронні WebSocket операції без блокування основного потоку

**Реалізація:**
```python
def send_websocket_notification_async(notification_func, **kwargs):
    """Helper функція для асинхронного виклику WebSocket повідомлень"""
    import threading
    import asyncio
    
    def _send_async():
        """Асинхронна відправка WebSocket повідомлення"""
        try:
            asyncio.run(notification_func(**kwargs))
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
    
    # Запускаємо в окремому потоці
    thread = threading.Thread(target=_send_async, daemon=True)
    thread.start()
```

## Послідовність подій

### При створенні нового раунду:

1. **Користувач викликає API:**
   ```
   POST /tournaments/{id}/next-round
   ```

2. **Бекенд створює раунд:**
   - Створюється новий `TournamentRound` в БД
   - Створюються ігри для раунду
   - Оновлюється `tournament.current_round`

3. **Бекенд відправляє WebSocket повідомлення:**
   - Викликається `notify_next_round_created()`
   - Повідомлення містить `force_reload: true`
   - Відправляється всім учасникам турніру

4. **Фронтенд отримує повідомлення:**
   - Перевіряє `force_reload === true`
   - Оновлює дані через API
   - Перезавантажує таб/сторінку
   - Переключається на новий раунд

### При завершенні турніру:

1. **Користувач викликає API:**
   ```
   POST /tournaments/{id}/finish
   ```

2. **Бекенд завершує турнір:**
   - Оновлюється `tournament.status = FINISHED`
   - Розраховуються фінальні позиції
   - Визначаються переможці

3. **Бекенд відправляє WebSocket повідомлення:**
   - Викликається `notify_tournament_finished()`
   - Повідомлення містить `force_reload: true`
   - Відправляється всім учасникам турніру

4. **Фронтенд отримує повідомлення:**
   - Перевіряє `force_reload === true`
   - Оновлює дані через API
   - Перезавантажує таб/сторінку
   - Показує фінальні результати

## Технічні деталі

### Асинхронна відправка

**Проблема:**
- FastAPI endpoints можуть бути синхронними або асинхронними
- WebSocket операції асинхронні
- `asyncio.create_task()` не працює, якщо викликається з синхронного контексту

**Рішення:**
- Використання `threading.Thread` для створення окремого потоку
- Використання `asyncio.run()` для створення нового event loop в цьому потоці
- Це дозволяє виконувати асинхронні операції без блокування основного потоку

### Відправка повідомлень

**Кому відправляються:**
- `next_round_created` - всім учасникам турніру (через `broadcast_to_tournament`)
- `tournament_finished` - всім учасникам турніру (через `broadcast_to_tournament`)

**Коли відправляються:**
- Після успішного збереження в БД
- Асинхронно (не блокує API запит)

### Структура повідомлень

**Обов'язкові поля:**
- `type` - тип повідомлення
- `tournament_id` - ID турніру
- `force_reload` - флаг для перезавантаження (завжди `true` для цих повідомлень)

**Додаткові поля:**
- `round_number` - номер раунду (для `next_round_created`)
- `is_final` - чи це фінальний раунд
- `round_name` - назва раунду (для відображення)
- `title`, `message`, `icon` - для показу повідомлення користувачу
- `timestamp` - час відправки

## Файли, які були змінені

1. **`services/notification_service.py`**
   - Додано функцію `notify_next_round_created()`
   - Оновлено функцію `notify_tournament_finished()`
   - Додано імпорт `datetime`

2. **`api/routers/tournaments.py`**
   - Оновлено `create_next_round_endpoint()` - використовує `notify_next_round_created`
   - Оновлено `start_finals_endpoint()` - додано виклик `notify_next_round_created`
   - Оновлено `finish_tournament_endpoint()` - використовує правильну асинхронну відправку

3. **`docs/WEBSOCKET_API.md`**
   - Додано документацію для `next_round_created`
   - Оновлено документацію для `tournament_finished`
   - Додано приклади обробки на фронтенді

4. **`docs/WEBSOCKET_TAB_RELOAD.md`** (новий файл)
   - Технічне завдання для бекенду

5. **`docs/FRONTEND_TAB_RELOAD_TASK.md`** (новий файл)
   - Технічне завдання для фронтенду

## Переваги реалізації

1. **Неблокуюча відправка:**
   - WebSocket повідомлення відправляються асинхронно
   - API запити не блокуються

2. **Надійність:**
   - Використання `threading.Thread` гарантує правильне виконання
   - Обробка помилок через try/except

3. **Гнучкість:**
   - Фронтенд може вирішити, як обробляти `force_reload`
   - Може використовувати повне перезавантаження або оновлення через API

4. **UX:**
   - Користувачі автоматично бачать нові раунди
   - Не потрібно вручну оновлювати сторінку

## Тестування

### Як перевірити:

1. **Створити раунд:**
   ```bash
   curl -X POST http://localhost:8000/tournaments/29/next-round \
     -H "Authorization: Bearer TOKEN"
   ```
   - Перевірити, що WebSocket повідомлення отримано
   - Перевірити, що `force_reload: true`

2. **Завершити турнір:**
   ```bash
   curl -X POST http://localhost:8000/tournaments/29/finish \
     -H "Authorization: Bearer TOKEN"
   ```
   - Перевірити, що WebSocket повідомлення отримано
   - Перевірити, що `force_reload: true`

### Очікуваний результат:

- WebSocket повідомлення відправляються всім учасникам турніру
- Повідомлення містять `force_reload: true`
- Фронтенд автоматично перезавантажує таб/сторінку
- Після перезавантаження відображаються нові дані

## Висновок

Реалізовано автоматичне перезавантаження табів через WebSocket повідомлення з полем `force_reload: true`. Це дозволяє користувачам автоматично бачити нові раунди та фінальні результати без необхідності вручну оновлювати сторінку.

