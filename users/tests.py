from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

import pytest

from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestMoneyTransferUserView(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create(
            username="testuser1",
            password="testpassword",
            email="testuser1@test.com",
            inn="1234567890",
            balance=100.0
        )
        self.user2 = User.objects.create(
            username="testuser2",
            email="testuser2@test.com",
            inn="0987654321",
            balance=200.0
        )
        self.valid_payload_data = {
            "inn": "01234567899",
            "balance": 50.0
        }
        self.invalid_payload_data = {
            "inn": "01234567891234",
            "balance": 50.0
        }
        self.client.force_login(self.user1)
        self.data_for_transfer_api = {
            "from_user_id": self.user1.id,
            "to_users_inn": [self.user2.inn, ],
            "debit_amount": 10

        }

    def test_create_user_with_valid_data(self):
        """
        We can to create a user with a valid INN.
        The length of INN cannot be less than 10 characters and more than 12 characters.
        """
        valid_user = User(
            username="testuser3",
            email="testuser3@test.com",
            password="testpassword",
            **self.valid_payload_data
        )
        try:
            valid_user.full_clean()
        except ValidationError as e:
            self.fail(f"ValidationError: {e}")

        user_with_invalid_inn = User(
            username="testuser4",
            email="testuser4@test.com",
            password="testpassword",
            **self.invalid_payload_data
        )
        self.assertRaises(ValidationError, user_with_invalid_inn.full_clean)

        self.invalid_payload_data['inn'] = '1234567890'

        user_with_invalid_inn = User(
            username="testuser4",
            email="testuser4@test.com",
            password="testpassword",
            **self.invalid_payload_data
        )
        self.assertRaises(ValidationError, user_with_invalid_inn.full_clean)

        self.invalid_payload_data['inn'] = 'some_string'

        user_with_invalid_inn = User(
            username="testuser4",
            email="testuser4@test.com",
            password="testpassword",
            **self.invalid_payload_data
        )
        self.assertRaises(ValidationError, user_with_invalid_inn.full_clean)

    def test_return_correct_status_code_from_request_url(self):
        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["Success"], 'Money transfer successful.')

    def test_unauthorized_user_cannot_make_transfer(self):
        self.client.logout()

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_after_transferring_balances_on_accounts_are_changed(self):
        self.assertEqual(self.user1.balance, 100)
        self.assertEqual(self.user2.balance, 200)

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user1.balance, 90)
        self.assertEqual(self.user2.balance, 210)

    def test_transfer_to_multiple_users(self):

        for i in range(10):
            User.objects.create(
                username="user" + str(i),
                email="testuser1@test.com",
                inn=str(i),
                balance=0
            )

        # transfer money to 10 users
        self.client.post(
            reverse("transfer-money"),
            data={
                "from_user_id": self.user1.id,
                "to_users_inn": [i for i in range(10)],
                "debit_amount": 15.40
            },
            format="json"
        )
        self.user1.refresh_from_db()
        self.assertEqual(float(self.user1.balance), 84.60)

        # Check changes to balance
        sum_users_balances = sum(
            User.objects.filter(inn__in=[i for i in range(10)])
            .values_list("balance", flat=True)
        )
        self.assertEqual(float(sum_users_balances), 15.40)

    def test_transfer_from_user_with_insufficient_funds(self):
        self.data_for_transfer_api["debit_amount"] = 100

        # after this transfer the balance is 0
        successful_response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(successful_response.status_code, status.HTTP_200_OK)

        unsuccessful_response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(unsuccessful_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unsuccessful_response.data['error'], 'This user has Insufficient funds')

    def test_transfer_to_non_existent_inn_returns_400(self):
        self.data_for_transfer_api["to_users_inn"] = ['111111111111', ]

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # User with INN 111111111111 - does not exist
        self.assertEqual(User.objects.filter(inn='111111111111').exists(), False)
        self.assertEqual(response.data['error'], 'Invalid INN(s)')

        # multiple_users
        self.data_for_transfer_api["to_users_inn"] = ['111111111111', self.user2.inn]

        response_with_multiple_users = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response_with_multiple_users.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(inn=self.user2.inn).exists(), True)
        self.assertEqual(response_with_multiple_users.data['error'], 'Invalid INN(s)')

    def test_transfer_from_non_existent_user_returns_400(self):
        self.data_for_transfer_api["from_user_id"] = 10

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        # User with id 10 does not exist
        self.assertEqual(User.objects.filter(id=self.data_for_transfer_api["from_user_id"]).exists(), False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Invalid user ID")

    def test_transfer_to_himself_returns_400(self):
        self.data_for_transfer_api["to_users_inn"] = [self.user1.inn, ]

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # multiple_users
        self.data_for_transfer_api = [self.user1.inn, self.user2.inn]
        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_money_with_invalid_amount_returns_400(self):
        self.data_for_transfer_api["debit_amount"] = 0

        response = self.client.post(
            reverse("transfer-money"),
            data=self.data_for_transfer_api,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['debit_amount'][0], 'Ensure this value is greater than or equal to 0.01.')

