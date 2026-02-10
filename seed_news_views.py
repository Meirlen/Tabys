"""
Seed script to set random view_count (90-150) for all news articles.
Run inside Docker: docker-compose exec api python seed_news_views.py
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.news_models import News


def seed_news_views(db):
    """Set view_count to a random value between 90-150 for each news article."""
    news_list = db.query(News).all()

    if not news_list:
        print("No news articles found in database.")
        return

    print(f"Updating view_count for {len(news_list)} news articles...")

    for article in news_list:
        views = random.randint(90, 150)
        article.view_count = views
        print(f"  [ID {article.id}] {article.title_kz or article.title_ru or article.title or 'Untitled'} -> {views} views")

    db.commit()
    print(f"\nDone! Updated {len(news_list)} articles with random views (90-150).")


def main():
    print("=" * 60)
    print("SARYARQA JASTARY - News View Count Seed Script")
    print("=" * 60)

    db = SessionLocal()
    try:
        seed_news_views(db)
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
