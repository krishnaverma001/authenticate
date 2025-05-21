from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .tokens import generate_token
from django.conf import settings
from django.core.mail import EmailMessage
from datetime import datetime


def index_view(request):
    return render(request, 'index.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'This username is already taken. Please choose another one.')
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return redirect('signup')

        if password1 != password2:
            messages.error(request, 'Passwords do not match. Please re-enter.')
            return redirect('signup')

        if not username.isalnum():
            messages.error(request, 'Username should contain only letters and numbers.')
            return redirect('signup')

        new_user = User.objects.create_user(username=username, email=email, password=password1)
        new_user.first_name = first_name
        new_user.last_name = last_name
        new_user.is_active = False
        new_user.save()

        current_site = get_current_site(request)
        from_email = settings.EMAIL_HOST_USER
        to_list = [new_user.email]
        subject = "Email confirmation"

        message = render_to_string('email.html', {
            'name': new_user.first_name,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(new_user.id)),
            'token': generate_token.make_token(new_user),
            'year': datetime.now().year,
        })

        email_msg = EmailMessage(subject, message, from_email, to_list)
        email_msg.content_subtype = 'html'  # Send as HTML email
        email_msg.send(fail_silently=True)

        link = f"http://{current_site.domain}" + reverse('activate', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(new_user.id)),
            'token': generate_token.make_token(new_user)
        })
        print("🔗 Confirmation link:", link)

        messages.success(request, "We've sent you a confirmation email. Please verify your account.")
        return redirect('login')

    return render(request, 'signup.html')


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        new_user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        new_user = None

    if new_user is not None and generate_token.check_token(new_user, token):
        new_user.is_active = True

        new_user.save()
        messages.success(request, "Your Account has been activated.")
        return redirect('login')

    else:
        return HttpResponse('Invalid Response.')


def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')

        user = authenticate(username=u, password=p)

        if user:
            login(request, user)
            messages.success(request, 'You have logged in successfully.')
            return render(request, 'index.html', {'name': user.first_name})
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return redirect('login')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect("index")
