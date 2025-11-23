# Utility Scripts

Корисні скрипти для управління базою даних та користувачами.

## Database Management

### create_tables.py
Створює всі таблиці в базі даних.
```bash
python scripts/create_tables.py
```

### drop_tables_except_users.py
Видаляє всі таблиці крім users.
```bash
python scripts/drop_tables_except_users.py --force
```

### reset_database.py
Повністю скидає базу даних.
```bash
python scripts/reset_database.py
```

## User Management

### create_super_admin.py
Інтерактивний скрипт для створення super admin користувача.
```bash
python scripts/create_super_admin.py
```

### create_test_users.py
Створює тестових користувачів.
```bash
python scripts/create_test_users.py
```

### add_goose_user.py
Додає користувача Goose#2555 з рейтингом 8000.
```bash
python scripts/add_goose_user.py
```

## Data Management

### recalculate_scores.py
Перераховує всі total_score для учасників турнірів.
```bash
python scripts/recalculate_scores.py
```

## Notes

Всі скрипти потрібно запускати з кореневої директорії проекту з активованим віртуальним середовищем:

```bash
source .venv/bin/activate
python scripts/<script_name>.py
```
