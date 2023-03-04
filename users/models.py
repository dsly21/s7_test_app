from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    inn = models.IntegerField(
        validators=[RegexValidator(r'^\d{10,12}$')],
        unique=True,
        verbose_name='ИНН пользователя',
    )
    balance = models.DecimalField(
        verbose_name='Баланс на счету',
        default=0,
        decimal_places=2,
        max_digits=100
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
