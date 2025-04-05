import os
import requests
from bs4 import BeautifulSoup
from expansions_list import HTML
class ExpansionsScraper:
    
    def __init__(self, output_dir = "expansion_images"):
        
        self.url = "https://www.pokemon.com/"
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        self.output_dir = output_dir
        
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
    
    def retrieve_images(self):
        
        soup = BeautifulSoup(HTML, 'html.parser')
        expansion_items = soup.find_all('li', {'class': 'animating'})
        
        print(f"Found {len(expansion_items)} expansion items")
        
        image_sources = {}
        for li in expansion_items:
            img = li.find('img')
            
            if img and img.has_attr('src'):
                source = img["src"]
                alt = img['alt']
                image_sources[alt] = source
                print(f"Found image source: {source}")
            
        return image_sources
    
    def download_image(self, image_url, filename=None):
        """Download an image from a URL and save it to the output directory."""
        try:
            # Make URL absolute if it's relative
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                image_url = 'https://www.pokemon.com' + image_url
            
            # Get the image file
            response = requests.get(image_url, headers=self.headers, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Generate filename if not provided
            if not filename:
                # Extract filename from URL or create a unique one
                path = os.path.basename(image_url.split('?')[0])  # Remove query parameters
                if not path or path == '':
                    # If no filename in URL, create one based on the URL
                    path = f"expansion_{hash(image_url) % 10000}.jpg"
            else:
                path = filename
            
            # Save the image
            file_path = os.path.join(self.output_dir, path)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded: {file_path}")
            return file_path
        
        except Exception as e:
            print(f"Error downloading {image_url}: {e}")
            return None
        
    def download_images(self):
        
        image_sources = self.retrieve_images()
        
        # Download each image
        if image_sources:
            print(f"\nDownloading {len(image_sources.keys())} images...")
            
            downloaded_count = 0
            for i, (alt, source) in enumerate(image_sources.items()):
                filename = f"{alt}.jpg"
                if self.download_image(source, filename):
                    downloaded_count += 1
            
            print(f"\nDownloaded {downloaded_count} out of {len(image_sources.keys())} images successfully.")
        else:
            print("No image sources found to download.")
        
expansion_scraper = ExpansionsScraper()
expansion_scraper.download_images()