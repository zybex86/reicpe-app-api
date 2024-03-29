import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPIES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return recipe image upload URL"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def recipe_detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Salt'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 10,
        'price': 5
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipiesApiTests(TestCase):
    """Test the publicly available ingredients API"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required for retrieving ingredients"""

        response = self.client.get(RECIPIES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipiesApiTest(TestCase):
    """Test the authorised user ingredients API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipies(self):
        """Test retrieving recipies"""

        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPIES_URL)

        recipies = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipies_limited_to_user(self):
        """Test that recipies returned are for the authenticated user"""
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'otherpass'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPIES_URL)

        recipies = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_detail_view(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = recipe_detail_url(recipe.id)
        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe_invalid(self):
        """Test creating recipe fails"""
        payload = {'title': ''}
        response = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recipe_successful(self):
        """Test creating a new recipe"""
        payload = {
            'title': 'Peanut Butter Sandwich',
            'time_minutes': 5,
            'price': 1.00
        }
        response = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Creating a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Vegetarian')
        tag2 = sample_tag(user=self.user, name='Breakfast')
        payload = {
            'title': 'Zuccini Scrambled Eggs',
            'time_minutes': 10,
            'price': 3.00,
            'tags': [tag1.id, tag2.id]
        }
        response = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        tags = recipe.tags.all()
        self.assertAlmostEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Creating a recipe with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name='Eggs')
        ingredient2 = sample_ingredient(user=self.user, name='Zuccini')
        payload = {
            'title': 'Zuccini Scrambled Eggs',
            'time_minutes': 10,
            'price': 3.00,
            'ingredients': [ingredient1.id, ingredient2.id]
        }
        response = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertAlmostEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Hot Or Cold')
        payload = {'title': 'Hard Boiled Eggs', 'tags': [new_tag.id]}
        url = recipe_detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.ingredients.add(sample_ingredient(user=self.user))

        payload = {
            'title': 'Puffed Omlette',
            'time_minutes': 10,
            'price': 3.00
        }
        url = recipe_detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])

        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)


class RecipeImageUploadTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        """Test uploading an image to recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as named_file:
            img = Image.new('RGB', (10, 10))
            img.save(named_file, format='JPEG')
            named_file.seek(0)
            response = self.client.post(
                url, {'image': named_file}, format='multipart'
            )

        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image"""
        url = image_upload_url(self.recipe.id)
        response = self.client.post(
            url, {'image': 'not image'}, format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        """Test returning recipies with specific tags"""
        recipe1 = sample_recipe(user=self.user, title='Boiled Sausages')
        recipe2 = sample_recipe(user=self.user, title='Zuccini Pasta')
        tag1 = sample_tag(user=self.user, name='Meat')
        tag2 = sample_tag(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = sample_recipe(user=self.user, title='Chocolate Cake')

        response = self.client.get(
            RECIPIES_URL,
            {'tags': f'{tag1.id}, {tag2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipies with specific ingredients"""
        recipe1 = sample_recipe(user=self.user, title='Pancakes')
        recipe2 = sample_recipe(user=self.user, title='Cheese Cake')
        ingredient1 = sample_ingredient(user=self.user, name='Milk')
        ingredient2 = sample_ingredient(user=self.user, name='Cottage Cheese')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = sample_recipe(user=self.user, title='Banana Shake')

        response = self.client.get(
            RECIPIES_URL,
            {'ingredients': f'{ingredient1.id}, {ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)
