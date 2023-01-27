from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, User, Comment, Follow
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.cache import cache_page


def get_paginated_page(request, queryset):
    paginator = Paginator(queryset, settings.QUANTITY_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {
        'paginator': paginator,
        'page_number': page_number,
        'page_obj': page_obj,
    }


@cache_page(20, key_prefix='index_page')
def index(request):
    """Выводит шаблон главной страницы."""
    posts = Post.objects.all()
    context = get_paginated_page(request, posts)
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Выводит шаблон с группами постов."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    context = {
        'group': group,
    }
    context.update(get_paginated_page(request, posts))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Выводит шаблон профайла пользователя."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    post_count = posts.count()
    following = author.following.exists()
    context = {
        'posts': posts,
        'author': author,
        'post_count': post_count,
        'following': following,
    }
    context.update(get_paginated_page(request, posts))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Выводит шаблон информации о посте пользователя."""
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, pk=post_id)
    post_count = post.author.posts.count()
    comments = Comment.objects.filter(post=post)
    context = {
        'post_count': post_count,
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Выводит шаблон добавления нового поста пользователя."""
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Выводит шаблон редактирование поста пользователя."""
    is_edit = True
    post = get_object_or_404(Post, id=post_id, author=request.user)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create_post.html',
                  {'form': form, 'post': post, 'is_edit': is_edit})


@login_required
def add_comment(request, post_id):
    """Для обработки отправленного комментария."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """информация о текущем пользователе в переменной request.user"""
    posts = Post.objects.filter(author__following__user=request.user)
    context = {
        'title': 'Избранное',
    }
    context.update(get_paginated_page(request, posts))
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписаться на автора."""
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    """Дизлайк, отписка."""
    author = get_object_or_404(User, username=username)
    Follow.objects.get(user=request.user, author=author).delete()
    return redirect('posts:follow_index')
