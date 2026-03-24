"""
Forms for Accounts Module
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Company


class UserRegistrationForm(UserCreationForm):
    """User Registration Form"""
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )
    user_type = forms.ChoiceField(
        choices=User.UserType.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2', 'user_type']


class ComprehensiveRegistrationForm(forms.Form):
    """Combined User and Company Registration Form"""
    
    # User Fields
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmer le mot de passe'}))
    
    # Company Fields
    company_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'entreprise'}))
    company_type = forms.ChoiceField(choices=Company.CompanyType.choices, widget=forms.Select(attrs={'class': 'form-select'}))
    registration_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° de Registre du Commerce'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville'}))
    country = forms.CharField(max_length=100, initial='Sénégal', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pays'}))
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        if User.objects.filter(email=cleaned_data.get("email")).exists():
            raise forms.ValidationError("Un utilisateur avec cet email existe déjà.")
        return cleaned_data


class UserLoginForm(AuthenticationForm):
    """User Login Form"""
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )


class CompanyForm(forms.ModelForm):
    """Company Creation/Update Form"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'company_type', 'accounting_standard',
            'registration_number', 'tax_id', 'vat_number',
            'address', 'city', 'country', 'postal_code',
            'phone', 'email', 'website',
            'legal_form', 'capital', 'fiscal_year_start', 'fiscal_year_end',
            'base_currency', 'timezone', 'language'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_type': forms.Select(attrs={'class': 'form-select'}),
            'accounting_standard': forms.Select(attrs={'class': 'form-select'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'legal_form': forms.TextInput(attrs={'class': 'form-control'}),
            'capital': forms.NumberInput(attrs={'class': 'form-control'}),
            'fiscal_year_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fiscal_year_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'base_currency': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
        }


class UserProfileForm(forms.ModelForm):
    """User Profile Update Form"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'job_title', 'department', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class UserPreferencesForm(forms.ModelForm):
    """User Preferences Form"""
    
    class Meta:
        model = User
        fields = ['language', 'timezone', 'currency']
        widgets = {
            'language': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }
