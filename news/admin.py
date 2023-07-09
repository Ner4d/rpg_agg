from django.contrib import admin

from news.models import GameModel, GameNewsPost

admin.site.register(GameNewsPost)


@admin.register(GameModel)
class GameModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'steam_appid')
    fields = ('name', 'description', 'image', 'steam_appid')
