from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers import TransferSerializer


class TransferView(APIView):
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        serializer = TransferSerializer(data=request.data)

        if serializer.is_valid():
            from_user_id = serializer.validated_data['from_user_id']
            to_users_inn = serializer.validated_data['to_users_inn']
            debit_amount = serializer.validated_data['debit_amount']

            if request.user.inn in to_users_inn:
                return Response(
                    {"error": "You cannot debit and credit money to the same account. Please enter a valid INN."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                try:
                    from_user = User.objects.select_for_update().get(id=from_user_id)
                    if from_user.balance < debit_amount:
                        return Response(
                            {"error": "This user has Insufficient funds"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    to_users = User.objects.filter(inn__in=to_users_inn)
                    to_users_count = to_users.count()
                    if to_users.count() != len(to_users_inn):
                        return Response({"error": "Invalid INN(s)"}, status=status.HTTP_400_BAD_REQUEST)

                    with transaction.atomic():
                        # update balance for from_user
                        from_user.balance -= debit_amount
                        from_user.save()

                        # update balances for to_users
                        for to_user in to_users:
                            to_user.balance += (debit_amount / to_users_count)
                            to_user.save()
                    return Response({"Success": "Money transfer successful."}, status=status.HTTP_200_OK)

                except User.DoesNotExist:
                    return Response({"error": "Invalid user ID"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
