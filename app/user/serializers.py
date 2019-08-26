from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """ Serializer for the users object """

    def create(self, validated_data):
        """
        Create a new user with encrypted password and return it
        """

        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """
        Update the user, setting the password correctly and return it
        """

        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user

    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'name')
        extra_kwargs = {
            'password':
            {
                'write_only': True,
                'min_length': 5
            }
        }


class AuthTokenSerializer(serializers.Serializer):
    """ Serializer for the user authentication token """

    email = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attribute):
        """ Validate and authenticate the user """

        email = attribute.get('email')
        password = attribute.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            message = _('Unable to authenticate with provided credentials.')
            raise serializers.ValidationError(message, code='authentication')

        attribute['user'] = user
        return attribute
