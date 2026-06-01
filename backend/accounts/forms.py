from django import forms


class RegisterForm(forms.Form):
    username = forms.CharField(max_length=64, label='登录账号')
    password = forms.CharField(widget=forms.PasswordInput, min_length=6, label='密码')
    password2 = forms.CharField(widget=forms.PasswordInput, label='确认密码')
    nickname = forms.CharField(max_length=64, required=False, label='昵称')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError('两次密码不一致')
        return cleaned


class LoginForm(forms.Form):
    username = forms.CharField(max_length=64, label='账号')
    password = forms.CharField(widget=forms.PasswordInput, label='密码')


class ProfileForm(forms.Form):
    nickname = forms.CharField(max_length=64, label='昵称')
    old_password = forms.CharField(widget=forms.PasswordInput, required=False, label='原密码')
    new_password = forms.CharField(widget=forms.PasswordInput, required=False, label='新密码')
