import logging

from constance import config
from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.context_processors import csrf
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers

from opds_catalog.models import (
    Author,
    Book,
    Catalog,
    Genre,
    Series,
    bookshelf,
    lang_menu,
)
from opds_catalog.services import (
    authors_services,
    book_services,
    catalog_services,
    genre_services,
    series_services,
)
from opds_catalog.services.catalog_services import DUMMY_CATALOG
from opds_catalog.utils import get_lang_name, to_int
from sopds_web_backend.services import auth_services

BREADCRUMBS = {
    "m": [_("Books"), _("Search by title")],
    "b": [_("Books"), _("Search by title")],
}

logger = logging.getLogger(__name__)


def sopds_login(function=None, redirect_field_name=REDIRECT_FIELD_NAME, url=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated if config.SOPDS_AUTH else True,
        login_url=reverse_lazy(url),
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def get_breadcrumbs(searchtype: str, append: str | None = None) -> list[str]:
    """Возвращает "хлебные крошки" для варианта поиска."""
    result = BREADCRUMBS[searchtype]
    if append is not None:
        result.append(append)
    return result


def _extract_input_parameters(request) -> dict[str, str]:
    args = {}
    args["searchtype"] = request.GET.get("searchtype", "m")
    args["searchterms"] = request.GET.get("searchterms", "")
    args["searchterms0"] = request.GET.get("searchterms0")
    args["page_num"] = request.GET.get("page")
    args["user"] = request.user.username
    return args


def search_book_by_title_match(args):
    args["breadcrumbs"] = [_("Books"), _("Search by title"), args["searchterms"]]
    args["searchobject"] = "title"


# Create your views here.
@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SearchBooksView(request):
    """Диспетчер для обработки параметров запроса книг."""
    SOPDS_AUTH = config.SOPDS_AUTH
    args = {}
    args.update(csrf(request))
    if request.GET:
        args.update(_extract_input_parameters(request))

        try:
            search_res = book_services.search_book_with_metadata(
                args["searchtype"],
                args["searchterms"],
                args["searchterms0"],
                request.user,
            )
        except ValueError:
            search_res = book_services.SearchResult(
                queryset=Book.objects.none(),
                breadcrumbs=[_("Books")],
                search_object="title",
            )

        books = search_res.queryset
        args["breadcrumbs"] = search_res.breadcrumbs
        args["searchobject"] = search_res.search_object
        args["isbookshelf"] = 1 if search_res.is_bookshelf else 0

        page_num = to_int(args.get("page_num"), 1)
        items, op = book_services.paginated_book_content(
            books,
            page_num,
            search_doubles=(args["searchtype"] != "d"),
            user=request.user,
            auth_enabled=SOPDS_AUTH,
        )

        args["paginator"] = op
        args["searchterms"] = args["searchterms"]
        args["searchtype"] = args["searchtype"]
        args["books"] = items
        args["current"] = "search"
        args["cache_id"] = "%s:%s:%s" % (
            args["searchterms"],
            args["searchtype"],
            op["number"],
        )

        args["cache_t"] = 0 if search_res.is_bookshelf else config.SOPDS_CACHE_TIME

    return render(request, "sopds_books.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SearchSeriesView(request):
    args = {}
    args.update(csrf(request))

    if request.GET:
        searchtype = request.GET.get("searchtype", "m")
        searchterms = request.GET.get("searchterms", "")
        page_num = to_int(request.GET.get("page"), 1)

        try:
            res = book_services.search_entities("series", searchtype, searchterms)
        except ValueError:
            res = book_services.EntitySearchResult(
                queryset=Series.objects.none(),
                breadcrumbs=[_("Series")],
                search_object="series",
                current_view="series",
            )

        series_qs = res.queryset
        paginator = Paginator(series_qs, config.SOPDS_MAXITEMS)
        try:
            page = paginator.page(page_num)
        except (EmptyPage, PageNotAnInteger):
            page = paginator.page(paginator.num_pages)

        items = [
            {
                "id": row.id,
                "ser": row.ser,
                "lang_code": row.lang_code,
                "book_count": row.count_book
                if hasattr(row, "count_book")
                else Book.objects.filter(series=row).count(),
            }
            for row in page.object_list
        ]

        from opds_catalog.services.book_services import _paginator_to_dict

        args["paginator"] = _paginator_to_dict(page)
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["series"] = items
        args["searchobject"] = res.search_object
        args["current"] = "search"
        args["breadcrumbs"] = res.breadcrumbs
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, page.number)
        args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_series.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SearchAuthorsView(request):
    args = {}
    args.update(csrf(request))

    if request.GET:
        searchtype = request.GET.get("searchtype", "m")
        searchterms = request.GET.get("searchterms", "")
        page_num = to_int(request.GET.get("page"), 1)

        try:
            res = book_services.search_entities("author", searchtype, searchterms)
        except ValueError:
            res = book_services.EntitySearchResult(
                queryset=Author.objects.none(),
                breadcrumbs=[_("Authors")],
                search_object="author",
                current_view="authors",
            )

        authors_qs = res.queryset
        paginator = Paginator(authors_qs, config.SOPDS_MAXITEMS)
        try:
            page = paginator.page(page_num)
        except (EmptyPage, PageNotAnInteger):
            page = paginator.page(paginator.num_pages)

        items = [
            {
                "id": row.id,
                "full_name": row.full_name,
                "lang_code": row.lang_code,
                "book_count": row.book_count
                if hasattr(row, "book_count")
                else Book.objects.filter(authors=row).count(),
            }
            for row in page.object_list
        ]

        from opds_catalog.services.book_services import _paginator_to_dict

        args["paginator"] = _paginator_to_dict(page)
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["authors"] = items
        args["searchobject"] = res.search_object
        args["current"] = "search"
        args["breadcrumbs"] = res.breadcrumbs
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, page.number)
        args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_authors.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def CatalogsView(request):
    args = {}

    if request.GET:
        cat_id = request.GET.get("cat", None)
        page_num = int(request.GET.get("page", "1"))
    else:
        cat_id = None
        page_num = 1

    try:
        if cat_id is not None:
            cat = Catalog.objects.get(id=cat_id)
        else:
            cat = Catalog.objects.get(parent__id=cat_id)
    except Catalog.DoesNotExist:
        cat = None

    items, op = catalog_services.paginated_catalog_content(
        cat or DUMMY_CATALOG,
        page_num,
        config.SOPDS_MAXITEMS,
        user=request.user,
        auth_enabled=config.SOPDS_AUTH,
    )

    args["paginator"] = op
    args["items"] = items
    args["cat_id"] = cat_id
    args["current"] = "catalog"

    breadcrumbs_list = []
    if cat:
        while cat.parent:
            breadcrumbs_list.insert(0, (cat.cat_name, cat.id))
            cat = cat.parent
        breadcrumbs_list.insert(0, (_("ROOT"), 0))
    # breadcrumbs_list.insert(0, (_('Catalogs'),-1))
    args["breadcrumbs_cat"] = breadcrumbs_list
    args["breadcrumbs"] = [_("Catalogs")]
    args["cache_id"] = "%s:%s:%s" % (args["current"], cat_id, op["number"])
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_catalogs.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def BooksView(request):
    args = {}

    if request.GET:
        lang_code = to_int(request.GET.get("lang"))
        chars = request.GET.get("chars", "")
    else:
        lang_code = 0
        chars = ""

    length = len(chars) + 1

    items = book_services.find_books_by_template(chars, length, lang_code)

    args["items"] = items
    args["current"] = "book"
    args["lang_code"] = lang_code
    args["breadcrumbs"] = [_("Books"), _("Select"), lang_menu[lang_code], chars]
    args["cache_id"] = "%s:%s:%s" % (args["current"], lang_code, chars)
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_selectbook.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def AuthorsView(request):
    args = {}

    if request.GET:
        lang_code = to_int(request.GET.get("lang"))
        chars = request.GET.get("chars", "")
    else:
        lang_code = 0
        chars = ""

    length = len(chars) + 1

    items = authors_services.find_authors_by_template(chars, length, lang_code)

    args["items"] = items
    args["current"] = "author"
    args["lang_code"] = lang_code
    args["breadcrumbs"] = [_("Authors"), _("Select"), lang_menu[lang_code], chars]
    args["cache_id"] = "%s:%s:%s" % (args["current"], lang_code, chars)
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_selectauthor.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SeriesView(request):
    args = {}

    if request.GET:
        lang_code = int(request.GET.get("lang", "0"))
        chars = request.GET.get("chars", "")
    else:
        lang_code = 0
        chars = ""

    length = len(chars) + 1

    items = series_services.get_series(chars, length, lang_code)

    args["items"] = items
    args["current"] = "series"
    args["lang_code"] = lang_code
    args["breadcrumbs"] = [_("Series"), _("Select"), lang_menu[lang_code], chars]
    args["cache_id"] = "%s:%s:%s" % (args["current"], lang_code, chars)
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_selectseries.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def GenresView(request):
    args = {}

    if request.GET:
        section_id = to_int(request.GET.get("section"))
    else:
        section_id = 0

    if section_id == 0:
        items = genre_services.get_genres()
        args["breadcrumbs"] = [_("Genres"), _("Select")]
    else:
        section = genre_services.get_genre_section(section_id)
        items = genre_services.get_genre_details(section_id)
        args["breadcrumbs"] = [_("Genres"), _("Select"), section]

    args["items"] = items
    args["current"] = "genre"
    args["parent_id"] = section_id
    args["cache_id"] = "%s:%s" % (args["current"], section_id)
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_selectgenres.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
# g @sopds_login(url="web:login")
def SearchSuggestView(request):
    """Подсказки для строки поиска через htmx."""
    logger.info("Suggestion helper")

    if request.method == "POST":
        q = request.POST.get("searchterms", "").strip()
        search_type = request.POST.get("type", "title")
    elif request.method == "GET":
        q = request.GET.get("searchterms", "").strip()
        search_type = request.GET.get("type", "title")
    else:
        return HttpResponseNotAllowed(["GET", "POST"])

    logger.info(f"Suggestion request '{q}' type '{search_type}'")

    if len(q) < 2:
        logger.info("suggestion query too short")
        return HttpResponse("")

    if search_type == "title":
        logger.info(f"Suggest books by title '{q}'")
        items = Book.objects.filter(search_title__contains=q.upper())[:10]
    elif search_type == "author":
        items = Author.objects.filter(search_full_name__contains=q.upper())[:10]
    elif search_type == "series":
        items = Series.objects.filter(search_ser__contains=q.upper())[:10]
    else:
        items = []

    return render(
        request,
        "sopds_search_suggestions.html",
        {"items": items, "search_type": search_type},
    )


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
@require_http_methods(["GET", "DELETE"])
def BSDelView(request):
    if request.GET:
        book = request.GET.get("book", None)
    else:
        book = None

    book = int(book)

    bookshelf.objects.filter(user=request.user, book=book).delete()

    if request.headers.get("HX-Request") == "true":
        return HttpResponse(
            status=200,
            headers={
                "HX-Redirect": "%s?searchtype=u&page=1" % reverse("web:searchbooks")
            },
        )

    return redirect("%s?searchtype=u" % reverse("web:searchbooks"))


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def BSClearView(request):
    bookshelf.objects.filter(user=request.user).delete()
    return redirect("%s?searchtype=u" % reverse("web:searchbooks"))


def hello(request):
    args = {}
    args["breadcrumbs"] = [_("HOME")]
    return render(request, "sopds_hello.html", args)


def LoginView(request):
    args = {}
    args["breadcrumbs"] = [_("Login")]
    args.update(csrf(request))
    try:
        username = request.POST["username"]
        password = request.POST["password"]
    except KeyError:
        return render(request, "sopds_login.html", args)

    # Rate limiting
    ip = request.META.get("REMOTE_ADDR", "unknown")
    if auth_services.is_rate_limited(ip):
        return HttpResponse(
            _("Too many login attempts. Please try again later."), status=429
        )

    next_url = request.GET.get("next", reverse("web:main"))

    # Валидация next_url для предотвращения open redirect
    allowed_hosts = {request.get_host()}
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts=allowed_hosts,
        require_https=False,
    ):
        next_url = reverse("web:main")

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_services.reset_attempts(ip)
            login(request, user)
            return redirect(next_url)
        else:
            args["system_message"] = {
                "text": _("This account is not active!"),
                "type": "alert",
            }
            return handler403(request, args)
    else:
        auth_services.record_failed_attempt(ip)
        args["system_message"] = {
            "text": _("User does not exist or the password is incorrect!"),
            "type": "alert",
        }
        return handler403(request, args)
    # return render(request, 'sopds_login.html', args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def LogoutView(request):
    logout(request)
    args = {}
    args["breadcrumbs"] = [_("Logout")]
    return redirect(reverse("web:main"))


def handler403(request, args):
    response = render(request, "sopds_login.html", args)
    response.status_code = 403
    return response
