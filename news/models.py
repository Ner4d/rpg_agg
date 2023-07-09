import os
from datetime import timedelta

from django.db import models

from users.models import User


class GameModel(models.Model):
    name = models.CharField(verbose_name='Название', unique=True)
    image = models.ImageField(upload_to='games_images', verbose_name='Изображение')
    description = models.TextField(verbose_name='Описание')
    full_description = models.TextField(verbose_name='Полное описание', blank=True)
    steam_appid = models.PositiveIntegerField(unique=True, verbose_name='Идентификатор Steam')
    metacritic = models.JSONField(default=dict, verbose_name='Данные metacritic')

    class META:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        # При удалении объекта, удаляем его изображение
        os.remove(self.image.path)
        return super(GameModel, self).delete(using=using, keep_parents=keep_parents)


class GameNewsPost(models.Model):
    game = models.ForeignKey(to=GameModel, on_delete=models.CASCADE, verbose_name='Игра')
    gid = models.CharField(verbose_name='Идентификатор новостей Steam')
    title = models.TextField(max_length=256, verbose_name='Заголовок')
    author = models.CharField(max_length=128, verbose_name='Автор')
    date = models.PositiveIntegerField(verbose_name='Дата')
    source_url = models.URLField(verbose_name='Источник')
    content = models.TextField(verbose_name='Наполнение')
    created_timestamp = models.DateTimeField(verbose_name='Дата публикации')
    rating = models.JSONField(default=dict)
    post_image = models.ImageField(upload_to='posts_images', blank=True, verbose_name='Обложка')

    class META:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # Формирует рейтинг на основе длинны списков "лайк" и "дизлайк", в которых находятся имена пользователей
        # Проголосовавших за тот или иной выбор
        self.rating['total'] = len(self.rating['likes']) - len(self.rating['dislikes'])
        return super(GameNewsPost, self).save(force_insert=force_insert, force_update=force_update,
                                              using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False):
        # Удаление обложки при удалении объекта
        if self.post_image:
            os.remove(self.post_image.path)
        return super(GameNewsPost, self).delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'{self.game.name} - {self.gid}'


# Модифицированный QuerySet (Django ORM)
class CommentQuerySet(models.query.QuerySet):
    # Возвращает общий рейтинг комментариев пользователя
    def make_user_rating(self):
        return sum(post.rating['total'] for post in self)


class PostUserComment(models.Model):
    objects = CommentQuerySet.as_manager()
    created_timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    finish_timestamp = models.DateTimeField(null=True, default=None, verbose_name='Возможность удалить ДО')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    post = models.ForeignKey(to=GameNewsPost, on_delete=models.CASCADE, verbose_name='Пост')
    message = models.TextField(max_length=512, verbose_name='Текст')
    rating = models.JSONField(default=dict, verbose_name='Рейтинговая система')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # При создании/изменении контролирует время возможности удалить пользователем свой коммент
        if not self.finish_timestamp:
            self.finish_timestamp = self.created_timestamp + timedelta(minutes=5)
        # Формирует рейтинг на основе длинны списков "лайк" и "дизлайк", в которых находятся имена пользователей
        # Проголосовавших за тот или иной выбор
        self.rating['total'] = len(self.rating['likes']) - len(self.rating['dislikes'])
        return super(PostUserComment, self).save(force_insert=force_insert, force_update=force_update,
                                                 using=using, update_fields=update_fields)

    def __str__(self):
        return f'{self.user.name} {self.post}'


class Subscription(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    game = models.ForeignKey(to=GameModel, on_delete=models.CASCADE)
