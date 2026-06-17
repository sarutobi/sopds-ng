from constance import config
from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.template.context_processors import csrf
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.views.decorators.vary import vary_on_headers

from opds_catalog.models import (
    Book,
    Catalog,
    Genre,
    Series,
    bookshelf,
    lang_menu,
)
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from opds_catalog.services import (
    authors_services,
    book_services,
    catalog_services,
    genre_services,
    series_services,
)
from opds_catalog.services.catalog_services import DUMMY_CATALOG
from opds_catalog.utils import get_lang_name, to_int

BREADCRUMBS = {
    "m": [_("Books"), _("Search by title")],
    "b": [_("Books"), _("Search by title")],
}


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
    """Диспетчер для обработки параемтров запроса книг."""
    SOPDS_AUTH = config.SOPDS_AUTH
    args = {}
    args.update(csrf(request))
    if request.GET:
        args.update(_extract_input_parameters(request))

        books = book_services.search_book(
            args["searchtype"], args["searchterms"], args["searchterms0"], args["user"]
        )
        if args["searchtype"] in ("m", "b"):
            args["breadcrumbs"] = [
                _("Books"),
                _("Search by title"),
                args["searchterms"],
            ]
            args["searchobject"] = "title"

        elif args["searchtype"] == "a":
            aname = authors_services.get_author_name(id=args["searchterms"])
            args["breadcrumbs"] = [_("Books"), _("Search by author"), aname]
            args["searchobject"] = "author"

        # Поиск книг по серии
        elif args["searchtype"] == "s":
            ser = series_services.get_series_name(args["searchterms"])
            # books = Book.objects.filter(series=ser_id).order_by('search_title','-docdate')
            args["breadcrumbs"] = [_("Books"), _("Search by series"), ser]
            args["searchobject"] = "series"

        # Поиск книг по жанру
        elif args["searchtype"] == "g":
            try:
                genre = Genre.objects.get(id=args["searchterms"])
                section = genre.section
                subsection = genre.subsection
                args["breadcrumbs"] = [
                    _("Books"),
                    _("Search by genre"),
                    section,
                    subsection,
                ]
            except:
                args["breadcrumbs"] = [_("Books"), _("Search by genre")]

            args["searchobject"] = "genre"

        # Поиск книг на книжной полке
        elif args["searchtype"] == "u":
            # if config.SOPDS_AUTH:
            if SOPDS_AUTH:
                books = Book.objects.filter(bookshelf__user=request.user).order_by(
                    "-bookshelf__readtime"
                )
                args["breadcrumbs"] = [
                    _("Books"),
                    _("Bookshelf"),
                    args["user"],
                ]
                # books = bookshelf.objects.filter(user=request.user).select_related('book')
            else:
                books = Book.objects.filter(id=0)
                args["breadcrumbs"] = [_("Books"), _("Bookshelf")]
            args["searchobject"] = "title"
            args["isbookshelf"] = 1

        # Поиск дубликатов для книги
        elif args["searchtype"] == "d":
            book_id = int(args["searchterms"])  # type: ignore[call-overload]
            mbook = Book.objects.get(id=book_id)
            books = (
                Book.objects.filter(title=mbook.title, authors__in=mbook.authors.all())
                .exclude(id=book_id)
                .distinct()
                .order_by("-docdate")
            )
            args["breadcrumbs"] = [_("Books"), _("Doubles for book"), mbook.title]
            args["searchobject"] = "title"

        # Поиск книги по ID
        elif args["searchtype"] == "i":
            book_id = to_int(args["searchterms"], 0)
            books = Book.objects.filter(id=book_id)
            try:
                args["breadcrumbs"] = [_("Books"), books[0].title]
            except IndexError:
                args["breadcrumbs"] = [_("Books")]
            args["searchobject"] = "title"

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

        if args["searchtype"] == "u":
            args["cache_t"] = 0
        else:
            args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_books.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SearchSeriesView(request):
    # Read searchtype, searchterms, searchterms0, page from form
    args = {}
    args.update(csrf(request))

    if request.GET:
        searchtype = request.GET.get("searchtype", "m")
        searchterms = request.GET.get("searchterms", "")
        # searchterms0 = int(request.POST.get('searchterms0', ''))
        page_num = int(request.GET.get("page", "1"))
        page_num = page_num if page_num > 0 else 1

        series = series_services.search_series(searchtype, searchterms)

        # Создаем результирующее множество
        paginator = Paginator(series, config.SOPDS_MAXITEMS)
        try:
            page = paginator.page(page_num)
        except (EmptyPage, PageNotAnInteger):
            page = paginator.page(paginator.num_pages)
        items = []
        for row in page.object_list:
            p = {
                "id": row.id,
                "ser": row.ser,
                "lang_code": row.lang_code,
                "book_count": row.count_book,
            }
            items.append(p)

        args["paginator"] = {
            "num_pages": paginator.num_pages,
            "has_previous": page.has_previous(),
            "has_next": page.has_next(),
            "previous_page_number": page.previous_page_number()
            if page.has_previous()
            else 1,
            "next_page_number": page.next_page_number()
            if page.has_next()
            else paginator.num_pages,
            "number": page.number,
            "page_range": list(paginator.page_range),
        }
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["series"] = items
        args["searchobject"] = "series"
        args["current"] = "search"
        args["breadcrumbs"] = [_("Series"), _("Search"), searchterms]
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, page.number)
        args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_series.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def SearchAuthorsView(request):
    # Read searchtype, searchterms, searchterms0, page from form
    args = {}
    args.update(csrf(request))

    if request.GET:
        searchtype = request.GET.get("searchtype", "m")
        searchterms = request.GET.get("searchterms", "")
        # searchterms0 = int(request.POST.get('searchterms0', ''))
        page_num = int(request.GET.get("page", "1"))
        page_num = page_num if page_num > 0 else 1

        # if searchtype == "m":
        #     authors = Author.objects.filter(
        #         search_full_name__contains=searchterms.upper()
        #     ).order_by("search_full_name")
        # elif searchtype == "b":
        #     authors = Author.objects.filter(
        #         search_full_name__startswith=searchterms.upper()
        #     ).order_by("search_full_name")
        # elif searchtype == "e":
        #     authors = Author.objects.filter(
        #         search_full_name=searchterms.upper()
        #     ).order_by("search_full_name")
        authors = authors_services.search_authors_with_counts(searchtype, searchterms)
        paginator = Paginator(authors, config.SOPDS_MAXITEMS)
        try:
            page = paginator.page(page_num)
        except (EmptyPage, PageNotAnInteger):
            page = paginator.page(paginator.num_pages)
        items = []

        for row in page.object_list:
            p = {
                "id": row.id,
                "full_name": row.full_name,
                "lang_code": row.lang_code,
                "book_count": row.book_count,
            }
            items.append(p)

        args["paginator"] = {
            "num_pages": paginator.num_pages,
            "has_previous": page.has_previous(),
            "has_next": page.has_next(),
            "previous_page_number": page.previous_page_number()
            if page.has_previous()
            else 1,
            "next_page_number": page.next_page_number()
            if page.has_next()
            else paginator.num_pages,
            "number": page.number,
            "page_range": list(paginator.page_range),
        }
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["authors"] = items
        args["searchobject"] = "author"
        args["current"] = "search"
        args["breadcrumbs"] = [_("Authors"), _("Search"), searchterms]
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
@sopds_login(url="web:login")
def BSDelView(request):
    if request.GET:
        book = request.GET.get("book", None)
    else:
        book = None

    book = int(book)

    bookshelf.objects.filter(user=request.user, book=book).delete()

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

    next_url = request.GET.get("next", reverse("web:main"))

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            return redirect(next_url)
        else:
            args["system_message"] = {
                "text": _("This account is not active!"),
                "type": "alert",
            }
            return handler403(request, args)
            # return render(request, 'sopds_login.html', args)
    else:
        args["system_message"] = {
            "text": _("User does not exist or the password is incorrect!"),
            "type": "alert",
        }
        return handler403(request, args)
        # return render(request, 'sopds_login.html', args)

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
