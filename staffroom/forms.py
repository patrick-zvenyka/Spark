from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User
from core.models import Department

from .models import Comment, Post


class StaffSignupForm(UserCreationForm):
    TITLE_CHOICES = [
        ("Dr", "Dr"),
        ("Mr", "Mr"),
        ("Mrs", "Mrs"),
        ("Ms", "Ms"),
    ]
    title = forms.ChoiceField(required=False, choices=TITLE_CHOICES, label="Title")
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), label="Department")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "title", "first_name", "last_name", "email", "department")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        user.employment_type = User.Employment.PERMANENT
        if commit:
            user.save()
        return user


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["kind", "title", "department", "course", "body", "link", "attachment", "is_pinned"]
        labels = {"department": "Share with", "is_pinned": "Pin to the top"}
        widgets = {"body": forms.Textarea(attrs={"rows": 9, "data-maxlength": 10000})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        department_field = self.fields["department"]
        if user.is_system_admin:
            department_field.queryset = Department.objects.all()
        else:
            department_field.queryset = Department.objects.filter(pk=user.department_id)
        department_field.empty_label = "Whole institution"
        if not self.instance.pk and user.department_id:
            self.initial.setdefault("department", user.department_id)
        if not user.can_supervise:
            del self.fields["is_pinned"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "Add a comment"}
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}
