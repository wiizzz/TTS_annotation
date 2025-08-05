#!/usr/bin/env python3
"""
HTTP server for word emphasis annotation interface with server-side annotation storage.
Saves emphasis annotations securely without exposing results to annotators.
"""

import http.server
import socketserver
import webbrowser
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8003))

class EmphasisAnnotationHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
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
    
    def do_POST(self):
        """Handle POST requests for saving emphasis annotations"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/save_emphasis_annotation':
            self.handle_save_emphasis_annotation()
        else:
            self.send_error(404, "Endpoint not found")
    
    def handle_save_emphasis_annotation(self):
        """Save emphasis annotation to CSV file"""
        try:
            # Read request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            annotation = json.loads(post_data.decode('utf-8'))
            
            # Validate annotation data
            required_fields = ['user_id', 'audio_url', 'sentence', 'selected_emphasis', 'timestamp', 'session_id']
            for field in required_fields:
                if field not in annotation:
                    raise ValueError(f"Missing required field: {field}")
            
            # Save to CSV file
            self.save_emphasis_annotation_to_csv(annotation)
            
            # Send success response
            response = {"status": "success", "message": "Emphasis annotation saved successfully"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
            print(f"✅ Saved emphasis annotation: {annotation['user_id']} - '{annotation['selected_emphasis']}'")
            
        except Exception as e:
            print(f"❌ Error saving emphasis annotation: {e}")
            
            # Send error response
            response = {"status": "error", "message": str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def save_emphasis_annotation_to_csv(self, annotation):
        """Save emphasis annotation to emphasis_split1.csv file"""
        # Create annotations directory if it doesn't exist
        annotations_dir = Path('annotations')
        annotations_dir.mkdir(exist_ok=True)
        
        # Use specific filename for emphasis annotations
        csv_file = annotations_dir / 'emphasis_split1.csv'
        
        # Check if file exists to determine if we need headers
        file_exists = csv_file.exists()
        
        # Write annotation to CSV
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['user_id', 'session_id', 'audio_url', 'sentence', 'selected_emphasis', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if new file
            if not file_exists:
                writer.writeheader()
                print(f"📁 Created new emphasis annotation file: {csv_file}")
            
            # Write annotation data
            writer.writerow({
                'user_id': annotation['user_id'],
                'session_id': annotation['session_id'],
                'audio_url': annotation['audio_url'],
                'sentence': annotation['sentence'],
                'selected_emphasis': annotation['selected_emphasis'],
                'timestamp': annotation['timestamp']
            })

def main():
    # Change to the script directory
    os.chdir(Path(__file__).parent)
    
    # Create server (bind to all interfaces for deployment)
    with socketserver.TCPServer(("0.0.0.0", PORT), EmphasisAnnotationHTTPRequestHandler) as httpd:
        print(f"🚀 Starting emphasis annotation server at http://localhost:{PORT}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print(f"🗣️  Open: http://localhost:{PORT}/emphasis.html")
        print(f"💾 Emphasis annotations will be saved to: annotations/emphasis_split1.csv")
        print(f"⏹️  Press Ctrl+C to stop the server")
        
        # Only open browser automatically in local development
        if os.environ.get('DEVELOPMENT') == 'true':
            try:
                webbrowser.open(f'http://localhost:{PORT}/emphasis.html')
                print("🌐 Opened browser automatically")
            except:
                print("❌ Could not open browser automatically")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️  Server stopped")

if __name__ == "__main__":
    main()