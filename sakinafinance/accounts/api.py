from rest_framework import serializers

from sakinafinance.core.api_mixins import CompanyScopedReadOnlyViewSet

from .models import User, Company, Entity

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'subscription_plan']

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class UserViewSet(CompanyScopedReadOnlyViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class CompanyViewSet(CompanyScopedReadOnlyViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    company_field = 'self'
