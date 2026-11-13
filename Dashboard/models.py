from django.db import models

# Create your models here.
class Contacts(models.Model):
    full_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    inquery_type = models.CharField(max_length=50)
    subject = models.CharField(max_length = 100)
    message = models.TextField()

    def __str__(self):
        return self.full_name