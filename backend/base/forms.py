from django import forms
from .models import Group,Expense, UserProfile,User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['paypal_email']

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = "__all__"

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['group', 'description', 'amount', 'split_type']