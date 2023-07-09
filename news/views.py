from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
# Библиотека для поиска игр в стиме, не уверен, что она официальная, так как парсит страницу поиска
from steam import Steam
# Библиотека с модулем прокси socks, для запросов через прокси
from urllib3.contrib.socks import SOCKSProxyManager
from datetime import timedelta

from news.forms import WriteCommentForm
from news.models import GameModel, GameNewsPost, PostUserComment, Subscription
from news.tasks import game_model_create
from users.forms import LoginUserForm

# Для работы библиотеки по поиску игр, необходим API key зарегистрированный в стим для работы с их API
steam = Steam(settings.STEAM_API_KEY)

# Для доступа к играм и новостям закрытых для ру региона, прокси менеджер из urllib3, по протоколу socks (подойдёт любой)
proxy = SOCKSProxyManager(settings.PROXY)


# Просто базовая страничка
class IndexView(LoginView):
    template_name = 'news/index.html'
    form_class = LoginUserForm


# Лента новостей
class NewsFeedView(ListView):
    model = GameNewsPost
    template_name = 'news/feed.html'
    paginate_by = 12
    paginate_orphans = True
    ordering = '-date'


# Кнопка "Подписки" на странице ленты, чтобы отобразить новости только тех игр, на которые он подписан
class NewsFeedOnlySubsView(LoginRequiredMixin, ListView):
    template_name = 'news/feed.html'
    paginate_by = 12
    paginate_orphans = True

    def get_queryset(self):
        # Сначала собираются id игр через связь User-SubModel-GameModel
        subs = [sub.game.id for sub in Subscription.objects.filter(user=self.request.user)]
        # Потом тупо отфильтровываются новости через список id в subs
        return [post for post in GameNewsPost.objects.all().order_by('-date') if post.game.id in subs]


# Поиск игр в steam через библиотеку Steam
class SearchGame(ListView):
    template_name = 'news/search.html'

    def get_queryset(self):
        # Если через форму было отправлено значение в поле game_name, то мы его получим
        game_name = self.request.GET.get('game_name', '')
        # Подкапотная магия из библиотеки Steam, с полученным именем, если оно не пустое
        game_list = steam.apps.search_games(game_name).get('apps') if game_name else []
        # По итогу возвращается список словарей, где словарь=игра, больше пяти не возвращается
        return game_list

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(SearchGame, self).get_context_data(object_list=object_list, **kwargs)
        # Список уникальных для steam номеров, чтобы видеть, есть ли эта игра уже у нас или нет
        context['game_in_library'] = [game.steam_appid for game in GameModel.objects.all()]
        return context


# Страничка библиотеки с играми, которые есть в базе
class OurLibraryListView(ListView):
    template_name = 'news/library.html'
    paginate_by = 6
    paginate_orphans = True

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(OurLibraryListView, self).get_context_data(object_list=object_list, **kwargs)
        # Если пользователь авторизован, мы получим список id игр, на которые он подписан
        # Если подписан кнопка-Отписаться, если нет-Подписаться
        # Если не авторизован, список пуст
        if self.request.user.is_authenticated:
            context['subs'] = [sub.game.id for sub in Subscription.objects.filter(user=self.request.user)]
        else:
            context['subs'] = []
        return context

    # Здесь реализован поиск игры уже по нашему сайту, просто для удобства поиска пользователю
    def get_queryset(self):
        # Если через форму было отправлено значение в поле game_name, то мы его получим
        name = self.request.GET.get('search_game', '')
        if name:
            # Если имя было отправлено, поиск осуществляется в Базе Данных через Django ORM
            return GameModel.objects.all().filter(name__icontains=name).order_by('name')
        return GameModel.objects.all().order_by('name')


# Функция добавления игры, декораторы проверяют авторизован ли пользователь и подтверждена ли почта
@login_required
@user_passes_test(lambda u: u.check_email, login_url='users:not_verify')
def add_game(request, appid: int) -> render:
    template_name = 'users/message_template.html'

    # Заготовка контекста
    context = {
        'message_head': 'Упс',
        'redirect_url': request.META['HTTP_REFERER'],
        'button_name': 'Вернуться'
    }

    # Ссылка с адресом указанным в документации steam web api, куда вставляется appid
    game_url = f'https://store.steampowered.com/api/appdetails/?appids={appid}&l=russian'
    # Выполняем get запрос, на указанный адрес, конвертируем в словарь
    # И сразу же берем значение по ключу appid(в виде строки)
    game_data = proxy.request('GET', game_url).json()[str(appid)]
    # Берём основную информацию по игре, которая хранится в ключе data
    game_data = game_data['data']
    # Проверяем, тип, так как в поиске стим также может возвращать саундтреки, фильмы и проч.
    if game_data['type'] != 'game':
        context['message'] = 'Этот объект не является игрой'
        return render(request, template_name=template_name, context=context)
    # Проверяем есть ли среди жанров этой игры, жанр РПГ, его id в steam это цифра 3
    if '3' in [genre['id'] for genre in game_data['genres']]:
        # Если РПГ присутствует, отправляем на выполнение отложенную задачу из news.tasks
        game_model_create.delay(data=game_data)
        # Корректируем контекст
        context['message_head'] = 'Отлично'
        context['message'] = 'Скоро игра будет добавлена в нашу библиотеку'
        # Перенаправляем на страничку с сообщением
        return render(request, template_name=template_name, context=context)
    # Если РПГ в списке не было
    else:
        context['message'] = 'Среди жанров этой игры РПГ не было найдено'
        return render(request, template_name=template_name, context=context)


# Детальная страница игры
class GameModelDetailView(DetailView):
    model = GameModel
    template_name = 'news/game_detail.html'

    def get_context_data(self, **kwargs):
        context = super(GameModelDetailView, self).get_context_data(**kwargs)
        # Собираем все новости по этой игре
        context['game_news'] = GameNewsPost.objects.filter(game=self.object).order_by('-created_timestamp')
        # Если пользователь авторизован, мы получим список id игр, на которые он подписан
        # Если подписан кнопка-Отписаться, если нет-Подписаться
        # Если не авторизован, список пуст
        if self.request.user.is_authenticated:
            context['subs'] = [sub.game.id for sub in Subscription.objects.filter(user=self.request.user)]
        else:
            context['subs'] = []
        return context


# Детальная страница новостного поста, но по сути это страница со списком комментариев к определенному посту
class NewsPostDetailView(ListView):
    template_name = 'news/post_detail.html'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = super(NewsPostDetailView, self).get_context_data(**kwargs)
        # контекст с данными поста, чей id получен через url
        context['object'] = GameNewsPost.objects.get(id=self.kwargs['pk'])
        return context

    # Список комментариев к данному посту
    def get_queryset(self):
        return PostUserComment.objects.filter(post_id=self.kwargs['pk']).order_by('created_timestamp')


# Написание комментария, с миксинами проверяющими аутентификацию и верификацию пользователя
class WriteComment(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = WriteCommentForm

    def get_success_url(self):
        # Возвращает на ту же страницу где был отправлен комментарий
        return reverse_lazy('news:post_detail', kwargs={'pk': self.kwargs['post_id']})

    def form_valid(self, form):
        # Заполняем необходимые данные для создания модели Поста
        form.instance.user = self.request.user
        form.instance.post = GameNewsPost.objects.get(id=self.kwargs['post_id'])
        form.instance.rating = {'total': 0, 'likes': [], 'dislikes': []}
        form.instance.message = self.request.POST['message']
        # Время после которого пользователь не сможет удалить свой комментарий
        form.instance.finish_timestamp = form.instance.created_timestamp + timedelta(minutes=5)
        return super(WriteComment, self).form_valid(form=form)

    # Функция необходимая для миксина UserPassesTestMixin, которая возвращает объект, чью истинность надо проверить
    def test_func(self):
        return self.request.user.check_email

    # Функция необходимая для миксина UserPassesTestMixin, которая перенаправит на страничку с сообщением
    # О том, что пользователь не подтвердил почту, в том случае, если test_func вернул False
    def handle_no_permission(self):
        return redirect('users:not_verify')


# Страничка где пользователь может просмотреть все свои комментарии
class MyCommentListView(LoginRequiredMixin, ListView):
    template_name = 'news/my_comments.html'
    paginate_by = 20

    def get_queryset(self):
        # Возвращает список комментариев пользователя отсортированных по убыванию времени их создания
        return PostUserComment.objects.filter(user=self.request.user).order_by('-created_timestamp')


# Страничка где пользователь может просмотреть свои подписки
class MySubscribesListView(LoginRequiredMixin, ListView):
    template_name = 'news/my_subscribes.html'
    paginate_by = 10

    def get_queryset(self):
        # Если через форму было отправлено значение в поле search_name, то мы его получим
        name = self.request.GET.get('search_game', '')
        # Cписок (querySet) подписок пользователя через связь Foreign Key
        queryset = Subscription.objects.filter(user=self.request.user)
        # Если в поиске введено имя
        if name:
            # Список игр по подпискам, которые содержат в имени подстроку name, сортировка в алфавитном порядке по имени
            return [sub.game for sub in queryset.filter(game__name__icontains=name).order_by('game__name')]
        # Иначе список игр по подпискам без поиска
        return [sub.game for sub in queryset.order_by('game__name')]


# Позволяет удалить свой комментарий пользователю, декоратор проверяет авторизован ли он
@login_required
def delete_comment(request, comment_id: int) -> HttpResponseRedirect:
    # Находим комментарий по его id полученному через url
    comment = PostUserComment.objects.get(id=comment_id)
    # Просто перестраховка, что удаляющий действительно автор комментария
    if comment.user.id == request.user.id:
        comment.delete()
    # Возвращаем на ту же страницу
    return HttpResponseRedirect(request.META['HTTP_REFERER'])


# Позволяет проголосовать, в декораторах проверка авторизации и верификации пользователя
@login_required
@user_passes_test(lambda u: u.check_email, login_url='users:not_verify')
def add_voice(request, object_type: str, object_id: int, voice_type: str) -> HttpResponseRedirect:
    username = request.user.username
    # Типы объектов которые могли получить голос
    voice_object = {
        'post': GameNewsPost,
        'comment': PostUserComment
    }
    # Через словарь получаем тип объекта и находим его через полученный id
    voice_object = voice_object[object_type].objects.get(id=object_id)
    # Противоположность, каждого голоса, чтобы к полученному прибавлять, у противоположного убавлять
    opposite_voice = {
        'likes': 'dislikes',
        'dislikes': 'likes'
    }
    # Получаем тип противоположного голоса
    opposite_voice = opposite_voice[voice_type]
    # Доп. проверка, что пользователя нет в списке проголосовавших к объекту тем или иным голосом
    if username not in voice_object.rating[voice_type]:
        # Если его нет, смело добавляем
        voice_object.rating[voice_type].append(username)

    # Если пользователь есть в списке противоположно проголосовавших, убираем его оттуда
    if username in voice_object.rating[opposite_voice]:
        voice_object.rating[opposite_voice].remove(username)
    # Cохраняем изменения
    voice_object.save()
    # Возвращает на ту же страницу, откуда делался запрос
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# Функция добавления подписки, декораторы проверяют авторизацию и верификацию
@login_required
@user_passes_test(lambda u: u.check_email, login_url='users:not_verify')
def add_subscribe(request, game_id: int) -> HttpResponseRedirect:
    # Находим игру по id полученному через url
    game = GameModel.objects.get(id=game_id)
    # Берём пользователя сделавшего запрос
    user = request.user
    # Создаём модель Subscription, со связью game и user ИЛИ обновляем текущую подписку (просто подстраховка)
    Subscription.objects.update_or_create(user=user, game=game)
    # Возвращаем на ту же страницу, откуда выполнен запрос
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# Функция удаления подписки, декоратор проверяет авторизацию
@login_required
def delete_subscribe(request, game_id: int) -> HttpResponseRedirect:
    # Берём пользователя сделавшего запрос
    user = request.user
    # Находим игру по id полученному через url
    game = GameModel.objects.get(id=game_id)
    # Находим подписку через связь user и game и удаляем
    Subscription.objects.get(user=user, game=game).delete()
    # Возвращаем на ту же страницу, откуда выполнен запрос
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
