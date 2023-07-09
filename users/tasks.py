import os
import uuid
from datetime import datetime, timedelta

from celery import shared_task
from django.http import HttpResponseBadRequest

from users.models import EmailVerification, User


# Запланированная задача для проверки срока жизни EmailVerification
@shared_task
def check_finish_email_verify():
    # Цикл по всем "живым" экземплярам EmailVerification
    for em_verify in EmailVerification.objects.all():
        # Если срок вышел, удаляем
        if em_verify.finish < datetime.utcnow():
            em_verify.delete()


# Запланированная задача, для поиска и удаления неиспользуемых изображений аватарок
# Так как при удалении пользователя удаляется только текущая аватарка
# Запускается при внесении изменений пользователями в профиль, а также для периодически по времени, для профилактики
@shared_task
def check_useless_avatar():
    # Собираем список используемых изображений
    list_of_needed_image = [user.avatar.url for user in User.objects.all() if user.avatar]
    # Собираем список всех хранящихся изображений, сравниваем и удаляем не нужные
    list_of_all_image = [path + file for path, _, files in os.walk('./media/users_images/') for file in files]
    for image in list_of_all_image:
        if image[1:] not in list_of_needed_image:
            os.remove(image)


# Отложенная задача, для отправки письма верификации
@shared_task
def send_verification_email(user_id: int):
    # Получаем пользователя через id полученного в качестве аргумента
    user = User.objects.get(id=user_id)
    # Просто подстраховка, если запрос сделан пользователем, с верификацией
    if user.check_email:
        return HttpResponseBadRequest()
    # Создаем конечное время жизни
    finish = datetime.astimezone(datetime.now() + timedelta(hours=24))
    # Создаем объект, с пользователем, уникальным кодом и временем жизни
    email = EmailVerification.objects.create(
        user=user,
        code=uuid.uuid4(),
        finish=finish
    )
    # Отправляем через метод, написанный в users.models.EmailVerification
    email.send_email_verificate()
