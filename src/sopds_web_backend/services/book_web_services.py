from django.utils.translation import gettext as _

from opds_catalog.config import catalog_config
from opds_catalog.models import Book
from opds_catalog.services import book_services
from opds_catalog.utils import to_int


def get_search_books_context(request, params: dict) -> dict:
    """
    Подготавливает контекст для SearchBooksView.
    Выносит бизнес-логику поиска и пагинации из view.
    """
    auth_enabled = catalog_config.AUTH_ENABLED

    try:
        search_res = book_services.search_book_with_metadata(
            params["searchtype"],
            params["searchterms"],
            params["searchterms0"],
            request.user,
        )
    except ValueError:
        search_res = book_services.SearchResult(
            queryset=Book.objects.none(),
            breadcrumbs=[_("Books")],
            search_object="title",
        )

    books = search_res.queryset

    page_num = to_int(params.get("page_num"), 1)
    if page_num < 1:
        page_num = 1

    items, op = book_services.paginated_book_content(
        books,
        page_num,
        search_doubles=(params["searchtype"] == "d"),
        user=request.user,
        auth_enabled=auth_enabled,
    )

    # Формируем итоговый контекст
    context = {
        "books": items,
        "paginator": op,
        "breadcrumbs": search_res.breadcrumbs,
        "searchobject": search_res.search_object,
        "isbookshelf": 1 if search_res.is_bookshelf else 0,
        "searchterms": params["searchterms"],
        "searchtype": params["searchtype"],
        "current": "search",
        "cache_id": f"{params['searchterms']}:{params['searchtype']}:{op['number']}",
        "cache_t": 0 if search_res.is_bookshelf else catalog_config.CACHE_TIME,
    }

    return context
