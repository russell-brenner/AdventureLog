# How to use AdventureLog

Welcome to AdventureLog! This guide will help you get started with AdventureLog and provide you with an overview of the features available to you.

## Key Terms

#### Adventures

- **Adventure**: think of an adventure as a point on a map, a location you want to visit, or a place you want to explore. An adventure can be anything you want it to be, from a local park to a famous landmark.
- **Visit**: a visit is added to an adventure. It contains a date and notes about when the adventure was visited. If an adventure is visited multiple times, multiple visits can be added. If there are no visits on an adventure or the date of all visits is in the future, the adventure is considered planned. If the date of the visit is in the past, the adventure is considered completed.
- **Category**: a category is a way to group adventures together. For example, you could have a category for parks, a category for museums, and a category for restaurants.
- **Tag**: a tag is a way to add additional information to an adventure. For example, you could have a tag for the type of cuisine at a restaurant or the type of art at a museum. Multiple tags can be added to an adventure.
- **Image**: an image is a photo that is added to an adventure. Images can be added to an adventure to provide a visual representation of the location or to capture a memory of the visit. These can be uploaded from your device or with a service like [Immich](/docs/configuration/immich_integration) if the integration is enabled.
- **Attachment**: an attachment is a file that is added to an adventure. Attachments can be added to an adventure to provide additional information, such as a map of the location or a brochure from the visit.

#### Collections

- **Collection**: a collection is a way to group adventures together. Collections are flexible and can be used in many ways. When no start or end date is added to a collection, it acts like a folder to group adventures together. When a start and end date is added to a collection, it acts like a trip to group adventures together that were visited during that time period. With start and end dates, the collection is transformed into a full itinerary with a map showing the route taken between adventures.
- **Transportation**: a transportation is a collection exclusive feature that allows you to add transportation information to your trip. This can be used to show the route taken between locations and the mode of transportation used. It can also be used to track flight information, such as flight number and departure time.
- **Lodging**: a lodging is a collection exclusive feature that allows you to add lodging information to your trip. This can be used to plan where you will stay during your trip and add notes about the lodging location. It can also be used to track reservation information, such as reservation number and check-in time.
- **Note**: a note is a collection exclusive feature that allows you to add notes to your trip. This can be used to add additional information about your trip, such as a summary of the trip or a list of things to do. Notes can be assigned to a specific day of the trip to help organize the information.
- **Checklist**: a checklist is a collection exclusive feature that allows you to add a checklist to your trip. This can be used to create a list of things to do during your trip or for planning purposes like packing lists. Checklists can be assigned to a specific day of the trip to help organize the information.

#### World Travel

- **World Travel**: the world travel feature of AdventureLog allows you to track the countries, regions, and cities you have visited during your lifetime. You can add visits to countries, regions, and cities, and view statistics about your travels. The world travel feature is a fun way to visualize where you have been and where you want to go next.
  - **Country**: a country is a geographical area that is recognized as an independent nation. You can add visits to countries to track where you have been.
  - **Region**: a region is a geographical area that is part of a country. You can add visits to regions to track where you have been within a country.
  - **City**: a city is a geographical area that is a populated urban center. You can add visits to cities to track where you have been within a region.

## Tutorial Video

<iframe width="560" height="315" src="https://www.youtube.com/embed/4Y2LvxG3xn4" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

## Importing Collections

AdventureLog allows you to quickly create a new collection and populate it with activities by importing data from a structured file. This is useful for migrating data from other services or for bulk-adding activities.

### Accessing the Import Feature

1.  Navigate to the "Collections" page from the main menu.
2.  Click the circular "+" (plus) button, usually located at the bottom right of the page.
3.  From the dropdown menu that appears, select "Import Collection".
4.  An "Import Collection" modal dialog will appear.

This modal allows you to either upload a JSON or CSV file, or directly paste JSON data into a textarea.

### Using JSON

When importing via JSON, the data should be an array of activity objects. Each object represents an activity and can have the following fields:

*   `date` (string, **required**): The date of the activity in `YYYY-MM-DD` format.
*   `name` (string, **required**): The name or title of the activity.
*   `location` (string, optional): The geographical location of the activity (e.g., "Paris, France", "123 Main St, Anytown").
*   `description` (string, optional): A more detailed description of the activity.
*   `category` (string, optional): The name of the category for this activity (e.g., "Dining", "Hiking", "Museum"). If a category with this name (case-insensitive) doesn't already exist for you, it will be created automatically.

**Example JSON Data:**

```json
[
  {
    "date": "2024-03-15",
    "name": "Dinner at The Italian Place",
    "location": "123 Main St, Anytown",
    "description": "Reservation at 7 PM.",
    "category": "Dining"
  },
  {
    "date": "2024-03-16",
    "name": "Hike to Summit Peak",
    "category": "Hiking"
  },
  {
    "date": "2024-03-17",
    "name": "Visit Art Gallery",
    "location": "Downtown Art Center",
    "description": "Special exhibition on impressionism."
  }
]
```

You can paste this JSON data directly into the textarea in the import modal or save it as a `.json` file and upload it.

### Using CSV

You can also import activities by uploading a CSV (Comma Separated Values) file. The first row of the CSV file **must** be a header row defining the columns.

**Headers (case-insensitive):**

*   `date` (**required**): The date of the activity in `YYYY-MM-DD` format.
*   `name` (**required**): The name or title of the activity.
*   `location` (optional): The geographical location.
*   `description` (optional): A more detailed description.
*   `category` (optional): The name of the category. If a category with this name (case-insensitive) doesn't already exist for you, it will be created.

**Example CSV Data:**

```csv
date,name,location,description,category
2024-03-15,Dinner at The Italian Place,"123 Main St, Anytown","Reservation at 7 PM.",Dining
2024-03-16,Hike to Summit Peak,,,Hiking
2024-03-17,Museum Visit,"City Art Museum",,Culture
2024-03-18,Morning Coffee,Local Cafe,Quick stop before work,Food
```

**CSV Import Notes:**

*   **Missing Optional Data:** If optional fields (like `location`, `description`, `category`) are left empty in a row (e.g., `,,,` in the "Hike to Summit Peak" example), they will simply be skipped for that activity, and no error will occur.
*   **Skipped Rows:** If a row in the CSV is missing data for required fields (`date` or `name`), that specific row will be skipped during the import process, and the system will attempt to import the remaining valid rows.
*   **File Encoding:** Ensure your CSV file is UTF-8 encoded.

### Import Process and Error Handling

*   Upon successful import, a new collection will be created. The collection will be named automatically (e.g., "Imported Collection - YYYY-MM-DD HH:MM:SS").
*   All successfully processed activities from your JSON or CSV data will be added to this new collection.
*   If there are issues with the file format (e.g., invalid JSON, malformed CSV), or if data within the file is incorrect (e.g., an invalid date format for an activity), the system will display an error message. For CSV files with row-specific errors (like an invalid date format in one row), the entire import for that file may be halted if the error prevents further processing (e.g., a critical date parsing error).
