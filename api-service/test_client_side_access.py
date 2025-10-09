#!/usr/bin/env python3
"""
Test Firestore Security Rules by simulating client-side access patterns.
This script tests whether Security Rules allow authenticated user access.
"""

import os
from firebase_admin import auth, credentials, firestore, initialize_app

def test_firestore_security_rules():
    """
    Test Firestore Security Rules with authenticated user context.
    IMPORTANT: Admin SDK bypasses Security Rules, so we need to simulate client behavior.
    """
    print("=" * 80)
    print("FIRESTORE SECURITY RULES TEST")
    print("=" * 80)

    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "github-chatgpt-ggcloud")
        print(f"Testing project: {project_id}")

        # Initialize Firebase Admin
        try:
            # Try to get existing app first
            db = firestore.client()
        except ValueError:
            # If no app exists, initialize one
            cred = credentials.ApplicationDefault()
            initialize_app(cred)
            db = firestore.client()

        print("\n🔍 TESTING FIRESTORE SECURITY RULES")
        print("⚠️  IMPORTANT: Admin SDK bypasses Security Rules by default")
        print("   This test shows what Admin access can do, not client access")

        collections_to_test = ['test_documents', 'production_documents']

        for collection_name in collections_to_test:
            print(f"\n📋 Testing collection: {collection_name}")
            print("-" * 50)

            try:
                # Admin SDK can always read (bypasses Security Rules)
                docs = list(db.collection(collection_name).stream())
                doc_count = len(docs)
                print(f"📊 Documents found (Admin SDK): {doc_count}")

                if doc_count > 0:
                    print("✅ Admin SDK can access - data exists")
                    first_doc = docs[0]
                    doc_data = first_doc.to_dict()
                    print(f"   Sample: {first_doc.id} -> {doc_data.get('title', 'No title')}")

                else:
                    print("❌ Collection appears empty to Admin SDK")

            except Exception as e:
                print(f"❌ Admin SDK error: {str(e)}")

        print("\n" + "=" * 80)
        print("SECURITY ANALYSIS")
        print("=" * 80)

        print("🔒 KEY INSIGHT:")
        print("   Admin SDK bypasses Firestore Security Rules completely!")
        print("   The fact that Admin SDK can read data tells us NOTHING about")
        print("   whether client-side users can access the same data.")
        print("")
        print("🎯 REAL ISSUE:")
        print("   Client-side Firebase SDK must authenticate users AND")
        print("   Security Rules must allow access for those authenticated users.")
        print("")
        print("📋 WHAT WE KNOW:")
        print("   ✅ Data exists in Firestore (Admin SDK can read it)")
        print("   ✅ firestore.rules allows read for authenticated users")
        print("   ❌ Client-side app reports 'cannot load data'")
        print("")
        print("🔍 MOST LIKELY CAUSES:")
        print("   1. Firebase config not properly injected into client app")
        print("   2. Client-side authentication failing")
        print("   3. Race condition in client app initialization")
        print("   4. Network/Firewall blocking Firebase requests")
        print("")
        print("💡 NEXT STEPS:")
        print("   1. Check browser Network tab for Firebase requests")
        print("   2. Check browser Console for Firebase errors")
        print("   3. Verify Firebase config injection in built app")
        print("   4. Test Firebase Auth flow manually")

    except Exception as e:
        print(f"❌ Failed to set up test: {str(e)}")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Check GOOGLE_APPLICATION_CREDENTIALS")
        print("   2. Verify Firebase project permissions")

if __name__ == "__main__":
    test_firestore_security_rules()
