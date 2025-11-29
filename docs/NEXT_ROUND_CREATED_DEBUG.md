# Відповіді на питання про next_round_created

## 1. Чи відправляється повідомлення?

**✅ ТАК, відправляється!**

### Де викликається:
- **Файл:** `api/routers/tournaments.py`
- **Функція:** `create_next_round_endpoint()` (рядок 597-608)
- **Функція:** `start_finals_endpoint()` (рядок 748-757)

### Код виклику:
```python
# Send WebSocket notification (with force_reload)
from services.notification_service import notify_next_round_created
from services.games_service import send_websocket_notification_async
final_round_number = next_round.round_number - tournament.regular_rounds if is_final else None
send_websocket_notification_async(
    notify_next_round_created,
    tournament_id=tournament_id,
    round_number=next_round.round_number,
    is_final=is_final,
    final_round_number=final_round_number,
    db=None
)
```

### Чи відправляється через WebSocket?
**✅ ТАК!** Використовується `websocket_manager.broadcast_to_tournament()` (рядок 194 в `notification_service.py`)

---

## 2. Структура повідомлення

**✅ Всі обов'язкові поля присутні!**

### Реальна структура, що відправляється:
```json
{
  "type": "next_round_created",           // ✅ ОБОВ'ЯЗКОВО
  "tournament_id": 39,                    // ✅ ОБОВ'ЯЗКОВО
  "tournament_name": "Summer Cup",       // Додатково
  "round_number": 3,                     // ✅ ОБОВ'ЯЗКОВО
  "is_final": false,                     // ✅ Присутнє
  "round_name": "Round 3",                // Додатково
  "force_reload": true,                  // ✅ ОБОВ'ЯЗКОВО (завжди true)
  "priority": "high",                    // Додатково
  "requires_action": true,               // Додатково
  "sound": "round_start",                // Додатково
  "title": "⚔️ Round 3 Created!",        // Додатково
  "message": "Round 3 of tournament 'Summer Cup' has been created. The page will reload to show the new round.",
  "action_text": "Add lobby maker as friend",
  "icon": "⚔️",
  "timestamp": "2025-11-28T10:30:00Z"   // ✅ ОБОВ'ЯЗКОВО
}
```

### Порівняння з вимогами фронтенду:
| Поле | Вимога | Статус | Примітка |
|------|--------|--------|----------|
| `type` | Обов'язково | ✅ | "next_round_created" |
| `tournament_id` | Обов'язково | ✅ | ID турніру |
| `round_number` | Обов'язково | ✅ | Номер нового раунду |
| `is_final` | Опціонально | ✅ | Присутнє |
| `force_reload` | Обов'язково (true) | ✅ | Завжди `true` |
| `timestamp` | Обов'язково | ✅ | ISO формат з Z |

**Висновок:** ✅ Всі обов'язкові поля присутні!

---

## 3. Коли саме відправляється?

### Послідовність подій:

1. **Користувач викликає API:**
   ```
   POST /tournaments/{id}/next-round
   ```

2. **Бекенд виконує:**
   - Валідація турніру та користувача
   - Створення раунду в БД: `manager.create_next_round(db)`
   - Оновлення `tournament.current_round` (всередині `create_next_round`)
   - Логування дії: `log_tournament_action()`
   - **Відправка WebSocket повідомлення:** `notify_next_round_created()`
   - Повернення відповіді

### Відправка відбувається:
- ✅ **Після** створення раунду в БД
- ✅ **Після** успішного виконання `create_next_round()`
- ✅ **Після** оновлення `tournament.current_round`
- ✅ **Перед** поверненням відповіді API

### Код (рядки 571-615):
```python
@router.post("/{tournament_id}/next-round")
async def create_next_round_endpoint(...):
    try:
        # 1. Валідація
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(...)
        
        # 2. Створення раунду (тут оновлюється current_round)
        manager = TournamentManager(tournament)
        next_round = manager.create_next_round(db)  # ← current_round оновлюється тут
        
        # 3. Логування
        log_tournament_action(...)
        
        # 4. WebSocket повідомлення (ПІСЛЯ створення раунду)
        send_websocket_notification_async(
            notify_next_round_created,
            tournament_id=tournament_id,
            round_number=next_round.round_number,  # ← Номер нового раунду
            ...
        )
        
        # 5. Повернення відповіді
        return {...}
```

---

## 4. Перевірка на фронтенді

### Що перевірити в консолі браузера (F12):

1. **Чи приходить повідомлення?**
   ```javascript
   // Шукайте в логах:
   [TournamentRounds] handleWebSocketMessage: {...}
   ```

2. **Чи обробляється?**
   ```javascript
   // Шукайте в логах:
   [TournamentRounds] next_round_created received: {...}
   ```

3. **Якщо немає логів:**
   - Перевірте, чи підключений WebSocket
   - Перевірте, чи користувач є учасником турніру
   - Перевірте логи бекенду на помилки

### Додаткові перевірки:

1. **WebSocket підключення:**
   ```javascript
   // В консолі браузера:
   ws.readyState  // Має бути 1 (OPEN)
   ```

2. **Фільтрація повідомлень:**
   - Перевірте, чи не фільтрується повідомлення за `tournament_id`
   - Перевірте, чи обробляється `type: "next_round_created"`

---

## 5. Що перевірити на бекенді

### ✅ Перевірено:

1. **Чи викликається `notify_next_round_created()`?**
   - ✅ ТАК, викликається в `create_next_round_endpoint()` (рядок 602)
   - ✅ ТАК, викликається в `start_finals_endpoint()` (рядок 751)

2. **Чи правильно передаються параметри?**
   ```python
   send_websocket_notification_async(
       notify_next_round_created,
       tournament_id=tournament_id,           # ✅ Правильно
       round_number=next_round.round_number,  # ✅ Правильно (номер нового раунду)
       is_final=is_final,                     # ✅ Правильно
       final_round_number=final_round_number, # ✅ Правильно (для фіналів)
       db=None                                 # ✅ Правильно
   )
   ```

3. **Чи відправляється через `send_websocket_notification_async()`?**
   - ✅ ТАК, використовується правильна асинхронна відправка

4. **Чи є помилки в логах?**
   - Перевірте логи бекенду на помилки при відправці
   - Шукайте: `ERROR`, `Exception`, `Traceback`

### Логування на бекенді:

**Файл:** `services/notification_service.py` (рядок 195)
```python
logger.info(f"Sent next_round_created notification for tournament {tournament_id}, round {round_number}")
```

**Що шукати в логах:**
```
INFO - Sent next_round_created notification for tournament 39, round 3
```

**Якщо немає цього логу:**
- Функція не викликається
- Або є помилка до цього моменту

---

## 6. Тестовий запит

### Можна створити тестовий ендпоінт для перевірки:

**Додати в `api/routers/tournaments.py`:**
```python
@router.post("/{tournament_id}/test-next-round-notification")
async def test_next_round_notification(
    tournament_id: int,
    round_number: int = Query(3),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Тестовий ендпоінт для перевірки next_round_created повідомлення"""
    from services.notification_service import notify_next_round_created
    from services.games_service import send_websocket_notification_async
    
    send_websocket_notification_async(
        notify_next_round_created,
        tournament_id=tournament_id,
        round_number=round_number,
        is_final=False,
        final_round_number=None,
        db=None
    )
    
    return {
        "message": "Test notification sent",
        "tournament_id": tournament_id,
        "round_number": round_number
    }
```

### Використання:
```bash
curl -X POST "http://localhost:8000/tournaments/39/test-next-round-notification?round_number=3" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 7. Альтернатива

### Якщо `next_round_created` не працює:

Можна використати `round_started` з `force_reload`, але це **НЕ рекомендується**, бо:
- `round_started` відправляється при старті раунду (коли гра починається)
- `next_round_created` відправляється при створенні раунду (коли раунд створюється, але гра ще не почалася)

### Рекомендація:
Використовувати `next_round_created` з `force_reload: true` - це правильний підхід.

---

## Діагностика проблем

### Якщо повідомлення не приходить:

1. **Перевірте WebSocket підключення:**
   - Чи підключений користувач до WebSocket?
   - Чи є помилки в консолі браузера?

2. **Перевірте, чи користувач є учасником турніру:**
   - `broadcast_to_tournament()` відправляє тільки учасникам
   - Перевірте в БД: `SELECT * FROM tournament_participants WHERE tournament_id = 39 AND user_id = ?`

3. **Перевірте логи бекенду:**
   ```bash
   # Шукайте:
   INFO - Sent next_round_created notification for tournament 39, round 3
   ERROR - Error sending WebSocket notification: ...
   ```

4. **Перевірте, чи викликається функція:**
   - Додайте `print()` або `logger.info()` перед викликом
   - Перевірте, чи доходить виконання до цього коду

### Додаткове логування (для діагностики):

Можна додати в `services/notification_service.py`:
```python
async def notify_next_round_created(...):
    logger.info(f"NOTIFY: Starting next_round_created for tournament {tournament_id}, round {round_number}")
    
    # ... код ...
    
    logger.info(f"NOTIFY: Message prepared: {message}")
    await websocket_manager.broadcast_to_tournament(tournament_id, message, db)
    logger.info(f"NOTIFY: Message sent successfully")
```

---

## Висновок

✅ **Всі обов'язкові поля присутні**
✅ **Повідомлення відправляється після створення раунду**
✅ **Використовується правильна асинхронна відправка**
✅ **Структура повідомлення відповідає вимогам**

**Якщо повідомлення не приходить на фронтенд:**
1. Перевірте WebSocket підключення
2. Перевірте, чи користувач є учасником турніру
3. Перевірте логи бекенду на помилки
4. Використайте тестовий ендпоінт для перевірки

