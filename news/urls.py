from django.urls import path

from news.views import (GameModelDetailView, MyCommentListView,
                        MySubscribesListView, NewsFeedOnlySubsView,
                        NewsFeedView, NewsPostDetailView, OurLibraryListView,
                        SearchGame, WriteComment, add_game, add_subscribe,
                        add_voice, delete_comment, delete_subscribe)

app_name = 'news'

urlpatterns = [
    path('feed', NewsFeedView.as_view(), name='feed'),
    path('search', SearchGame.as_view(), name='search'),
    path('library', OurLibraryListView.as_view(), name='library'),
    path('add_game/<int:appid>', add_game, name='add_game'),
    path('post_detail/<int:pk>', NewsPostDetailView.as_view(), name='post_detail'),
    path('write_comment/<int:post_id>', WriteComment.as_view(), name='write_comment'),
    path('add_voice/<str:object_type>/<int:object_id>/<str:voice_type>', add_voice, name='add_voice'),
    path('my_comments', MyCommentListView.as_view(), name='my_comments'),
    path('delete_comment/<int:comment_id>', delete_comment, name='delete_comment'),
    path('my_subscribes', MySubscribesListView.as_view(), name='my_subscribes'),
    path('add_subscribe/<int:game_id>', add_subscribe, name='add_subscribe'),
    path('delete_subscribe/<int:game_id>', delete_subscribe, name='delete_subscribe'),
    path('game_detail/<int:pk>', GameModelDetailView.as_view(), name='game_detail'),
    path('only_subs_feed', NewsFeedOnlySubsView.as_view(), name='subs_feed'),
]
