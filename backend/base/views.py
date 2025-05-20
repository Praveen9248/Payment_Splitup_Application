from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render,redirect
from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.ipn.models import PayPalIPN
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from .forms import ExpenseForm, GroupForm,UserForm,UserProfileForm
from .models import Expense, ExpenseParticipant, Group, Settlement, UserProfile
from decimal import Decimal,ROUND_HALF_UP
from django.contrib import messages

def payment(request,expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    print(expense)
    host = request.get_host()
    paypal_dict = {
        'business': settings.PAYPAL_RECEIVER_EMAIL,
        'amount': float(expense.amount / Decimal('86.10')),
        'item_name': f'Expense #{expense.id} - {expense.description}',
        'invoice': str(expense.id),
        'currency_code': 'USD',
        'notify_url': f"http://{host}{reverse('paypal-ipn')}",
        'return_url': f"http://{host}{reverse('payment-success',args=[expense.id])}",
        'cancel_return': f"http://{host}{reverse('payment-failed')}",
    }

    paypal_form = PayPalPaymentsForm(initial=paypal_dict)

    return render(request, 'payment.html', {'paypal_form': paypal_form, 'expense': expense})

def payment_success(request,expense_id):
    return redirect('expense_detail', expense_id=expense_id)

def payment_failed(request):
    return render(request,'failed.html',{})

def settlementPayment(request, participant_id):
    participant = get_object_or_404(ExpenseParticipant, id=participant_id)
    receiver = participant.expense.paid_by

    try:
        receiver_profile = receiver.profile
    except UserProfile.DoesNotExist:
        return render(request, 'settlementFailed.html', {'message': 'Receiver PayPal email not set.'})

    amount_due = participant.amount_due
    if amount_due == 0:
        return redirect('expense_list')

    host = request.get_host()
    paypal_dict = {
        'business': receiver_profile.paypal_email,
        'amount': float(amount_due / Decimal('86.10')),
        'item_name': f'Settlement for {participant.expense.description}',
        'invoice': f'settlement-{participant.id}',
        'currency_code': 'USD',
        'notify_url': f"http://{host}{reverse('paypal-ipn')}",
        'return_url': f"http://{host}{reverse('settlement-success', args=[participant.id])}",
        'cancel_return': f"http://{host}{reverse('settlement-failed')}",
    }

    paypal_form = PayPalPaymentsForm(initial=paypal_dict)
    return render(request, 'settlementPayment.html', {
        'paypal_form': paypal_form,
        'participant': participant
    })

def settlementSuccess(request, participant_id):
    participant = get_object_or_404(ExpenseParticipant, id=participant_id)

    # Mark amount_due as settled
    participant.amount_due = 0
    participant.save()

    # Create Settlement record
    Settlement.objects.create(
        group=participant.expense.group,
        payer=request.user,
        receiver=participant.expense.paid_by,
        amount=participant.share_value,
        status='Completed'
    )

    return render(request, 'settlementSuccess.html', {'participant': participant})

def settlementFailed(request):
    return render(request, 'settlementFailed.html', {'message': 'Payment was canceled or failed.'})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home_page')
            else:
                form.add_error(None, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home_page')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect("login_page")

def homeView(request):
    return render(request, 'index.html',{})

def groupList(request):
    groups = Group.objects.filter(members=request.user).order_by('-created_at')
    return render(request, 'groupList.html', {'groups': groups})

def groupCreate(request):
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.save()
            group.members.add(request.user)
            member_ids = request.POST.getlist('members')
            member_ids = [user_id for user_id in member_ids if int(user_id) != request.user.id]
            group.members.add(*member_ids)
            return redirect('group_detail', group_id=group.id)
        else:
            return render(request, 'groupDetail.html', {'form': form})
    else:
        form = GroupForm()
        return render(request, 'groupCreate.html',{'form':form})

def groupDetail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    context = {'group': group}
    return render(request, 'groupDetail.html', context)

def expenseList(request):
    user = request.user
    paid_expenses = Expense.objects.filter(paid_by=user)
    participant_expenses = Expense.objects.filter(expenseparticipant__user=user).distinct()
    user_expenses = paid_expenses.union(participant_expenses).order_by('-created_at')
    for expense in user_expenses:
        expense.is_participant = expense.expenseparticipant_set.filter(user=user).exists()
        if expense.is_participant:
            try:
                expense.amount_owed = expense.expenseparticipant_set.get(user=user).amount_due
            except ExpenseParticipant.DoesNotExist:
                expense.amount_owed = None
    return render(request, 'expenseList.html', {'expenses': user_expenses})

def expenseDetail(request, expense_id):
    currentUser = request.user
    expense = get_object_or_404(Expense, pk=expense_id)
    participants = ExpenseParticipant.objects.filter(expense=expense)
    return render(request, 'expenseDetail.html', {'expense': expense, 'participants': participants,'currentUser':currentUser})

def get_group_members(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
        members = group.members.all()
        data = {
            'members': [
                {'id': member.id, 'username': member.username}
                for member in members
            ]
        }
        return JsonResponse(data)
    except Group.DoesNotExist:
        return JsonResponse({'error': 'Group not found'}, status=404)
    
def expenseCreate(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.save()

            group_members = expense.group.members.all()
            total_amount = expense.amount.quantize(Decimal('0.01'))

            if expense.split_type == 'equal':
                num_members = group_members.count()
                if num_members == 0:
                    messages.error(request, "Group has no members.")
                    expense.delete()
                    return redirect('expense_create')

                share = (total_amount / num_members).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                for member in group_members:
                    ExpenseParticipant.objects.create(
                        expense=expense,
                        user=member,
                        share_value=share,
                        amount_due=Decimal('0.00') if member == expense.paid_by else share
                    )

            elif expense.split_type == 'unequal':
                total_entered = Decimal('0.00')
                for member in group_members:
                    amount_str = request.POST.get(f'custom_split_{member.id}', '0').strip()
                    try:
                        amount = Decimal(amount_str).quantize(Decimal('0.01'))
                        total_entered += amount
                        ExpenseParticipant.objects.create(
                            expense=expense,
                            user=member,
                            share_value=amount,
                            amount_due=Decimal('0.00') if member == expense.paid_by else amount
                        )
                    except:
                        messages.error(request, f"Invalid amount for {member.username}.")
                        expense.delete()
                        return redirect('expense_create')

                if total_entered != total_amount:
                    messages.error(request, f"Custom shares total ₹{total_entered}, but expense is ₹{total_amount}.")
                    expense.delete()
                    return redirect('expense_create')

            host = request.get_host()
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': float(expense.amount / Decimal('86.10')),
                'item_name': f'Expense #{expense.id} - {expense.description}',
                'invoice': str(expense.id),
                'currency_code': 'USD',
                'notify_url': f"http://{host}{reverse('paypal-ipn')}",
                'return_url': f"http://{host}{reverse('payment-success',args=[expense.id])}",
                'cancel_return': f"http://{host}{reverse('payment-failed')}",
            }
            paypal_form = PayPalPaymentsForm(initial=paypal_dict)
            return render(request, 'payment.html', {'paypal_form': paypal_form, 'expense': expense})
    else:
        form = ExpenseForm()

    return render(request, 'expenseCreate.html', {'form': form})


def profileView(request):
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = None

    context = {'user_profile': user_profile}
    return render(request, 'profile.html', context)

def profileCreate(request):
    try:
        request.user.profile
        return redirect('profile_view')
    except UserProfile.DoesNotExist:
        if request.method == 'POST':
            user_form = UserForm(request.POST, instance=request.user)
            profile_form = UserProfileForm(request.POST)
            if user_form.is_valid() and profile_form.is_valid():
                user = user_form.save()
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()
                messages.success(request, 'Profile created successfully!')
                return redirect('profile_view')
        else:
            user_form = UserForm(instance=request.user)
            profile_form = UserProfileForm()
        return render(request, 'profileCreate.html', {
            'user_form': user_form,
            'profile_form': profile_form
        })

def profileUpdate(request):
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile does not exist. Please create one.')
        return redirect('create_profile')

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=user_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    return render(request, 'profileUpdate.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


def user_payments_view(request):
    user = request.user
    # Get payments where the user is the payer or the receiver
    payments_made = Settlement.objects.filter(payer=user).order_by('-date')
    payments_received = Settlement.objects.filter(receiver=user).order_by('-date')

    context = {
        'payments_made': payments_made,
        'payments_received': payments_received,
    }
    return render(request, 'user_payments.html', context)