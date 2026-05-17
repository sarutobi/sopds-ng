from opds_catalog.services import (
    authors_services,
    book_services,
    series_services,
    genre_services,
)
from django.shortcuts import render, redirect
from django.template.context_processors import csrf
from django.db.models import Count, Prefetch
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate, login, logout, REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.vary import vary_on_headers
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags

from opds_catalog.models import (
    Book,
    Author,
    Series,
    bookshelf,
    Catalog,
    Genre,
    lang_menu,
)

from constance import config
from opds_catalog.opds_paginator import Paginator as OPDS_Paginator
from opds_catalog.utils import get_lang_name, to_int

from sopds_web_backend.settings import HALF_PAGES_LINKS

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
    args["user"] = request.user.usernname
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
        if args["searchtype"] in "mb":
            args["breadcrumbs"] = [_("Books"), _("Search by title"), searchterms]
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
                section: str = Genre.objects.get(id=args["searchterms"]).section
                subsection: str = Genre.objects.get(id=args["searchterms"]).subsection
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
            # try:
            book_id = int(args["searchterms"])
            mbook = Book.objects.get(id=book_id)
            books = (
                Book.objects.filter(title=mbook.title, authors__in=mbook.authors.all())
                .exclude(id=book_id)
                .distinct()
                .order_by("-docdate")
            )
            args["breadcrumbs"] = [_("Books"), _("Doubles for book"), mbook.title]
            args["searchobject"] = "title"

        # Поиск книги по ID. Хотел найти еще и дубликаты к книге, но почему-то не работает запрос правильно. Ума не приложу почему.
        elif args["searchtype"] == "i":
            try:
                book_id = int(searchterms)
                # mbook = Book.objects.get(id=book_id)
            except:
                book_id = 0
                # mbook = None
            books = Book.objects.filter(id=book_id)
            args["breadcrumbs"] = [_("Books"), books[0].title]
            # books = Book.objects.filter(title=mbook.title, authors__in=mbook.authors.all()).distinct().order_by('-docdate')
            # args['breadcrumbs'] = [_('Books'),mbook.title]
            args["searchobject"] = "title"

        # prefetch_related on sqlite on items >999 therow error "too many SQL variables"
        # if len(books)>0:
        #    books = books.select_related('authors','genres','series')

        # Добавляем Left Join с таблицей BookShelfб чтобы вытащить дату прочтения книги из книжной полки
        # books = books.filter(Q(bookshelf__isnull=True)|Q(bookshelf__user=request.user))
        # books = books.prefetch_related('bookshelf_set')
        # print(books.query)

        # Фильтруем дубликаты и формируем выдачу затребованной страницы
        books = books.prefetch_related(
            Prefetch("authors", to_attr="c_authors"),
            Prefetch("series", to_attr="c_series"),
            Prefetch("genres", to_attr="c_genres"),
        )
        books_count = books.count()
        op = OPDS_Paginator(
            books_count, 0, page_num, config.SOPDS_MAXITEMS, HALF_PAGES_LINKS
        )
        items = []

        prev_title = ""
        prev_authors_set = set()

        # Начаинам анализ с последнего элемента на предидущей странице, чторбы он "вытянул" с этой страницы
        # свои дубликаты если они есть
        summary_DOUBLES_HIDE = config.SOPDS_DOUBLES_HIDE and (args["searchtype"] != "d")
        start = (
            op.d1_first_pos
            if ((op.d1_first_pos == 0) or (not summary_DOUBLES_HIDE))
            else op.d1_first_pos - 1
        )
        finish = op.d1_last_pos

        for row in books[start : finish + 1]:
            p = {
                "doubles": 0,
                "lang_code": row.lang_code,
                "filename": row.filename,
                "path": row.path,
                "registerdate": row.registerdate,
                "id": row.id,
                "annotation": strip_tags(row.annotation),
                "docdate": row.docdate,
                "format": row.format,
                "title": row.title,
                "lang": get_lang_name(row.lang),
                "filesize": row.filesize,
                "authors": row.c_authors,
                "genres": row.c_genres,
                "series": row.c_series,
                "ser_no": row.bseries_set.values("ser_no"),
                #'readtime':row.bookshelf_set.filter(user=request.user).values('readtime') if config.SOPDS_AUTH else None
                "readtime": row.bookshelf_set.filter(user=request.user).values(
                    "readtime"
                )
                if SOPDS_AUTH
                else None,
            }
            if summary_DOUBLES_HIDE:
                title: str = p["title"]
                authors_set = {a.id for a in p["authors"]}
                if (
                    title.upper() == prev_title.upper()
                    and authors_set == prev_authors_set
                ):
                    items[-1]["doubles"] += 1
                else:
                    items.append(p)
                prev_title = title
                prev_authors_set = authors_set
            else:
                items.append(p)

        # "вытягиваем" дубликаты книг со следующей страницы и удаляем первый элемент который с предыдущей страницы и "вытягивал" дубликаты с текущей
        if summary_DOUBLES_HIDE:
            double_flag = True
            while ((finish + 1) < books_count) and double_flag:
                finish += 1
                if (
                    books[finish].title.upper() == prev_title.upper()
                    and {a["id"] for a in books[finish].authors.values()}
                    == prev_authors_set
                ):
                    items[-1]["doubles"] += 1
                else:
                    double_flag = False

            if op.d1_first_pos != 0:
                items.pop(0)

        args["paginator"] = op.get_data_dict()
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["books"] = items
        args["current"] = "search"
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, op.page_num)

        if searchtype == "u":
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

        if searchtype == "m":
            series = Series.objects.filter(search_ser__contains=searchterms.upper())
        elif searchtype == "b":
            series = Series.objects.filter(search_ser__startswith=searchterms.upper())
        elif searchtype == "e":
            series = Series.objects.filter(search_ser=searchterms.upper())

        # if len(series)>0:
        #    series = series.order_by('ser')
        series = (
            series.annotate(count_book=Count("book")).distinct().order_by("search_ser")
        )

        # Создаем результирующее множество
        series_count = series.count()
        op = OPDS_Paginator(
            series_count, 0, page_num, config.SOPDS_MAXITEMS, HALF_PAGES_LINKS
        )
        items = []
        for row in series[op.d1_first_pos : op.d1_last_pos + 1]:
            # p = {'id':row.id, 'ser':row.ser, 'lang_code': row.lang_code, 'book_count': Book.objects.filter(series=row).count()}
            p = {
                "id": row.id,
                "ser": row.ser,
                "lang_code": row.lang_code,
                "book_count": row.count_book,
            }
            items.append(p)

        args["paginator"] = op.get_data_dict()
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["series"] = items
        args["searchobject"] = "series"
        args["current"] = "search"
        args["breadcrumbs"] = [_("Series"), _("Search"), searchterms]
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, op.page_num)
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
        authors = authors_services.search_authors(searchtype, searchterms)
        # Создаем результирующее множество
        authors_count = authors.count()
        op = OPDS_Paginator(
            authors_count, 0, page_num, config.SOPDS_MAXITEMS, HALF_PAGES_LINKS
        )
        items = []

        for row in authors[op.d1_first_pos : op.d1_last_pos + 1]:
            p = {
                "id": row.id,
                "full_name": row.full_name,
                "lang_code": row.lang_code,
                "book_count": Book.objects.filter(authors=row).count(),
            }
            items.append(p)

        args["paginator"] = op.get_data_dict()
        args["searchterms"] = searchterms
        args["searchtype"] = searchtype
        args["authors"] = items
        args["searchobject"] = "author"
        args["current"] = "search"
        args["breadcrumbs"] = [_("Authors"), _("Search"), searchterms]
        args["cache_id"] = "%s:%s:%s" % (searchterms, searchtype, op.page_num)
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

    catalogs_list = Catalog.objects.filter(parent=cat).order_by("cat_name")
    catalogs_count = catalogs_list.count()
    # prefetch_related on sqlite on items >999 therow error "too many SQL variables"
    # books_list = Book.objects.filter(catalog=cat).prefetch_related('authors','genres','series').order_by("title")
    books_list = Book.objects.filter(catalog=cat).order_by("search_title")
    books_count = books_list.count()

    # Получаем результирующий список
    op = OPDS_Paginator(
        catalogs_count, books_count, page_num, config.SOPDS_MAXITEMS, HALF_PAGES_LINKS
    )
    items = []

    for row in catalogs_list[op.d1_first_pos : op.d1_last_pos + 1]:
        p = {
            "is_catalog": 1,
            "title": row.cat_name,
            "id": row.id,
            "cat_type": row.cat_type,
            "parent_id": row.parent_id,
        }
        items.append(p)

    for row in books_list[op.d2_first_pos : op.d2_last_pos + 1]:
        p = {
            "is_catalog": 0,
            "lang_code": row.lang_code,
            "filename": row.filename,
            "path": row.path,
            "registerdate": row.registerdate,
            "id": row.id,
            "annotation": strip_tags(row.annotation),
            "docdate": row.docdate,
            "format": row.format,
            "title": row.title,
            "lang": row.lang,
            "filesize": row.filesize,
            "authors": row.authors.values(),
            "genres": row.genres.values(),
            "series": row.series.values(),
            "ser_no": row.bseries_set.values("ser_no"),
            #'readtime': row.bookshelf_set.filter(user=request.user).values('readtime') if config.SOPDS_AUTH else None
            "readtime": row.bookshelf_set.filter(user=request.user).values("readtime")
            if config.SOPDS_AUTH
            else None,
        }
        items.append(p)

    args["paginator"] = op.get_data_dict()
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
    args["cache_id"] = "%s:%s:%s" % (args["current"], cat_id, op.page_num)
    args["cache_t"] = config.SOPDS_CACHE_TIME

    return render(request, "sopds_catalogs.html", args)


@vary_on_headers("HTTP_ACCEPT_LANGUAGE")
@sopds_login(url="web:login")
def BooksView(request):
    args = {}

    if request.GET:
        lang_code = to_int(request.GET.get("lang"))
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
