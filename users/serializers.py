from rest_framework import serializers


class TransferSerializer(serializers.Serializer):

    from_user_id = serializers.IntegerField()
    to_users_inn = serializers.ListField(child=serializers.IntegerField())
    debit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
