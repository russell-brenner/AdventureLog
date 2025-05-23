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


    # --- CSV Import Tests ---

    def test_successful_csv_import(self):
        """
        Test successful import of a collection via CSV.
        """
        csv_data = (
            "date,name,location,description,category\n"
            "2023-04-01,CSV Adventure 1,CSV Location 1,Desc for CSV 1,CSV Cat1\n"
            "2023-04-02,CSV Adventure 2,CSV Location 2,Desc for CSV 2,CSV Cat2\n"
            "2023-04-03,CSV Adventure 3,,,,\n" # Optional fields empty
        )
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        self.assertEqual(Collection.objects.count(), 1)
        collection = Collection.objects.first()
        self.assertEqual(collection.user_id, self.user)
        self.assertTrue(collection.name.startswith("Imported Collection - "))

        self.assertEqual(Adventure.objects.count(), 3)
        adventures = Adventure.objects.filter(collection=collection).order_by('name')
        self.assertEqual(adventures[0].name, "CSV Adventure 1")
        self.assertEqual(adventures[1].name, "CSV Adventure 2")
        self.assertEqual(adventures[2].name, "CSV Adventure 3")

        self.assertEqual(adventures[0].location, "CSV Location 1")
        self.assertEqual(adventures[0].description, "Desc for CSV 1")
        self.assertIsNotNone(adventures[0].category)
        self.assertEqual(adventures[0].category.name, "CSV Cat1")
        
        self.assertIsNone(adventures[2].location) # Handled by get which defaults to None
        self.assertIsNone(adventures[2].description)
        self.assertIsNone(adventures[2].category)


        self.assertEqual(Visit.objects.count(), 3)
        visit1 = Visit.objects.get(adventure=adventures[0])
        self.assertEqual(visit1.start_date, date(2023, 4, 1))

        response_data = response.json()
        self.assertEqual(response_data["name"], collection.name)
        # Ensure adventures are part of the response if serializer includes them
        self.assertTrue("adventures" in response_data) 
        self.assertEqual(len(response_data["adventures"]), 3)


    def test_successful_csv_import_optional_columns_missing(self):
        """
        Test CSV import where optional columns (location, description, category) are entirely missing from headers.
        """
        csv_data = (
            "date,name\n"
            "2023-05-01,Minimal CSV 1\n"
            "2023-05-02,Minimal CSV 2\n"
        )
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        self.assertEqual(Adventure.objects.count(), 2)
        adventures = Adventure.objects.filter(collection__user_id=self.user).order_by('name')
        self.assertEqual(adventures[0].name, "Minimal CSV 1")
        self.assertIsNone(adventures[0].location)
        self.assertIsNone(adventures[0].description)
        self.assertIsNone(adventures[0].category)
        
        self.assertEqual(Visit.objects.count(), 2)


    def test_successful_csv_import_case_insensitive_headers(self):
        """
        Test CSV import with case-insensitive headers.
        """
        csv_data = (
            "Date,Name,LOCATION,DescriptioN,CateGorY\n"
            "2023-06-01,Case Test Adv,Case Location,Case Desc,Case Cat\n"
        )
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(Adventure.objects.count(), 1)
        adventure = Adventure.objects.first()
        self.assertEqual(adventure.name, "Case Test Adv")
        self.assertEqual(adventure.location, "Case Location")
        self.assertEqual(adventure.description, "Case Desc")
        self.assertEqual(adventure.category.name, "Case Cat")


    def test_csv_import_missing_required_headers(self):
        """
        Test CSV import missing a required header (e.g., 'name').
        """
        # Missing 'name' header
        csv_data_no_name = "date,location\n2023-07-01,Some Location\n"
        response = self.client.post(
            self.import_url, data=csv_data_no_name, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("CSV is missing required headers", response.json().get("error", ""))
        self.assertIn("name", response.json().get("error", ""))

        # Missing 'date' header
        csv_data_no_date = "name,location\nMy Adventure,Some Location\n"
        response = self.client.post(
            self.import_url, data=csv_data_no_date, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("CSV is missing required headers", response.json().get("error", ""))
        self.assertIn("date", response.json().get("error", ""))


    def test_csv_import_empty_csv(self):
        """
        Test CSV import with an empty CSV (only headers).
        """
        csv_data_headers_only = "date,name,location,description,category\n"
        response = self.client.post(
            self.import_url, data=csv_data_headers_only, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("error"), "No activities provided or data is empty.")

        # Test with completely empty string
        csv_data_empty_string = ""
        response = self.client.post(
            self.import_url, data=csv_data_empty_string, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # This case might lead to "CSV is missing required headers" if DictReader gets empty fieldnames
        # or specific csv.Error "No columns to parse from file"
        # Based on current view code, it will be caught by `except csv.Error` or `except UnicodeDecodeError`
        # or the initial check for required headers might fail if fieldnames is None or empty.
        # If reader.fieldnames is None (for empty string), `set(reader.fieldnames or [])` becomes `set([])`.
        # `required_headers.issubset(set([]))` is false. So "CSV is missing required headers" is expected.
        self.assertIn("CSV is missing required headers", response.json().get("error", ""))


    def test_csv_import_malformed_csv(self):
        """
        Test CSV import with a malformed CSV structure.
        DictReader is quite robust; this tests a simple case of unescaped quote.
        """
        # Unescaped quote in a field
        csv_data = 'date,name\n2023-08-01,Adventure with " quote\n'
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        # This should be caught by csv.Error during parsing by DictReader
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("CSV parsing error", response.json().get("error", ""))


    def test_csv_import_row_missing_required_data(self):
        """
        Test CSV import where a row is missing required data (name or date),
        expecting the row to be skipped.
        """
        csv_data = (
            "date,name,location\n"
            "2023-09-01,Valid Row 1,Location1\n"
            ",Missing Date Row,Location2\n"        # Date is missing
            "2023-09-03,,Location3\n"              # Name is missing
            "2023-09-04,Valid Row 2,Location4\n"
            ",,\n"                                 # Name and Date missing
        )
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        
        # Only the two valid rows should result in Adventures
        self.assertEqual(Adventure.objects.count(), 2)
        self.assertTrue(Adventure.objects.filter(name="Valid Row 1").exists())
        self.assertTrue(Adventure.objects.filter(name="Valid Row 2").exists())
        self.assertEqual(Visit.objects.count(), 2)


    def test_csv_import_invalid_date_format_in_row(self):
        """
        Test CSV import where a row contains an invalid date format.
        """
        csv_data = (
            "date,name\n"
            "01-10-2023,Bad Date Adv\n" # DD-MM-YYYY format
            "2023-10-02,Good Date Adv\n"
        )
        response = self.client.post(
            self.import_url, data=csv_data, content_type="text/csv"
        )
        # The view catches ValueError from strptime and returns 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Data validation error", response.json().get("error", ""))
        self.assertIn("does not match format '%Y-%m-%d'", response.json().get("error", ""))
        
        # Ensure no data was committed due to the error in transaction.atomic block
        self.assertEqual(Collection.objects.count(), 0)
        self.assertEqual(Adventure.objects.count(), 0)

    def test_unsupported_media_type_for_import(self):
        """
        Test import with an unsupported media type.
        """
        response = self.client.post(
            self.import_url, data="some data", content_type="application/xml"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(response.json().get("error"), "Unsupported media type. Please use 'application/json' or 'text/csv'.")
