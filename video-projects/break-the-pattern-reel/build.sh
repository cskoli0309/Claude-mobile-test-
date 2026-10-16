#!/bin/bash
# "Break the pattern" reel, cut to music.mp3 (13.0s, 1080x1920, 30fps).
# Voiceover section: cuts on the accent hits. Drop at 9.03s: a cut on every beat (~0.3925s).
set -e
S=/tmp/claude-0/-home-user-Claude-mobile-test-/4aa42345-96bf-5298-9600-802b21be64c8/scratchpad
U=/root/.claude/uploads/4aa42345-96bf-5298-9600-802b21be64c8
I=$S/../images
P1=$U/9a458922-Untitled_Artwork.mov; P2=$U/2bc07eab-Untitled_Artwork.mov; P4=$U/edfa197e-Untitled_Artwork.mov
A=$I/1.webp; B=$I/2.jpg
DIR=$(cd "$(dirname "$0")" && pwd); O=$S/seg3; mkdir -p $O; cd $O
ENC="-r 30 -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -an"
FIT="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
# eased zoom/pan: z0 z1 cx0 cy0 cx1 cy1 frames
ez(){ local p="min(on/$7,1)"; local e="(3*pow($p,2)-2*pow($p,3))"
 echo "scale=2160:3840,zoompan=z='$1+($2-$1)*$e':x='2*($3+($5-$3)*$e)-iw/zoom/2':y='2*($4+($6-$4)*$e)-ih/zoom/2':d=1:s=1080x1920:fps=30"; }
# beat pulse: scale bump that decays, at frame 0 (+ optional second frame)
pulse(){ local k="1+0.07*exp(-n*0.35)${1:+ +0.07*if(gte(n,$1),exp(-(n-$1)*0.35),0)}"
 echo "scale=w='trunc(1080*($k)/2)*2':h='trunc(1920*($k)/2)*2':eval=frame,crop=1080:1920"; }
still(){ ffmpeg -v error -y -loop 1 -framerate 30 -i $1 -vf "$FIT,$3" $ENC -frames:v $2 $4; }
proc(){ ffmpeg -v error -ss $2 -t $3 -i $1 -vf "setpts=PTS/$4,fps=30,$FIT" -f rawvideo -pix_fmt rgb24 - | python3 $DIR/degrey.py $8 | \
  ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - -vf "$6" $ENC -frames:v $5 $7; }
word(){ still $A $3 "$(ez 2.5 2.35 $1 $2 $1 $2 $3),$(pulse)" $4; }

# --- voiceover section ---
still $A 31 "$(ez 1.35 1.0 540 960 540 960 31)" c01.mp4                       # 0.00 hook: finished piece
proc $P1 2.2 58.3 29 60 "$(ez 1.0 1.06 540 960 540 900 60)" c02.mp4           # 1.03 lettering writes itself
proc $P2 0 40 35 34 "$(ez 1.06 1.0 540 900 540 960 34),$(pulse)" c03.mp4      # 3.04 hit
still $B 46 "$(ez 1.0 1.12 562 960 562 960 46),$(pulse)" c04.mp4              # 4.18 eyes artwork
proc $P4 30 7.5 15 15 "$(ez 1.15 1.25 400 500 380 470 15),$(pulse)" c05.mp4 --keep-grey  # 5.69 eye arc
still $A 47 "$(ez 2.2 2.2 540 640 540 1300 47),$(pulse)" c06.mp4              # 6.20 burst: pan down the words
proc $P4 52 7 6.4 33 "$(ez 1.0 1.1 540 960 540 960 33)" c07.mp4 --keep-grey  # 7.77 blue->red, tension
still $B 5 "$(ez 1.0 1.6 562 1000 562 1000 5)" c08.mp4                        # 8.85 whoosh into the drop
# --- drop: one shot per beat ---
still $A 12 "$(ez 1.0 1.0 540 960 540 960 12),$(pulse)" c09.mp4               # 9.03
word 540 690 12 c10.mp4                                                        # Break
word 560 905 11 c11.mp4                                                        # today
still $B 12 "$(ez 1.2 1.25 562 1000 562 1000 12),$(pulse)" c12.mp4
word 470 1085 12 c13.mp4                                                       # loop
word 520 1290 12 c14.mp4                                                       # tomorrow
proc $P2 30 30 82 11 "$(pulse)" c15.mp4
still $B 12 "$(ez 1.5 1.6 562 1000 562 1000 12),$(pulse)" c16.mp4
still $A 25 "$(ez 1.08 1.0 540 960 540 960 25),$(pulse 12)" c17.mp4           # 12.17 hero, ends with the music

printf "file '%s'\n" c01.mp4 c02.mp4 c03.mp4 c04.mp4 c05.mp4 c06.mp4 c07.mp4 c08.mp4 c09.mp4 c10.mp4 c11.mp4 c12.mp4 c13.mp4 c14.mp4 c15.mp4 c16.mp4 c17.mp4 > list.txt
ffmpeg -v error -y -f concat -safe 0 -i list.txt -i $DIR/music.mp3 -map 0:v -map 1:a \
  -vf "noise=alls=4:allf=t,vignette=PI/8,format=yuv420p" -r 30 -c:v libx264 -preset slow -crf 19 -maxrate 14M -bufsize 28M -profile:v high \
  -c:a aac -b:a 192k -movflags +faststart -t 13 $DIR/break-the-pattern-reel.mp4
ffprobe -v error -show_entries stream=codec_type,duration,nb_frames -of compact $DIR/break-the-pattern-reel.mp4
