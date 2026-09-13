from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt

from opds_catalog.models import Author, Book, Genre, Series


class GenreAdmin(admin.ModelAdmin):
    list_display = ("genre", "section", "subsection")
    search_fields = ("genre", "section", "subsection")


class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "lang", "format", "filesize")
    search_fields = ("title", "search_title")
    list_filter = ("format", "lang")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            re_path(
                r"^(?P<pk>\d+)/inline-save/$",
                self.admin_site.admin_view(self.inline_save_view),
                name="opds_catalog_book_inline_save",
            ),
        ]
        return custom_urls + urls

    @csrf_exempt
    def inline_save_view(self, request, pk):
        """Inline-редактирование поля книги из списка админки."""
        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=405)

        if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "AJAX required"}, status=400)

        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        field = request.POST.get("field")
        value = request.POST.get("value")

        allowed_fields = {"title"}
        if field not in allowed_fields:
            return JsonResponse({"error": f"Field '{field}' not allowed"}, status=400)

        setattr(book, field, value)
        if field == "title":
            book.search_title = value.upper()
        book.save(update_fields=[field, "search_title"])

        return JsonResponse({"ok": True, "value": value})


class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "lang_code")
    search_fields = ("full_name", "search_full_name")


class SeriesAdmin(admin.ModelAdmin):
    list_display = ("ser", "lang_code")
    search_fields = ("ser", "search_ser")


admin.site.register(Genre, GenreAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Series, SeriesAdmin)
