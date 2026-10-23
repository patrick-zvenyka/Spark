from django.contrib import messages
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.models import User
from notifications.models import Notification
from notifications.services import notify

from .forms import CommentForm, PostForm, StaffSignupForm
from .models import Post



class StaffLoginView(auth_views.LoginView):
    template_name = "tutors/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("dashboard:home")


class StaffSignupView(CreateView):
    form_class = StaffSignupForm
    template_name = "tutors/signup.html"
    success_url = reverse_lazy("staffroom:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Your staff account has been created.")
        return response


class PostListView(LoginRequiredMixin, ListView):
    template_name = "staffroom/list.html"
    context_object_name = "posts"
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Post.objects.visible_to(self.request.user)
            .select_related("author", "department")
            .annotate(num_comments=Count("comments"))
        )
        self.kind = self.request.GET.get("kind", "")
        if self.kind in Post.Kind.values:
            qs = qs.filter(kind=self.kind)
        else:
            self.kind = ""
        self.query = self.request.GET.get("q", "").strip()[:100]
        if self.query:
            qs = qs.filter(Q(title__icontains=self.query) | Q(body__icontains=self.query) | Q(course__icontains=self.query))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(kinds=Post.Kind.choices, kind=self.kind, query=self.query)
        return ctx


class PostVisibilityMixin:
    def get_visible_post(self, pk):
        return get_object_or_404(
            Post.objects.visible_to(self.request.user).select_related("author", "department"), pk=pk
        )


class PostDetailView(LoginRequiredMixin, PostVisibilityMixin, View):
    template_name = "staffroom/detail.html"

    def render_page(self, post, form=None, status=200):
        return render(
            self.request,
            self.template_name,
            {
                "post": post,
                "comments": post.comments.select_related("author"),
                "comment_form": form or CommentForm(),
                "can_edit": post.can_edit(self.request.user),
                "can_delete": post.can_delete(self.request.user),
            },
            status=status,
        )

    def get(self, request, pk):
        return self.render_page(self.get_visible_post(pk))

    def post(self, request, pk):
        post = self.get_visible_post(pk)
        form = CommentForm(request.POST)
        if not form.is_valid():
            return self.render_page(post, form, status=400)
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        if post.author_id != request.user.pk:
            notify(
                [post.author],
                kind=Notification.Kind.STAFFROOM_COMMENT,
                title=f"{request.user.display_name} commented on “{post.title[:80]}”",
                url=post.get_absolute_url(),
            )
        messages.success(request, "Comment added.")
        return redirect(post)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "staffroom/form.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        post = self.object
        recipients = User.objects.filter(is_active=True).exclude(pk=self.request.user.pk)
        if post.department_id:
            recipients = recipients.filter(department_id=post.department_id)
        notify(
            recipients,
            kind=Notification.Kind.STAFFROOM_POST,
            title=f"{post.get_kind_display()}: {post.title[:100]}",
            message=f"Posted by {self.request.user.display_name}",
            url=post.get_absolute_url(),
        )
        messages.success(self.request, "Posted to the staff room.")
        return response


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = "staffroom/form.html"

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        if not post.can_edit(self.request.user):
            raise PermissionDenied
        return post

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        messages.success(self.request, "Post updated.")
        return super().form_valid(form)


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = "staffroom/confirm_delete.html"
    success_url = reverse_lazy("staffroom:list")

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        if not post.can_delete(self.request.user):
            raise PermissionDenied
        return post

    def form_valid(self, form):
        if self.object.attachment:
            self.object.attachment.delete(save=False)
        messages.success(self.request, "Post deleted.")
        return super().form_valid(form)


class AttachmentDownloadView(LoginRequiredMixin, PostVisibilityMixin, View):
    """Serve staff-room files only to staff who are allowed to see the post."""

    def get(self, request, pk):
        post = self.get_visible_post(pk)
        if not post.attachment:
            raise Http404
        try:
            handle = post.attachment.open("rb")
        except FileNotFoundError as exc:
            raise Http404 from exc
        return FileResponse(handle, as_attachment=True, filename=post.attachment_name)
