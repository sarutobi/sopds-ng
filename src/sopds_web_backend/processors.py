from random import randint

from constance import config
from django.db.models import Max

from opds_catalog import settings
from opds_catalog.models import Book, Counter, bookshelf, lang_menu


def sopds_processor(request):
    args = {}
    args["app_title"] = settings.TITLE
    args["sopds_auth"] = config.SOPDS_AUTH
    args["sopds_version"] = settings.VERSION
    args["alphabet"] = config.SOPDS_ALPHABET_MENU
    args["splititems"] = config.SOPDS_SPLITITEMS
    args["fb2tomobi"] = config.SOPDS_FB2TOMOBI != ""
    args["fb2toepub"] = config.SOPDS_FB2TOEPUB != ""
    args["nozip"] = settings.NOZIP_FORMATS
    args["cache_t"] = 0

    # if config.SOPDS_ALPHABET_MENU:
    if args["alphabet"]:
        args["lang_menu"] = lang_menu

    # if config.SOPDS_AUTH:
    if args["sopds_auth"]:
        user = request.user
        if user.is_authenticated:
            result = []
            # Оптимизация N+1: используем select_related и prefetch_related
            shelf_items = (
                bookshelf.objects.filter(user=user)
                .select_related("book")
                .prefetch_related("book__authors")
                .order_by("-readtime")[:8]
            )
            for row in shelf_items:
                book = row.book
                p = {
                    "id": row.id,
                    "readtime": row.readtime,
                    "book_id": book.id,
                    "title": book.title,
                    "authors": list(book.authors.values()),
                }
                result.append(p)
            args["bookshelf"] = result

    # Формируем статистику по каталогу
    stats_data = list(Counter.obj.all().values())
    stats = {d["name"]: d["value"] for d in stats_data}
    lastscan = [d["update_time"] for d in stats_data if d["name"] == "allbooks"]
    stats["lastscan_date"] = lastscan[0] if lastscan else None
    args["stats"] = stats

    # Поиск случайной книги
    books_count = stats.get("allbooks", 0)
    if books_count:
        try:
            # Эффективный поиск случайной записи без OFFSET:
            # 1. Получаем максимальный ID
            max_id = Book.objects.aggregate(max_id=Max("id"))["max_id"]
            if max_id:
                # 2. Генерируем случайный ID в диапазоне [1, max_id]
                random_id = randint(1, max_id)
                # 3. Берем первую запись с id >= random_id (O(log N) индексный поиск)
                random_book = (
                    Book.objects.filter(id__gte=random_id)
                    .values("id", "title", "annotation")
                    .first()
                )
        except Exception:
            random_book = None
    else:
        random_book = None

    args["random_book"] = random_book

    return args
