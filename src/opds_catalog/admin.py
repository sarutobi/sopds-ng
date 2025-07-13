from django.contrib import admin
from opds_catalog.models import Genre, Book

# Register your models here.
class Genre_admin(admin.ModelAdmin):
    list_display = ('genre', 'section', 'subsection')


class Book_admin(admin.ModelAdmin):
    pass

admin.site.register(Genre, Genre_admin)
admin.site.register(Book, Book_admin)
