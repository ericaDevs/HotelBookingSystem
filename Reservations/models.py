from django.db import models

# Create your models here.
class Guests(models.Model):
    full_name = models.CharField(max_length=50)
    Id_no = models.CharField(max_length=12)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    county_of_origin = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    check_in_date = models.DateField()
    check_out_date = models.DateField()


    def __str__(self):
        return self.full_name