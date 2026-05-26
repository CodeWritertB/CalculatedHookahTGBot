# Contributing to Hookah Shift Bot

Спасибо за интерес к нашему проекту! Мы приветствуем вклады от всех.

## Как начать

1. **Сделайте fork репозитория**
   ```bash
   git clone https://github.com/username/schetchik-kalikov.git
   cd schetchik-kalikov
   ```

2. **Создайте feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Установите зависимости**
   ```bash
   pip install -r requirements.txt
   ```

## Правила кодирования

### Python стиль (PEP 8)
- Используйте 4 пробела для отступов
- Максимальная длина строки 100 символов
- Используйте type hints где возможно
- Добавляйте docstring'и ко всем функциям

### Комментарии
- Пишите ясные и понятные комментарии
- На русском языке для русскоязычного проекта
- Следуйте существующему стилю

### Commit messages
- На английском языке
- Используйте present tense ("Add feature" вместо "Added feature")
- Первая строка максимум 50 символов
- Добавляйте подробное описание если нужно

Примеры:
```
Add hookah filtering by type
Fix database connection timeout
Update README with new installation steps
```

## Процесс Pull Request

1. **Перед тем как отправлять PR:**
   - Убедитесь что код работает
   - Проверьте синтаксис (python -m py_compile *.py)
   - Обновите документацию если нужно

2. **Отправьте PR на GitHub**
   - Дайте понятное описание изменений
   - Ссылайтесь на related issues
   - Добавьте скриншоты если есть UI изменения

3. **Обработка отзывов**
   - Вежливо отвечайте на комментарии
   - Применяйте предложенные изменения
   - Пушьте обновления в ваш branch

## Сообщение об ошибках

Перед тем как создавать issue, проверьте:
- Нет ли уже такого issue?
- Это не дублирование?

При создании issue:
- Используйте понятный заголовок
- Опишите проблему детально
- Добавьте шаги для воспроизведения
- Укажите версию Python и ОС

Пример:
```
Title: Bot crashes when closing shift with no hookahs

Description:
When I try to close a shift that has no hookahs added, the bot crashes.

Steps to reproduce:
1. Start the bot
2. Open a shift
3. Don't add any hookahs
4. Try to close the shift

Expected: Shift closes with message "0 hookahs"
Actual: Bot crashes with error...

Environment:
- Python 3.10
- Windows 10
```

## Лицензия

Все вклады должны быть под MIT лицензией.

## Вопросы?

Свяжитесь с нами через:
- GitHub Issues
- GitHub Discussions
- Email

Спасибо за вклад! 🍃
