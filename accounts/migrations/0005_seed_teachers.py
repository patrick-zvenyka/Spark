from django.contrib.auth.hashers import make_password
from django.db import migrations


TEACHERS = [
    {
        "username": "zororot",
        "first_name": "TINASHE",
        "last_name": "ZORORO",
        "email": "zororot@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
        "department": "SCIENCES",
    },
    {
        "username": "chimombel",
        "first_name": "LOVENESS",
        "last_name": "CHIMOMBE",
        "email": "chimombel@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
        "department": "COMMERCE",
    },
    {
        "username": "gariras",
        "first_name": "SAMSON",
        "last_name": "GARIRA",
        "email": "gariras@students.schoolbridge.ac.zw",
        "password": "vykrie18*",
        "department": "ARTS",
    },
]


def seed_teachers(apps, schema_editor):
    user = apps.get_model("accounts", "User")
    department = apps.get_model("core", "Department")

    for values in TEACHERS:
        assigned_department = department.objects.filter(name=values["department"]).first()
        defaults = {
            "first_name": values["first_name"],
            "last_name": values["last_name"],
            "email": values["email"],
            "role": "teacher",
            "department": assigned_department,
            "is_active": True,
            "is_staff": False,
        }
        account, created = user.objects.get_or_create(
            username=values["username"],
            defaults={**defaults, "password": make_password(values["password"])},
        )
        if not created:
            user.objects.filter(pk=account.pk).update(**defaults)


def remove_teachers(apps, schema_editor):
    user = apps.get_model("accounts", "User")
    user.objects.filter(
        username__in=[values["username"] for values in TEACHERS],
        role="teacher",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_alter_user_contract_end_alter_user_role"),
        ("core", "0002_seed_departments"),
    ]

    operations = [
        migrations.RunPython(seed_teachers, remove_teachers),
    ]
