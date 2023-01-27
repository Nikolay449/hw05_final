from http import HTTPStatus
from posts.forms import PostForm
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Post, Group, User


User = get_user_model()


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Страница создания поста: валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый тестовый пост',
            'group': self.group.id
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        last_object = Post.objects.all()[0]
        self.assertEqual(last_object.text, 'Новый тестовый пост')
        self.assertEqual(last_object.author, self.user)
        self.assertEqual(last_object.group.title, 'Тестовая группа')

    def test_edit_post(self):
        """Страница редактирования поста: валидная форма """
        """изменяет запись в Post по id."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменённый тестовый пост',
            'author': self.user
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.id, )),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.id, )
        ))
        edit_object = Post.objects.all().last()
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(edit_object.text, 'Изменённый тестовый пост', )
        self.assertEqual(edit_object.author, self.user)
