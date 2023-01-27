import shutil
import tempfile

from ..models import Post, Group, User, Comment, Follow

from django import forms
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='StasBasov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif', content=cls.small_gif, content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': cls.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.client = Client()
        self.user = User.objects.create_user(username='user')
        self.client.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, reverse_name in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        expected = list(Post.objects.filter(group_id=self.group.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        expected = list(Post.objects.filter(author_id=self.post.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        form_fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_comment_correct(self):
        """Форма комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {'text': 'Тестовый коммент'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(text='Тестовый коммент').exists()
        )

    def test_check_cache_index(self):
        """Проверка работы кэша страници index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='Тестовый пост',
            author=self.user,
        )
        response_old = self.authorized_client.get(reverse('posts:index'))
        posts_old = response_old.content
        self.assertEqual(posts_old, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        posts_new = response_new.content
        self.assertNotEqual(posts_old, posts_new)

    def test_follow(self):
        """Тест подписаться."""
        self.response = (self.client.get(
            reverse('posts:profile_follow', args={self.post.author})))
        self.assertIs(
            Follow.objects.
            filter(user=self.user, author=self.post.author).exists(),
            True
        )

    def test_unfollow(self):
        """Тест отписаться."""
        self.response = (self.client.get(
            reverse('posts:profile_follow', args={self.post.author})))
        self.response = (self.client.get(
            reverse('posts:profile_unfollow', args={self.post.author})))
        self.assertIs(
            Follow.objects.
            filter(user=self.user, author=self.post.author).exists(),
            False
        )

    def test_new_post_for_follow_authorized_client(self):
        """Пост появляется у подписанного пользователя."""
        Follow.objects.create(user=self.user, author=self.post.author)
        response = (self.client.get(reverse('posts:follow_index')))
        self.assertIn(self.post, response.context['page_obj'])

    def test_new_post_for_follow_guest_client(self):
        """Пост не появляется у не подписанного пользователя."""
        User.objects.create_user(username='user_test', password='pass')
        self.client.login(username='user_test', password='pass')
        response = (self.client.get(reverse('posts:follow_index')))
        self.assertNotIn(self.post, response.context['page_obj'])
