# Зміни в next_round_created повідомленні

## Що змінилося

### 1. Аудиторія отримувачів

**ДО:**
- Повідомлення відправлялося **тільки учасникам турніру** через `broadcast_to_tournament()`

**ПІСЛЯ:**
- Повідомлення відправляється **всім підключеним користувачам** через `broadcast_to_all()`
- Це дозволяє всім бачити оновлення UI (наприклад, якщо користувач переглядає турнір, але не зареєстрований)

### 2. Нове поле `show_notification`

**Додано поле:**
```json
{
  "show_notification": false  // Завжди false
}
```

**Призначення:**
- Завжди `false` в повідомленні від бекенду
- Фронтенд сам вирішує, чи показувати пушап/сповіщення, перевіривши чи користувач є учасником турніру

### 3. Структура повідомлення (оновлена)

```json
{
  "type": "next_round_created",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "round_number": 3,
  "is_final": false,
  "round_name": "Round 3",
  "force_reload": true,
  "show_notification": false,  // ← НОВЕ ПОЛЕ
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

## Що потрібно зробити на фронтенді

### 1. Обробка повідомлення

```typescript
handleMessage(data: any) {
  if (data.type === 'next_round_created') {
    // 1. Перевірити, чи користувач є учасником турніру
    const isParticipant = this.checkIfUserIsParticipant(data.tournament_id);
    
    // 2. Оновити UI (всі отримують це повідомлення)
    if (data.force_reload) {
      this.reloadTournamentTab(data.tournament_id, data.round_number);
    }
    
    // 3. Показати пушап/сповіщення ТІЛЬКИ якщо користувач є учасником
    if (isParticipant) {
      this.showNotification({
        title: data.title,
        message: data.message,
        icon: data.icon,
        sound: data.sound,
        priority: data.priority
      });
    }
  }
}
```

### 2. Перевірка участі в турнірі

**Варіант 1: Перевірка через стан додатку**
```typescript
checkIfUserIsParticipant(tournamentId: number): boolean {
  // Перевірити в локальному стані/кеші
  const tournament = this.tournamentService.getTournament(tournamentId);
  return tournament?.my_status !== null && tournament?.my_status !== undefined;
}
```

**Варіант 2: Перевірка через API**
```typescript
async checkIfUserIsParticipant(tournamentId: number): Promise<boolean> {
  try {
    const tournament = await this.tournamentService.getTournament(tournamentId).toPromise();
    return tournament.my_status !== null;
  } catch (error) {
    return false;
  }
}
```

**Варіант 3: Перевірка через список учасників**
```typescript
async checkIfUserIsParticipant(tournamentId: number): Promise<boolean> {
  const currentUser = this.authService.getCurrentUser();
  if (!currentUser) return false;
  
  const participants = await this.tournamentService.getParticipants(tournamentId).toPromise();
  return participants.some(p => p.user_id === currentUser.id);
}
```

### 3. Приклад повної реалізації

```typescript
// tournament-websocket.service.ts
handleMessage(data: any) {
  switch(data.type) {
    case 'next_round_created':
      this.handleNextRoundCreated(data);
      break;
    // ... інші типи
  }
}

private async handleNextRoundCreated(data: any) {
  // 1. Оновити UI (всі отримують)
  if (data.force_reload) {
    await this.tournamentService.refreshTournament(data.tournament_id);
    this.router.navigate(
      ['/tournaments', data.tournament_id],
      { 
        queryParams: { 
          tab: 'rounds',
          round: data.round_number 
        },
        replaceUrl: true 
      }
    );
  }
  
  // 2. Перевірити участь і показати пушап
  const isParticipant = await this.checkIfUserIsParticipant(data.tournament_id);
  
  if (isParticipant) {
    // Показати пушап/сповіщення тільки учасникам
    this.notificationService.show({
      title: data.title,
      message: data.message,
      icon: data.icon,
      type: 'info',
      duration: 3000,
      sound: data.sound
    });
  } else {
    // Не показувати пушап, але UI вже оновлено
    console.log(`[TournamentRounds] Round ${data.round_number} created (not a participant, UI updated)`);
  }
}

private async checkIfUserIsParticipant(tournamentId: number): Promise<boolean> {
  try {
    const tournament = await this.tournamentService.getTournament(tournamentId).toPromise();
    // my_status буде null/undefined якщо не учасник
    return tournament.my_status !== null && tournament.my_status !== undefined;
  } catch (error) {
    console.error('Error checking participant status:', error);
    return false;
  }
}
```

## Переваги змін

1. **Всі бачать оновлення UI** - навіть якщо не зареєстровані, можуть бачити новий раунд
2. **Пушап тільки для учасників** - не засмічує сповіщеннями тих, хто не бере участі
3. **Гнучкість** - фронтенд сам вирішує, коли показувати пушап

## Важливо

- Поле `show_notification` завжди `false` в повідомленні від бекенду
- Фронтенд **обов'язково** має перевірити участь користувача перед показом пушапу
- Всі отримують повідомлення для оновлення UI, але пушап показується тільки учасникам

## Тестування

1. **Як учасник:**
   - Отримає повідомлення
   - UI оновиться
   - Пушап покажеться

2. **Як неучасник:**
   - Отримає повідомлення
   - UI оновиться (якщо переглядає турнір)
   - Пушап НЕ покажеться

