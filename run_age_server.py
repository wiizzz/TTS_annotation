#!/usr/bin/env python3
"""
HTTP server for audio annotation interface with server-side annotation storage.
Saves annotations securely without exposing results to annotators.
"""

import http.server
import socketserver
from socketserver import ThreadingMixIn
import webbrowser
import os
import json
import csv
import fcntl
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8000))

class ThreadedAgeServer(ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

class AnnotationHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        # Serve annotation files for accuracy calculation
        if parsed_path.path.startswith('/annotations/') or parsed_path.path.startswith('/answer/'):
            try:
                # Remove leading slash and construct file path
                file_path = Path(parsed_path.path[1:])  # Remove leading '/'
                
                if file_path.exists() and file_path.is_file():
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.end_headers()
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                    return
                else:
                    self.send_error(404, f"File not found: {file_path}")
                    return
                    
            except Exception as e:
                print(f"Error serving file: {e}")
                self.send_error(500, f"Server error: {e}")
                return
        
        # Default GET handler for regular files
        super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for saving annotations"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/save_annotation':
            self.handle_save_annotation()
        else:
            self.send_error(404, "Endpoint not found")
    
    def handle_save_annotation(self):
        """Save annotation to CSV file"""
        try:
            # Read request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            annotation = json.loads(post_data.decode('utf-8'))
            
            # Validate annotation data
            required_fields = ['user_id', 'audio_url', 'selected_age', 'timestamp', 'session_id']
            for field in required_fields:
                if field not in annotation:
                    raise ValueError(f"Missing required field: {field}")
            
            # Extract split number from the annotation data if available
            split_number = annotation.get('split', 1)
            
            # Save to CSV file
            self.save_annotation_to_csv(annotation, split_number)
            
            # Send success response
            response = {"status": "success", "message": "Annotation saved successfully"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
            print(f"✅ Saved annotation: {annotation['user_id']} - {annotation['selected_age']}")
            
        except Exception as e:
            print(f"❌ Error saving annotation: {e}")
            
            # Send error response
            response = {"status": "error", "message": str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def save_annotation_to_csv(self, annotation, split_number=1):
        """Save annotation to timestamped CSV file with file locking"""
        # Create annotations directory if it doesn't exist
        annotations_dir = Path('annotations')
        annotations_dir.mkdir(exist_ok=True)
        
        # Generate filename based on split number
        csv_file = annotations_dir / f'age_split{split_number}.csv'
        
        # Retry mechanism for file locking - increased for concurrent users
        max_retries = 50
        for attempt in range(max_retries):
            try:
                # Check if file exists to determine if we need headers
                file_exists = csv_file.exists()
                
                # Write annotation to CSV with file locking
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    # Lock the file (Unix/Linux/Mac)
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    
                    fieldnames = ['user_id', 'session_id', 'Input.audio_url', 'Answer.perceived_age_group.label', 'timestamp']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    # Write header if new file (check again after acquiring lock)
                    if not file_exists and f.tell() == 0:
                        writer.writeheader()
                        print(f"📁 Created new annotation file: {csv_file}")
                    
                    # Write annotation data
                    writer.writerow({
                        'user_id': annotation['user_id'],
                        'session_id': annotation['session_id'],
                        'Input.audio_url': annotation['audio_url'],
                        'Answer.perceived_age_group.label': annotation['selected_age'],
                        'timestamp': annotation['timestamp']
                    })
                    
                    # File lock is automatically released when file is closed
                break
                
            except (IOError, OSError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ File lock attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.2 * (attempt + 1))  # Longer exponential backoff for concurrent users
                else:
                    raise Exception(f"Failed to acquire file lock after {max_retries} attempts: {e}")

def main():
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Create threaded server for concurrent users (bind to all interfaces for deployment)
    with ThreadedAgeServer(("0.0.0.0", PORT), AnnotationHTTPRequestHandler) as httpd:
        print(f"🚀 Starting annotation server at http://localhost:{PORT}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print(f"🎯 Open: http://localhost:{PORT}/age_home.html")
        print(f"💾 Annotations will be saved to: annotations/age_split1.csv or annotations/age_split2.csv")
        print(f"⏹️  Press Ctrl+C to stop the server")
        
        # Only open browser automatically in local development
        if os.environ.get('DEVELOPMENT') == 'true':
            try:
                webbrowser.open(f'http://localhost:{PORT}/age_home.html')
                print("🌐 Opened browser automatically")
            except:
                print("❌ Could not open browser automatically")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Server stopped")

if __name__ == "__main__":
    main()