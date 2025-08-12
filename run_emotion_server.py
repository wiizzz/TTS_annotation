#!/usr/bin/env python3
"""
HTTP server for emotion annotation interface with server-side annotation storage.
Saves emotion annotations securely without exposing results to annotators.
"""

import http.server
import socketserver
from socketserver import ThreadingMixIn
import webbrowser
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8001))

class ThreadedEmotionServer(ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

class EmotionAnnotationHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
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
        """Handle POST requests for saving emotion annotations"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/save_emotion_annotation':
            self.handle_save_emotion_annotation()
        else:
            self.send_error(404, "Endpoint not found")
    
    def handle_save_emotion_annotation(self):
        """Save emotion annotation to CSV file"""
        try:
            # Read request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            annotation = json.loads(post_data.decode('utf-8'))
            
            # Validate annotation data
            required_fields = ['user_id', 'audio_url', 'selected_emotion', 'timestamp', 'session_id']
            for field in required_fields:
                if field not in annotation:
                    raise ValueError(f"Missing required field: {field}")
            
            # Extract split number from the annotation data if available
            split_number = annotation.get('split', 1)
            
            # Save to CSV file
            self.save_emotion_annotation_to_csv(annotation, split_number)
            
            # Send success response
            response = {"status": "success", "message": "Emotion annotation saved successfully"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
            print(f"✅ Saved emotion annotation: {annotation['user_id']} - {annotation['selected_emotion']}")
            
        except Exception as e:
            print(f"❌ Error saving emotion annotation: {e}")
            
            # Send error response
            response = {"status": "error", "message": str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def save_emotion_annotation_to_csv(self, annotation, split_number=1):
        """Save emotion annotation to emotion_class_split*.csv file"""
        # Create annotations directory if it doesn't exist
        annotations_dir = Path('annotations')
        annotations_dir.mkdir(exist_ok=True)
        
        # Use specific filename for emotion annotations based on split
        csv_file = annotations_dir / f'emotion_class_split{split_number}.csv'
        
        # Check if file exists to determine if we need headers
        file_exists = csv_file.exists()
        
        # Write annotation to CSV
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['user_id', 'session_id', 'Input.audio_url', 'Answer.perceived_emotion.label', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if new file
            if not file_exists:
                writer.writeheader()
                print(f"📁 Created new emotion annotation file: {csv_file}")
            
            # Write annotation data
            writer.writerow({
                'user_id': annotation['user_id'],
                'session_id': annotation['session_id'],
                'Input.audio_url': annotation['audio_url'],
                'Answer.perceived_emotion.label': annotation['selected_emotion'],
                'timestamp': annotation['timestamp']
            })

def main():
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Create threaded server for concurrent users (bind to all interfaces for deployment)
    with ThreadedEmotionServer(("0.0.0.0", PORT), EmotionAnnotationHTTPRequestHandler) as httpd:
        print(f"🚀 Starting emotion annotation server at http://localhost:{PORT}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print(f"🎭 Open: http://localhost:{PORT}/emotion_home.html")
        print(f"💾 Emotion annotations will be saved to: annotations/emotion_class_split1-6.csv")
        print(f"⏹️  Press Ctrl+C to stop the server")
        
        # Only open browser automatically in local development
        if os.environ.get('DEVELOPMENT') == 'true':
            try:
                webbrowser.open(f'http://localhost:{PORT}/emotion_home.html')
                print("🌐 Opened browser automatically")
            except:
                print("❌ Could not open browser automatically")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Server stopped")

if __name__ == "__main__":
    main()