#!/usr/bin/env python3
"""
Script to check data in Firestore collections for production_documents and test_documents.
This helps diagnose why the frontend cannot load data from production_documents.
"""

import os
from google.cloud import firestore
from google.oauth2 import service_account

def check_firestore_collections():
    """
    Check and report the number of documents in test_documents and production_documents collections.
    """
    print("=" * 80)
    print("FIRESTORE DATA DIAGNOSTIC REPORT")
    print("=" * 80)

    try:
        # Initialize Firestore client with explicit project
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "github-chatgpt-ggcloud")
        print(f"Using project: {project_id}")

        db = firestore.Client(project=project_id)

        # Collections to check
        collections = ['test_documents', 'production_documents']

        for collection_name in collections:
            print(f"\n🔍 Checking collection: {collection_name}")
            print("-" * 50)

            try:
                # Get all documents in the collection
                docs = list(db.collection(collection_name).stream())

                doc_count = len(docs)
                print(f"📊 Total documents: {doc_count}")

                if doc_count > 0:
                    print("📋 Document details:")
                    for i, doc in enumerate(docs, 1):
                        doc_data = doc.to_dict()
                        title = doc_data.get('title', 'No title')
                        parent = doc_data.get('parent', 'No parent')
                        order = doc_data.get('order', 'No order')
                        status = doc_data.get('status', 'No status')

                        print(f"  {i}. ID: {doc.id}")
                        print(f"     Title: {title}")
                        print(f"     Parent: {parent}")
                        print(f"     Order: {order}")
                        print(f"     Status: {status}")
                        print()

                    print("✅ Collection has data and should be readable by frontend")

                else:
                    print("❌ Collection is EMPTY - This explains why frontend cannot load data!")
                    print("   ℹ️  Frontend will show 'Không thể tải sơ đồ tri thức' error")

            except Exception as e:
                print(f"❌ Error accessing collection {collection_name}: {str(e)}")

        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)

        # Check both collections and provide summary
        test_count = len(list(db.collection('test_documents').stream()))
        prod_count = len(list(db.collection('production_documents').stream()))

        print(f"test_documents: {test_count} documents")
        print(f"production_documents: {prod_count} documents")

        if prod_count == 0:
            print("\n🎯 ROOT CAUSE IDENTIFIED:")
            print("   production_documents collection is EMPTY!")
            print("   This is why the frontend shows 'Không thể tải dữ liệu từ production_documents'")
            print("\n💡 SOLUTION:")
            print("   Run the create_sample_data.py script to populate production_documents")

        elif test_count == 0:
            print("\n⚠️  WARNING:")
            print("   test_documents collection is also EMPTY!")
            print("   Both collections need to be populated")

        else:
            print("\n✅ Both collections have data - issue may be elsewhere")
            print("   Check frontend environment selector and Firebase config")

    except Exception as e:
        print(f"❌ Failed to connect to Firestore: {str(e)}")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Check GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("   2. Verify GCP project ID and permissions")
        print("   3. Ensure Firestore is enabled in the project")

if __name__ == "__main__":
    check_firestore_collections()
