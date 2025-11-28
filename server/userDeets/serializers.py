from rest_framework import serializers
from .models import UserDeets,Medicine,Dose

class accountSerializers(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    is_staff = serializers.SerializerMethodField()


    class Meta:
        model = UserDeets
        fields = [
            'userid',
            'user',
            'email',
            'is_staff',
            'username',
            'phoneNo',
            'address',
            'fcm_token'
        ]

    def get_email(self, obj):
        return obj.user.email

    def get_is_staff(self, obj):
        return obj.user.is_staff



class DoseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dose
        fields = ['dose_name', 'description', 'dose_time']

class MedicineSerializer(serializers.ModelSerializer):
    doses = DoseSerializer(many=True)
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'description', 'manufacturer', 'expiry_date', 'doses']