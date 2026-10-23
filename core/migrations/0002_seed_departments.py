from django.db import migrations


DEPARTMENTS = [
    {
        "name": "SCIENCES",
        "code": "DP001",
        "slug": "dp001",
        "description": "DEPARTMENT OF SCIENCES",
    },
    {
        "name": "ARTS",
        "code": "DP002",
        "slug": "dp002",
        "description": "DEPARTMENT OF ARTS",
    },
    {
        "name": "COMMERCE",
        "code": "DP003",
        "slug": "dp003",
        "description": "DEPARTMENT OF COMMERCE",
    },
]


def seed_departments(apps, schema_editor):
    department = apps.get_model("core", "Department")

    for values in DEPARTMENTS:
        department.objects.update_or_create(
            code=values["code"],
            defaults={
                "name": values["name"],
                "slug": values["slug"],
                "description": values["description"],
                "is_active": True,
            },
        )


def remove_departments(apps, schema_editor):
    department = apps.get_model("core", "Department")
    department.objects.filter(code__in=[item["code"] for item in DEPARTMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_departments, remove_departments),
    ]
