# Короткий опис: Автоматичне перезавантаження табів

## Що було зроблено на бекенді

### 1. Додано нове WebSocket повідомлення `next_round_created`
- Відправляється після створення нового раунду
- Містить поле `force_reload: true` для вказівки фронтенду про перезавантаження
- Працює для звичайних раундів та фіналів

### 2. Оновлено повідомлення `tournament_finished`
- Додано поле `force_reload: true`
- Змінено `priority` на `"high"`

### 3. Виправлено асинхронну відправку
- Замінено `asyncio.create_task()` на `send_websocket_notification_async()`
- Використовується `threading.Thread` для правильного виконання асинхронного коду

## Що потрібно зробити на фронтенді

### 1. Обробити повідомлення `next_round_created`
```typescript
if (data.type === 'next_round_created' && data.force_reload) {
  // Оновити дані турніру
  // Перезавантажити таб/сторінку
  // Переключитися на новий раунд (data.round_number)
}
```

### 2. Обробити повідомлення `tournament_finished`
```typescript
if (data.type === 'tournament_finished' && data.force_reload) {
  // Оновити дані турніру
  // Перезавантажити таб/сторінку
  // Показати фінальні результати
}
```

### 3. Автоматичне перемикання раундів
- Після перезавантаження переключитися на раунд з `data.round_number`
- Прокрутити до активного табу (для горизонтального скролу)

## Структура повідомлень

### `next_round_created`
```json
{
  "type": "next_round_created",
  "tournament_id": 29,
  "round_number": 3,
  "is_final": false,
  "round_name": "Round 3",
  "force_reload": true,  // ← Ключове поле!
  "title": "⚔️ Round 3 Created!",
  "message": "...",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

### `tournament_finished`
```json
{
  "type": "tournament_finished",
  "tournament_id": 29,
  "force_reload": true,  // ← Ключове поле!
  "priority": "high",
  "title": "✅ Tournament Finished",
  "message": "...",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

## Детальна документація

- **Для фронтенду:** `docs/FRONTEND_TAB_RELOAD_TASK.md`
- **Для бекенду:** `docs/BACKEND_CHANGES_EXPLANATION.md`
- **WebSocket API:** `docs/WEBSOCKET_API.md`

