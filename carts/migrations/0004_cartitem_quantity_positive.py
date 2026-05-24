from django.core.validators import MinValueValidator
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0003_cartitem_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='quantity',
            field=models.PositiveIntegerField(
                validators=[MinValueValidator(1)],
            ),
        ),
        migrations.AddConstraint(
            model_name='cartitem',
            constraint=models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name='cartitem_quantity_at_least_one',
            ),
        ),
    ]
