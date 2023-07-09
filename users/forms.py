from django import forms
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                       PasswordResetForm, SetPasswordForm,
                                       UserChangeForm, UserCreationForm)

from users.models import User


class LoginUserForm(AuthenticationForm):
    username = forms.CharField(label='Логин', widget=forms.TextInput({
        'placeholder': 'Введите ваш логин',
        'class': 'form-control',
        'autofocus': True,
        'aria-describedby': "usernameHelp"
    }))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput({
        'placeholder': 'Введите пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))

    class Meta:
        model = User
        fields = ('username', 'password')


class ProfileUserForm(UserChangeForm):
    avatar = forms.ImageField(widget=forms.FileInput(attrs={'class': 'custom-file-input', 'draggable': True}),
                              required=False)
    username = forms.CharField(widget=forms.TextInput({
        'placeholder': 'Введите ваш логин',
        'class': 'form-control',
        'aria-describedby': "usernameHelp"
    }))
    email = forms.EmailField(widget=forms.EmailInput({
        'placeholder': 'Введите эл. почту',
        'class': 'form-control',
        'aria-describedby': "emailHelp",
        'readonly': 'true'
    }))

    class Meta:
        model = User
        fields = ('username', 'avatar', 'email')


class RegisterUserForm(UserCreationForm):
    username = forms.CharField(label='Логин', widget=forms.TextInput({
        'placeholder': 'Введите ваш логин',
        'class': 'form-control',
        'aria-describedby': "usernameHelp"
    }))
    email = forms.EmailField(label='Эл. Почта', widget=forms.EmailInput({
        'placeholder': 'Введите эл. почту',
        'class': 'form-control',
        'aria-describedby': "emailHelp"
    }))
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput({
        'placeholder': 'Введите пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput({
        'placeholder': 'Повторите пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ChangeUserPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput({
        'placeholder': 'Введите cтарый пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp",
        'autofocus': True
    }))
    new_password1 = forms.CharField(widget=forms.PasswordInput({
        'placeholder': 'Введите новый пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput({
        'placeholder': 'Повторите новый пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))

    class Meta:
        model = User
        fields = ('old_password', 'new_password1', 'new_password2')


class ResetUserPasswordForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput({
        'placeholder': 'Введите эл. почту',
        'class': 'form-control',
        'aria-describedby': "emailHelp",
        'autofoucs': True
    }))

    class Meta:
        model = User
        fields = ('email',)


class ResetUserPasswordConfirmForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput({
        'placeholder': 'Введите новый пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp",
        'autofocus': True
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput({
        'placeholder': 'Повторите новый пароль',
        'class': 'form-control',
        'aria-describedby': "passwordHelp"
    }))

    class Meta:
        model = User
        fields = ('new_password1', 'new_password2')
