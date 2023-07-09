from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (LoginView, PasswordChangeDoneView,
                                       PasswordChangeView,
                                       PasswordResetCompleteView,
                                       PasswordResetConfirmView,
                                       PasswordResetDoneView,
                                       PasswordResetView)
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from news.models import GameModel, PostUserComment
from users.forms import (ChangeUserPasswordForm, LoginUserForm,
                         ProfileUserForm, RegisterUserForm,
                         ResetUserPasswordConfirmForm, ResetUserPasswordForm)
from users.models import EmailVerification, User
from users.tasks import send_verification_email, check_useless_avatar


# Представление для регистрации пользователя, основанное на базовом от Django
class RegisterUserView(CreateView):
    template_name = 'users/register.html'
    form_class = RegisterUserForm

    # В случае успеха и перенаправления на страничку с сообщением об успехе
    def get_success_url(self):
        # Пользователь будет авторизован
        login(self.request, self.object)
        # А также отправлено письмо с подтверждением почты отложенной задачой из users.tasks
        send_verification_email.delay(self.object.id)
        # Перенаправление на страничку с сообщением об успехе
        return reverse_lazy('users:register_complete')


# Просто страничка для ссылки на неё через reverse_lazy класса RegisterUserView
class RegisterCompleteView(TemplateView):
    template_name = 'users/register_complete.html'


# Представление с изменением пароля
class ChangePasswordUserView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    form_class = ChangeUserPasswordForm
    success_url = reverse_lazy('users:change_password_done')


# Представление странички с сообщением об успешной смене пароля
class ChangePasswordUserDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'users/message_template.html'
    extra_context = {
        'message_head': 'Успех',
        'message': 'Пароль успешно изменён',
        'redirect_url': reverse_lazy('index'),
        'button_name': 'На главную'
    }


# Представление странички для авторизации
class LoginUserView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginUserForm


# Представление профиля
class ProfileUserView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'users/profile.html'
    form_class = ProfileUserForm

    def get_context_data(self, **kwargs):
        context = super(ProfileUserView, self).get_context_data(**kwargs)
        # формируем рейтинг пользователя на основе рейтинга всех его комментариев
        context['user_rating'] = PostUserComment.objects.filter(user=self.request.user).make_user_rating()
        return context

    # В случае успешного внесения изменений в профиле (изменяется только username и аватар)
    def get_success_url(self):
        # Отложенная задачка для чистки неиспользуемых аватарок
        check_useless_avatar.delay()
        # Возвращает обратно в профиль
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.id})


# Представление для сброса пароля, здесь формируется письмо которое будет отправлено на почту
class ResetPasswordUserView(PasswordResetView):
    # От кого отправлено
    from_email = settings.EMAIL_HOST_USER
    template_name = 'users/reset_password.html'
    form_class = ResetUserPasswordForm
    success_url = reverse_lazy('users:reset_password_done')
    email_template_name = 'users/password_reset_email.html'


# Представление успешного сброса пароля
class ResetPasswordUserDoneView(PasswordResetDoneView):
    template_name = 'users/message_template.html'
    extra_context = {
        'message_head': 'Сброс пароля',
        'message': 'Инструкция по изменению пароля отправлена на указанную почту',
        'redirect_url': reverse_lazy('index'),
        'button_name': 'На главную'
    }


# Представление об изменении пароля после сброса
class ResetPasswordUserConfirmView(PasswordResetConfirmView):
    form_class = ResetUserPasswordConfirmForm
    template_name = 'users/reset_password_confirm.html'
    success_url = reverse_lazy('users:reset_password_complete')


# Представление об успешном изменении пароля
class ResetPasswordUserCompleteView(PasswordResetCompleteView):
    template_name = 'users/message_template.html'
    extra_context = {
        'message_head': 'Успех',
        'message': 'Пароль успешно изменён',
        'redirect_url': reverse_lazy('index'),
        'button_name': 'На главную'
    }


# Представление о верификации почты
def email_verification(request, code):
    # Находим объект верификации по коду (uuid)
    email_verify = EmailVerification.objects.filter(code=code)
    # Дабы избежать ошибки, пользуемся filter вместо get, хотя можно было бы и через try/except
    if email_verify.exists():
        email_verify = email_verify.first()
        user = email_verify.user
        message_head = 'Поздравляем'
        message = 'Верификация вашего адреса электронной почты прошла успешна'
        user.check_email = True
        user.save()
        email_verify.delete()
    else:
        message_head = 'Упс'
        message = 'К сожалению верификация вашего адреса электронной почты не удалась.' \
                  ' Запросить повторную верификацию вы можете на странице профиля'
    return render(request, template_name='users/message_template.html', context={
        'message': message,
        'message_head': message_head,
        'redirect_url': reverse('index'),
        'button_name': 'На главную'
    })


# Базовое представление выхода из аккаунта, в оболочке с возвратом на главную, декоратор проверяет авторизацию
@login_required
def logout_user_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


# Представление нового запроса верификации, если пользователь утратил/не получил/просрочил первичную после регистрации
@login_required
def new_verification_email(request):
    template_name = 'users/message_template.html'
    # Заготовка контекста
    context = {
        'message_head': 'Успех',
        'message': 'Письмо для верификации отправлено к Вам на почту',
        'redirect_url': reverse('users:profile', kwargs={'pk': request.user.id}),
        'button_name': 'Вернуться'
    }
    # Если "живых" верификаций у данного пользователя больше трёх, больше создавать не дадим
    if len(EmailVerification.objects.filter(user=request.user)) > 3:
        context['message_head'] = 'Упс'
        context['message'] = 'У вас сформировано слишком много действующих писем с верификацией, попробуйте завтра'
        return render(request, template_name, context)
    # Если всё в порядке, отправляем письмо
    send_verification_email(request.user.id)
    return render(request, template_name, context)


# Представление сообщающее пользователю о том, что его почта не подтверждена
def not_verificate(request):
    template_name = 'users/message_template.html'
    context = {
        'message_head': 'Упс',
        'message': 'Ваш аккаунт не верифицирован, пожалуйста подтвердите свой адрес электронной почты',
        'redirect_url': request.META['HTTP_REFERER'],
        'button_name': 'Вернуться'
    }
    return render(request, template_name, context)
