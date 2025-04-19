from TCGCSVScraper import TCGCSVScraper
from VideoCreation import VideoCreation
from UploadContent import UploadContent

if __name__ == "__main__":
    
    # Start scraping the CSV data again. 
    # scraper = TCGCSVScraper()
    # scraper.parser()
    
    # Create a random video.
    # video_creation = VideoCreation()
    # video_path = video_creation.build_clip()
    
    # Upload the content to TikTok profile. 
    content_parser = UploadContent('./video/TOP_10_EXPENSIVE_CARDS_Hidden_Legends.mp4')
    content_parser.extract_upload_info()