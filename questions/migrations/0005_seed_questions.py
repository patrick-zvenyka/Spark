from datetime import timedelta

from django.db import migrations
from django.utils import timezone


QUESTIONS = {
    "moyot": {
        "department": "SCIENCES",
        "topic_prefix": "science",
        "questions": [
            ("How does photosynthesis convert light into energy?", "Please explain the main stages of photosynthesis and where each stage takes place in a plant cell."),
            ("What is the difference between speed and velocity?", "Explain speed and velocity with examples, including the role of direction in each quantity."),
            ("How are elements arranged in the periodic table?", "Describe the arrangement of elements by atomic number and explain the patterns found in groups and periods."),
            ("Why is biodiversity important to ecosystems?", "Discuss how species diversity helps ecosystems remain stable and resilient to environmental change."),
            ("How does the greenhouse effect influence climate?", "Explain the greenhouse effect, the gases involved, and how it contributes to climate change."),
        ],
    },
    "chihonas": {
        "department": "ARTS",
        "topic_prefix": "arts",
        "questions": [
            ("How did colonial rule affect African societies?", "Explain at least three political, economic, or social effects of colonial rule on African societies."),
            ("What makes a poem effective?", "Describe the use of imagery, rhythm, and symbolism in an effective poem, with one simple example."),
            ("How can oral traditions preserve cultural history?", "Discuss the value of oral traditions in passing knowledge, values, and historical events between generations."),
            ("What is the purpose of figurative language?", "Explain how metaphors, similes, and personification help writers communicate ideas and emotions."),
            ("How should evidence be used in a history essay?", "Describe how students can select, cite, and interpret evidence to support a clear historical argument."),
        ],
    },
    "hondop": {
        "department": "COMMERCE",
        "topic_prefix": "commerce",
        "questions": [
            ("How does double-entry accounting work?", "Explain the debit and credit rules and demonstrate how a cash purchase affects a basic ledger."),
            ("What factors influence consumer demand?", "Discuss how price, income, tastes, substitutes, and advertising can change the demand for a product."),
            ("Why is cash-flow management important for a business?", "Explain how cash inflows and outflows affect a business and why forecasting cash flow helps prevent problems."),
            ("How do businesses set a selling price?", "Compare cost-based and market-based pricing and identify factors that a business should consider."),
            ("What is the role of entrepreneurship in the economy?", "Explain how entrepreneurs create businesses, employment, innovation, and value for communities."),
        ],
    },
}

TOPICS = {
    "SCIENCES": ["Biology", "Chemistry", "Mathematics", "Geography", "Science"],
    "ARTS": ["History", "English", "Chishona", "Heritage Studies"],
    "COMMERCE": ["Accounts", "Business Studies", "Commerce"],
}


def slugify(value):
    return "-".join(value.lower().replace("/", " ").split())[:90]


def seed_questions(apps, schema_editor):
    user = apps.get_model("accounts", "User")
    department = apps.get_model("core", "Department")
    topic = apps.get_model("core", "Topic")
    question = apps.get_model("questions", "Question")

    for department_name, topic_names in TOPICS.items():
        department_record = department.objects.filter(name=department_name).first()
        if department_record is None:
            continue
        for topic_name in topic_names:
            topic.objects.get_or_create(
                department_id=department_record.pk,
                slug=slugify(topic_name)[:90],
                defaults={"name": topic_name, "is_active": True},
            )

    now = timezone.now()
    for student_index, (username, data) in enumerate(QUESTIONS.items(), start=0):
        student = user.objects.filter(username=username, role="student").first()
        department_record = department.objects.filter(name=data["department"]).first()
        if student is None or department_record is None:
            continue

        department_topics = list(
            topic.objects.filter(department_id=department_record.pk, is_active=True)
            .order_by("name")[:5]
        )
        for question_index, (title, body) in enumerate(data["questions"]):
            assigned_topic = department_topics[question_index % len(department_topics)] if department_topics else None
            created_at = now - timedelta(days=student_index * 2 + question_index + 1)
            due_at = created_at + timedelta(hours=department_record.response_time_hours)
            question.objects.update_or_create(
                asked_by_id=student.pk,
                title=title,
                defaults={
                    "department_id": department_record.pk,
                    "topic_id": assigned_topic.pk if assigned_topic else None,
                    "body": body,
                    "status": "open",
                    "is_public": True,
                    "created_at": created_at,
                    "due_at": due_at,
                    "updated_at": created_at,
                },
            )


def remove_seeded_questions(apps, schema_editor):
    question = apps.get_model("questions", "Question")
    titles = [
        title
        for data in QUESTIONS.values()
        for title, body in data["questions"]
    ]
    question.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_seed_teachers"),
        ("core", "0002_seed_departments"),
        ("questions", "0004_remove_question_reference"),
    ]

    operations = [
        migrations.RunPython(seed_questions, remove_seeded_questions),
    ]
