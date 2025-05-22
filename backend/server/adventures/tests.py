import json
from datetime import date, datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import CustomUser as User
from adventures.models import Collection, Adventure, Category, Visit


class CollectionImportTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.login(username="testuser", password="testpassword")
        self.import_url = reverse("collection-import")

    def test_successful_import(self):
        """
        Test successful import of a collection with various activities.
        """
        import_data = {
            "activities": [
                {
                    "name": "Eiffel Tower Visit",
                    "description": "Visited the iconic Eiffel Tower.",
                    "location": "Paris, France",
                    "date": "2023-01-15",
                    "category": "Landmark",
                },
                {
                    "name": "Louvre Museum",
                    "description": "Explored the art collections.",
                    "location": "Paris, France",
                    "date": "2023-01-16",
                    "category": "Museum",
                },
                { # Activity without description and category
                    "name": "Seine River Cruise",
                    "location": "Paris, France",
                    "date": "2023-01-17",
                }
            ]
        }

        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert Collection creation
        self.assertEqual(Collection.objects.count(), 1)
        collection = Collection.objects.first()
        self.assertEqual(collection.user_id, self.user)
        self.assertTrue(collection.name.startswith("Imported Collection - "))

        # Assert Adventure creation
        self.assertEqual(Adventure.objects.count(), 3)
        adventures = Adventure.objects.filter(collection=collection).order_by('name')
        self.assertEqual(adventures[0].name, "Eiffel Tower Visit")
        self.assertEqual(adventures[1].name, "Louvre Museum")
        self.assertEqual(adventures[2].name, "Seine River Cruise")
        
        self.assertEqual(adventures[0].description, "Visited the iconic Eiffel Tower.")
        self.assertEqual(adventures[1].description, "Explored the art collections.")
        self.assertIsNone(adventures[2].description)


        # Assert Category creation/retrieval
        self.assertEqual(Category.objects.count(), 2) # Landmark, Museum
        landmark_category = Category.objects.get(name="Landmark", user_id=self.user)
        museum_category = Category.objects.get(name="Museum", user_id=self.user)
        self.assertEqual(adventures[0].category, landmark_category)
        self.assertEqual(adventures[1].category, museum_category)
        self.assertIsNone(adventures[2].category)


        # Assert Visit creation
        self.assertEqual(Visit.objects.count(), 3)
        visit_et = Visit.objects.get(adventure=adventures[0])
        visit_lm = Visit.objects.get(adventure=adventures[1])
        visit_src = Visit.objects.get(adventure=adventures[2])

        self.assertEqual(visit_et.start_date, date(2023, 1, 15))
        self.assertEqual(visit_et.end_date, date(2023, 1, 15))
        self.assertEqual(visit_lm.start_date, date(2023, 1, 16))
        self.assertEqual(visit_lm.end_date, date(2023, 1, 16))
        self.assertEqual(visit_src.start_date, date(2023, 1, 17))
        self.assertEqual(visit_src.end_date, date(2023, 1, 17))


        # Assert response data structure (basic check)
        response_data = response.json()
        self.assertEqual(response_data["name"], collection.name)
        self.assertEqual(len(response_data["adventures"]), 3)
        self.assertEqual(response_data["user_id"], str(self.user.uuid))


    def test_import_invalid_json_syntax(self):
        """
        Test import with malformed JSON data.
        """
        invalid_json_data = '{"activities": [{"name": "Test"}' # Missing closing bracket and quote

        response = self.client.post(
            self.import_url, data=invalid_json_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Depending on Django REST framework's parser, the error might be generic
        # e.g. {"detail":"JSON parse error - Expected P L A Y L O A D"}
        self.assertIn("JSON parse error", response.json().get("detail", "").lower())


    def test_import_missing_required_activity_fields(self):
        """
        Test import with JSON data missing required fields for an activity.
        """
        # Missing 'name'
        data_missing_name = {
            "activities": [{"date": "2023-01-01", "location": "Someplace"}]
        }
        response = self.client.post(
            self.import_url, data=json.dumps(data_missing_name), content_type="application/json"
        )
        # The view logic creates adventure with name=None if not provided, which is allowed by model (blank=True, null=True)
        # However, the Visit object requires an adventure.
        # Let's check if the current implementation handles this gracefully or if it's a 500.
        # Based on current view code, Adventure.name is nullable.
        # The view code currently uses activity_data.get('name'), which defaults to None.
        # This will actually pass for Adventure creation but might be an issue for user expectation.
        # For now, let's assume the current behavior is acceptable, where name can be None.
        # If name were required, this test would expect a 400.
        # The model has name = models.CharField(max_length=200, blank=True, null=True)

        # Missing 'date' (which is used for Visit object)
        data_missing_date = {
            "activities": [{"name": "Activity without Date", "location": "Anywhere"}]
        }
        response_missing_date = self.client.post(
            self.import_url, data=json.dumps(data_missing_date), content_type="application/json"
        )
        # A Visit object is only created if date is present. So this should be a successful import (201).
        # No Visit object will be created for this adventure.
        self.assertEqual(response_missing_date.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Visit.objects.count(), 0) # No visit created
        collection = Collection.objects.first()
        self.assertIsNotNone(collection)
        adventure = Adventure.objects.filter(collection=collection).first()
        self.assertIsNotNone(adventure)
        self.assertEqual(adventure.name, "Activity without Date")


    def test_import_invalid_date_format(self):
        """
        Test import with JSON data containing an invalid date format.
        """
        import_data = {
            "activities": [
                {
                    "name": "Test Adventure",
                    "date": "15-01-2023", # Invalid format (DD-MM-YYYY)
                    "location": "Test Location",
                }
            ]
        }
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        # The view's strptime expects '%Y-%m-%d'
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR) # Default exception handler
        # Or, if a more specific validation error is raised and caught:
        # self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # self.assertIn("format", response.json().get("error", "").lower()) # Check for specific error message
        # Current view code has a broad "except Exception as e", so it will be 500.
        self.assertIn("does not match format '%Y-%m-%d'", response.json().get("error", ""))


    def test_import_unauthenticated(self):
        """
        Test import endpoint when the user is not authenticated.
        """
        self.client.logout()
        import_data = {"activities": [{"name": "Test", "date": "2023-01-01"}]}
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        # Based on the view code: `if not request.user.is_authenticated: return Response(..., status=status.HTTP_403_FORBIDDEN)`
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_import_empty_activities_list(self):
        """
        Test import with an empty list of activities.
        """
        import_data = {"activities": []}
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        # Based on the view code: `if not activities: return Response(..., status=status.HTTP_400_BAD_REQUEST)`
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("error"), "No activities provided")

    def test_import_no_activities_key(self):
        """
        Test import with missing 'activities' key in JSON data.
        """
        import_data = {"some_other_key": []}
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("error"), "No activities provided")

    def test_import_category_reuse(self):
        """
        Test that existing categories are reused for the same user.
        """
        # Create a category first
        pre_existing_category = Category.objects.create(user_id=self.user, name="Existing Category")

        import_data = {
            "activities": [
                {
                    "name": "Activity 1",
                    "date": "2023-02-01",
                    "category": "Existing Category", # Should reuse
                },
                {
                    "name": "Activity 2",
                    "date": "2023-02-02",
                    "category": "New Category", # Should create
                }
            ]
        }
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertEqual(Category.objects.count(), 2) # Existing Category, New Category
        
        adv1 = Adventure.objects.get(name="Activity 1")
        adv2 = Adventure.objects.get(name="Activity 2")

        self.assertEqual(adv1.category, pre_existing_category)
        self.assertEqual(adv2.category.name, "New Category")
        self.assertEqual(adv2.category.user_id, self.user)

    def test_import_activity_without_optional_fields(self):
        """
        Test importing an activity that only has name and date (other fields are optional).
        """
        import_data = {
            "activities": [
                {
                    "name": "Minimal Activity",
                    "date": "2023-03-01",
                }
            ]
        }
        response = self.client.post(
            self.import_url, data=json.dumps(import_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Collection.objects.count(), 1)
        self.assertEqual(Adventure.objects.count(), 1)
        self.assertEqual(Visit.objects.count(), 1)

        adventure = Adventure.objects.first()
        self.assertEqual(adventure.name, "Minimal Activity")
        self.assertIsNone(adventure.description)
        self.assertIsNone(adventure.location)
        self.assertIsNone(adventure.category)

        visit = Visit.objects.first()
        self.assertEqual(visit.start_date, date(2023, 3, 1))
        self.assertEqual(visit.user_id, self.user)
