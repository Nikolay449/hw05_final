from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Group, Post, User
from django.core.cache import cache

User = get_user_model()


class URLsPostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.no_author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        """Создаем пользователей."""
        self.guest_client = Client()
        self.author = Client()
        self.author.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.no_author)
        cache.clear()

    def test_pages_url_exists_at_desired_location(self):
        """Проверяем доступность страниц для пользователей."""
        pages: tuple = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user}/',
            f'/posts/{self.post.id}/',
        )
        for page in pages:
            with self.subTest(address=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_task_list_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу '/create/', '/posts/<post_id>/edit/'
         перенаправит анонимного
        пользователя на страницу логина.
        """
        url_pages_readdress_pages = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{self.post.id}/edit/': f'/auth/login/?next='
            f'/posts/{self.post.id}/edit/',
        }
        for address, readdress in url_pages_readdress_pages.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, readdress)

    def test_new_post_page_exists_at_authorized(self):
        """Страница создания поста доступна авторизованному прользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post_page_exists_at_desired_location_author(self):
        """Страница '/post/<post_id>/edit/' доступна авторизованному
        пользователю."""
        response = self.author.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующие шаблоны страниц."""
        # Шаблоны по адресам
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.user}/',
            'posts/create_post.html': '/create/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_unexisting_page_url_exists_at_desired_location(self):
        """Проверяем вызов несуществующей страницы."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
