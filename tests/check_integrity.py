import sys
import os
import traceback
from unittest.mock import MagicMock, patch

# Add project root to path (one level up from tests directory)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

print("--- Starting Integrity Check ---")

def mock_db_if_needed():
    try:
        import src.database
        print("Database connection attempt...")
        # Access db to trigger connection
        src.database.db.get_connection()
        print("Database connected successfully.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Mocking database for structural verification...")
        
        # Create a mock for the database module
        mock_db_module = MagicMock()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Setup context manager for get_connection
        mock_db.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_db_module.db = mock_db
        
        # Inject into sys.modules
        sys.modules['src.database'] = mock_db_module
        
        # Also need to patch psycopg2 because some modules might import it directly
        sys.modules['psycopg2'] = MagicMock()
        sys.modules['psycopg2.extras'] = MagicMock()

try:
    mock_db_if_needed()

    print("Importing modules...")
    
    import src.logger
    print("✓ Logger module imported")
    
    import src.extractor
    print("✓ Extractor module imported")
    
    import src.classifier
    print("✓ Classifier module imported")
    
    import src.proveedor_matcher
    print("✓ ProveedorMatcher module imported")
    
    import src.learning
    print("✓ Learning module imported")
    
    import src.api
    print("✓ API module imported")

    print("\nVerifying Class Instantiation...")
    
    from src.extractor import InvoiceExtractor
    extractor = InvoiceExtractor()
    print("✓ InvoiceExtractor instantiated")
    
    from src.classifier import PDFClassifier
    classifier = PDFClassifier()
    print("✓ PDFClassifier instantiated")
    
    from src.proveedor_matcher import ProveedorMatcher
    matcher = ProveedorMatcher()
    print("✓ ProveedorMatcher instantiated")

    print("\n--- Integrity Check PASSED ---")

except Exception as e:
    print(f"\n--- Integrity Check FAILED ---")
    traceback.print_exc()
