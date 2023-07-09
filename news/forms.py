from django import forms

from news.models import PostUserComment


class WriteCommentForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': '3',
        'placeholder': 'Напишите что-нибудь'
    }))

    class Meta:
        model = PostUserComment
        fields = ('message',)
