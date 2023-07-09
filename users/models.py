import os

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    # Просто небольшое изображение, которое пользователь может установить по желанию
    avatar = models.ImageField(upload_to='users_images', null=True)
    # Для проверки верификации почты
    check_email = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    # Действия при удалении экземпляра модели (задействуется эта функция)
    def delete(self, using=None, keep_parents=False):
        # Если у пользователя была своя аватарка, мы её удаляем
        if self.avatar:
            os.remove(self.avatar.path)
        return super(User, self).delete(using=using, keep_parents=keep_parents)


# Модель подтверждения почты
class EmailVerification(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    code = models.UUIDField()
    start = models.DateTimeField(auto_now_add=True)
    finish = models.DateTimeField()

    # Функция для отправки письма с подтверждением почты
    def send_email_verificate(self):
        # Создаём ссылку по которой пользователь сможет подтвердить свою почту
        link = f"{settings.FULL_DOMAIN_NAME}{reverse('users:verification', kwargs={'code': self.code})}"
        # функция отправки письма из django.core.mail
        send_mail(
            subject='Email Verification from rpg_agg',
            message=f'Dear, {self.user.username}! Please activate your email: {link}',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.user.email],
        )
