from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('coach', 'Coach'),
        ('athlete', 'Athlete'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    

class LessonPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course_id = models.CharField(max_length=100)
    lesson_index = models.IntegerField()
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course_id', 'lesson_index')


class Course(models.Model):
    course_id_str = models.CharField(max_length=50, unique=True, primary_key=True) # e.g., 'course-1'
    name = models.CharField(max_length=100)
    price = models.IntegerField() # Store price in paise (e.g., 10000 for ₹100)

    def __str__(self):
        return self.name

# 2. NEW: Model to track which user has unlocked which course
class UserCourseUnlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures a user can't unlock the same course twice
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} unlocked {self.course.name}"