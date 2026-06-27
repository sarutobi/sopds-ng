"""
Management command to generate fixture data for load testing.

Creates:
- 10,000 authors (Author)
- 100,000 books (Book) with author relationships (bauthor)
- 1 catalog entry

Usage:
    DJANGO_SETTINGS_MODULE=sopds.settings.test python src/manage.py generate_load_test_data
"""

import random
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from opds_catalog.models import (
    Author,
    Book,
    Catalog,
    Counter,
    bauthor,
    counter_allauthors,
    counter_allbooks,
)

FIRST_NAMES = [
    "Иван",
    "Пётр",
    "Алексей",
    "Дмитрий",
    "Сергей",
    "Андрей",
    "Михаил",
    "Николай",
    "Владимир",
    "Александр",
    "Евгений",
    "Виктор",
    "Григорий",
    "Борис",
    "Константин",
    "Лев",
    "Юрий",
    "Василий",
    "Илья",
    "Павел",
    "Роман",
    "Олег",
    "Артём",
    "Максим",
    "John",
    "William",
    "James",
    "Robert",
    "Charles",
    "George",
    "Richard",
    "Edward",
    "Thomas",
    "David",
    "Michael",
    "Henry",
    "Joseph",
    "Frank",
    "Samuel",
    "Daniel",
]

LAST_NAMES = [
    "Иванов",
    "Петров",
    "Сидоров",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Васильев",
    "Зайцев",
    "Соколов",
    "Михайлов",
    "Фёдоров",
    "Морозов",
    "Волков",
    "Алексеев",
    "Лебедев",
    "Семёнов",
    "Егоров",
    "Павлов",
    "Козлов",
    "Степанов",
    "Николаев",
    "Орлов",
    "Макаров",
    "Никитин",
    "Захаров",
    "Зелёный",
    "Белый",
    "Чёрный",
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Wilson",
    "Anderson",
    "Taylor",
    "Thomas",
    "Moore",
]

MIDDLE_NAMES = [
    "Иванович",
    "Петрович",
    "Сергеевич",
    "Александрович",
    "Дмитриевич",
    "Алексеевич",
    "Михайлович",
    "Николаевич",
    "Владимирович",
    "Андреевич",
    "Евгеньевич",
    "Викторович",
    "Борисович",
    "Константинович",
    "Григорьевич",
]

FRAGMENT_PREFIXES = [
    "Война",
    "Мир",
    "Тень",
    "Свет",
    "Ночь",
    "День",
    "Звезда",
    "Планета",
    "Кровь",
    "Честь",
    "Меч",
    "Камень",
    "Ветер",
    "Огонь",
    "Вода",
    "Земля",
    "The",
    "A",
    "Lord",
    "King",
    "Queen",
    "Shadow",
    "Light",
    "Darkness",
]

FRAGMENT_SUFFIXES = [
    "и миров",
    "и надежд",
    "и времени",
    "и судьбы",
    "и вечности",
    "в тумане",
    "на рассвете",
    "в пустоте",
    "забытых снов",
    "бесконечности",
    "of Kings",
    "of Shadows",
    "of the World",
    "of Time",
    "of Eternity",
    "and Peace",
    "and War",
    "and Fire",
    "and Ice",
    "and Fate",
]

FORMATS = ["fb2", "epub", "mobi", "pdf", "djvu"]


def _make_author_name(index: int) -> str:
    """Generate a deterministic author name from an index."""
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    mid = MIDDLE_NAMES[index % len(MIDDLE_NAMES)]
    return f"{last} {first} {mid}"


def _make_book_title(index: int) -> str:
    """Generate a deterministic book title from an index."""
    prefix = FRAGMENT_PREFIXES[index % len(FRAGMENT_PREFIXES)]
    suffix = FRAGMENT_SUFFIXES[
        (index // len(FRAGMENT_PREFIXES)) % len(FRAGMENT_SUFFIXES)
    ]
    return f"{prefix} {suffix} #{index}"


class Command(BaseCommand):
    help = "Generate load test data: 10k authors, 100k books."

    def add_arguments(self, parser):
        parser.add_argument(
            "--authors",
            type=int,
            default=10_000,
            help="Number of authors to create (default: 10,000)",
        )
        parser.add_argument(
            "--books",
            type=int,
            default=100_000,
            help="Number of books to create (default: 100,000)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5_000,
            help="Batch size for bulk_create (default: 5,000)",
        )

    def handle(self, *args, **options):
        num_authors: int = options["authors"]
        num_books: int = options["books"]
        batch_size: int = options["batch_size"]

        self.stdout.write(
            f"Generating {num_authors:,} authors and {num_books:,} books ..."
        )

        # --- Create Catalog ---
        catalog, created = Catalog.objects.get_or_create(
            cat_name="Load Test Catalog",
            defaults={
                "parent": None,
                "path": "load_test/",
                "cat_type": 0,
                "cat_size": 0,
            },
        )
        if created:
            self.stdout.write(f"  Created catalog: {catalog.cat_name}")
        else:
            self.stdout.write(f"  Reusing catalog: {catalog.cat_name}")

        # --- Create Authors ---
        existing_author_count = Author.objects.count()
        if existing_author_count >= num_authors:
            self.stdout.write(
                f"  Already have {existing_author_count} authors, skipping creation."
            )
            all_authors: list[Author] = list(Author.objects.all()[:num_authors])
        else:
            authors_to_create = num_authors - existing_author_count
            self.stdout.write(
                f"  Creating {authors_to_create:,} new authors (already have {existing_author_count}) ..."
            )

            author_objs: list[Author] = []
            for i in range(existing_author_count, num_authors):
                full_name = _make_author_name(i)
                search_name = full_name.lower()
                lang_code = 9  # Other
                author_objs.append(
                    Author(
                        full_name=full_name,
                        search_full_name=search_name,
                        lang_code=lang_code,
                    )
                )

            Author.objects.bulk_create(
                author_objs, batch_size=batch_size, ignore_conflicts=True
            )
            all_authors = list(Author.objects.all()[:num_authors])
            self.stdout.write(
                f"  Created {len(author_objs):,} authors. Total: {Author.objects.count():,}"
            )

        # --- Create Books ---
        existing_book_count = Book.objects.count()
        if existing_book_count >= num_books:
            self.stdout.write(
                f"  Already have {existing_book_count} books, skipping creation."
            )
            return

        books_to_create = num_books - existing_book_count
        self.stdout.write(
            f"  Creating {books_to_create:,} new books (already have {existing_book_count}) ..."
        )

        now = datetime.now(timezone.utc)
        total_book_objs = 0
        total_bauthor_objs = 0
        processed = 0

        while processed < books_to_create:
            current_batch = min(batch_size, books_to_create - processed)

            book_objs: list[Book] = []
            bauthor_objs: list[bauthor] = []

            for j in range(current_batch):
                idx = existing_book_count + processed + j
                title = _make_book_title(idx)
                search_title = title.lower()
                fmt = random.choice(FORMATS)

                book_objs.append(
                    Book(
                        filename=f"book_{idx}.{fmt}",
                        path=f"load_test/book_{idx}.{fmt}",
                        filesize=random.randint(100_000, 5_000_000),
                        format=fmt,
                        catalog=catalog,
                        cat_type=0,
                        registerdate=now,
                        docdate=f"{random.randint(2000, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                        lang="ru",
                        title=title,
                        search_title=search_title,
                        annotation=f"Load test book #{idx}.",
                        lang_code=9,
                        avail=1,
                    )
                )

            Book.objects.bulk_create(
                book_objs, batch_size=batch_size, ignore_conflicts=True
            )
            total_book_objs += len(book_objs)

            # Retrieve the created books to set up author relationships
            created_books = list(
                Book.objects.filter(
                    search_title__in=[b.search_title for b in book_objs]
                ).only("id", "search_title")
            )

            # Build title -> pk lookup
            title_to_pk: dict[str, int] = {b.search_title: b.pk for b in created_books}

            # Create bauthor relationships — each book gets 1-3 random authors
            for b in book_objs:
                pk = title_to_pk.get(b.search_title)
                if pk is None:
                    continue
                num_authors_for_book = random.randint(1, 3)
                chosen_authors = random.sample(
                    all_authors, min(num_authors_for_book, len(all_authors))
                )
                for author in chosen_authors:
                    bauthor_objs.append(bauthor(book_id=pk, author=author))

            if bauthor_objs:
                bauthor.objects.bulk_create(
                    bauthor_objs, batch_size=batch_size, ignore_conflicts=True
                )
                total_bauthor_objs += len(bauthor_objs)

            processed += current_batch
            self.stdout.write(
                f"    Progress: {processed:,} / {books_to_create:,} books "
                f"({total_bauthor_objs:,} author links) ..."
            )

        # Update counters
        Counter.objects.update_known_counters()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created {total_book_objs:,} books, {total_bauthor_objs:,} author links. "
                f"Total authors: {Author.objects.count():,}, Total books: {Book.objects.count():,}"
            )
        )
