#!/usr/bin/env python3
"""
Script to create sample data in Firestore for testing the knowledge tree
"""

from google.cloud import firestore

def create_sample_data():
    db = firestore.Client()
    
    # Dọn dẹp collection cũ (nếu có) để đảm bảo idempotency
    print("Cleaning up existing documents...")
    for doc in db.collection(u'knowledge_documents').stream():
        doc.reference.delete()
    
    # Tạo node cha
    print("Creating parent node...")
    parent_ref = db.collection(u'knowledge_documents').document(u'incomex_corp_project')
    parent_ref.set({
        'title': 'Dự án Incomex Corp (từ Firestore)',
        'parent': None
    })
    
    # Tạo node con
    print("Creating child nodes...")
    child1_ref = db.collection(u'knowledge_documents').document(u'planning_docs')
    child1_ref.set({
        'title': 'Tài liệu Kế hoạch',
        'parent': 'incomex_corp_project'
    })
    
    child2_ref = db.collection(u'knowledge_documents').document(u'app_service_plan')
    child2_ref.set({
        'title': 'APP Service Plan v6.0.docx',
        'parent': 'planning_docs'
    })
    
    print("Sample data created successfully in Firestore.")

if __name__ == "__main__":
    create_sample_data()
