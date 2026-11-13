from django.db import models

# Create your models here.
class Users(models.Model):
    fullname = models.CharField(max_length = 100)
    username = models.CharField(max_length = 100)
    email = models.EmailField()
    phone = models.CharField(max_length = 10)
    role = models.CharField(max_length = 100)
    password = models.CharField(max_length = 100)

    def __str__(self):
        return self.username
