# Manual Test for Tournament Status Filter

### 1. List all tournaments (no filter)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/tournaments/?limit=10' \
  -H 'accept: application/json'
```

### 2. Filter by single status (e.g., registration)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/tournaments/?limit=10&status=registration' \
  -H 'accept: application/json'
```

### 3. Filter by multiple statuses (e.g., active and finished)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/tournaments/?limit=10&status=active&status=finished' \
  -H 'accept: application/json'
```
