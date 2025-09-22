import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from sqlalchemy.orm import Session
from models.database import Topic, Schedule, User

class ExcelService:
    @staticmethod
    def parse_excel_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse Excel file and extract topic data
        Expected columns: date, topic_title, textual_description, target_accounts, image_constraints
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Expected columns (case-insensitive matching)
            expected_columns = {
                'date': ['date', 'scheduled_date', 'posting_date'],
                'topic_title': ['topic_title', 'title', 'topic', 'subject'],
                'textual_description': ['textual_description', 'description', 'content', 'text'],
                'target_accounts': ['target_accounts', 'accounts', 'targets', 'audience'],
                'image_constraints': ['image_constraints', 'constraints', 'image_notes', 'notes']
            }
            
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Map columns
            column_mapping = {}
            for standard_col, possible_names in expected_columns.items():
                for col in df.columns:
                    if col in possible_names:
                        column_mapping[col] = standard_col
                        break
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Validate required columns
            required_columns = ['topic_title', 'textual_description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Process data
            topics = []
            for index, row in df.iterrows():
                try:
                    # Parse date
                    scheduled_date = None
                    if 'date' in df.columns and pd.notna(row.get('date')):
                        date_value = row['date']
                        if isinstance(date_value, str):
                            # Try to parse string date
                            try:
                                scheduled_date = pd.to_datetime(date_value)
                            except:
                                # If parsing fails, schedule for tomorrow
                                scheduled_date = datetime.now() + timedelta(days=1)
                        elif isinstance(date_value, datetime):
                            scheduled_date = date_value
                        else:
                            scheduled_date = pd.to_datetime(date_value)
                    else:
                        # Default to tomorrow if no date provided
                        scheduled_date = datetime.now() + timedelta(days=1)
                    
                    topic_data = {
                        'topic_title': str(row['topic_title']).strip(),
                        'textual_description': str(row['textual_description']).strip(),
                        'target_accounts': str(row.get('target_accounts', '')).strip(),
                        'image_constraints': str(row.get('image_constraints', '')).strip(),
                        'scheduled_date': scheduled_date,
                        'row_number': index + 1
                    }
                    
                    # Validate topic data
                    if not topic_data['topic_title'] or topic_data['topic_title'] == 'nan':
                        continue  # Skip empty titles
                    
                    if not topic_data['textual_description'] or topic_data['textual_description'] == 'nan':
                        continue  # Skip empty descriptions
                    
                    topics.append(topic_data)
                    
                except Exception as e:
                    print(f"Error processing row {index + 1}: {e}")
                    continue
            
            return topics
            
        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    @staticmethod
    def create_topics_from_excel(
        db: Session, 
        user: User, 
        file_path: str, 
        schedule_name: str = None
    ) -> Dict[str, Any]:
        """
        Create topics in database from Excel file
        """
        try:
            # Parse Excel file
            topics_data = ExcelService.parse_excel_file(file_path)
            
            if not topics_data:
                return {
                    'success': False,
                    'error': 'No valid topics found in Excel file',
                    'topics_created': 0
                }
            
            # Create schedule if name provided
            schedule = None
            if schedule_name:
                schedule = Schedule(
                    user_id=user.id,
                    name=schedule_name,
                    status="active"
                )
                db.add(schedule)
                db.commit()
                db.refresh(schedule)
            
            # Create topics
            created_topics = []
            errors = []
            
            for topic_data in topics_data:
                try:
                    topic = Topic(
                        user_id=user.id,
                        schedule_id=schedule.id if schedule else None,
                        topic_title=topic_data['topic_title'],
                        textual_description=topic_data['textual_description'],
                        target_accounts=topic_data['target_accounts'],
                        image_constraints=topic_data['image_constraints'],
                        scheduled_date=topic_data['scheduled_date'],
                        status='pending'
                    )
                    
                    db.add(topic)
                    created_topics.append(topic)
                    
                except Exception as e:
                    errors.append(f"Row {topic_data['row_number']}: {str(e)}")
            
            # Commit all topics
            if created_topics:
                db.commit()
                
                # Refresh all topics to get IDs
                for topic in created_topics:
                    db.refresh(topic)
            
            return {
                'success': True,
                'topics_created': len(created_topics),
                'schedule_id': schedule.id if schedule else None,
                'schedule_name': schedule_name,
                'errors': errors,
                'topics': [
                    {
                        'id': topic.id,
                        'title': topic.topic_title,
                        'scheduled_date': topic.scheduled_date
                    } for topic in created_topics
                ]
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'error': str(e),
                'topics_created': 0
            }
    
    @staticmethod
    def validate_excel_format(file_path: str) -> Dict[str, Any]:
        """
        Validate Excel file format without creating topics
        """
        try:
            topics_data = ExcelService.parse_excel_file(file_path)
            
            return {
                'valid': True,
                'topics_found': len(topics_data),
                'sample_topics': topics_data[:3],  # First 3 topics as preview
                'columns_detected': list(topics_data[0].keys()) if topics_data else []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'topics_found': 0
            }
    
    @staticmethod
    def create_sample_excel(file_path: str) -> bool:
        """
        Create a sample Excel file with the expected format
        """
        try:
            sample_data = {
                'date': [
                    datetime.now() + timedelta(days=1),
                    datetime.now() + timedelta(days=2),
                    datetime.now() + timedelta(days=3)
                ],
                'topic_title': [
                    'Summer Sale Campaign',
                    'New Product Launch',
                    'Customer Testimonial Feature'
                ],
                'textual_description': [
                    'Promote our summer sale with bright, energetic visuals showcasing discounted products',
                    'Introduce our latest product with professional, modern imagery highlighting key features',
                    'Share authentic customer testimonials with warm, trustworthy visual design'
                ],
                'target_accounts': [
                    '@fashion_lovers, @style_enthusiasts',
                    '@tech_reviewers, @gadget_experts',
                    '@satisfied_customers, @brand_advocates'
                ],
                'image_constraints': [
                    'Use bright summer colors, show products clearly, include sale percentage',
                    'Clean background, product focus, professional lighting',
                    'Include customer photo, warm colors, testimonial quote visible'
                ]
            }
            
            df = pd.DataFrame(sample_data)
            df.to_excel(file_path, index=False)
            return True
            
        except Exception as e:
            print(f"Error creating sample Excel: {e}")
            return False