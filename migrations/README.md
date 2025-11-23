# Database Migrations

This directory contains database migration scripts.

## Initial Setup

To create all tables from scratch:

```bash
python create_tables.py
```

To drop all tables except users:

```bash
python drop_tables_except_users.py --force
```

## Available migrations

- `add_user_roles.py` - Adds role field to users table (super_admin, admin, premium, user)

## Notes

- All tables are now created via SQLAlchemy models in `create_tables.py`
- Old migration files have been removed as tables were recreated
- User roles migration is kept for reference
