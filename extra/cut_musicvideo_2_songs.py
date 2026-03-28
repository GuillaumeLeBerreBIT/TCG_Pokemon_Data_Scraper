from tracklist import TRACKLIST
from moviepy import VideoFileClip
import os, pathlib

FULL_VIDEO = "/Users/guillaumeleberre/Downloads/YTDown.com_YouTube_Pokemon-_-Chill-Mix-LoFi-No-Copyright-Mu_Media_-B-BltVcDJE_001_1080p.mp4"
tracklist  = VideoFileClip(FULL_VIDEO)

for name, tup in TRACKLIST.items():
    
    startpos, endpos = tup[0], tup[1]
    
    song = tracklist.subclipped(startpos, endpos)
    song_name = f"CinderyLofi_{name.replace(' ', '_')}.mp4"
    
    song.write_videofile(os.path.join(os.path.dirname(__file__), '../music', song_name), codec='libx264', audio_codec='aac')