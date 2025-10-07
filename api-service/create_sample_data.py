#!/usr/bin/env python3
"""
Script to create sample data in Firestore for testing the knowledge tree

Implements Constitution-compliant strategy (QD-LAW §2):
"Việc phân tách dữ liệu giữa các môi trường BẮT BUỘC phải được thực hiện
bằng cách sử dụng các collection riêng biệt"

Creates data in both test_documents and production_documents collections.
"""

from google.cloud import firestore


def populate_collection(db, collection_name, sample_data):
    """
    Populate a specific collection with sample data.

    Args:
        db: Firestore client
        collection_name: Name of the collection to populate
        sample_data: List of (doc_id, doc_data) tuples
    """
    print(f"\nPopulating {collection_name}...")

    # Clean up existing documents for idempotency
    print(f"  Cleaning up existing documents in {collection_name}...")
    for doc in db.collection(collection_name).stream():
        doc.reference.delete()

    # Create documents
    for doc_id, doc_data in sample_data:
        doc_ref = db.collection(collection_name).document(doc_id)
        doc_ref.set(doc_data)
        print(f"  ✓ Created: {doc_id}")

    print(f"  ✓ {collection_name} populated successfully")


def create_sample_data():
    """
    Create sample data in both test and production collections.
    """
    db = firestore.Client()

    # Define sample data structure (shared across environments)
    test_data = [
        (
            "incomex_corp_project_test",
            {"title": "Dự án Incomex Corp (Test)", "parent": None, "order": 1},
        ),
        (
            "planning_docs_test",
            {
                "title": "Tài liệu Kế hoạch (Test)",
                "parent": "incomex_corp_project_test",
                "order": 2,
            },
        ),
        (
            "app_service_plan_test",
            {
                "title": "APP Service Plan v6.0.docx (Test)",
                "parent": "planning_docs_test",
                "order": 1,
            },
        ),
    ]

    production_data = [
        (
            "incomex_corp_project_prod",
            {"title": "Dự án Incomex Corp (Production)", "parent": None, "order": 1},
        ),
        (
            "planning_docs_prod",
            {
                "title": "Tài liệu Kế hoạch (Production)",
                "parent": "incomex_corp_project_prod",
                "order": 2,
            },
        ),
        (
            "app_service_plan_prod",
            {
                "title": "APP Service Plan v6.0.docx (Production)",
                "parent": "planning_docs_prod",
                "order": 1,
            },
        ),
        (
            "sales_enablement_prod",
            {
                "title": "Sales Enablement (Production)",
                "parent": "incomex_corp_project_prod",
                "order": 3,
                "status": "yellow",
            },
        ),
    ]

    print("=" * 60)
    print("Creating sample data following Constitution QD-LAW §2")
    print("Using separate collections per environment")
    print("=" * 60)

    # Populate test collection
    populate_collection(db, "test_documents", test_data)

    # Populate production collection
    populate_collection(db, "production_documents", production_data)

    print("\n" + "=" * 60)
    print("✓ All sample data created successfully!")
    print(f"  - test_documents: {len(test_data)} documents")
    print(f"  - production_documents: {len(production_data)} documents")
    print("=" * 60)


if __name__ == "__main__":
    create_sample_data()
