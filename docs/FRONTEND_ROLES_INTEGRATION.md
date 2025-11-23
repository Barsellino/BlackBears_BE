# Інтеграція системи ролей на фронтенді

## 1. Enum ролей

```typescript
export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  PREMIUM = 'premium',
  USER = 'user'
}
```

## 2. Ієрархія ролей

Вищі ролі мають доступ до всіх функцій нижчих ролей:

```typescript
export const ROLE_HIERARCHY: Record<UserRole, UserRole[]> = {
  [UserRole.SUPER_ADMIN]: [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PREMIUM, UserRole.USER],
  [UserRole.ADMIN]: [UserRole.ADMIN, UserRole.PREMIUM, UserRole.USER],
  [UserRole.PREMIUM]: [UserRole.PREMIUM, UserRole.USER],
  [UserRole.USER]: [UserRole.USER]
};

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  return ROLE_HIERARCHY[userRole]?.includes(requiredRole) || false;
}
```

## 3. Оновлена модель User

Додай поле `role` до інтерфейсу User:

```typescript
export interface User {
  id: number;
  battlenet_id: string;
  battletag: string;
  name?: string;
  email?: string;
  phone?: string;
  battlegrounds_rating?: number;
  role: UserRole;  // ⬅️ НОВЕ ПОЛЕ
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
```

## 4. API Endpoints

### 4.1 Отримання користувачів (тільки для ADMIN+)

**GET** `/admin/users`

**Query параметри:**
- `limit` (number, default: 20, max: 100) - кількість записів
- `offset` (number, default: 0) - зсув від початку
- `search` (string, optional) - пошук по battletag, name, email
- `role` (UserRole, optional) - фільтр по ролі
- `is_active` (boolean, optional) - фільтр по активності
- `sort_by` (string, default: "created_at") - поле для сортування (created_at, battletag, battlegrounds_rating)
- `sort_order` (string, default: "desc") - порядок (asc/desc)

**Response:**
```typescript
{
  data: User[];
  total: number;
  limit: number;
  offset: number;
}
```

**Приклади запитів:**
```typescript
// Перші 20 користувачів
GET /admin/users?limit=20&offset=0

// Наступні 20
GET /admin/users?limit=20&offset=20

// Пошук
GET /admin/users?search=Barsellino&limit=20&offset=0

// Фільтр по ролі
GET /admin/users?role=premium&limit=50&offset=0

// Тільки активні
GET /admin/users?is_active=true&limit=20&offset=0

// Сортування по рейтингу
GET /admin/users?sort_by=battlegrounds_rating&sort_order=desc&limit=20&offset=0

// Комбінація
GET /admin/users?search=Bar&role=user&is_active=true&sort_by=created_at&sort_order=desc&limit=50&offset=0
```

### 4.2 Зміна ролі користувача (ADMIN+)

**PATCH** `/admin/users/{user_id}/role`

**Body:**
```typescript
{
  role: UserRole
}
```

**Правила:**
- ADMIN може змінювати тільки USER та PREMIUM
- Тільки SUPER_ADMIN може призначати ADMIN та SUPER_ADMIN
- Не можна змінити свою власну роль

**Response:** `User`

### 4.3 Деактивація користувача (тільки SUPER_ADMIN)

**DELETE** `/admin/users/{user_id}`

**Response:**
```typescript
{
  message: string
}
```

### 4.4 Статистика (ADMIN+)

**GET** `/admin/stats`

**Response:**
```typescript
{
  total_users: number;
  active_users: number;
  inactive_users: number;
  new_users_week: number;
  new_users_month: number;
  roles: {
    super_admin: number;
    admin: number;
    premium: number;
    user: number;
  }
}
```

### 4.5 Мої права доступу (всі користувачі)

**GET** `/admin/me/permissions`

**Response:**
```typescript
{
  user_id: number;
  battletag: string;
  role: UserRole;
  permissions: UserRole[];
}
```

### 4.6 Преміум функції (тільки PREMIUM+)

**GET** `/premium/features`

**Response:**
```typescript
{
  message: string;
  user: string;
  role: UserRole;
  features: string[];
}
```

**GET** `/premium/stats/advanced`

**Response:**
```typescript
{
  user_id: number;
  message: string;
  stats: {
    total_tournaments: number;
    win_rate: number;
    average_placement: number;
    best_performance: any;
  }
}
```

**GET** `/premium/check-access`

**Response:**
```typescript
{
  user: string;
  role: UserRole;
  has_premium_access: boolean;
}
```

## 5. Приклад Angular Service

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UsersListParams {
  limit?: number;
  offset?: number;
  search?: string;
  role?: UserRole;
  is_active?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface UsersListResponse {
  data: User[];
  total: number;
  limit: number;
  offset: number;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getUsers(params: UsersListParams = {}): Observable<UsersListResponse> {
    let httpParams = new HttpParams();
    
    if (params.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params.offset) httpParams = httpParams.set('offset', params.offset.toString());
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.role) httpParams = httpParams.set('role', params.role);
    if (params.is_active !== undefined) httpParams = httpParams.set('is_active', params.is_active.toString());
    if (params.sort_by) httpParams = httpParams.set('sort_by', params.sort_by);
    if (params.sort_order) httpParams = httpParams.set('sort_order', params.sort_order);

    return this.http.get<UsersListResponse>(`${this.apiUrl}/admin/users`, { params: httpParams });
  }

  updateUserRole(userId: number, role: UserRole): Observable<User> {
    return this.http.patch<User>(`${this.apiUrl}/admin/users/${userId}/role`, { role });
  }

  deactivateUser(userId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/admin/users/${userId}`);
  }

  getStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/admin/stats`);
  }

  getMyPermissions(): Observable<any> {
    return this.http.get(`${this.apiUrl}/admin/me/permissions`);
  }
}
```

## 6. Приклад компонента з пагінацією

```typescript
export class UsersListComponent implements OnInit {
  users: User[] = [];
  total = 0;
  limit = 20;
  offset = 0;
  
  // Фільтри
  searchTerm = '';
  selectedRole: UserRole | null = null;
  isActiveFilter: boolean | null = null;
  sortBy = 'created_at';
  sortOrder: 'asc' | 'desc' = 'desc';

  constructor(private adminService: AdminService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    const params: UsersListParams = {
      limit: this.limit,
      offset: this.offset,
      search: this.searchTerm || undefined,
      role: this.selectedRole || undefined,
      is_active: this.isActiveFilter ?? undefined,
      sort_by: this.sortBy,
      sort_order: this.sortOrder
    };

    this.adminService.getUsers(params).subscribe(response => {
      this.users = response.data;
      this.total = response.total;
    });
  }

  onPageChange(newOffset: number) {
    this.offset = newOffset;
    this.loadUsers();
  }

  onSearch() {
    this.offset = 0; // Скинути на першу сторінку
    this.loadUsers();
  }

  onFilterChange() {
    this.offset = 0;
    this.loadUsers();
  }

  changeUserRole(userId: number, newRole: UserRole) {
    this.adminService.updateUserRole(userId, newRole).subscribe(
      updatedUser => {
        // Оновити користувача в списку
        const index = this.users.findIndex(u => u.id === userId);
        if (index !== -1) {
          this.users[index] = updatedUser;
        }
      }
    );
  }
}
```

## 7. Route Guards

```typescript
import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    const user = this.authService.currentUser;
    if (user && hasPermission(user.role, UserRole.ADMIN)) {
      return true;
    }
    this.router.navigate(['/']);
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class PremiumGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    const user = this.authService.currentUser;
    if (user && hasPermission(user.role, UserRole.PREMIUM)) {
      return true;
    }
    this.router.navigate(['/']);
    return false;
  }
}
```

## 8. Використання в роутах

```typescript
const routes: Routes = [
  {
    path: 'admin',
    canActivate: [AdminGuard],
    children: [
      { path: 'users', component: UsersListComponent },
      { path: 'stats', component: StatsComponent }
    ]
  },
  {
    path: 'premium',
    canActivate: [PremiumGuard],
    children: [
      { path: 'features', component: PremiumFeaturesComponent },
      { path: 'stats', component: AdvancedStatsComponent }
    ]
  }
];
```

## 9. Умовний рендеринг в шаблонах

```html
<!-- Показати тільки адмінам -->
<div *ngIf="hasPermission(currentUser.role, UserRole.ADMIN)">
  <button (click)="openAdminPanel()">Admin Panel</button>
</div>

<!-- Показати тільки преміум+ -->
<div *ngIf="hasPermission(currentUser.role, UserRole.PREMIUM)">
  <app-premium-features></app-premium-features>
</div>

<!-- Показати тільки super admin -->
<button 
  *ngIf="currentUser.role === UserRole.SUPER_ADMIN"
  (click)="deleteUser(user.id)">
  Delete User
</button>
```

## 10. Іконки для ролей (опціонально)

```typescript
export const ROLE_ICONS = {
  [UserRole.SUPER_ADMIN]: '👑',
  [UserRole.ADMIN]: '🛡️',
  [UserRole.PREMIUM]: '⭐',
  [UserRole.USER]: '👤'
};

export const ROLE_LABELS = {
  [UserRole.SUPER_ADMIN]: 'Super Admin',
  [UserRole.ADMIN]: 'Admin',
  [UserRole.PREMIUM]: 'Premium',
  [UserRole.USER]: 'User'
};
```

Готово! Все що потрібно для інтеграції системи ролей на фронтенді.
