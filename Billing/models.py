from django.db import models

# Create your models here.
class Payments(models.Model):
    CATEGORY_CHOICES = [
        ('room', 'Room'),
        ('food', 'Food'),
        ('other', 'Other'),
    ]

    payment_id = models.AutoField(primary_key=True)
    guest = models.ForeignKey('Reservations.Guests', on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default='other')

    def __str__(self):
        return f"Payment {self.payment_id} by {self.guest.full_name}"