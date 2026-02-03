# 🤖 AI Agent Instructions & Coding Standards (Stellar Gateway)

**ROLE:** Senior Python Software Engineer & Software Architect.
**CONTEXT:** You are building "Stellar Gateway", a Serverless API Proxy for SWAPI hosted on GCP.
**MANDATE:** Follow the rules below strictly. If a user prompt contradicts these rules, warn the user before proceeding.

---

## 1. Project Architecture (Hexagonal / Clean Arch)

The project follows strict separation of concerns.

* **Layer 1: Domain (`src/domain/`)**
    * **Allowed:** Pure Python, Pydantic.
    * **FORBIDDEN:** Imports from `src/adapters`, `src/use_cases`, external I/O libs (requests, redis).
* **Layer 2: Use Cases (`src/use_cases/`)**
    * **Allowed:** Imports from `src/domain`, `src/interfaces`.
    * **FORBIDDEN:** Direct imports from `src/adapters` (No concrete implementations).
* **Layer 3: Adapters (`src/adapters/`)**
    * **Allowed:** Implementation of Interfaces using external libs (`httpx`, `redis`).
* **Layer 4: Drivers (`src/main.py`)**
    * **Allowed:** Wires everything together (Dependency Injection root).

---

## 2. Strict Typing & Docstrings (No "Any")

**RULE:** Python's dynamic typing is forbidden here. You must use explicit type hints for EVERYTHING (args, returns, variables).
**RULE:** Do not use `Any`. If you are tempted to use `Any`, define a Pydantic model or a TypedDict instead.

### ❌ Bad Implementation
```python
# BAD: Missing types, using implicit Any, no docstring
def process_data(data):
    result = data['items']
    return result

# BAD: Lazy typing
def fetch_user(id: int) -> Any: 
    pass
``` 

### ✅ Good Implementation
```python
from typing import List, Dict, Optional

# GOOD: Explicit types, Pydantic models, Google Style Docstring
def process_data(data: Dict[str, List[str]]) -> List[str]:
    """
    Extracts items from the payload.

    Args:
        data: A dictionary containing a list of items.

    Returns:
        A list of item strings.
    """
    return data.get("items", [])
```

## 3. Workflow: TDD (Red-Green-Refactor)

**RULE:** You never write implementation code (`src/`) before writing a failing test (`tests/`).

### ❌ Bad Implementation (Coding First)
> *User asks for a feature.*
> *AI generates `src/domain/person.py` immediately.*
> *AI generates tests afterwards just to check coverage.*

### ✅ Good Implementation (Test First)
> *User asks for a feature.*
> *AI Action:* "I will start by creating the test case."
>
> 1.  **RED:** Create `tests/unit/test_person.py`. Assert that `Person(name="Luke")` works. Run test -> **FAIL** (ImportError).
> 2.  **GREEN:** Create minimal `src/domain/person.py`. Run test -> **PASS**.
> 3.  **REFACTOR:** Add validation logic. Ensure test still **PASSES**.

---

## 4. Pattern: Use Cases & Dependency Injection (SOLID/DIP)

**RULE:** Business logic must not depend on concrete infrastructure. Use Interfaces (Protocols or Abstract Base Classes).

### ❌ Bad Implementation (Coupling)
```python
# BAD: Use Case creates the Redis connection directly.
# This violates Dependency Inversion Principle.
import redis
from src.domain.models import Person

class GetPersonUseCase:
    def execute(self, id: int):
        r = redis.Redis(host='localhost') # ⛔ HARD COUPLED
        data = r.get(f"person:{id}")
        return Person(**data)
```

### ✅ Good Implementation (Injection)
```python
# GOOD: Use Case receives the contract (Interface).
# It doesn't care if it's Redis, SQL, or In-Memory.
from src.interfaces.cache_repository import CacheRepositoryInterface
from src.domain.models import Person

class GetPersonUseCase:
    def __init__(self, cache_repo: CacheRepositoryInterface):
        self.cache_repo = cache_repo  # ✅ INJECTED

    async def execute(self, id: int) -> Person:
        data = await self.cache_repo.get(f"person:{id}")
        return Person(**data)
```

## 5. Pattern: Adapters & Async I/O

**RULE:** All I/O (Network, Disk, DB) must be asynchronous (`async/await`).
**RULE:** Adapters must implement the Interface defined in the Application Layer.

### ❌ Bad Implementation (Blocking/Sync)
```python
# BAD: Using synchronous requests blocks the Event Loop.
import requests 

class SwapiClient:
    def get_person(self, id: int):
        # ⛔ BLOCKING CALL - Kills performance in Cloud Functions
        response = requests.get(f"[https://swapi.dev/api/people/](https://swapi.dev/api/people/){id}")
        return response.json()
```

### ✅ Good Implementation (Async/Non-blocking)
```python
# GOOD: Using httpx with async/await.
import httpx
from src.interfaces.swapi_interface import SwapiInterface

class SwapiClient(SwapiInterface):
    async def get_person(self, id: int) -> dict:
        async with httpx.AsyncClient() as client:
            # ✅ NON-BLOCKING
            response = await client.get(f"[https://swapi.dev/api/people/](https://swapi.dev/api/people/){id}")
            response.raise_for_status()
            return response.json()
```

## 6. Pattern: Clean Code & DRY

**RULE:** Avoid magic numbers, duplicated logic, and large functions.

### ❌ Bad Implementation
```python
# BAD: Magic strings, mixed responsibilities
if user.role == "admin": # Magic string
    if len(password) < 8: # Magic number
        raise Exception("Error") # Generic exception
```

### ✅ Good Implementation
```python
# GOOD: Constants, Custom Exceptions, Single Responsibility
MIN_PASSWORD_LENGTH = 8
ADMIN_ROLE = "admin"

def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError("Password too short")
```

### 🔒 Security Rule
**NEVER** hardcode secrets (API Keys, Token, Project IDs). Always use `src/core/config.py` which loads from `os.getenv`.

## 7. Libraries to Use
* **Web/Http:** `httpx` (Async), `flask` (only for entrypoint).
* **Validation:** `pydantic` (Strict Models).
* **Resilience:** `tenacity` (Retry decorators).
* **Testing:** `pytest`, `pytest-asyncio`, `respx` (HTTP Mocking).
* **Auth:** `firebase-admin`.

---

## 8. Directory Structure Map

You must place files in their correct architectural layer according to this map.

```text
.
├── src/
│   ├── domain/          # 🟡 Layer 1: Entities (Pure Python)
│   │   └── models.py    #    (e.g., class Person)
│   ├── interfaces/      # 🟡 Layer 2: Gateways/Protocols (Abstract)
│   │   └── swapi.py     #    (e.g., class SwapiInterface(Protocol))
│   ├── use_cases/       # 🟡 Layer 2: Application Logic
│   │   └── get_person.py#    (e.g., class GetPersonUseCase)
│   ├── adapters/        # 🟢 Layer 3: Infrastructure Impl
│   │   ├── swapi.py     #    (e.g., class SwapiClient(SwapiInterface))
│   │   └── redis.py     #    (e.g., class RedisCache)
│   ├── core/            # 🔵 Cross-Cutting
│   │   ├── config.py    #    (Env vars)
│   │   └── exceptions.py#    (Custom Errors)
│   └── main.py          # 🔴 Layer 4: Entrypoint (Wiring/DI Root)
├── tests/
│   ├── unit/            #    (Mocked logic tests - Fast)
│   └── integration/     #    (Real I/O tests - Slow)
├── AGENTS.md            #    (This file)
└── TASKS.md             #    (Project Roadmap)
```

## 9. Git & Commit Standards (Conventional Commits)

**RULE:** When you complete a task, you must suggest a git commit message following the Conventional Commits specification.

**Format:** `<type>(<scope>): <subject>`

**Types:**
* `feat`: New feature (e.g., adding a new Use Case).
* `fix`: Bug fix.
* `test`: Adding missing tests or correcting existing tests.
* `refactor`: Code change that neither fixes a bug nor adds a feature.
* `chore`: Build process, auxiliary tools, or library changes (e.g., poetry add).

**Examples:**
* `feat(domain): add Person entity with pydantic validation`
* `test(adapter): add unit test for SwapiClient with respx mock`
* `refactor(usecase): switch from synchronous request to async/await`