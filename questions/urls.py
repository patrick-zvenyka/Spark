from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("ask/", views.AskView.as_view(), name="ask"),
    path("board/", views.BoardView.as_view(), name="board"),
    path("board/<int:pk>/", views.QuestionDetailView.as_view(), name="detail"),
    path("my-questions/", views.StudentInboxView.as_view(), name="student_inbox"),
    path("my-questions/<int:pk>/", views.StudentInboxDetailView.as_view(), name="student_inbox_detail"),
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("inbox/<int:pk>/", views.InboxDetailView.as_view(), name="inbox_detail"),
    path("answers/<int:pk>/edit/", views.AnswerEditView.as_view(), name="answer_edit"),
]
