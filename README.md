# Telegram Bot

Бот для управления пользователями и рассылкой сообщений.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/your-bot.git
cd your-bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корневой директории проекта со следующим содержимым:
```
BOT_API_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_id_here
```

## Запуск

```bash
python bot.py
```

## Функциональность

- Админ-панель с функциями:
  - Просмотр статистики пользователей
  - Рассылка сообщений
  - Экспорт данных в Excel
- Автоматическое логирование действий
- Обработка неизвестных команд
- Система промокодов

## Структура проекта

- `bot.py` - основной файл бота
- `requirements.txt` - зависимости проекта
- `.env` - конфигурационный файл (не включен в репозиторий)
- `users.db` - база данных пользователей (создается автоматически)
- `logs.json` - файл логов (создается автоматически)
- `users.json` - список пользователей (создается автоматически)
- `stats.json` - статистика (создается автоматически)

## Требования

- Python 3.8+
- aiogram 3.0+
- python-dotenv
- aiofiles
- pandas
- xlsxwriter 