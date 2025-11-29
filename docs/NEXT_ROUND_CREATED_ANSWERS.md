# Відповіді на питання фронтенду про next_round_created

## ✅ 1. Чи відправляється повідомлення?

**ТАК!** Повідомлення відправляється в двох місцях:

1. **`POST /tournaments/{id}/next-round`** (рядок 597-608)
2. **`POST /tournaments/{id}/start-finals`** (рядок 748-757)

### Виклик:
```python
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
**ТАК!** Використовується `websocket_manager.broadcast_to_tournament()`

---

## ✅ 2. Структура повідомлення

**Всі обов'язкові поля присутні!**

```json
{
  "type": "next_round_created",           // ✅ ОБОВ'ЯЗКОВО
  "tournament_id": 39,                    // ✅ ОБОВ'ЯЗКОВО
  "round_number": 3,                     // ✅ ОБОВ'ЯЗКОВО
  "is_final": false,                     // ✅ Присутнє
  "force_reload": true,                  // ✅ ОБОВ'ЯЗКОВО (завжди true)
  "timestamp": "2025-11-28T10:30:00Z"   // ✅ ОБОВ'ЯЗКОВО
}
```

**Додаткові поля (для UI):**
- `tournament_name` - назва турніру
- `round_name` - назва раунду ("Round 3" або "Final 1")
- `title`, `message`, `icon` - для показу повідомлення
- `priority`, `requires_action`, `sound` - для стилізації

---

## ✅ 3. Коли саме відправляється?

**Послідовність:**

1. ✅ Валідація турніру та користувача
2. ✅ Створення раунду в БД: `manager.create_next_round(db)`
3. ✅ Оновлення `tournament.current_round` (всередині `create_next_round`)
4. ✅ Логування дії
5. ✅ **Відправка WebSocket повідомлення** ← ТУТ
6. ✅ Повернення відповіді API

**Висновок:** Повідомлення відправляється **ПІСЛЯ** створення раунду та оновлення `current_round`.

---

## 4. Перевірка на фронтенді

### Що шукати в консолі браузера (F12):

```javascript
// 1. Чи приходить повідомлення?
[TournamentRounds] handleWebSocketMessage: {...}

// 2. Чи обробляється?
[TournamentRounds] next_round_created received: {...}
```

### Якщо немає логів:

1. **Перевірте WebSocket підключення:**
   ```javascript
   ws.readyState  // Має бути 1 (OPEN)
   ```

2. **Перевірте, чи користувач є учасником турніру:**
   - `broadcast_to_tournament()` відправляє тільки учасникам
   - Перевірте в БД або через API

3. **Перевірте логи бекенду:**
   - Шукайте: `[NOTIFY] Starting next_round_created`
   - Шукайте: `[WS] Broadcasting to tournament`

---

## ✅ 5. Що перевірено на бекенді

### ✅ Виклик функції:
- Викликається в `create_next_round_endpoint()` (рядок 602)
- Викликається в `start_finals_endpoint()` (рядок 751)

### ✅ Параметри:
```python
tournament_id=tournament_id,           # ✅ Правильно
round_number=next_round.round_number,  # ✅ Правильно (номер нового раунду)
is_final=is_final,                     # ✅ Правильно
final_round_number=final_round_number, # ✅ Правильно (для фіналів)
db=None                                 # ✅ Правильно
```

### ✅ Асинхронна відправка:
- Використовується `send_websocket_notification_async()`
- Правильна реалізація через `threading.Thread` + `asyncio.run()`

### ✅ Логування:
Додано детальне логування:
- `[NOTIFY] Starting next_round_created...`
- `[NOTIFY] Message prepared: ...`
- `[NOTIFY] Sent next_round_created notification...`
- `[WS] Broadcasting to tournament...`
- `[WS] Sent to X/Y connected participants...`

---

## 6. Тестовий запит

### ✅ Створено тестовий ендпоінт:

**URL:** `POST /tournaments/{tournament_id}/test-next-round-notification`

**Параметри:**
- `round_number` (query, default: 3) - номер раунду для тесту
- `is_final` (query, default: false) - чи це фінальний раунд

**Приклад:**
```bash
curl -X POST "http://localhost:8000/tournaments/39/test-next-round-notification?round_number=3&is_final=false" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Відповідь:**
```json
{
  "message": "Test notification sent",
  "tournament_id": 39,
  "round_number": 3,
  "is_final": false,
  "force_reload": true
}
```

**Використання:**
- Відправляє тестове повідомлення без створення раунду
- Дозволяє перевірити, чи приходить повідомлення на фронтенд
- Потрібні права: учасник турніру або адмін

---

## 7. Альтернатива

### ❌ НЕ рекомендується використовувати `round_started` з `force_reload`

**Причина:**
- `round_started` відправляється при **старті раунду** (коли гра починається)
- `next_round_created` відправляється при **створенні раунду** (коли раунд створюється, але гра ще не почалася)

**Рекомендація:** Використовувати `next_round_created` з `force_reload: true` - це правильний підхід.

---

## Діагностика проблем

### Якщо повідомлення не приходить:

1. **Перевірте логи бекенду:**
   ```
   [NOTIFY] Starting next_round_created for tournament 39, round 3
   [NOTIFY] Message prepared: type=next_round_created, tournament_id=39, round_number=3, force_reload=True
   [WS] Broadcasting to tournament 39: 8 participants, message type: next_round_created
   [WS] Sent to 3/8 connected participants for tournament 39
   ```

2. **Перевірте WebSocket підключення:**
   - Чи підключений користувач?
   - Чи є помилки в консолі браузера?

3. **Перевірте участь в турнірі:**
   - `broadcast_to_tournament()` відправляє тільки учасникам
   - Перевірте: `SELECT * FROM tournament_participants WHERE tournament_id = 39 AND user_id = ?`

4. **Використайте тестовий ендпоінт:**
   ```bash
   POST /tournaments/39/test-next-round-notification?round_number=3
   ```

---

## Висновок

✅ **Всі обов'язкові поля присутні**
✅ **Повідомлення відправляється після створення раунду**
✅ **Використовується правильна асинхронна відправка**
✅ **Структура повідомлення відповідає вимогам**
✅ **Додано детальне логування для діагностики**
✅ **Створено тестовий ендпоінт для перевірки**

**Якщо повідомлення все ще не приходить:**
1. Використайте тестовий ендпоінт для перевірки
2. Перевірте логи бекенду на помилки
3. Перевірте WebSocket підключення на фронтенді
4. Перевірте, чи користувач є учасником турніру

