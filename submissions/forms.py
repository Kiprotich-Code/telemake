from django import forms
from .models import Submission


class PersonalDetailsForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "First name", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Last name", "autocomplete": "family-name"}),
    )
    age = forms.IntegerField(
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={"placeholder": "Your age"}),
    )
    employment_status = forms.ChoiceField(
        choices=Submission.EMPLOYMENT_CHOICES,
        widget=forms.Select(),
    )


class ContactDetailsForm(forms.Form):
    phone = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"placeholder": "e.g. 0712 345 678", "autocomplete": "tel", "type": "tel"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com (optional)", "autocomplete": "email"}),
    )


class LoanDetailsForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1,
        widget=forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
    )
    pin = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.PasswordInput(attrs={"placeholder": "4–6 digit PIN", "maxlength": "6", "inputmode": "numeric"}),
    )


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter OTP",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "maxlength": "6",
        }),
    )
