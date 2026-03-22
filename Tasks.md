# Tasks

## Архитектурный план: от CLI к high-load сервису

### Проблемы текущей реализации

- `watch` хранит состояние обработанных файлов в `seen: set[Path]` в памяти — после рестарта процесса теряется, файлы обрабатываются повторно
- Защита от дублей через `output_path()` (проверка коллизий имён в raw-text папке) — костыль, а не архитектурное решение
- Один поток на обработку: пока транскрибируется файл, новые ждут
- Нет трекинга заданий: нет retry, нет статусов, нет audit trail
- Нет API: нельзя принять задание извне
- Скан папки за O(N) при большом количестве файлов

---

### Фаза 0 — Исправить сейчас (без смены архитектуры)

Заменить `seen: set[Path]` на SQLite-базу с таблицей `jobs`:

```sql
jobs(id, file_path, file_hash, status, created_at, updated_at, error)
-- status: pending | processing | done | error
```

- Персистентность после рестарта
- Идемпотентность по хэшу файла (не по имени)
- Retry для упавших заданий
- Audit trail

- [x] Реализовать SQLite job store в `storage.py`
- [x] Заменить `seen` в `watch` на обращение к БД
- [x] Добавить дедупликацию по `file_hash` (sha256 первых 64KB достаточно)

---

### Фаза 1 — Разделение: Watcher + Worker

```
┌─────────────┐     job queue      ┌─────────────┐
│   Watcher   │ ─── (SQLite) ───► │   Worker    │
│ (scanner)   │                    │ (transcribe) │
└─────────────┘                    └─────────────┘
```

- Watcher: только сканирует папку, пишет `status=pending` в БД, сам не транскрибирует
- Worker: берёт `pending` задания атомарно, обрабатывает, обновляет статус
- Несколько воркеров можно запустить параллельно
- SQLite WAL достаточно до ~1000 заданий/день

- [ ] Выделить `watcher.py` — только скан и запись в очередь
- [ ] Выделить `worker.py` — только чтение очереди и обработка
- [ ] Добавить команды CLI: `transcribe watcher start`, `transcribe worker start`

---

### Фаза 2 — HTTP API + единый Node Protocol

```
┌──────────┐   POST /jobs   ┌─────────────┐   ┌──────────────┐
│  Клиент  │ ────────────► │  FastAPI    │──►│   Worker     │
│ (любой)  │               │  (gateway)  │   │   pool       │
└──────────┘               └─────────────┘   └──────────────┘
                                │
                          GET /jobs/{id}
```

Единый интерфейс для любого вычислительного узла:

```python
class Node(Protocol):
    name: str
    async def process(self, job: Job) -> JobResult: ...
    async def health(self) -> bool: ...

@dataclass
class Job:
    id: UUID
    node: str          # "transcriber", "polisher", ...
    input: dict        # {"file": "/path/...", "lang": "ru"}
    pipeline_id: UUID  # к какому пайплайну принадлежит
    next_node: str     # куда передать результат
```

- [ ] Добавить FastAPI gateway (`api.py`)
- [ ] Определить протокол Job/JobResult
- [ ] POST /jobs — сабмит задания
- [ ] GET /jobs/{id} — статус
- [ ] Webhook callback по завершении

---

### Фаза 3 — Pipeline Engine

Пайплайн описывается декларативно (YAML):

```yaml
name: "voice-to-note"
steps:
  - node: transcriber
    config: {model: "small", lang: "ru"}
  - node: polisher
    config: {model: "deepseek-chat"}
  - node: obsidian-writer
    config: {vault: "~/Obsidian", folder: "00.Inbox"}
```

- Движок прогоняет задание через цепочку узлов
- Каждый узел получает output предыдущего
- Состояние каждого шага сохраняется — retry только проблемного шага
- Узлы независимы и переиспользуемы в разных пайплайнах

- [ ] Реализовать `pipeline.py` — загрузка и исполнение YAML-пайплайнов
- [ ] Хранить состояние каждого шага в БД
- [ ] Реализовать retry с backoff для отдельных шагов

---

### Фаза 4 — Распределённые воркеры

Только когда нагрузка превысит одну машину:

```
                    ┌─── Worker node 1 (GPU) ───┐
API Gateway ──► Redis Queue ◄─────────────────── ┤
                    └─── Worker node 2 (CPU) ───┘
```

- Redis вместо SQLite как брокер очереди
- Celery или Dramatiq как worker framework
- GPU-воркеры для Whisper, CPU-воркеры для text processing
- Модели загружаются один раз на воркере (уже есть `_model_cache`)

---

### Фаза 5 — Платформа

```
┌─────────────────────────────────────┐
│          Control Plane              │
│  (pipeline registry, scheduling,    │
│   metrics, dead letter queue)       │
└─────────────────────────────────────┘
         │                    │
┌────────┴──────┐   ┌────────┴──────────┐
│ Transcriber   │   │  Text Processing  │
│ Worker Pool   │   │  Worker Pool      │
└───────────────┘   └───────────────────┘
```

---

## Текущие мелкие задачи

- [ ] Очистка raw-text папки: файлы накапливаются бесконечно, нужна стратегия TTL или связь с job store