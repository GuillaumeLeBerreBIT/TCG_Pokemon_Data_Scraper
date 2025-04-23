from TCGCSVScraper import TCGCSVScraper
from VideoCreation import VideoCreation
from UploadContent import UploadContent
import argparse

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        prog='TCG Pokemon Video Generator',
        description='The program will create a one minute video of showing the Top 10 most expensive pokemon cards.',
    )
    parser.add_argument('-s', '--expansion_set',)
    parser.add_argument('-rdb', '--renew_database', action='store_true')
    args = parser.parse_args()
    
    if args.renew_database:
        # Start scraping the CSV data again. 
        scraper = TCGCSVScraper()
        scraper.parser()
    
    # Create a random video.
    video_creation = VideoCreation()
    video_path = video_creation.build_clip(expansion_name=args.expansion_set)
    
    # Upload the content to TikTok profile. 
    # content_parser = UploadContent('./video/TOP_10_EXPENSIVE_CARDS_Hidden_Legends.mp4')
    # data = content_parser.extract_upload_info()
    # content_parser.upload_to_tiktok(data['upload_url'], )