from TCGCSVScraper import TCGCSVScraper
from VideoCreation import VideoCreation
from UploadContent import UploadContentYouTube
from TCGApi import TCGApi
import argparse

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        prog='TCG Pokemon Video Generator',
        description='The program will create a one minute video of showing the Top 10 most expensive pokemon cards.',
    )
    parser.add_argument('-s', '--expansion_name',)
    parser.add_argument('-rdb', '--renew_database', action='store_true')
    args = parser.parse_args()
    
    if args.renew_database:
        # Start scraping the CSV data again. 
        scraper = TCGCSVScraper()
        scraper.parser()
        
    tcg_api = TCGApi()
    expansion, cards, expansion_image_path = tcg_api.get_cards_expansion()
    
    # if args.expansion_name: expansion = args.expansion_name
    
    # Create a random video.
    video_creation = VideoCreation(expansion=expansion.get('name', None), expansion_image_path=expansion_image_path, cards_dict=cards)
    video_path, expansion_full_name, song_name = video_creation.build_clip()
    
    # Upload the content to the YouTube API 
    # yt_parser = UploadContentYouTube(
    #     video_path=video_path, 
    #     set_expansion=expansion_full_name, 
    #     artist_song=song_name)
    # yt_parser.upload_to_yt()