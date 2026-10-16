#!/bin/bash
# "Break the pattern" reel, cut to music.mp3 (13.0s, 4K 2160x3840, 30fps).
# While the voice speaks, the lettering writes itself, each word finishing as it is
# spoken (writing.py time-remaps the timelapses). Only when the voice stops and the
# beat hits (3.08-3.55, 6.23-6.65, 9.03-13.0) does the eye artwork come in.
set -e
S=/tmp/claude-0/-home-user-Claude-mobile-test-/4aa42345-96bf-5298-9600-802b21be64c8/scratchpad
U=/root/.claude/uploads/4aa42345-96bf-5298-9600-802b21be64c8
I=$S/../images
P1=$U/9a458922-Untitled_Artwork.mov; P2=$U/2bc07eab-Untitled_Artwork.mov; P4=$U/edfa197e-Untitled_Artwork.mov
A=$I/1.webp; B=$I/2.jpg
DIR=$(cd "$(dirname "$0")" && pwd); O=$S/seg4; mkdir -p $O; cd $O
ENC="-r 30 -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -an"
FIT="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
ez(){ local p="min(on/$7,1)"; local e="(3*pow($p,2)-2*pow($p,3))"
 echo "scale=2160:3840,zoompan=z='$1+($2-$1)*$e':x='2*($3+($5-$3)*$e)-iw/zoom/2':y='2*($4+($6-$4)*$e)-ih/zoom/2':d=1:s=1080x1920:fps=30"; }
pulse(){ echo "scale=w='trunc(1080*(1+0.07*exp(-n*0.35))/2)*2':h='trunc(1920*(1+0.07*exp(-n*0.35))/2)*2':eval=frame,crop=1080:1920"; }
still(){ ffmpeg -v error -y -loop 1 -framerate 30 -i $1 -vf "$FIT,$3" $ENC -frames:v $2 $4; }
writing(){ (cd $DIR && python3 writing.py $1 $P1 $P2) | ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - $ENC $1.mp4; }

# --- voice: the lettering writes itself; beat hits between lines: eye artwork ---
writing p1                                                                      # 0.00 voice, line 1
still $B 8 "$(ez 1.05 1.0 562 960 562 960 8),$(pulse)" h1a.mp4                  # 3.08 beat hit
still $B 7 "$(ez 2.3 2.15 614 854 614 854 7),$(pulse)" h1b.mp4                  # 3.35
writing p2                                                                      # 3.55 voice, line 2
still $B 6 "$(ez 3.4 3.2 640 600 640 600 6),$(pulse)" h2a.mp4                   # 6.23 beat hit
still $A 7 "$(ez 3.8 3.5 340 240 340 240 7),$(pulse)" h2b.mp4                   # 6.43
writing p3                                                                      # 6.65 voice, line 3
# --- beat drop 9.03: eye artwork, one shot per beat ---
still $B 12 "$(ez 1.0 1.0 562 960 562 960 12),$(pulse)" e01.mp4               # framed eyes
still $B 12 "$(ez 2.3 2.1 614 854 614 854 12),$(pulse)" e02.mp4               # the big eye
still $B 11 "$(ez 3.6 3.3 640 600 640 600 11),$(pulse)" e03.mp4               # small eye, top right
still $A 12 "$(ez 3.8 3.5 340 240 340 240 12),$(pulse)" e04.mp4               # background eye, top
still $B 12 "$(ez 1.35 1.25 562 1000 562 1000 12),$(pulse)" e05.mp4           # framed eyes
still $B 12 "$(ez 3.6 3.3 538 1248 538 1248 12),$(pulse)" e06.mp4             # small eye, bottom
still $B 11 "$(ez 3.4 3.1 800 1150 800 1150 11),$(pulse)" e07.mp4             # small eye, right
still $A 12 "$(ez 3.6 3.3 930 1680 930 1680 12),$(pulse)" e08.mp4             # background eye, bottom right
# 12.17 last beat: the final artwork, pulse again on 12.56, ends with the music
ffmpeg -v error -y -loop 1 -framerate 30 -i $A -vf "$FIT,$(ez 1.06 1.0 540 960 540 960 25),scale=w='trunc(1080*(1+0.06*exp(-n*0.35)+0.05*if(gte(n,12),exp(-(n-12)*0.35),0))/2)*2':h='trunc(1920*(1+0.06*exp(-n*0.35)+0.05*if(gte(n,12),exp(-(n-12)*0.35),0))/2)*2':eval=frame,crop=1080:1920" $ENC -frames:v 25 final.mp4

printf "file '%s'\n" p1.mp4 h1a.mp4 h1b.mp4 p2.mp4 h2a.mp4 h2b.mp4 p3.mp4 e01.mp4 e02.mp4 e03.mp4 e04.mp4 e05.mp4 e06.mp4 e07.mp4 e08.mp4 final.mp4 > list.txt
ffmpeg -v error -y -f concat -safe 0 -i list.txt -i $DIR/music.mp3 -map 0:v -map 1:a \
  -vf "scale=2160:3840:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t,vignette=PI/8,format=yuv420p" -r 30 -c:v libx264 -preset slow -crf 18 -maxrate 45M -bufsize 90M -profile:v high -level 5.1 \
  -c:a aac -b:a 192k -movflags +faststart -t 13 $DIR/break-the-pattern-reel.mp4
ffprobe -v error -show_entries stream=codec_type,duration,nb_frames -of compact $DIR/break-the-pattern-reel.mp4
