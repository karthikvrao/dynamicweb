from django.views.generic import FormView
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.http import HttpResponseRedirect


from membership.models import CustomUser

from .mailer import BaseEmail
from .forms import SetPasswordForm


class PasswordResetViewMixin(FormView):
    # template_name = 'hosting/reset_password.html'
    # form_class = PasswordResetRequestForm
    success_message = "The link to reset your email has been sent to your email"
    # success_url = reverse_lazy('hosting:login')

    def test_generate_email_context(self, user):
        context = {
            'user': user,
            'token': default_token_generator.make_token(user),
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'site_name': 'ungleich',
            'base_url': "{0}://{1}".format(self.request.scheme, self.request.get_host())

        }
        return context

    def form_valid(self, form):

        email = form.cleaned_data.get('email')
        user = CustomUser.objects.get(email=email)

        messages.add_message(self.request, messages.SUCCESS, self.success_message)

        context = self.test_generate_email_context(user)
        email_data = {
            'subject': 'Password Reset',
            'to': email,
            'context': context,
            'template_name': 'password_reset_email',
            'template_path': self.template_email_path
        }
        email = BaseEmail(**email_data)
        email.send()

        return HttpResponseRedirect(self.get_success_url())


class PasswordResetConfirmViewMixin(FormView):
    # template_name = 'hosting/confirm_reset_password.html'
    form_class = SetPasswordForm
    # success_url = reverse_lazy('hosting:login')

    def post(self, request, uidb64=None, token=None, *arg, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64)
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None

        form = self.form_class(request.POST)

        if user is not None and default_token_generator.check_token(user, token):
            if form.is_valid():
                new_password = form.cleaned_data['new_password2']
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password has been reset.')
                return self.form_valid(form)
            else:
                messages.error(request, 'Password reset has not been unsuccessful.')
                form.add_error(None, 'Password reset has not been unsuccessful.')
                return self.form_invalid(form)

        else:
            messages.error(request, 'The reset password link is no longer valid.')
            form.add_error(None, 'Password reset has not been unsuccessful.')
            return self.form_invalid(form)
