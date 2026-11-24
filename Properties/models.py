from django.db import models

# Create your models here.
class Rooms(models.Model):
    room_number = models.IntegerField(unique=True)
    room_type = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Room {self.room_number}"


class RoomImage(models.Model):
    room = models.ForeignKey(
        Rooms,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='room_images/')
    caption = models.CharField(max_length=120, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('position', 'pk')

    def __str__(self):
        return f"Image for {self.room}"