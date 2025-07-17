from constance import config
from opds_catalog import settings
from opds_catalog.models import Book, bookshelf, Counter, lang_menu

def sopds_processor(request):
    args={}
    args['app_title']=settings.TITLE
    args['sopds_auth']=config.SOPDS_AUTH
    args['sopds_version']=settings.VERSION
    args['alphabet'] = config.SOPDS_ALPHABET_MENU
    args['splititems'] = config.SOPDS_SPLITITEMS
    args['fb2tomobi'] = (config.SOPDS_FB2TOMOBI!="")
    args['fb2toepub'] = (config.SOPDS_FB2TOEPUB!="")
    args['nozip'] = settings.NOZIP_FORMATS
    args['cache_t']=0

    #if config.SOPDS_ALPHABET_MENU:
    if args['alphabet']:
        args['lang_menu'] = lang_menu
    
   # if config.SOPDS_AUTH:
    if args['sopds_auth']:
        user=request.user
        if user.is_authenticated:
            result=[]
            for row in bookshelf.objects.filter(user=user).order_by('-readtime')[:8]:
                book = Book.objects.get(id=row.book_id)
                p = {'id':row.id, 'readtime': row.readtime, 'book_id': row.book_id, 'title': book.title, 'authors':book.authors.values()}
                result.append(p)
            args['bookshelf']=result
 
    # Формируем статистику по каталогу
    stats_data = Counter.obj.all().values()
    stats = { d['name']:d['value'] for d in stats_data }
    stats['lastscan_date'] = [ d['update_time'] for d in stats_data if d['name'] == 'allbooks' ][0]
    args['stats'] = stats
    
    # Поиск случайной книги
    books_count = stats['allbooks']
    if books_count:
        try:
            random_book = Book.objects.values('id', 'title', 'annotation').order_by('?')[:1][0]
        except Book.DoesNotExist:
            random_book= None
    else:
        random_book= None        
                   
    args['random_book'] = random_book
  
    return args

