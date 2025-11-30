# News Categories Feature

## Overview
This migration adds a `category` field to the news model, allowing news articles to be categorized and filtered.

## Changes Made

### 1. Database Model (`app/news_models.py`)
- Added `category` column (VARCHAR(100), nullable, default=None)
- Field is optional to maintain backward compatibility

### 2. Pydantic Schemas (`app/news_schemas.py`)
- Added `category: Optional[str] = None` to `NewsBase`
- Added `category: Optional[str] = None` to `NewsUpdate`
- Added `category: Optional[str] = None` to `NewsResponse`

### 3. API Routes (`app/routers/news.py`)
- Updated `GET /api/v2/news/` to support optional `category` query parameter
- Added `GET /api/v2/news/categories` to retrieve all unique categories
- All existing routes remain fully functional

## API Usage

### Get All News (with optional category filter)
```bash
# Get all news
GET /api/v2/news/

# Get news by category
GET /api/v2/news/?category=Technology
```

### Get All Categories
```bash
GET /api/v2/news/categories
```

### Create News with Category
```json
POST /api/v2/admin/news/
{
  "title": "News Title",
  "description": "Description",
  "content_text": "Content",
  "category": "Technology"
}
```

### Update News Category
```json
PUT /api/v2/admin/news/{id}
{
  "category": "Sports"
}
```

## Migration Instructions

### For New Installations
The category column will be automatically created when running the application.

### For Existing Databases
Run the migration script:

```bash
# Connect to your PostgreSQL database
psql -U your_user -d your_database

# Run the migration
\i migrations/add_news_category.sql
```

Or using Docker:
```bash
docker exec -i postgres-container-name psql -U postgres -d database_name < migrations/add_news_category.sql
```

## Backward Compatibility

✅ **Frontend**: No changes required. The `category` field will be `null` for existing news and can be safely ignored.

✅ **CRM**: No changes required. The category field is optional in all create/update operations.

✅ **API**: All existing API calls continue to work without modification.

## Suggested Category Values

Here are some suggested category values (customize as needed):
- "Новости" / "News"
- "Технологии" / "Technology"
- "Спорт" / "Sports"
- "Культура" / "Culture"
- "Образование" / "Education"
- "События" / "Events"
- "Объявления" / "Announcements"

## Testing

1. **Test backward compatibility:**
   ```bash
   # Create news without category (should work)
   POST /api/v2/admin/news/ {"title": "Test", "description": "Test", "content_text": "Test"}

   # Verify it returns null for category
   GET /api/v2/news/
   ```

2. **Test with categories:**
   ```bash
   # Create news with category
   POST /api/v2/admin/news/ {"title": "Test", "description": "Test", "content_text": "Test", "category": "Tech"}

   # Filter by category
   GET /api/v2/news/?category=Tech

   # Get all categories
   GET /api/v2/news/categories
   ```

## Future Enhancements

Consider adding:
- Category management endpoints (CRUD for categories)
- Predefined category list/enum
- Category translations (kz/ru/en)
- Category icons/colors
- News count per category
