from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("ask/", views.AskView.as_view(), name="ask"),
    path("ask/done/", views.AskDoneView.as_view(), name="ask_done"),
    path("board/", views.BoardView.as_view(), name="board"),
    path("board/<str:reference>/", views.QuestionDetailView.as_view(), name="detail"),
    path("track/", views.TrackView.as_view(), name="track"),
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("inbox/<str:reference>/", views.InboxDetailView.as_view(), name="inbox_detail"),
    path("answers/<int:pk>/edit/", views.AnswerEditView.as_view(), name="answer_edit"),
]
