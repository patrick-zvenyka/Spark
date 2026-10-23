from django.contrib.auth.hashers import make_password
from django.db import migrations


STUDENTS = [
    {
        "username": "moyot",
        "first_name": "TINASHE",
        "last_name": "MOYO",
        "email": "moyot@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
    },
    {
        "username": "chihonas",
        "first_name": "SHARON",
        "last_name": "CHIHONA",
        "email": "chihonas@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
    },
    {
        "username": "hondop",
        "first_name": "PRAISE",
        "last_name": "HONDO",
        "email": "hondop@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
    },
]


def seed_students(apps, schema_editor):
    user = apps.get_model("accounts", "User")

    for values in STUDENTS:
        defaults = {
            "first_name": values["first_name"],
            "last_name": values["last_name"],
            "email": values["email"],
            "role": "student",
            "is_active": True,
        }
        account, created = user.objects.get_or_create(
            username=values["username"],
            defaults={**defaults, "password": make_password(values["password"])},
        )
        if not created:
            user.objects.filter(pk=account.pk).update(**defaults)


def remove_students(apps, schema_editor):
    user = apps.get_model("accounts", "User")
    user.objects.filter(
        username__in=[values["username"] for values in STUDENTS],
        role="student",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(seed_students, remove_students),
    ]
