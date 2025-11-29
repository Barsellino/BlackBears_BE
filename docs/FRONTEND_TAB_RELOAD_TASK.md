# Технічне завдання: Автоматичне перезавантаження табів при створенні раундів та завершенні турніру

## Мета
Реалізувати автоматичне перезавантаження табу/сторінки з турніром при отриманні WebSocket повідомлень про створення нового раунду або завершення турніру.

## Контекст
Бекенд відправляє WebSocket повідомлення з полем `force_reload: true` коли:
1. Створюється новий раунд (`next_round_created`)
2. Завершується турнір (`tournament_finished`)

Фронтенд повинен автоматично перезавантажити таб/сторінку для відображення нових даних.

## Вимоги

### 1. Обробка WebSocket повідомлення `next_round_created`

**Коли відправляється:**
- Після створення нового раунду через `POST /tournaments/{id}/next-round`
- Після старту фіналів через `POST /tournaments/{id}/start-finals`

**Структура повідомлення:**
```json
{
  "type": "next_round_created",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "round_number": 3,
  "is_final": false,
  "round_name": "Round 3",
  "force_reload": true,              // ← Ключове поле!
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
  "round_number": 6,
  "is_final": true,
  "round_name": "Final 1",
  "force_reload": true,              // ← Ключове поле!
  ...
}
```

**Дії фронтенду:**
1. Перевірити `force_reload === true`
2. Опціонально: показати повідомлення користувачу (toast/notification)
3. Перезавантажити сторінку/таб з турніром
4. Після перезавантаження автоматично переключитися на новий раунд (якщо є таби раундів)

### 2. Обробка WebSocket повідомлення `tournament_finished`

**Коли відправляється:**
- Після завершення турніру через `POST /tournaments/{id}/finish`

**Структура повідомлення:**
```json
{
  "type": "tournament_finished",
  "tournament_id": 29,
  "tournament_name": "Summer Cup",
  "force_reload": true,              // ← Ключове поле!
  "priority": "high",
  "requires_action": false,
  "sound": "tournament_finished",
  "title": "✅ Tournament Finished",
  "message": "Tournament 'Summer Cup' has finished. The page will reload to show the final results.",
  "icon": "✅",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Дії фронтенду:**
1. Перевірити `force_reload === true`
2. Опціонально: показати повідомлення користувачу
3. Перезавантажити сторінку/таб з турніром
4. Після перезавантаження показати фінальні результати

## Реалізація

### Варіант 1: Повне перезавантаження сторінки (найпростіший)

```typescript
// В WebSocket handler
handleMessage(data: any) {
  switch(data.type) {
    case 'next_round_created':
      if (data.force_reload) {
        // Показати повідомлення (опціонально)
        this.showNotification(data.title, data.message);
        
        // Перезавантажити сторінку
        setTimeout(() => {
          window.location.reload();
        }, 1000); // Невелика затримка для показу повідомлення
      }
      break;
      
    case 'tournament_finished':
      if (data.force_reload) {
        this.showNotification(data.title, data.message);
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
      break;
  }
}
```

### Варіант 2: Перезавантаження через Router (для SPA)

```typescript
// В Angular/React/Vue компоненті
handleMessage(data: any) {
  switch(data.type) {
    case 'next_round_created':
      if (data.force_reload) {
        // Показати повідомлення
        this.notificationService.show(data.title, data.message);
        
        // Оновити дані через API
        this.tournamentService.getTournament(data.tournament_id)
          .subscribe(tournament => {
            // Оновити стан компонента
            this.tournament = tournament;
            
            // Переключитися на новий раунд
            if (data.round_number) {
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
          });
      }
      break;
      
    case 'tournament_finished':
      if (data.force_reload) {
        this.notificationService.show(data.title, data.message);
        
        // Оновити дані
        this.tournamentService.getTournament(data.tournament_id)
          .subscribe(tournament => {
            this.tournament = tournament;
            
            // Переключитися на таб з результатами
            this.router.navigate(
              ['/tournaments', data.tournament_id],
              { 
                queryParams: { tab: 'results' },
                replaceUrl: true 
              }
            );
          });
      }
      break;
  }
}
```

### Варіант 3: Гібридний підхід (рекомендований)

```typescript
// WebSocket service
class TournamentWebSocketService {
  
  handleMessage(data: any) {
    switch(data.type) {
      case 'next_round_created':
        if (data.force_reload) {
          this.handleForceReload(data, () => {
            // Після перезавантаження переключитися на новий раунд
            if (data.round_number) {
              this.navigateToRound(data.tournament_id, data.round_number);
            }
          });
        }
        break;
        
      case 'tournament_finished':
        if (data.force_reload) {
          this.handleForceReload(data, () => {
            // Після перезавантаження показати результати
            this.navigateToResults(data.tournament_id);
          });
        }
        break;
    }
  }
  
  private handleForceReload(data: any, callback?: () => void) {
    // Показати повідомлення
    this.notificationService.show({
      title: data.title,
      message: data.message,
      icon: data.icon,
      duration: 2000
    });
    
    // Перезавантажити дані
    this.tournamentService.refreshTournament(data.tournament_id)
      .subscribe(() => {
        // Викликати callback для навігації
        if (callback) {
          callback();
        }
      });
  }
  
  private navigateToRound(tournamentId: number, roundNumber: number) {
    this.router.navigate(
      ['/tournaments', tournamentId],
      { 
        queryParams: { 
          tab: 'rounds',
          round: roundNumber 
        },
        replaceUrl: true 
      }
    );
  }
  
  private navigateToResults(tournamentId: number) {
    this.router.navigate(
      ['/tournaments', tournamentId],
      { 
        queryParams: { tab: 'results' },
        replaceUrl: true 
      }
    );
  }
}
```

## Автоматичне перемикання раундів

### Після перезавантаження при `next_round_created`:

1. **Визначити поточний раунд:**
   - Використати `data.round_number` з повідомлення
   - Або отримати з оновлених даних турніру

2. **Переключити таб раундів:**
   ```typescript
   // Якщо є таби з раундами
   const roundTab = this.roundTabs.find(tab => tab.roundNumber === data.round_number);
   if (roundTab) {
     this.activeRoundTab = roundTab;
     this.scrollToActiveTab(); // Прокрутити до активного табу
   }
   ```

3. **Прокрутити до активного табу (для горизонтального скролу):**
   ```typescript
   scrollToActiveTab() {
     const activeTabElement = document.querySelector('.round-tab.active');
     if (activeTabElement) {
       activeTabElement.scrollIntoView({ 
         behavior: 'smooth', 
         block: 'nearest',
         inline: 'center' 
       });
     }
   }
   ```

## Приклад повної реалізації (Angular)

```typescript
// tournament-websocket.service.ts
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { TournamentService } from './tournament.service';
import { NotificationService } from './notification.service';

@Injectable({
  providedIn: 'root'
})
export class TournamentWebSocketService {
  
  constructor(
    private router: Router,
    private tournamentService: TournamentService,
    private notificationService: NotificationService
  ) {}
  
  handleMessage(data: any) {
    switch(data.type) {
      case 'next_round_created':
        this.handleNextRoundCreated(data);
        break;
        
      case 'tournament_finished':
        this.handleTournamentFinished(data);
        break;
        
      // ... інші типи повідомлень
    }
  }
  
  private handleNextRoundCreated(data: any) {
    if (!data.force_reload) return;
    
    // Показати повідомлення
    this.notificationService.show({
      title: data.title,
      message: data.message,
      icon: data.icon,
      type: 'info',
      duration: 2000
    });
    
    // Оновити дані турніру
    this.tournamentService.refreshTournament(data.tournament_id)
      .subscribe(tournament => {
        // Переключитися на новий раунд
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
      });
  }
  
  private handleTournamentFinished(data: any) {
    if (!data.force_reload) return;
    
    this.notificationService.show({
      title: data.title,
      message: data.message,
      icon: data.icon,
      type: 'success',
      duration: 3000
    });
    
    this.tournamentService.refreshTournament(data.tournament_id)
      .subscribe(() => {
        this.router.navigate(
          ['/tournaments', data.tournament_id],
          { 
            queryParams: { tab: 'results' },
            replaceUrl: true 
          }
        );
      });
  }
}
```

```typescript
// tournament-rounds.component.ts
import { Component, OnInit, AfterViewInit, ViewChild, ElementRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-tournament-rounds',
  templateUrl: './tournament-rounds.component.html'
})
export class TournamentRoundsComponent implements OnInit, AfterViewInit {
  @ViewChild('roundTabsContainer', { static: false }) roundTabsContainer!: ElementRef;
  
  tournament: any;
  activeRound: number = 1;
  
  constructor(
    private route: ActivatedRoute,
    private router: Router
  ) {}
  
  ngOnInit() {
    // Отримати номер раунду з query параметрів
    this.route.queryParams.subscribe(params => {
      if (params['round']) {
        this.activeRound = +params['round'];
        // Прокрутити до активного табу після завантаження
        setTimeout(() => this.scrollToActiveTab(), 100);
      }
    });
  }
  
  ngAfterViewInit() {
    // Прокрутити до активного табу після рендерингу
    this.scrollToActiveTab();
  }
  
  scrollToActiveTab() {
    if (!this.roundTabsContainer) return;
    
    const activeTab = this.roundTabsContainer.nativeElement.querySelector(
      `.round-tab[data-round="${this.activeRound}"]`
    );
    
    if (activeTab) {
      activeTab.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'nearest',
        inline: 'center' 
      });
    }
  }
  
  selectRound(roundNumber: number) {
    this.activeRound = roundNumber;
    this.router.navigate(
      [],
      {
        relativeTo: this.route,
        queryParams: { round: roundNumber },
        queryParamsHandling: 'merge',
        replaceUrl: true
      }
    );
    this.scrollToActiveTab();
  }
}
```

```html
<!-- tournament-rounds.component.html -->
<div class="round-tabs" #roundTabsContainer>
  <button 
    *ngFor="let round of tournament.rounds" 
    class="round-tab"
    [class.active]="round.number === activeRound"
    [class.final-tab]="round.is_final"
    [attr.data-round]="round.number"
    (click)="selectRound(round.number)">
    <span *ngIf="round.is_final">🏆 </span>
    {{ round.is_final ? 'Final' : 'Round' }} {{ round.display_number }}
  </button>
</div>
```

## Тестування

### Сценарії тестування:

1. **Створення нового раунду:**
   - Адмін створює новий раунд через API
   - Перевірити, що WebSocket повідомлення отримано
   - Перевірити, що сторінка/таб перезавантажився
   - Перевірити, що активний таб переключився на новий раунд
   - Перевірити, що горизонтальний скрол прокрутився до активного табу

2. **Старт фіналів:**
   - Адмін стартує фінали через API
   - Перевірити, що повідомлення отримано
   - Перевірити, що переключилося на перший фінальний раунд
   - Перевірити, що таб має іконку 🏆

3. **Завершення турніру:**
   - Адмін завершує турнір через API
   - Перевірити, що повідомлення отримано
   - Перевірити, що переключилося на таб з результатами
   - Перевірити, що фінальні результати відображаються

## Важливі моменти

1. **Перевірка `force_reload`:**
   - Завжди перевіряти `data.force_reload === true` перед перезавантаженням
   - Не перезавантажувати, якщо поле відсутнє або `false`

2. **Обробка помилок:**
   - Якщо оновлення даних не вдалося, показати помилку
   - Не перезавантажувати при помилках

3. **UX:**
   - Показати повідомлення користувачу перед перезавантаженням
   - Використати плавну анімацію при переключенні табів
   - Прокрутити до активного табу автоматично

4. **Продуктивність:**
   - Не робити зайві API запити
   - Кешувати дані турніру, якщо можливо
   - Використовувати debounce для WebSocket повідомлень (якщо приходять дублікати)

## Додаткові покращення (опціонально)

1. **Показ прогресу:**
   - Показати індикатор завантаження під час оновлення даних

2. **Збереження стану:**
   - Зберегти позицію скролу перед перезавантаженням
   - Відновити після перезавантаження

3. **Анімація:**
   - Додати плавну анімацію при переключенні раундів
   - Підсвітити новий раунд при перезавантаженні

