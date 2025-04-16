import os
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    """Class for handling local storage of complaint data and response status."""
    
    def __init__(self, db_path="reclameaqui_data.db"):
        """
        Initialize the database connection and create tables if they don't exist.
        
        Args:
            db_path (str, optional): Path to the SQLite database file
        """
        self.db_path = db_path
        self._create_tables()
        logger.info(f"Database initialized at {db_path}")
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create complaints table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS complaints (
                    complaint_id TEXT PRIMARY KEY,
                    customer_name TEXT,
                    complaint_text TEXT,
                    response_text TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database tables created or already exist")
            
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def is_complaint_processed(self, complaint_id):
        """
        Check if a complaint has already been processed.
        
        Args:
            complaint_id (str): ID of the complaint to check
            
        Returns:
            bool: True if the complaint has been processed, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM complaints WHERE complaint_id = ?",
                (complaint_id,)
            )
            
            result = cursor.fetchone() is not None
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking if complaint is processed: {str(e)}")
            return False
    
    def save_complaint(self, complaint_id, customer_name, complaint_text, response_text, status):
        """
        Save complaint details and response status to the database.
        
        Args:
            complaint_id (str): ID of the complaint
            customer_name (str): Name of the customer
            complaint_text (str): Text of the complaint
            response_text (str): Generated response text
            status (str): Status of the response ('completed' or 'failed')
            
        Returns:
            bool: True if the save was successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO complaints (
                    complaint_id, customer_name, complaint_text, 
                    response_text, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    complaint_id, customer_name, complaint_text,
                    response_text, status, now, now
                )
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Complaint ID {complaint_id} saved to database with status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving complaint to database: {str(e)}")
            return False
    
    def update_complaint_status(self, complaint_id, status):
        """
        Update the status of a complaint.
        
        Args:
            complaint_id (str): ID of the complaint to update
            status (str): New status value
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE complaints SET status = ?, updated_at = ? WHERE complaint_id = ?",
                (status, now, complaint_id)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated complaint ID {complaint_id} status to: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating complaint status: {str(e)}")
            return False
    
    def get_all_complaints(self, limit=100):
        """
        Retrieve all complaints from the database.
        
        Args:
            limit (int, optional): Maximum number of complaints to retrieve
            
        Returns:
            list: List of dictionaries containing complaint details
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM complaints 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (limit,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries
            complaints = [dict(row) for row in rows]
            
            logger.info(f"Retrieved {len(complaints)} complaints from database")
            return complaints
            
        except Exception as e:
            logger.error(f"Error retrieving complaints from database: {str(e)}")
            return []
    
    def get_statistics(self):
        """
        Get statistics about the complaints.
        
        Returns:
            dict: Statistics including total, completed, and failed complaints
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total complaints
            cursor.execute("SELECT COUNT(*) FROM complaints")
            total = cursor.fetchone()[0]
            
            # Get completed complaints
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'completed'")
            completed = cursor.fetchone()[0]
            
            # Get failed complaints
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'failed'")
            failed = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                "total": total,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / total * 100) if total > 0 else 0
            }
            
            logger.info(f"Retrieved statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving statistics from database: {str(e)}")
            return {"total": 0, "completed": 0, "failed": 0, "success_rate": 0}
    
    def export_to_json(self, file_path="complaints_export.json"):
        """
        Export all complaints to a JSON file.
        
        Args:
            file_path (str, optional): Path to save the JSON file
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            complaints = self.get_all_complaints(limit=1000)  # Get up to 1000 complaints
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(complaints, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Exported {len(complaints)} complaints to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting complaints to JSON: {str(e)}")
            return False
