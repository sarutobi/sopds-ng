# Консолидированный план устранения технического долга (Kiro SDD)

> Объединён из: `.kiro/debt/opds_catalog.md`, `.kiro/debt/book_tools.md`, `.kiro/debt/sopds_web-backend.md`
> Дата: 2026-09-03
> Методология: декомпозиция от критического (P0) к второстепенному (P2+), приоритезация по влиянию на релиз 1.0 (ТЗ v2.1).

---

## Этап 1: Стабильность и Безопасность (P0) — краш-баги, дыры в безопасности, блокирующие нарушения ТЗ

### opds_catalog
1. ~~**[opds_catalog] SEC-1: Обход Basic Auth на Cover и ConvertFB2**~~ (DONE) → `dl.py:110,159` — `Cover` и `ConvertFB2` не декорированы `sopds_auth_validate`. (ID: SEC-1)
2. ~~**[opds_catalog] БАГ-33: Дублирование жанров книги → IntegrityError UNIQUE при сканировании**~~ (DONE) → `scanner.py:148` `addbgenre` через `get_or_create`; нормализация на входе (дедуп жанров/серий, авторов) в `sopdscan.py`; регрессион-тест `test_duplicate_genres.py`. (ID: БАГ-33)
2. ~~**[opds_catalog] SEC-2: `@csrf_exempt` на `inline_save_view`**~~ (DONE) → `admin.py:30` — AJAX-редактирование без CSRF-защиты. (ID: SEC-2)
3. ~~**[opds_catalog] SEC-3: Базовый Auth `b64decode` без обработки ошибок**~~ (DONE) → `decorators.py:27-33` — кривой заголовок → 500 вместо 401; хрупкий `args[0]/args[1]`. (ID: SEC-3)
15. ~~**[opds_catalog] БАГ-2: 500 вместо 404 на несуществующие book_id**~~ (DONE) → `dl.py:40,110,159` — `Book.objects.get()` без обработки `DoesNotExist` в `Download`, `Cover`, `ConvertFB2`. (ID: БАГ-2)
5. ~~**[opds_catalog] БАГ-4: Битая заглушка обложки**~~ (DONE) → `dl.py:28` — `SOPDS_DEFAULT_COVER` ссылался на несуществующий `/static/images/sopds-ng-nocover.png`. (ID: БАГ-4)
5. ~~**[opds_catalog] БАГ-1: Bare `except:`**~~ (DONE) → `dl.py:233,237` — прямое нарушение ТЗ п.9; проверен конфиг ruff (E722). (ID: БАГ-1)
6. ~~**[opds_catalog] БАГ-8: F-string без `f`**~~ (DONE) → `sopdscan.py:127` — в лог пишется литерал `{file}`. (ID: БАГ-8)
7. ~~**[opds_catalog] БАГ-5: Мёртвый try/except в `findauthor`**~~ (DONE) → `opdsdb.py:336-342` — `filter()` не бросает `DoesNotExist`. (ID: БАГ-5)
8. ~~**[opds_catalog] БАГ-6: `UnboundLocalError` в `search_series`**~~ (DONE) → `series_services.py:37-48` — при неизвестном `searchtype` переменная не определена. (ID: БАГ-6)
9. ~~**[opds_catalog] БАГ-7: `item_updateddate` — класс-атрибут**~~ (DONE) → `feeds.py:247` — вычислялся один раз при импорте. (ID: БАГ-7)
10. ~~**[opds_catalog] БАГ-15: Закомментированный `parser.parse()` в `extract_fb2_cover`**~~ (DONE) → `services/__init__.py:77` — мёртвая закомментированная строка удалена: `parse()` уже вызывается в конструкторах `FB2`/`FB2sax`. (ID: БАГ-15)

### book_tools
12. ~~**[book_tools] P0-2: `book_metadata_to_bookfile()` создаёт BookFile через name-mangled методы**~~ (DONE) → `services.py:336,64` — нарушение инкапсуляции, хрупкий контракт. (ID: P0-2)
13. ~~**[book_tools] P0-3: `EpubParser.authors/tags` — `creator.text` может быть `None`**~~ (DONE) → `parsers.py:439-444,450` → `AttributeError` в `split()`. (ID: P0-3)
14. ~~**[book_tools] P0-4: `EpubParser` — `[0]` без проверки длины**~~ (DONE) → `parsers.py:435,456,502` — `IndexError` на EPUB без title/language/description. (ID: P0-4)
15. ~~**[book_tools] P0-5: `format/mobi.py:17` — `modificationDate.strftime()` без проверки на `None`/ошибки**~~ (DONE) → возможен `OverflowError`/`ValueError`. (ID: P0-5)
16. ~~**[book_tools] P0-6: Утечка файлового дескриптора в `pymobi/mobi.py:261-268`**~~ (DONE) → файл открывается в `__init__`, но не закрывается. (ID: P0-6)

### sopds_web_backend
17. ~~**[sopds_web_backend] SearchSuggestView работает без аутентификации**~~ (DONE) → `views.py:477-479` — декоратор `@sopds_login` закомментирован. (ID: 1.1)
18. ~~**[sopds_web_backend] KeyError в контекстном процессоре при пустом Counter**~~ (DONE) → `processors.py:50` — исправлено заменой прямого обращения на `.get()`. (ID: 1.2)
19. ~~**[sopds_web_backend] Небезопасные преобразования `int()` на пользовательском вводе**~~ (DONE) → `views.py:150,210,267,331,430,524` — `ValueError`/`TypeError` → 500. (ID: 1.3)
20. ~~**[sopds_web_backend] ValueError для неизвестного searchtype → 500**~~ (DONE) → `views.py:89-91` — исключение из сервиса не перехватывается. (ID: 1.4)
21. ~~**[sopds_web_backend] IndexError в поиске случайной книги**~~ (DONE) → `processors.py:52-57` — устаревший счётчик Counter. (ID: 1.5)

---

## Этап 2: Корректность и Качество (P1) — логические ошибки, покрытие тестами, стандарты кода

### opds_catalog
1. ~~**[opds_catalog] БАГ-9/18: Утечки файловых дескрипторов**~~ (DONE) → `opdsdb.py:95-105` (cursor), `inpx_parser.py:63,160` (ZipFile), `utils.py:229-232` (ручной open/close). (ID: БАГ-9, БАГ-18)
2. ~~**[opds_catalog] БАГ-3/17: SQL без транзакций / `create index concurrently` внутри atomic**~~ (DONE) → `opdsdb.py:72-91`, `sopds_scanner.py:94`. (ID: БАГ-3, БАГ-17)
3. ~~**[opds_catalog] АРХ-6: in-memory пагинация каталогов (O(N) памяти)**~~ (DONE) → `catalog_services.py` — критично для ТЗ 5.3 (100k+ книг). (ID: АРХ-6)
4. ~~**[opds_catalog] АРХ-7: Сканирование в одной `transaction.atomic()`**~~ (DONE) → `sopds_scanner.py` — блокирует БД. (ID: АРХ-7)
5. ~~**[opds_catalog] Дедупликация пагинатора и Prefetch**~~ (DONE) → `book_services`, `catalog_services`, `feeds` (АРХ-3, АРХ-4); унификация через `pagination_utils.py`, commit `3b3cff9`. (ID: АРХ-3, АРХ-4)
6. ~~**[opds_catalog] ТЗ-1: Покрытие ~67% при цели ≥80%**~~ (DONE) → `dl.py`, `admin.py`, `middleware.py`, `models.py` — 100%; management-команды покрыты интеграционными тестами в `tests/integration/opds_catalog/test_management_commands.py`. (ID: ТЗ-1)
7. ~~**[opds_catalog] ТЗ-2: Фиксированный FB2-парсер**~~ (DONE) → `sopdscan.py:46-48` — `config.SOPDS_FB2SAX` теперь учитывается. (ID: ТЗ-2)
8. ~~**[opds_catalog] ТЗ-3: `unique_together` на M2M**~~ (DONE) → имена моделей исправлены (`Book`, `Author`, `Genre`, `Series`, `BookShelf`, commit `b63144d`); `unique_together` добавлен в `BookAuthor`/`BookGenre`/`BookSeries` + миграция 0008 с дедупликацией дублей. (ID: ТЗ-3)
9. ~~**[opds_catalog] БАГ-13/14: Глотающие `except Exception` в сервисах**~~ (DONE) → `catalog_services.py:19-26`, `feeds.py` API неконсистентность. (ID: БАГ-13, БАГ-14)
10. ~~**[opds_catalog] БАГ-16: Конфликт имён URL**~~ (DONE) → `urls.py:42-43` — дубли `name="genres"`, `name="searchbooks"`. (ID: БАГ-16)
11. ~~**[opds_catalog] БАГ-17a: `Counter.name` max_length=16**~~ (DONE) → увеличено до 64. (ID: БАГ-17a)
12. **[opds_catalog] Проверка необходимости кэширования (замеры производительности)** → фиды, поиск, счётчики. (ID: подтверждённый техдолг 15, 16) [ОТЛОЖЕНО]

### book_tools
14. ~~**[book_tools] P1-1: 9 голых `except:` в `format/epub.py`**~~ (DONE) — нарушение ТЗ Never-правила; `except Exception: pass` проглатывает ошибки. (ID: P1-1)
15. ~~**[book_tools] P1-2: `print()` в production-коде — 8 мест**~~ (DONE) → `parsers.py:201`, `format/mobi.py:62`, `pymobi/mobi.py` (множество). (ID: P1-2)
16. ~~**[book_tools] P1-3: `error.message` не существует в Python 3**~~ (DONE) → `format/epub.py:87` — `AttributeError` при обработке ошибки. (ID: P1-3)
17. ~~**[book_tools] P1-4: `shutil.move(new_epub, self.path)` — `self.path` не определён**~~ (DONE) → `format/epub.py:495` — мёртвый код `encrypt()`/`repair()`. (ID: P1-4)
18. ~~**[book_tools] P1-5: `itervalues()` не существует в Python 3**~~ (DONE) → `pymobi/mobi.py:392`. (ID: P1-5)
19. ~~**[book_tools] P1-6/7: Palmdoc/Huffcdic `unpack` только для Python 2**~~ (DONE) → `pymobi/compression.py` — HUFF/CDIC сломаны в Python 3. (ID: P1-6, P1-7)
20. ~~**[book_tools] P1-8: `last_name = \"\"` для однословных авторов**~~ (DONE) → `services.py:128` — рассинхронизация sortkey. (ID: P1-8)
21. ~~**[book_tools] P1-9: `series_no=0` молчаливая подмена отсутствующего номера**~~ (DONE) → `services.py:196`, `epub.py:153`. (ID: P1-9)
22. ~~**[book_tools] P1-10: LSP нарушение — `FB2sax.authors` генератор vs `FB2.authors` список**~~ (DONE) → исправлено принудительным UTF-8/CP1251 fallback. (ID: P1-10)
23. ~~**[book_tools] P1-11: `FB2.title` — `UnboundLocalError` при отсутствии title**~~ (DONE) → исправлено принудительным UTF-8/CP1251 fallback. (ID: P1-11)
24. ~~**[book_tools] P1-12: Потеря `file_size`, `file_format`, `publication_date`, cover в конвертере**~~ (DONE) → заменен `mktemp` на `mkstemp`. (ID: P1-12)
25. ~~**[book_tools] P1-14: `encrypt()` вызывает несуществующую функцию**~~ (DONE) → исправлена обработка None в `parse_book_data`. (ID: P1-14)

### sopds_web_backend
26. ~~**[sopds_web_backend] Покрытие 73% против цели ≥80%**~~ (DONE) → `SearchBooksView` (строки 87-194) не покрыт вообще. (ID: 1.7)
27. ~~**[sopds_web_backend] Сломанные лог-сообщения**~~ (DONE) → аудит логов в `views.py` и проекте; спам CRITICAL и ошибки f-строк не обнаружены в актуальном коде. (ID: 1.8)
28. ~~**[sopds_web_backend] Монстр `SearchBooksView` (~115 строк)**~~ (DONE) → высокая цикломатическая сложность, бизнес-логика во view. (ID: 2.1)
29. ~~**[sopds_web_backend] Дублирование `SearchSeriesView` / `SearchAuthorsView`**~~ (DONE) → 50+ строк копипасты. (ID: 2.2)
30. ~~**[sopds_web_backend] Прямые запросы к моделям вместо сервисного слоя**~~ (DONE) → `views.py:115,133,151-157,500-504`. (ID: 2.7)
31. ~~**[sopds_web_backend] N+1 в процессорах**~~ (DONE) → `processors.py:30-39` — 17 запросов на страницу. (ID: 2.9)
32. ~~**[sopds_web_backend] Статистика и случайная книга без кэша**~~ (DONE) → `processors.py:43-64` — OFFSET-скан устранен, статистика хранится в `Counter`. (ID: 2.10)
33. ~~**[sopds_web_backend] Rate limiting на LoginView (M1 Security Audit)**~~ (DONE) → `views.py:552`. (ID: 2.16)
34. ~~**[sopds_web_backend] Security-заголовки (L1-L5)**~~ (DONE) → `settings/base.py` — `SESSION_COOKIE_SECURE`, HSTS, etc. (ID: 2.17)

---

## Этап 3: Архитектура и Оптимизация (P2) — устранение N+1, рефакторинг, оптимизация ресурсов

### opds_catalog
1. ~~**[opds_catalog] АРХ-2/3/4/5: Дублирование кода**~~ (DONE) → общая конвертация `dl`/`utils`, три копии `arc_skip`/`inp_skip`/`inpx_skip`, «божественный модуль» `opdsdb.py`. (ID: подтверждённый техдолг 1, 2, 3, 4)
2. ~~**[opds_catalog] АРХ-9: Захардкоженные кодировки/языки**~~ (DONE) → SQLite overrides, `LangCodes` в моделях. (ID: АРХ-9)
3. ~~**[opds_catalog] АРХ-10: Конфигурация через `getattr(settings, ...)` — два источника правды**~~ (DONE) → (ID: АРХ-10)
4. ~~**[opds_catalog] АРХ-5: Сериализация OPDS через dict-or-object ветвления**~~ (DONE) → (ID: АРХ-5)
5. ~~**[opds_catalog] CounterManager без кэша/batch-обновлений**~~ → отложен (ID: подтверждённый техдолг 19).
    Counter — это по сути кэш на уровне БД, обновляемый раз в часы/дни при сканировании. 5 строк,
    один `SELECT` на HTTP-запрос — тривиальная нагрузка. Внешний кэш (Redis/Memcached) для 5 целых чисел — overengineering,
    добавляет компоненты и точки отказа без доказанной проблемы. При увеличении нагрузки (RPS, N+1)
    — пересмотреть.
6. ~~**[opds_catalog] Отсутствие индексов на through-таблицы**~~ → (DONE) (ID: подтверждённый техдолг 20)
7. ~~**[opds_catalog] Дубликаты книг: линейный поиск**~~ → (DONE) (ID: подтверждённый техдолг 38).
    Устранён O(N²) поиск в `sopds_duplicates_scanner`. Логика вынесена в `DuplicatesService`
    (`_make_signature`, `find_doubles_for_book`, `find_all_duplicates`, `find_first_double_ids`),
    который используется из `book_services.find_book_doubles`, OPDS-фидов и сканера.
    Критерий дублей: `(title, lang, sorted_author_names)` — разные языки = разные книги.

    **Отложено в Release 2.0**: модель `BookGroup` с M2M на `Book`, хранение групп в БД,
    UI раздел «Другие издания» в карточке книги, обнаружение сборников.
8. ~~**[opds_catalog] `sopds_telebot` — монолит**~~ (DONE) → (ID: подтверждённый техдолг 39)

### book_tools
9. ~~**[book_tools] P2-1: 3 реализации парсинга FB2 вместо одной**~~ (DONE) → оставлен единый `parsers.FB2` (lxml); удалены `parsers.py`-FB2sax, `fb2.py`, `fb2sax.py`, `opds_catalog/fb2parse.py`; CP1251-fallback перенесён в `parsers.FB2`; убрана настройка `SOPDS_FB2SAX`; commit `8092a2a`. (ID: P2-1)
10. ~~**[book_tools] P2-2: Мёртвый `aes.py`**~~ (DONE) → удалён `src/book_tools/format/aes.py` (заглушка, `pycryptodome` не в зависимостях); в `epub.py` удалена мёртвая шифровальная ветка (`encrypt`/`repair`/`__add_encryption_section`/`__create_encryption_file`), сохранён `get_encryption_info`; commit `d9edb53`. (ID: P2-2)
11. ~~**[book_tools] P2-3: `minify_cover` — заглушка `pass`**~~ (DONE) → удалена заглушка `minify_cover` (`format/util.py`), в базовом `BookFile` удалены мёртвые `extract_cover`/`extract_cover_internal`/`get_encryption_info`/`repair` (in_degree 0); контейнер сохранён; commit `eeff21f`. (ID: P2-3)
12. ~~**[book_tools] P2-4: `other.py` — Dummy-класс 0% покрытия**~~ (DONE) → удалён `src/book_tools/format/other.py` (не импортируется, cartog in_degree 0); commit `2b0dfde`. (ID: P2-4)
13. ~~**[book_tools] P2-5: `__metaclass__ = ABCMeta` — py2-синтаксис**~~ (DONE) → удалён `__metaclass__ = ABCMeta` (`format/bookfile.py:8`, в py3 игнорируется, `BookFile` — конкретный контейнер без abstractmethod), `class BookFile(object)` → `class BookFile:`, убран неиспользуемый импорт `abc`; commit `e68f098`. (ID: P2-5)
14. ~~**[book_tools] P2-6/7: Дубль mime-detector'а в `format/__init__.py` + циклический риск импорта**~~ (DONE) → единый источник `Mimetype.FORMAT_MIME_MAP` + `mime_by_format`/`mime_by_suffix`; удалён класс `mime_detector` из `format/__init__.py` и `_SUFFIX_MIME_MAP` из `mime_detector.py`; `detect_by_suffix` переведён на `Mimetype` (сохранён приоритет `.fb2.zip`); `dl.py`/`feeds.py` на `mime_by_format`; commit `6634ba0`. (ID: P2-6, P2-7)
15. ~~**[book_tools] P2-9: `mime_by_type` KeyError вместо fallback**~~ (DONE) → `mime_by_type`/`suffix_mime_mapper` заменены на `mime_by_format`/`FORMAT_MIME_MAP` через `.get(..., OCTET_STREAM)`; KeyError закрыт; commit `6634ba0`. (ID: P2-9)
16. ~~**[book_tools] P0-7: Двойная/тройная распаковка FB2_ZIP в памяти**~~ (DONE/ABANDONED) → Фаза 1 (DONE): лишняя копия устранена (`BytesIO(d.read())` в `create_bookfile_service` и `parse_fb2_zip`). Фаза 2 (ABANDONED): попытка внедрить стриминг (`iterparse`) для метаданных была отклонена из-за высокого риска потери данных, проблем с вложенностью XML и несовместимости с перекодировкой CP1251. Выигрыш в памяти признан незначительным по сравнению с риском нарушения корректности парсинга. (ID: P0-7)
17. ~~**[book_tools] Иерархия исключений не соответствует ТЗ**~~ (DONE) → создана иерархия BookToolsError $\rightarrow$ ParserError $\rightarrow$ UnsupportedFormatError в `exceptions.py`; обновлены все raise и импорты. (ID: P1-13)
18. ~~**[book_tools] EPub монолит 547 строк**~~ (DONE) → рефакторинг в пакет `src/book_tools/format/epub/` с разделением на `model`, `metadata`, `cover` и `encryption`. (ID: подтверждённый техдолг)
19. **[book_tools] `ebook_parsers` пакет недостроен и не используется** → подключить или удалить. (ID: подтверждённый техдолг)
20. **[book_tools] LRU-кэш метаданных (path, mtime)** → ТЗ-parsers 3.5. (ID: подтверждённый техдолг)
21. **[book_tools] Потоковая обработка больших файлов** → отсутствует. (ID: подтверждённый техдолг)
22. **[book_tools] mypy --strict для book_tools** → отключены error codes в pyproject.toml. (ID: подтверждённый техдолг)

### sopds_web_backend
23. **[sopds_web_backend] Ruff «чистый» за счёт отключения правил** → `E722`, `F401`, `F841`, `F821`, `F403` в pyproject.toml. (ID: 1.9)
24. **[sopds_web_backend] Unreachable-код в LoginView** → `views.py:593`. (ID: 1.10)
25. **[sopds_web_backend] `re_path` вместо `path()` для 14 маршрутов** → `urls.py:8-23`. (ID: 2.11)
26. **[sopds_web_backend] Мёртвый `settings.py` (HALF_PAGES_LINKS не импортируется)** → (ID: 2.12)
27. **[sopds_web_backend] Кэш: включить `{% cache %}` с учётом `cache_t=0` для полки ИЛИ убрать вычисления** → (ID: 2.13)
28. **[sopds_web_backend] Шаблоны: пагинация в 4 копии, Tabs → Accordion, foundation-icons** → (ID: 2.15, 2.16)
29. **[sopds_web_backend] STATIC_ROOT указывает на несуществующий путь (20 warnings)** → (ID: 3.8)
30. **[sopds_web_backend] admin.py/models.py пустые — решить судьбу** → (ID: 2.17)

---

## Этап 4: Гигиена и Очистка — удаление мёртвого кода, мусора, исправление линтера


### opds_catalog
1. **[opds_catalog] `__pycache__`-артефакты в дереве исходников** → `.pyc` несуществующих модулей. (ID: разд. 3)
2. **[opds_catalog] `log/` и `tmp/` в репозитории** → добавить в `.gitignore`. (ID: разд. 3)
3. **[opds_catalog] Дубли fixtures `testdb.json`** → `fixtures/` vs `tests/opds_catalog/fixtures/`. (ID: разд. 3)
4. ~~**[opds_catalog] `generate_load_test_data.py` (382 строки) в прод-коде**~~ (DONE) → перенесено в `tests/`. (ID: разд. 3)
5. **[opds_catalog] Мёртвый код: `set_autocommit`, `books_del_logical`, закомментированные блоки в `services/__init__.py`, `middleware.py`, `settings.py`** → (ID: разд. 3)
6. **[opds_catalog] `# noqa: F841` вместо удаления неиспользуемых переменных** → `dl.py:214`, `utils.py:240`. (ID: разд. 3)
7. **[opds_catalog] Параметр `type` затеняет builtin** → `search_book(type: str...)`. (ID: разд. 3)
8. **[opds_catalog] Опечатки: «неправлено», «праметры», `books_del_phisical`** → (ID: разд. 3)

### book_tools
9. **[book_tools] `__pycache__/` в `src/book_tools/` и `format/`** → проверить `.gitignore`. (ID: разд. 4)
10. **[book_tools] `format/aes.py` — 90% закомментированного кода** → (ID: разд. 4)
11. **[book_tools] Комментарии-руины** → `parsers.py:120,244,246`, `fb2.py:237-251`, `format/__init__.py:53-86,117-130`, `pymobi/mobi.py:8-14`. (ID: разд. 4)
12. **[book_tools] `pymobi/util.py:encodeVarint` — не используется** → (ID: разд. 4)
13. **[book_tools] `extract_cover_memory` —.delegate-обёртка без docstring, дублируется в 3 классах** → (ID: разд. 4)
14. **[book_tools] P2-8: Мутируемые атрибуты класса `BookMobi`** → `header/records/... = OrderedDict()` на уровне класса. (ID: P2-8)
15. **[book_tools] P2-10: `ns_map` в `EbookMetaParser` не используется** → (ID: P2-10)
16. **[book_tools] P2-12: `import *` в `pymobi/__init__.py:8`** → нарушение AGENTS.md. (ID: P2-12)
17. **[book_tools] P2-13: `Optional` вместо `\|`** → `services.py:6`. (ID: P2-13)
18. **[book_tools] P2-14: Тест-хелпер дублирует DTO** → `tests/book_tools/conftest.py`. (ID: P2-14)
19. **[book_tools] P2-15: Санитизация basename в `pymobi/mobi.py:482`** → security (низкий). (ID: P2-15)

### sopds_web_backend
20. **[sopds_web_backend] `migrations/__pycache__/*.pyc` в репо** → (ID: 3.1)
21. **[sopds_web_backend] Артефакт `# g ` перед закомментированным декоратором** → `views.py:478`. (ID: 3.2)
22. **[sopds_web_backend] Мёртвые функции: `search_book_by_title_match`, `get_breadcrumbs`, `BREADCRUMBS`** → `views.py:36-39,73-75`. (ID: 3.3, 3.4)
23. **[sopds_web_backend] Самоприсваивание `args[\"searchterms\"] = args[\"searchterms\"]`** → `views.py:181-182`. (ID: 3.5)
24. **[sopds_web_backend] Недостижимый `return` в LoginView** → `views.py:593`. (ID: 3.6)
25. **[sopds_web_backend] Тесты мёртвого кода при непокрытом `SearchBooksView`** → `test_views.py:29-60`. (ID: 3.9)
26. ~~**[инфра] `just postgres_tests` не передавал `--ds`**~~ (DONE) → тесты запускались с `sopds.settings.local` (debug_toolbar + whitenoise Manifest без collectstatic) → 19 ложных падений `Missing staticfiles manifest entry`; `--ds={{ django_settings }}` добавлен в рецепт. (ID: новый)
27. ~~**[инфра] `tests/test_unsafe_conversions.py` не входил в `testpaths`**~~ (DONE) → файл не запускался в `just test`/`postgres_tests` (350 из 363); `tests` добавлен в `testpaths`, тесты переписаны под актуальное поведение (fallback вместо 500), мусорный `force_login(None)` удалён. (ID: 3.9, новый)
28. ~~**[opds_catalog] `find_book_doubles`: `DoesNotExist` на некорректный/несуществующий book_id → 500**~~ (DONE) → `book_services.py` — обработка `Book.DoesNotExist`, возврат пустого QuerySet. (ID: БАГ-2-подобный)

---

## Конфликты и противоречия (требуют ADR/решения)

1. **[opds_catalog] `pg_optimize` с `create index concurrently` внутри atomic** — steering советует atomic для записи, но это сломает `pg_optimize`. (БАГ-17)
2. **[book_tools] ТЗ parsers vs ТЗ format** — разные имена интерфейсов (`EbookParser` vs `BookParser`) и сигнатуры. (Конфликт 1)
3. **[book_tools] ТЗ parsers п.3.6 vs ТЗ format п.5.1** — «старые делегируют новым» vs «старые содержат функциональность». (Конфликт 2)
4. **[book_tools] ТЗ §2 Assumptions: SAX через constance** — constance не импортируется, выбор захардкожен. (Конфликт 3)
5. **[book_tools] Steering async/await vs Django sync сканирование** — требует отдельного ADR. (Конфликт 4)
6. **[book_tools] Steering новая структура vs ТЗ структура** — конфликт до рефакторинга. (Конфликт 5)
7. **[book_tools] ТЗ-format п.3.6 ложный статус «выполнено»** — fallback сломан. (Конфликт 6)
8. **[sopds_web_backend] Кэш против книжной полки** — steering требует кэш, но searchtype `u` per-user. (Конфликт 1)
9. **[sopds_web_backend] Разбиение SearchBooksView vs сервисный слой** — риск дублирования `SEARCH_BOOK_REGISTRY`. (Конфликт 2)
10. **[sopds_web_backend] admin_optimization.md vs ТЗ Release 2.0** — пункты преждевременны. (Конфликт 3)
11. **[sopds_web_backend] urls_optimization.md §4 — кэш regex не нужен** — Django уже кэширует. (Конфликт 4)

---

## Не делать сейчас (вне скоупа Release 1.0)
- Плагины, read replicas, материализованные представления, Redis, Prometheus/алертинг, WebSocket, 2FA в телеграм-боте, DDoS-защита — пост-2.0.
- Замена `fb2parse.py` — по своему плану ТЗ.

---

## Принципы приоритизации (обоснование)

| Приоритет | Критерий | Примеры |
|-----------|----------|---------|
| **P0** | Security-уязвимости, краш на проде (500), блокируют релиз 1.0 по ТЗ §4 | SEC-1/2/3, БАГ-2, P0-1..6, 1.1..1.5 |
| **P1** | Нарушение ТЗ (покрытие, Never-правила), логические ошибки данных, N+1 | ТЗ-1/2/3, P1-1..14, 1.7..1.10, 2.1..2.17 |
| **P2** | Архитектурный техдолг, дублирование, оптимизации производительности | АРХ-1..10, P2-1..9, 2.1..2.17 |
| **P4** | Мёртвый код, мусор, линтер, конвенции, опечатки | Разд. 3/4, P2-8..15, 3.1..3.9 |

---

## Метрики входа/выхода этапов

| Этап | Вход (DoR) | Выход (DoD) |
|------|------------|-------------|
| **P0** | План создан, ветка `fix/p0-*` | Все P0 закрыты; `ruff check` 0 (E722 включён); `pytest` зелёные; security-аудит чистый |
| **P1** | P0 done; тестовая инфраструктура готова | Покрытие ≥80% по всем трём модулям; mypy clean; N+1 устранены; логи корректны |
| **P2** | P1 done; архитектурные решения зафиксированы (ADR) | Дублирование устранено; `opdsdb` разделено; пагинация SQL; кэш работает; `ebook_parsers` интегрирован/удалён |
| **P4** | P2 done | Репозиторий чист: нет `__pycache__`, `log/`, `tmp/`, мёртвого кода, закомментированных блоков; `.gitignore` актуален; все опечатки исправлены |

---

## Порядок выполнения (рекомендуемый)

1. ~~**Спринт 1 (P0-opds_catalog)**~~ (DONE)
2. ~~**Спринт 2 (P0-book_tools)**~~ (DONE)
3. ~~**Спринт 3 (P0-sopds_web_backend)**~~ (DONE)
4. ~~**Спринт 4 (P1-opds_catalog)**~~ (DONE)
5. ~~**Спринт 5 (P1-book_tools)**~~ (DONE)
6. **Спринт 6 (P1-sopds_web_backend)**: 1.7, 1.8, 2.1, 2.2, 2.7, 2.9, 2.10, 2.16, 2.17
7. **Спринт 7 (P2-архитектура)**: АРХ-2..5, P2-1..9, EPub рефакторинг, `ebook_parsers` решение
8. **Спринт 8 (P2-оптимизации)**: кэширование, индексы, CounterManager, duplicates scanner, telebot
9. **Спринт 9 (P4-гигиена)**: весь мусор из раздела 4 по всем трём модулям

---

*План готов к исполнению через SDD pipeline: ADR → requirements → design → tasks.*
