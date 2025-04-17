from django.contrib import admin
from .models import UserProfile,Group,Expense,ExpenseParticipant,Settlement
admin.site.register(UserProfile)
admin.site.register(Group)
admin.site.register(Expense)
admin.site.register(ExpenseParticipant)
admin.site.register(Settlement)