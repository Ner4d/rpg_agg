import io
import re
from datetime import datetime

import PIL
from celery import shared_task
from django.conf import settings
from PIL import Image
from urllib3.contrib.socks import SOCKSProxyManager

from news.models import GameModel, GameNewsPost

# Для запросов через прокси
proxy = SOCKSProxyManager(settings.PROXY)


def save_image(path, image_url):
    """
    Функция для сохранения изображений, io.BytesIO отрисовывает картинку на основе b-строки, так как при получении
    картинки прямым путем через протокол socks у меня не вышло, а при авторизации прокси через http возникала ошибка
    Image позволяет подогнать картинку под необходимый размер и формат и сохранить
    """
    # Получаем данные об изображении
    image = proxy.request('GET', image_url)
    # Отрисовываем
    image = io.BytesIO(image.data)
    # Если картинка не отрисована
    try:
        image = Image.open(image)
    # Возвращаем False
    except PIL.UnidentifiedImageError:
        return False
    # Подгоняем под необходимый размер
    image.thumbnail((989, 427))
    # Конвертируем в RGB, так как не все форматы изображений подходят для сохранения в jpg и сохраняем
    image.convert('RGB').save(path)
    return True


# Запланированная задача для обновления новостей по всем играм
@shared_task
def all_game_news_update():
    for game in GameModel.objects.all():
        news_post_update(game)


# Создание/обновление новостей по конкретной игре
def news_post_update(game):
    # url адрес представляемый steam web api, с параметрами русского языка, 20 последних
    news_url = f'https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={game.steam_appid}&count=20&l=russian'

    # Запрос, формируем в json, получаем словарь по ключу appnews, в котором получаем список словарей по ключу newsitems
    request = proxy.request('GET', news_url).json()['appnews']['newsitems']

    # Составляем список gid(steam идентификатор для новостей) имеющихся новостей по игре
    list_of_gid = [post.gid for post in GameNewsPost.objects.filter(game=game)]

    # Шаблон для библиотеки re, чтобы взять первое попавшееся изображение в теле поста и установить в качестве обложки
    pattern = r'<img(.*?)? src="(.+?)"(.*?)?>'

    # Итерируемся по списку словарей, где каждый словарь = словарь(конкретный пост) с данными о себе
    for news_post in request:
        # Если gid(steam идентификатор для новостей) поста отсутствует в нашем списке уже имеющихся gid'ов
        if news_post['gid'] not in list_of_gid:
            # Тело новости
            content = news_post['contents']
            # Готовим путь к изображению, который по умолчанию пуст (False)
            path_to_image = ''
            # Если новость сделана steam сообществом, то необходимо отрендерить тело новости (content)
            if news_post['feedname'] == 'steam_community_announcements':
                # Первый проход, который меняет основные теги
                content = first_rendering_bbcode_in_html(content)
                # Второй проход, форматирующий "обрубки" и "голые" url адреса
                content = second_rendering_bbcode_in_html(content)
            else:
                # Если новость из другого источника, то находим изображение по нашему шаблону pattern для обложки
                src = re.search(pattern, content)
                # Если таковое имелось
                if src:
                    # Формируем новый путь к изображению, где в качестве имени будет применён gid, в формате jpg
                    path_to_image = f'posts_images/{news_post["gid"]}.jpg'
                    # Удаляем из тела (content) выдернутое нами изображение, так как оно будет на обложке
                    content = content.replace(content[src.span()[0]:src.span()[1]], '')
                    # Формируем url для функции, которая отрисует и сохранит изображение
                    src = src[2]

                    # Если работа функции не будет успешной, вновь сделаем строку пустой
                    if not save_image(path=settings.MEDIA_ROOT / path_to_image, image_url=src):
                        path_to_image = ''
            # Cоздаем объект Новостного Поста
            GameNewsPost.objects.create(
                game=game,
                gid=news_post['gid'],
                title=news_post['title'],
                author=news_post.get('author', 'Неизвестен'),
                date=news_post['date'],
                source_url=news_post['url'],
                content=content,
                created_timestamp=datetime.astimezone(datetime.fromtimestamp(int(news_post['date']))),
                post_image=path_to_image,
                rating={'total': 0, 'likes': [], 'dislikes': []}
            )
            list_of_gid.append(news_post['gid'])
        # Если gid (steam идентификатор для новостей) уже находится в нашем списке, пропускаем новость и идём к следующей
        else:
            continue
    # В случае добавления новых новостей, необходимо уменьшить их общее количество, удалив самые старые
    # Общий лимит для каждой игры, девять постов
    while len(list_of_gid) > 9:
        GameNewsPost.objects.last().delete()
        list_of_gid.pop()


# Отложенная задача для создания игры
@shared_task
def game_model_create(data: dict):
    # Формируем путь к изображению на основе имени и формата jpg
    path_to_image = f'{settings.MEDIA_ROOT / "games_images" / data["name"]}.jpg'
    # Пользуемся нашей функцией для отрисовки и сохранения изображения
    save_image(path=path_to_image, image_url=data['header_image'])
    game = GameModel.objects.create(
        name=data['name'][:99],
        steam_appid=data['steam_appid'],
        image=f'games_images/{data["name"]}.jpg',
        description=data['short_description'],
        full_description=data['about_the_game'],
    )
    # Вызываем функцию для формирования новостных постов
    news_post_update(game)


# Парсинг и рендеринг bbcode в html
def first_rendering_bbcode_in_html(content):
    """
    В новостных постах от сообщества Steam используется bbcode, однако он модифицирован Steam'ом
    Эта функция находится и заменяет steam bbcode на стандартный html
    """
    pattern_sub_flags = [
        (r'{STEAM_CLAN_IMAGE}', r'https://clan.cloudflare.steamstatic.com/images/', 0),  # Просто ссылка на хранилище
        (r'\[previewyoutube=(?P<YOUTUBECODE>.*?);full\]\[/previewyoutube\]',
         r'<br><iframe width="620" height="320" src="https://www.youtube.com/embed/\g<YOUTUBECODE>"></iframe><br>', 0),
        (r'\[video.*?\](?P<URL>.*?)\[/video\]', r'<br><iframe width="620" height="320" src="\g<URL>"></iframe><br>', 0),
        (r'\[center\](?P<TEXT>.*?)\[/center\]', r'<div style="text-align:center;">\g<TEXT></div>', 0),
        (r'\[code\](?P<TEXT>.*?)\[/code\]', r'<code>\g<TEXT></code>', 0),
        (r'\[color=(?P<COLOR>.*?)\](?P<TEXT>.*?)\[/code\]', r'<span style="color:\g<COLOR>;">\g<TEXT></span>', 0),
        (r'\[img\](?P<URL>.*?)\[/img\]', r'<img style="max-width:989px; max-height:427px" src="\g<URL>">', 0),
        (r'\[i\](?P<TEXT>.*?)\[/i\]', r'<em>\g<TEXT></em>', 0),
        (r'\[list\](?P<TEXT>.*?)\[/list\]', r'<ul>\g<TEXT></ul>', re.DOTALL),
        (r'\[\*\](?P<TEXT>.*?)(\[/\*\])?', r'<li>\g<TEXT></li>', 0),
        (r'\[quote\](?P<TEXT>.*?)\[/quote\]', r'<blockquote>\g<TEXT></blockquote>', 0),
        (r'\[s\](?P<TEXT>.*?)\[/s\]', r'<strike>\g<TEXT></strike>', 0),
        (r'\[b\](?P<TEXT>.*?)\[/b\]', r'<strong>\g<TEXT></strong>', re.DOTALL),
        (r'\[u\](?P<TEXT>.*?)\[/u\]', r'<u>\g<TEXT></u>', 0),
        (r'\[url=\s?(?P<URL>.*?)\](?P<TEXT>.*?)\[/url\]?', r'<a href="\g<URL>">\g<TEXT></a>', 0),
        (r'\[h(?P<NUMBER>[0-9])\](?P<TEXT>.*?)\[/h(?P=NUMBER)\]', r'<h\g<NUMBER>>\g<TEXT></h\g<NUMBER>>', 0),
    ]
    for pattern, sub, flags in pattern_sub_flags:
        content = re.sub(pattern, sub, content, flags=flags)
    return content


def second_rendering_bbcode_in_html(content):
    """
    Эта функция добивает "хвосты", так как не все авторы придерживаются синтаксиса, но видно в steam bbcode,
        он не так строг, как html и отрисовывает неккоректно сформированные теги
    Также функция оборачивает голые url адреса, в кликабельные ссылки
    """
    pattern_sub_flags = [
        (r'\[url=\s?(?P<URL>.*?)/?\]', r'<a href="\g<URL>"></a>', 0),
        (r'\[/url\]', r'', 0),
        (r'\[/\*\]', r'', 0),
        (r'\s(?P<URL>https?://[\w/\.]+?)\s', r'<p><a href="\g<URL>">\g<URL></a></p>', 0),
    ]
    for pattern, sub, flags in pattern_sub_flags:
        content = re.sub(pattern, sub, content, flags=flags)
    return content
