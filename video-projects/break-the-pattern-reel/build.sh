#!/bin/bash
# "Break the pattern" reel — clean professional cut (20s, 1080x1920, 30fps)
set -e
S=/tmp/claude-0/-home-user-Claude-mobile-test-/4aa42345-96bf-5298-9600-802b21be64c8/scratchpad
U=/root/.claude/uploads/4aa42345-96bf-5298-9600-802b21be64c8
I=$S/../images
P1=$U/9a458922-Untitled_Artwork.mov; P2=$U/2bc07eab-Untitled_Artwork.mov; P4=$U/edfa197e-Untitled_Artwork.mov
A=$I/1.webp; B=$I/2.jpg
DIR=$(cd "$(dirname "$0")" && pwd); O=$S/seg2; mkdir -p $O; cd $O
ENC="-r 30 -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -an"
FIT="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
# eased zoom/pan: z0 z1 cx0 cy0 cx1 cy1 frames  (smoothstep easing, 2x supersampled for smooth motion)
ez(){ local p="min(on/$7,1)"; local e="(3*pow($p,2)-2*pow($p,3))"
 echo "scale=2160:3840,zoompan=z='$1+($2-$1)*$e':x='2*($3+($5-$3)*$e)-iw/zoom/2':y='2*($4+($6-$4)*$e)-ih/zoom/2':d=1:s=1080x1920:fps=30"; }
still(){ ffmpeg -v error -y -loop 1 -framerate 30 -t $2 -i $1 -vf "$FIT,$3" $ENC -t $2 $4; }
# process clip with tracing reference removed (degrey.py)
proc(){ ffmpeg -v error -ss $2 -t $3 -i $1 -vf "setpts=PTS/$4,fps=30,$FIT" -f rawvideo -pix_fmt rgb24 - | python3 $DIR/degrey.py | \
  ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - -vf "$6" $ENC -t $5 $7; }
plain(){ ffmpeg -v error -ss $2 -t $3 -i $1 -vf "setpts=PTS/$4,fps=30,$FIT" -f rawvideo -pix_fmt rgb24 - | python3 $DIR/degrey.py --keep-grey | \
  ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - -vf "$6" $ENC -t $5 $7; }

still $A 1.8  "$(ez 1.3 1.0 540 960 540 960 54)" a1.mp4                 # open on the finished piece, settle back
proc $P1 2.2 58.3 16.2 3.6 "$(ez 1.0 1.08 540 960 540 900 108)" a2.mp4       # lettering writes itself
proc $P2 0 60 22 2.75 "$(ez 1.08 1.0 540 900 540 960 82)" a3.mp4
still $B 2.0  "$(ez 1.0 1.15 562 960 562 960 60)" a4.mp4                 # eyes artwork breather
plain $P4 30 7.5 5 1.5 "$(ez 1.15 1.25 400 500 380 470 45)" a5.mp4      # brushing the eye arc
still $A 3.2  "$(ez 2.2 2.2 540 640 540 1300 96)" a6.mp4                 # macro pan down the words
plain $P4 52 7 3.5 2.0 "$(ez 1.1 1.0 540 960 540 960 60)" a7.mp4        # blue -> red colour pass
still $B 1.6  "$(ez 1.0 1.55 562 1000 562 1000 48)" a8.mp4               # push into the frame
still $A 3.4  "$(ez 1.0 1.06 540 960 540 960 102)" a9.mp4                # hero hold

# transitions: name:duration between consecutive shots
T=(fade:0.2 fade:0.3 fade:0.2 smoothup:0.25 fade:0.2 fade:0.25 fadeblack:0.2 zoomin:0.25)
L=(1.8 3.6 2.75 2.0 1.5 3.2 2.0 1.6 3.4)
in=""; fc=""; off=0; prev="[0:v]"
for i in 0 1 2 3 4 5 6 7 8; do in="$in -i a$((i+1)).mp4"; done
for i in 0 1 2 3 4 5 6 7; do t=${T[$i]%:*}; d=${T[$i]#*:}
 off=$(python3 -c "print(round($off+${L[$i]}-$d,3))")
 fc="$fc${prev}[$((i+1)):v]xfade=transition=$t:duration=$d:offset=$off[x$i];"; prev="[x$i]"
 off=$(python3 -c "print(round($off,3))"); done
fc="$fc${prev}noise=alls=4:allf=t,vignette=PI/8,fade=t=out:st=19.6:d=0.4,format=yuv420p[v]"
ffmpeg -v error -y $in -filter_complex "$fc" -map "[v]" -r 30 -c:v libx264 -preset slow -crf 19 -maxrate 14M -bufsize 28M -profile:v high -movflags +faststart -t 20 $DIR/break-the-pattern-reel.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 $DIR/break-the-pattern-reel.mp4
