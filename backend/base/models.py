from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    paypal_email = models.EmailField(
        blank=False,
        null=False,
        help_text="PayPal email address for receiving internal payments."
    )
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Group(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='payment_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(User, related_name='paid_expenses', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    SPLIT_TYPES = [
        ('equal', 'Equal Split'),
        ('unequal', 'Unequal Split'),
    ]
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES, default='equal')

    def __str__(self):
        return f"{self.description} in {self.group.name}"

class ExpenseParticipant(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    share_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('expense', 'user')

    def __str__(self):
        return f"{self.user.username} for {self.expense.description}: {self.amount_due}"

class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    payer = models.ForeignKey(User, related_name='settled_payments', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_settlements', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    paypal_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending')

    def __str__(self):
        return f"{self.payer.username} paid {self.receiver.username} ₹{self.amount} in {self.group.name}"
