from tracklist import TRACKLIST
from moviepy import VideoFileClip
import os, pathlib

FULL_VIDEO = "/Users/GuillaumeLeBerre/VisualStudioCode/Projects_Guillaume/Python_Automation/TCG_POKEMON_DATA_SCRAPER/full_music_video/Pokémon_LoFi _No_Copyright_Music_Mix_Free_DMCA.mp4"
tracklist  = VideoFileClip(FULL_VIDEO)

for name, tup in TRACKLIST.items():
    
    startpos, endpos = tup[0], tup[1]
    
    song = tracklist.subclipped(startpos, endpos)
    song_name = f"CinderyLofi_{name.replace(' ', '_')}.mp4"
    
    song.write_videofile(os.path.join(os.path.dirname(__file__), '../music', song_name), codec='libx264', audio_codec='aac')