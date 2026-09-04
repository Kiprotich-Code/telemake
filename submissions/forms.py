from django import forms


class LoginForm(forms.Form):
    """Phone number + PIN — the only data we collect on the login page."""

    phone = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "placeholder": "712 345 678",
            "autocomplete": "tel",
            "inputmode": "tel",
            "id": "id_phone",
        }),
    )
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            "inputmode": "numeric",
            "maxlength": "4",
            "autocomplete": "current-password",
        }),
    )

    def clean_pin(self):
        pin = self.cleaned_data.get("pin", "")
        if not pin.isdigit():
            raise forms.ValidationError("PIN must be 4 digits.")
        return pin


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "maxlength": "6",
        }),
    )
