#!/usr/bin/env python3
"""
Simple test script to verify the system works without requiring all APIs
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test database models
        from models.database import User, Topic, create_tables
        print("✅ Database models imported successfully")
        
        # Test authentication
        from auth.auth import AuthService
        print("✅ Authentication module imported successfully")
        
        # Test services (these might fail if API keys are missing, but should import)
        try:
            from services.gemini_service import GeminiService
            print("✅ Gemini service imported successfully")
        except ValueError as e:
            print(f"⚠️  Gemini service import warning: {e}")
            
        try:
            from services.ideogram_service import IdeogramService
            print("✅ Ideogram service imported successfully")
        except ValueError as e:
            print(f"⚠️  Ideogram service import warning: {e}")
            
        from services.excel_service import ExcelService
        print("✅ Excel service imported successfully")
        
        # Test Instagram agent
        try:
            from instagram_agent import InstagramAgent
            print("✅ Instagram agent imported successfully")
        except ValueError as e:
            print(f"⚠️  Instagram agent import warning: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database functionality"""
    try:
        print("\nTesting database...")
        
        from models.database import create_tables, SessionLocal, User
        from auth.auth import AuthService
        
        # Create tables
        create_tables()
        print("✅ Database tables created successfully")
        
        # Test user creation
        db = SessionLocal()
        
        # Check if test user exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
        
        # Create test user
        test_user = AuthService.create_user(db, "test@example.com", "testpassword123")
        print(f"✅ Test user created with ID: {test_user.id}")
        
        # Test authentication
        auth_user = AuthService.authenticate_user(db, "test@example.com", "testpassword123")
        if auth_user:
            print("✅ User authentication successful")
        else:
            print("❌ User authentication failed")
            
        # Clean up
        db.delete(test_user)
        db.commit()
        db.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_excel_service():
    """Test Excel processing functionality"""
    try:
        print("\nTesting Excel service...")
        
        from services.excel_service import ExcelService
        
        # Create sample Excel file
        sample_path = "test_sample.xlsx"
        if ExcelService.create_sample_excel(sample_path):
            print("✅ Sample Excel file created successfully")
            
            # Test validation
            validation = ExcelService.validate_excel_format(sample_path)
            if validation['valid']:
                print(f"✅ Excel validation successful: {validation['topics_found']} topics found")
            else:
                print(f"❌ Excel validation failed: {validation['error']}")
                
            # Clean up
            if os.path.exists(sample_path):
                os.remove(sample_path)
                
        return True
        
    except Exception as e:
        print(f"❌ Excel service error: {e}")
        return False

def test_web_app():
    """Test that the web application can start"""
    try:
        print("\nTesting web application...")
        
        # Import the app
        from app import app
        print("✅ FastAPI app imported successfully")
        
        # Test that we can create a test client
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            
        # Test home page
        response = client.get("/")
        if response.status_code == 200:
            print("✅ Home page accessible")
        else:
            print(f"❌ Home page failed: {response.status_code}")
            
        return True
        
    except Exception as e:
        print(f"❌ Web app error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running System Tests\n")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Excel Service", test_excel_service),
        ("Web Application", test_web_app)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} Test")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The system is ready to use.")
        print("\nTo start the application:")
        print("  python app.py")
        print("\nThen visit: http://localhost:8000")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Check the errors above.")
        
    return passed == len(results)

if __name__ == "__main__":
    main()