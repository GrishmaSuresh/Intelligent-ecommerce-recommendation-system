from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.FloatField()
    category = models.CharField(max_length=120, blank=True)
    rating = models.FloatField(default=0.0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def purchased_by_any_in_circle(self, user):
        from .models import Circle, Purchase
        circle_members = Circle.objects.filter(owner=user).values_list('member', flat=True)
        return Purchase.objects.filter(user__in=circle_members, product=self).exists()

    def __str__(self):
        return self.name

class Circle(models.Model):
    owner = models.ForeignKey(User, related_name='circle_owner', on_delete=models.CASCADE)
    member = models.ForeignKey(User, related_name='circle_member', on_delete=models.CASCADE)
    relation = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('owner', 'member')

    def __str__(self):
        return f"{self.owner.username} -> {self.member.username}"

class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)
    qty = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} bought {self.product.name}"

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg from {self.sender} to {self.recipient} about {self.product.name}"


# 🆕 Reaction Model (for thumbs up/down)
class ProductFeedback(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(
        max_length=10,
        choices=[('like', 'Like'), ('dislike', 'Dislike')]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.user.username} -> {self.reaction} on {self.product.name}"