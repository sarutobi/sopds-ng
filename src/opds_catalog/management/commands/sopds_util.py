from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

# from django.db import connection
# from django.conf import settings as main_settings
from opds_catalog.constants import CAT_INP, CAT_NORMAL, CAT_ZIP
from opds_catalog.db_utils import clear_all, clear_genres, pg_optimize
from opds_catalog.models import Counter
from opds_catalog.services import scanner

# from constance import config


class Command(BaseCommand):
    help = "Utils for SOPDS."
    verbose = False

    def add_arguments(self, parser):
        parser.add_argument(
            "command",
            action="store",
            nargs="*",
            help="Use [ clear | info | save_mygenres | load_mygenres | setconf | getconf | pg_optimize ]",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Set verbosity level for books collection scan.",
        )
        parser.add_argument(
            "--nogenres",
            action="store_true",
            dest="nogenres",
            default=False,
            help="Not install genres fom fixtures.",
        )

    def handle(self, *args, **options):
        if len(options["command"]) > 0:
            action = options["command"][0]
        else:
            import sys

            self.print_help("manage.py", "sopds_util")
            sys.exit(1)

        self.verbose = options["verbose"]
        self.nogenres = options["nogenres"]

        if action == "clear":
            self.stdout.write("Clear book database.")
            self.clear()
        elif action == "info":
            self.info()
        elif action == "save_mygenres":
            self.save_mygenres()
        elif action == "load_mygenres":
            self.load_mygenres()
        elif action == "setconf":
            self.confparam = (
                options["command"][1] if len(options["command"]) > 1 else None
            )
            self.confvalue = (
                options["command"][2] if len(options["command"]) > 2 else None
            )
            self.setconf(self.confparam, self.confvalue)
        elif action == "getconf":
            self.confparam = (
                options["command"][1] if len(options["command"]) > 1 else None
            )
            self.getconf(self.confparam)
        elif action == "pg_optimize":
            self.pg_optimize()

    def clear(self):
        with transaction.atomic():
            clear_all(self.verbose)
        if not self.nogenres:
            call_command("loaddata", "genre.json")
        Counter.objects.update_known_counters()
        pg_optimize(False)

    def info(self):
        Counter.objects.update_known_counters()
        self.stdout.write(
            "Books count    = %s"
            % Counter.objects.get_counter(Counter.counter_allbooks)
        )
        self.stdout.write(
            "Catalogs count = %s"
            % Counter.objects.get_counter(Counter.counter_allcatalogs)
        )
        self.stdout.write(
            "Authors count  = %s"
            % Counter.objects.get_counter(Counter.counter_allauthors)
        )
        self.stdout.write(
            "Genres count   = %s"
            % Counter.objects.get_counter(Counter.counter_allgenres)
        )
        self.stdout.write(
            "Series count   = %s"
            % Counter.objects.get_counter(Counter.counter_allseries)
        )

    def save_mygenres(self):
        call_command(
            "dumpdata",
            "opds_catalog.genre",
            "--output",
            "opds_catalog/fixtures/mygenres.json",
        )
        self.stdout.write("Genre dump saved in opds_catalog/fixtures/mygenres.json")

    def load_mygenres(self):
        clear_genres(self.verbose)
        call_command("loaddata", "mygenres.json")
        Counter.objects.update_known_counters()
        self.stdout.write("Genres load from opds_catalog/fixtures/mygenres.json")

    def setconf(self, confparam, confvalue):
        if confparam and confvalue:
            call_command("constance", "set", confparam, confvalue)
            self.stdout.write("Config parameter %s set to %s" % (confparam, confvalue))

    def getconf(self, confparam):
        if confparam:
            call_command("constance", "get", confparam)
        else:
            call_command("constance", "list")

    def pg_optimize(self):
        pg_optimize(True)
