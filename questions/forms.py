from django import forms

from core.models import Department, Topic

from .models import Answer, Question, normalize_code


class TopicSelect(forms.Select):
    """Select that tags each topic with its department so JS can filter options."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-department"] = str(instance.department_id)
        return option


class AskForm(forms.ModelForm):
    agree_rules = forms.BooleanField(
        label="I have not included my name, registration number or class details, and I agree to the community rules.",
    )
    # Honeypot: real users never see or fill this field.
    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = Question
        fields = ["department", "topic", "title", "body"]
        labels = {
            "department": "Which department should answer?",
            "topic": "Topic (optional)",
            "title": "Your question in one line",
            "body": "Details",
        }
        help_texts = {
            "body": "Explain what you need to know. Do not include names, registration numbers, phone numbers or class details.",
        }
        widgets = {
            "topic": TopicSelect,
            "title": forms.TextInput(attrs={"placeholder": "e.g. How is the coursework mark weighted?", "maxlength": 160}),
            "body": forms.Textarea(attrs={"rows": 7, "data-maxlength": 4000, "data-pii-check": "true"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["department"].empty_label = "Choose a department"
        self.fields["topic"].queryset = Topic.objects.filter(
            is_active=True, department__is_active=True
        ).select_related("department")
        self.fields["topic"].required = False
        self.fields["topic"].empty_label = "Not sure / general"
        self.fields["title"].widget.attrs["data-pii-check"] = "true"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""

    def clean_title(self):
        return " ".join(self.cleaned_data["title"].split())

    def clean_body(self):
        return self.cleaned_data["body"].strip()

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        topic = cleaned.get("topic")
        if department and topic and topic.department_id != department.pk:
            self.add_error("topic", "That topic does not belong to the selected department.")
        return cleaned


class TrackForm(forms.Form):
    reference = forms.CharField(
        max_length=20, label="Question reference", widget=forms.TextInput(attrs={"placeholder": "e.g. K7M2QX9P", "autocomplete": "off"})
    )
    access_key = forms.CharField(
        max_length=40,
        label="Private key",
        widget=forms.PasswordInput(attrs={"placeholder": "XXXX-XXXX-XXXX", "autocomplete": "off"}, render_value=True),
    )

    error_message = "We could not find a question with that reference and key."

    def clean(self):
        cleaned = super().clean()
        reference = normalize_code(cleaned.get("reference", ""))
        key = cleaned.get("access_key", "")
        if not reference or not key:
            return cleaned
        question = Question.objects.filter(reference=reference).select_related("department", "topic").first()
        if question is None or not question.check_access_key(key):
            raise forms.ValidationError(self.error_message)
        cleaned["question"] = question
        return cleaned


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["body"]
        labels = {"body": "Your answer"}
        help_texts = {"body": "Your name will be shown with this answer on the public board."}
        widgets = {"body": forms.Textarea(attrs={"rows": 7, "data-maxlength": 8000})}

    def clean_body(self):
        return self.cleaned_data["body"].strip()


class ModerationForm(forms.Form):
    ACTION_LABELS = {
        "publish": "Publish on the board",
        "unpublish": "Hide from the board",
        "close": "Close (no more answers)",
        "reopen": "Reopen",
        "forward": "Forward to another department",
        "reject": "Remove for misuse",
    }

    action = forms.ChoiceField(choices=())
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), required=False, label="Forward to"
    )
    note = forms.CharField(
        required=False,
        max_length=1000,
        label="Reason",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Required when removing a question. Shown to the student on the tracking page.",
    )

    def __init__(self, *args, question, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        self.user = user
        self.fields["action"].choices = [(a, self.ACTION_LABELS[a]) for a in self.available_actions()]
        self.fields["department"].queryset = Department.objects.filter(is_active=True).exclude(pk=question.department_id)

    def available_actions(self):
        q, S = self.question, Question.Status
        actions = []
        if q.status != S.REJECTED:
            actions.append("unpublish" if q.is_public else "publish")
        if q.status in (S.OPEN, S.ANSWERED):
            actions.append("close")
        if q.status in (S.CLOSED, S.REJECTED):
            actions.append("reopen")
        if q.status == S.OPEN:
            actions.append("forward")
        if q.status != S.REJECTED and self.user.can_supervise:
            actions.append("reject")
        return actions

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        if action == "forward" and not cleaned.get("department"):
            self.add_error("department", "Choose the department to forward this question to.")
        if action == "reject" and not cleaned.get("note", "").strip():
            self.add_error("note", "Please give a reason so the student understands why.")
        return cleaned
