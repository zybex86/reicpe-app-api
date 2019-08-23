from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


class AdminSiteTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@domo.pl',
            password='admin123'
        )
        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email='test@test.pl',
            password='test123',
            name='Test user full name'
        )

    def test_users_listed(self):
        """
        Test that users are listed on user page
        """
        url = reverse('admin:core_user_changelist')
        result = self.client.get(url)

        self.assertContains(result, self.user.name)
        self.assertContains(result, self.user.email)

    def test_user_change_page(self):
        """
        Test that the user edit page works
        """
        url = reverse('admin:core_user_change', args=[self.user.id])
        result = self.client.get(url)

        self.assertEqual(result.status_code, 200)

    def test_create_user_page(self):
        """
        Test that the user page works
        """
        url = reverse('admin:core_user_add')
        result = self.client.get(url)

        self.assertEqual(result.status_code, 200)