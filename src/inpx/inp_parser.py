INP_DELIMITER = chr(0x04)
FIELD_SEPARATOR = ":"
VALUE_SEPARATOR = ","

INP_STANDARD = (
    "AUTHOR",
    "GENRE",
    "TITLE",
    "SERIES",
    "SERNO",
    "FILE",
    "SIZE",
    "LIBID",
    "DEL",
    "EXT",
    "DATE",
)
INP_EXTENDED = (
    "AUTHOR",
    "GENRE",
    "TITLE",
    "SERIES",
    "SERNO",
    "FILE",
    "SIZE",
    "LIBID",
    "DEL",
    "EXT",
    "DATE",
    "INSNO",
    "FOLDER",
)
INP_FULL = (
    "AUTHOR",
    "GENRE",
    "TITLE",
    "SERIES",
    "SERNO",
    "FILE",
    "SIZE",
    "LIBID",
    "DEL",
    "EXT",
    "DATE",
    "LANG",
    "INSNO",
    "FOLDER",
    "LIBRATE",
    "KEYWORDS",
)

MY_FORMAT = (
    "AUTHOR",
    "GENRE",
    "TITLE",
    "SERIES",
    "SERNO",
    "FILE",
    "SIZE",
    "LIBID",
    "DEL",
    "EXT",
    "DATE",
    "LANG",
    "INSNO",
    "FOLDER",
    "LIBRATE",
    "KEYWORDS",
)


def get_inp_structure(descriptor):
    """Определяем пользоовательский формат inp."""
    return descriptor.split(";")


def read_lines(file_name):
    """lines generator"""
    try:
        with open(file_name, "r") as inp:
            for line in inp:
                yield line.strip("\n")
    except FileNotFoundError:
        print("No such file ")
    except Exception:
        print("Unknown exception !")


def extract_inp_record(line):
    parts = line.split(INP_DELIMITER)
    _l = len(parts)
    if _l < 11:
        raise ValueError("Error: Unknown inp file format")
    archive = None

    if _l == 11:  # Standard
        parts.append(None)
    elif _l == 15:  # Extended
        parts = parts[:12]
    elif _l == 17:  # Full
        archive = parts[12]
        lang = parts[13]
        parts = parts[:11] + [lang]

    return archive, parts


def split_multifield(value):
    """Разделение поля, содержащего несколько значений, на набор полей"""
    fields = [f for f in value.split(FIELD_SEPARATOR) if f != ""]
    return fields


def build_author_name(value):
    chunks = value.split(",")
    surname = chunks[0].strip()
    if len(chunks) == 3:
        patronymic = chunks[2]
    else:
        patronymic = ""
    if len(chunks) > 1:
        name = chunks[1]
    return surname, name, patronymic


for line in read_lines("./online.inp"):
    archive, data = extract_inp_record(line)
    (
        authors,
        genres,
        title,
        series,
        ser_no,
        file,
        size,
        lib_id,
        deleted,
        suffix,
        date,
        lang,
    ) = data
#    authors = split_multifield(authors)
#    print(authors)
#    for a in authors:
#        print(build_author_name(a))
#    print(split_multifield(genres))
#    print("Title", title)
#    print("Series",series)
#    print("Ser_no", ser_no)
#    print(file, suffix)
#    print("Size", size)
#    print("Lib_id",lib_id)
#    print("Deleted", deleted)
#    print(date)
#    print(lang)
