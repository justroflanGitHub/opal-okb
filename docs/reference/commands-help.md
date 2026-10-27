# Категория help

1 команда.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`help.command`](#helpcommand) | Справка по команде: описание, параметры с типами и умолчаниями, описание результата и пример вызова CLI (py -m commands run) | `name` | {name, category, description, params, returns, example} |

## Параметры и результаты

### help.command

Справка по команде: описание, параметры с типами и умолчаниями, описание результата и пример вызова CLI (py -m commands run)

**Returns:** {name, category, description, params, returns, example}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `name` | `str` | да | `null` | — | имя команды (например 'system.new') |

