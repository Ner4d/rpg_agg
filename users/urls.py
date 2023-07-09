from django.urls import path

from users.views import (ChangePasswordUserDoneView, ChangePasswordUserView,
                         LoginUserView, ProfileUserView, RegisterCompleteView,
                         RegisterUserView, ResetPasswordUserCompleteView,
                         ResetPasswordUserConfirmView,
                         ResetPasswordUserDoneView, ResetPasswordUserView,
                         email_verification, logout_user_view,
                         new_verification_email, not_verificate)

app_name = 'users'

urlpatterns = [
    path('register', RegisterUserView.as_view(), name='register'),
    path('register_complete', RegisterCompleteView.as_view(), name='register_complete'),
    path('change_password', ChangePasswordUserView.as_view(), name='change_password'),
    path('change_password_done', ChangePasswordUserDoneView.as_view(), name='change_password_done'),
    path('login', LoginUserView.as_view(), name='login'),
    path('profile/<int:pk>', ProfileUserView.as_view(), name='profile'),
    path('reset_password', ResetPasswordUserView.as_view(), name='reset_password'),
    path('reset_password_done', ResetPasswordUserDoneView.as_view(), name='reset_password_done'),
    path('reset_password_confirm/<uidb64>/<token>', ResetPasswordUserConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset_password_complete', ResetPasswordUserCompleteView.as_view(), name='reset_password_complete'),
    path('email_verify/<uuid:code>', email_verification, name='verification'),
    path('logout', logout_user_view, name='logout'),
    path('not_verify', not_verificate, name='not_verify'),
    path('new_verify', new_verification_email, name='new_verify'),
]
